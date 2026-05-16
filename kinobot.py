import os
import sqlite3
import threading
from flask import Flask
import telebot
from telebot import types

# Render uchun Web Server (Bot 24/7 yoniq turishi uchun)
app = Flask('')

@app.route('/')
def home():
    return "Kino Bot Yoniq!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Botni sozlash
TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# 🛠️ ASOSIY SOZLANMA: 
# Quyidagi 123456789 raqami o'rniga o'zingizning Telegram ID raqamingizni yozing!
CHIEF_ADMIN = 7180864511  

# Ma'lumotlar bazasini yaratish va sozlash
def init_db():
    conn = sqlite3.connect("kinobot.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS movies (code TEXT PRIMARY KEY, file_id TEXT, name TEXT, format TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS channels (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, link TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Adminlarni tekshirish funksiyasi
def is_admin(user_id):
    if user_id == CHIEF_ADMIN:
        return True
    conn = sqlite3.connect("kinobot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res is not None

# Majburiy a'zolikni tekshirish funksiyasi (Barcha kanallarni tekshiradi)
def check_sub(user_id):
    conn = sqlite3.connect("kinobot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM channels")
    channels = cursor.fetchall()
    conn.close()
    
    if not channels:
        return True  # Agar bazaga hali kanal qo'shilmagan bo'lsa, hamma o'ta oladi

    for channel in channels:
        try:
            status = bot.get_chat_member(channel[0], user_id).status
            if status not in ['member', 'administrator', 'creator']:
                return False
        except Exception:
            # Agar bot kanalda admin bo'lmasa yoki kanal topilmasa, bu kanalni o'tkazib yuboradi
            continue
    return True

# /start buyrug'i
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    
    # Bazaga foydalanuvchini qo'shish va adminga xabar berish
    conn = sqlite3.connect("kinobot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        try:
            bot.send_message(CHIEF_ADMIN, f"🆕 Yangi foydalanuvchi qo'shildi!\nID: `{user_id}`\nIsm: {message.from_user.first_name}", parse_mode="Markdown")
        except:
            pass
    conn.close()

    # Majburiy a'zolikni tekshirish
    if not check_sub(user_id):
        conn = sqlite3.connect("kinobot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT username, link FROM channels")
        channels = cursor.fetchall()
        conn.close()

        markup = types.InlineKeyboardMarkup()
        for i, channel in enumerate(channels, 1):
            markup.add(types.InlineKeyboardButton(text=f"{i}-kanalga obuna bo'lish 📢", url=channel[1]))
        markup.add(types.InlineKeyboardButton(text="Tekshirish ✅", callback_data="check_subscription"))
        
        bot.send_message(user_id, "Botdan foydalanish uchun quyidagi kanallarimizga a'zo bo'ling! 👇", reply_markup=markup)
        return

    # Admin yoki foydalanuvchi menyusi
    if is_admin(user_id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🎬 Kino qo'shish", "📊 Statistika")
        markup.add("📢 Reklama yuborish", "📢 Kanallarni boshqarish")
        markup.add("➕ Admin qo'shish")
        bot.send_message(user_id, "👨‍💻 Xush kelibsiz Admin! Kerakli bo'limni tanlang:", reply_markup=markup)
    else:
        bot.send_message(user_id, "🍿 Salom! Kino ko'rish uchun kino kodini yoki nomini yuboring.")

# Obuna tekshirish Callback
@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def check_callback(call):
    user_id = call.from_user.id
    if check_sub(user_id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        start_cmd(call)
    else:
        bot.answer_callback_query(call.id, "Siz hali barcha kanallarga a'zo bo'lmadingiz! ❌", show_alert=True)

# Admin: Kanallarni boshqarish paneli
@bot.message_handler(func=lambda m: m.text == "📢 Kanallarni boshqarish" and is_admin(m.from_user.id))
def manage_channels(message):
    conn = sqlite3.connect("kinobot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM channels")
    channels = cursor.fetchall()
    conn.close()

    text = "📢 **Hozirgi majburiy kanallar ro'yxati:**\n\n"
    if not channels:
        text += "Hozircha kanallar qo'shilmagan."
    for ch in channels:
        text += f"🆔 {ch[0]} | {ch[1]}\n"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Kanal qo'shish", "❌ Kanalni o'chirish")
    markup.add("⬅️ Orqaga")
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "⬅️ Orqaga" and is_admin(m.from_user.id))
def back_to_menu(message):
    start_cmd(message)

# Admin: Kanal qo'shish boshlanishi
@bot.message_handler(func=lambda m: m.text == "➕ Kanal qo'shish" and is_admin(m.from_user.id))
def add_channel_start(message):
    msg = bot.reply_to(message, "Kanal userneymini yuboring (Masalan: @yangi_kinolar_dunyosi):")
    bot.register_next_step_handler(msg, add_channel_link)

def add_channel_link(message):
    username = message.text.strip()
    if not username.startswith("@"):
        bot.reply_to(message, "Xato! Username @ belgisi bilan boshlanishi kerak. Qaytadan boshlang.")
        return
    msg = bot.reply_to(message, "Endi kanalning to'liq ssilkasi (linki)ni yuboring (Masalan: https://t.me/...):")
    bot.register_next_step_handler(msg, add_channel_save, username)

def add_channel_save(message, username):
    link = message.text.strip()
    conn = sqlite3.connect("kinobot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO channels (username, link) VALUES (?, ?)", (username, link))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"✅ {username} kanali muvaffaqiyatli majburiy obunalar ro'yxatiga qo'shildi!")

# Admin: Kanalni o'chirish
@bot.message_handler(func=lambda m: m.text == "❌ Kanalni o'chirish" and is_admin(m.from_user.id))
def delete_channel_start(message):
    msg = bot.reply_to(message, "O'chirmoqchi bo'lgan kanalingizning 🆔 raqamini yuboring (Ro'yxatda yozilgan raqam):")
    bot.register_next_step_handler(msg, delete_channel_save)

def delete_channel_save(message):
    if not message.text.isdigit():
        bot.reply_to(message, "Xato! Faqat ID raqamini yuboring.")
        return
    ch_id = int(message.text)
    conn = sqlite3.connect("kinobot.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM channels WHERE id = ?", (ch_id,))
    conn.commit()
    conn.close()
    bot.reply_to(message, "✅ Kanal majburiy obunalar ro'yxatidan o'chirildi.")

# Admin: Statistika
@bot.message_handler(func=lambda m: m.text == "📊 Statistika" and is_admin(m.from_user.id))
def stat_cmd(message):
    conn = sqlite3.connect("kinobot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM movies")
    movies_count = cursor.fetchone()[0]
    conn.close()
    bot.reply_to(message, f"📊 **Bot Statistikasi:**\n\n👤 Foydalanuvchilar: {users_count} ta\n🎬 Yuklangan kinolar: {movies_count} ta", parse_mode="Markdown")

# Admin: Admin qo'shish
@bot.message_handler(func=lambda m: m.text == "➕ Admin qo'shish" and is_admin(m.from_user.id))
def add_admin_start(message):
    msg = bot.reply_to(message, "Yangi admin Telegram ID raqamini yuboring:")
    bot.register_next_step_handler(msg, add_admin_save)

def add_admin_save(message):
    if not message.text.isdigit():
        bot.reply_to(message, "Xato! ID faqat raqamlardan iborat bo'lishi kerak.")
        return
    new_admin_id = int(message.text)
    conn = sqlite3.connect("kinobot.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO admins (user_id) VALUES (?)", (new_admin_id,))
        conn.commit()
        bot.reply_to(message, f"✅ ID: {new_admin_id} muvaffaqiyatli admin qilib tayinlandi!", parse_mode="Markdown")
    except:
        bot.reply_to(message, "Bu foydalanuvchi allaqachon admin.")
    conn.close()

# Admin: Reklama tarqatish
@bot.message_handler(func=lambda m: m.text == "📢 Reklama yuborish" and is_admin(m.from_user.id))
def broadcast_start(message):
    msg = bot.reply_to(message, "Barcha foydalanuvchilarga yuboriladigan reklama matni yoki rasmini yuboring:")
    bot.register_next_step_handler(msg, broadcast_send)

def broadcast_send(message):
    conn = sqlite3.connect("kinobot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    
    bot.send_message(message.chat.id, f"📢 Reklama tarqatish boshlandi... ({len(users)} ta odamga)")
    success = 0
    for user in users:
        try:
            bot.copy_message(chat_id=user[0], from_chat_id=message.chat.id, message_id=message.message_id)
            success += 1
        except:
            pass
    bot.send_message(message.chat.id, f"✅ Reklama yakunlandi.\nMuvaffaqiyatli yetkazildi: {success} ta foydalanuvchiga.")

# Admin: Kino qo'shish bosqichlari
@bot.message_handler(func=lambda m: m.text == "🎬 Kino qo'shish" and is_admin(m.from_user.id))
def add_movie_start(message):
    msg = bot.reply_to(message, "1️⃣ Kino faylini (Video shaklida) yuboring:")
    bot.register_next_step_handler(msg, process_movie_file)

def process_movie_file(message):
    if message.content_type != 'video':
        bot.reply_to(message, "Xato! Iltimos video fayl yuboring. Qaytadan boshlang.")
        return
    file_id = message.video.file_id
    msg = bot.reply_to(message, "2️⃣ Kino nomini yozing:")
    bot.register_next_step_handler(msg, process_movie_name, file_id)

def process_movie_name(message, file_id):
    movie_name = message.text
    msg = bot.reply_to(message, "3️⃣ Kino formatini kiriting (Masalan: HD, 720p):")
    bot.register_next_step_handler(msg, process_movie_format, file_id, movie_name)

def process_movie_format(message, file_id, movie_name):
    movie_format = message.text
    msg = bot.reply_to(message, "4️⃣ Kino uchun maxsus KOD yarating (Faqat raqam yoki so'z):")
    bot.register_next_step_handler(msg, process_movie_code, file_id, movie_name, movie_format)

def process_movie_code(message, file_id, movie_name, movie_format):
    movie_code = message.text.strip()
    conn = sqlite3.connect("kinobot.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO movies (code, file_id, name, format) VALUES (?, ?, ?, ?)", 
                       (movie_code, file_id, movie_name, movie_format))
        conn.commit()
        bot.reply_to(message, f"🎉 Kino muvaffaqiyatli bazaga qo'shildi!\n🔑 Kino kodi: `{movie_code}`", parse_mode="Markdown")
    except sqlite3.IntegrityError:
        bot.reply_to(message, "❌ Bu kod band! Boshqa kod yozib qaytadan urinib ko'ring.")
    conn.close()

# Foydalanuvchilar uchun qidiruv tizimi
@bot.message_handler(func=lambda message: True)
def search_movie(message):
    user_id = message.from_user.id
    if not check_sub(user_id):
        start_cmd(message)
        return

    search_query = message.text.strip()
    bot_info = bot.get_me()
    bot_username = f"@{bot_info.username}"

    # Bazadan oxirgi qo'shilgan kanalni otpisaniyaga chiqarish uchun olish
    conn = sqlite3.connect("kinobot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM channels ORDER BY id DESC LIMIT 1")
    main_channel_res = cursor.fetchone()
    main_channel = main_channel_res[0] if main_channel_res else "@Kanal_sozlangan"
# Qidiruv logikasi (Kod yoki Ism orqali)
    cursor.execute("SELECT file_id, name, format FROM movies WHERE code = ?", (search_query,))
    res = cursor.fetchone()
    if res is None:
        cursor.execute("SELECT file_id, name, format FROM movies WHERE name LIKE ?", (f"%{search_query}%",))
        res = cursor.fetchone()
    conn.close()

    if res:
        file_id, name, movie_format = res
        
        # SIZ AYTGAN AVTOMATIK TAYYOR TAVSIF (OTPISANIYA)
        caption_text = (
            f"🎬 Kino nomi: {name}\n"
            f"📀 Formati: {movie_format}\n\n"
            f"📢 Rasmiy kanal: {main_channel}\n"
            f"🤖 Bizning bot: {bot_username}"
        )
        bot.send_video(message.chat.id, video=file_id, caption=caption_text, parse_mode="Markdown")
    else:
        bot.reply_to(message, "😔 Bunday kod yoki nom bilan kino topilmadi. Qaytadan tekshirib ko'ring.")

if __name__ == "__main__":
    t = threading.Thread(target=run_server)
    t.start()
    print("Kino bot ishga tushdi...")
    bot.infinity_polling()
