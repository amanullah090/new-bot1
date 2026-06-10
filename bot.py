import os
import time
import threading

import telebot
from telebot import types
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from werkzeug.utils import secure_filename

from database import (
    init_db, add_user, get_all_users, get_user_count, get_today_joined,
    get_all_buttons, add_button, update_button, delete_button,
    get_button_by_key, check_admin_password, update_admin_password,
    make_premium, remove_premium,
)

# ========== কনফিগারেশন ==========
TOKEN = "8814546620:AAGP8JRif1Qe3b9vkU0bKZPrIK19uTfSA-U"
ADMIN_ID = 8556230749

BOT_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.join(BOT_DIR, "photos")
os.makedirs(PHOTOS_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ========== ডাটাবেস ইনিশিয়ালাইজ ==========
init_db()

# ========== বট ইনিশিয়ালাইজ ==========
bot = telebot.TeleBot(TOKEN)

# ========== ডায়নামিক কিবোর্ড তৈরি ==========
def create_dynamic_keyboard(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = get_all_buttons()
    
    row = []
    for btn in buttons:
        if btn[7] == 1:  # is_active
            btn_text = f"{btn[3]} {btn[2]}".strip()
            row.append(types.KeyboardButton(btn_text))
            if len(row) == 2:
                markup.row(*row)
                row = []
    if row:
        markup.row(*row)
    
    if chat_id == ADMIN_ID:
        markup.row(types.KeyboardButton("👑 অ্যাডমিন প্যানেল 👑"))
        markup.row(types.KeyboardButton("🔐 পাসওয়ার্ড পরিবর্তন 🔐"))
    
    return markup

def update_all_keyboards():
    users = get_all_users()
    for user in users:
        try:
            markup = create_dynamic_keyboard(user[1])
            bot.send_message(user[1], "🔄 কিবোর্ড আপডেট হয়েছে!", reply_markup=markup)
        except:
            pass

# ========== বট কমান্ড ==========
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    username = message.chat.username or ""
    first_name = message.chat.first_name or ""
    add_user(chat_id, username, first_name)
    
    markup = create_dynamic_keyboard(chat_id)
    welcome = "🔥 *Welcome To My Bot* 🔥\n\nআমি একটি স্মার্ট বট। নিচের বাটনগুলোর মাধ্যমে কন্টেন্ট পেতে পারেন।"
    
    if chat_id == ADMIN_ID:
        welcome += "\n\n👑 আপনি অ্যাডমিন\nনিচে অ্যাডমিন প্যানেল ও পাসওয়ার্ড পরিবর্তনের বাটন পাবেন।"
    
    bot.send_message(chat_id, welcome, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "❌ আপনি অ্যাডমিন নন!")
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📊 ওয়েব প্যানেল", url="https://new-bot1-1.onrender.com"))
    markup.add(types.InlineKeyboardButton("➕ বাটন যোগ", callback_data="add_btn"))
    markup.add(types.InlineKeyboardButton("📋 বাটন লিস্ট", callback_data="list_btn"))
    markup.add(types.InlineKeyboardButton("📢 ব্রডকাস্ট", callback_data="broadcast_btn"))
    
    bot.send_message(ADMIN_ID, "👑 *অ্যাডমিন প্যানেল*\n\nনিচের অপশন বেছে নিন:", 
                     reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def admin_callback(call):
    if call.message.chat.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "অনুমতি নেই!")
        return
    
    if call.data == "add_btn":
        msg = bot.send_message(ADMIN_ID, "📝 *বাটনের কী লিখুন (ইংরেজি, স্পেস ছাড়া):*", parse_mode='Markdown')
        bot.register_next_step_handler(msg, add_btn_key)
    
    elif call.data == "list_btn":
        buttons = get_all_buttons()
        if not buttons:
            bot.send_message(ADMIN_ID, "❌ কোনো বাটন নেই!")
            return
        text = "📋 *বাটনের তালিকা*\n\n"
        for btn in buttons:
            status = "✅" if btn[7] == 1 else "❌"
            text += f"{status} `{btn[1]}` → {btn[3]} {btn[2]}\n"
        bot.send_message(ADMIN_ID, text, parse_mode='Markdown')
    
    elif call.data == "broadcast_btn":
        msg = bot.send_message(ADMIN_ID, "📢 *ব্রডকাস্ট মেসেজ লিখুন:*", parse_mode='Markdown')
        bot.register_next_step_handler(msg, broadcast_send)

def add_btn_key(message):
    key = message.text.strip().replace(" ", "_")
    msg = bot.send_message(ADMIN_ID, "✏️ *বাটনের টেক্সট লিখুন:*", parse_mode='Markdown')
    bot.register_next_step_handler(msg, lambda m: add_btn_text(m, key))

def add_btn_text(message, key):
    text = message.text.strip()
    msg = bot.send_message(ADMIN_ID, "😊 *ইমোজি দিন (যেমন: 🔥):*", parse_mode='Markdown')
    bot.register_next_step_handler(msg, lambda m: add_btn_emoji(m, key, text))

def add_btn_emoji(message, key, text):
    emoji = message.text.strip() or "🔘"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📝 টেক্সট", callback_data=f"type_text_{key}_{text}_{emoji}"))
    markup.add(types.InlineKeyboardButton("🖼️ ফটো", callback_data=f"type_photo_{key}_{text}_{emoji}"))
    bot.send_message(ADMIN_ID, "📤 *রেসপন্স টাইপ সিলেক্ট করুন:*", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith("type_"))
def add_btn_type(call):
    parts = call.data.split("_")
    resp_type = parts[1]
    key = parts[2]
    text = parts[3]
    emoji = parts[4]
    
    if resp_type == "text":
        msg = bot.send_message(ADMIN_ID, "✏️ *রেসপন্স টেক্সট লিখুন:*", parse_mode='Markdown')
        bot.register_next_step_handler(msg, lambda m: save_text_btn(m, key, text, emoji))
    else:
        msg = bot.send_message(ADMIN_ID, "🖼️ *ফটো পাঠান (caption দিতে পারবেন):*", parse_mode='Markdown')
        bot.register_next_step_handler(msg, lambda m: save_photo_btn(m, key, text, emoji))

def save_text_btn(message, key, text, emoji):
    add_button(key, text, emoji, 'text', message.text.strip(), '', '', 999)
    bot.send_message(ADMIN_ID, f"✅ বাটন যোগ হয়েছে!\n`{emoji} {text}`", parse_mode='Markdown')
    update_all_keyboards()

def save_photo_btn(message, key, text, emoji):
    if message.photo:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        filename = f"{key}.jpg"
        photo_path = os.path.join(PHOTOS_DIR, filename)
        with open(photo_path, 'wb') as f:
            f.write(downloaded_file)
        caption = message.caption or ""
        add_button(key, text, emoji, 'photo', '', photo_path, caption, 999)
        bot.send_message(ADMIN_ID, f"✅ বাটন যোগ হয়েছে (ফটো সহ)!\n`{emoji} {text}`", parse_mode='Markdown')
        update_all_keyboards()
    else:
        bot.send_message(ADMIN_ID, "❌ ফটো পাঠাননি! আবার চেষ্টা করুন।")

def broadcast_send(message):
    users = get_all_users()
    success, fail = 0, 0
    bot.send_message(ADMIN_ID, f"⏳ ব্রডকাস্ট শুরু... {len(users)} জন ইউজার পাবে")
    
    for user in users:
        try:
            bot.send_message(user[1], f"📢 *ব্রডকাস্ট*\n\n{message.text}", parse_mode='Markdown')
            success += 1
        except:
            fail += 1
        time.sleep(0.05)
    
    bot.send_message(ADMIN_ID, f"✅ ব্রডকাস্ট শেষ!\nসফল: {success}\nব্যর্থ: {fail}")

@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(message, "📖 সাহায্য:\n/start - বট চালু\n/myid - আপনার আইডি\n/admin - অ্যাডমিন প্যানেল")

@bot.message_handler(commands=['myid'])
def myid_command(message):
    bot.reply_to(message, f"🆔 আপনার আইডি: `{message.chat.id}`", parse_mode='Markdown')

def admin_panel_msg(message):
    if message.chat.id != ADMIN_ID:
        return
    panel_text = f"""👑 অ্যাডমিন প্যানেল

🌐 ওয়েব প্যানেল: https://new-bot1-1.onrender.com
🔑 পাসওয়ার্ড: admin123

💡 পাসওয়ার্ড পরিবর্তন করতে নিচের বাটন ব্যবহার করুন।"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🌐 প্যানেল ওপেন করুন", url="https://new-bot1-1.onrender.com"))
    bot.send_message(message.chat.id, panel_text, reply_markup=markup)

def change_pass_start(message):
    if message.chat.id != ADMIN_ID:
        return
    msg = bot.reply_to(message, "🔐 নতুন পাসওয়ার্ড লিখুন (৪+ অক্ষর):")
    bot.register_next_step_handler(msg, change_pass_process)

def change_pass_process(message):
    if message.chat.id != ADMIN_ID:
        return
    new_pass = message.text.strip()
    if len(new_pass) < 4:
        bot.reply_to(message, "❌ পাসওয়ার্ড কমপক্ষে ৪ অক্ষরের হতে হবে!")
        return
    update_admin_password(new_pass)
    bot.reply_to(message, f"✅ পাসওয়ার্ড পরিবর্তন হয়েছে!\n🔑 নতুন পাসওয়ার্ড: `{new_pass}`", parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    chat_id = message.chat.id
    text = message.text
    
    if chat_id == ADMIN_ID:
        if text == "👑 অ্যাডমিন প্যানেল 👑":
            admin_panel_msg(message)
            return
        if text == "🔐 পাসওয়ার্ড পরিবর্তন 🔐":
            change_pass_start(message)
            return
    
    buttons = get_all_buttons()
    for btn in buttons:
        btn_display = f"{btn[3]} {btn[2]}".strip()
        if text == btn_display and btn[7] == 1:
            if btn[4] == 'photo':
                photo_path = btn[6]
                caption = btn[8] or ""
                try:
                    if photo_path and os.path.exists(photo_path):
                        with open(photo_path, "rb") as photo:
                            bot.send_photo(chat_id, photo, caption=caption)
                    else:
                        bot.send_message(chat_id, caption or "কন্টেন্ট পাওয়া যায়নি।")
                except:
                    bot.send_message(chat_id, "❌ ফটো পাঠাতে সমস্যা হয়েছে।")
            else:
                bot.send_message(chat_id, btn[5] or "")
            return
    
    bot.reply_to(message, "❓ দয়া করে নিচের বাটনগুলোর একটি সিলেক্ট করুন।")

# ========== Flask ওয়েব অ্যাপ ==========
app = Flask(__name__, template_folder=os.path.join(BOT_DIR, "templates"))
app.secret_key = "your_secret_key_here_change_it"

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if check_admin_password(request.form['password']):
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="ভুল পাসওয়ার্ড!")
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    all_buttons = get_all_buttons()
    return render_template('dashboard.html',
        total_users=get_user_count(),
        today_joined=get_today_joined(),
        premium_users=sum(1 for u in get_all_users() if u[5] == 1),
        active_buttons=sum(1 for b in all_buttons if b[7] == 1),
        total_buttons=len(all_buttons))

@app.route('/users')
@login_required
def users_list():
    return render_template('users.html', users=get_all_users(), total_users=get_user_count())

@app.route('/make_premium', methods=['POST'])
@login_required
def make_premium_route():
    make_premium(int(request.form['chat_id']))
    return redirect(url_for('users_list'))

@app.route('/remove_premium', methods=['POST'])
@login_required
def remove_premium_route():
    remove_premium(int(request.form['chat_id']))
    return redirect(url_for('users_list'))

@app.route('/buttons')
@login_required
def buttons_list():
    return render_template('buttons.html', buttons=get_all_buttons())

@app.route('/add_button_page', methods=['GET', 'POST'])
@login_required
def add_button_page():
    if request.method == 'POST':
        photo_path = ""
        
        if request.form.get('response_type') == 'photo':
            file = request.files.get('photo')
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                photo_path = os.path.join(PHOTOS_DIR, filename)
                file.save(photo_path)
        
        add_button(
            request.form['key'],
            request.form['text'],
            request.form.get('emoji', '🔘'),
            request.form.get('response_type', 'text'),
            request.form.get('response_text', ''),
            photo_path,
            request.form.get('caption', ''),
            int(request.form.get('sort_order', 999))
        )
        update_all_keyboards()
        return redirect(url_for('buttons_list'))
    
    return render_template('add_button.html')

@app.route('/edit_button/<key>', methods=['GET', 'POST'])
@login_required
def edit_button_route(key):
    button = get_button_by_key(key)
    if not button:
        return "বাটন খুঁজে পাওয়া যায়নি", 404
    
    if request.method == 'POST':
        photo_path = button[6]
        
        if request.form.get('response_type') == 'photo':
            file = request.files.get('photo')
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                photo_path = os.path.join(PHOTOS_DIR, filename)
                file.save(photo_path)
        
        update_button(
            key,
            request.form.get('text'),
            request.form.get('emoji', '🔘'),
            request.form.get('response_type'),
            request.form.get('response_text', ''),
            photo_path,
            request.form.get('caption', ''),
            1 if request.form.get('is_active') == 'on' else 0
        )
        update_all_keyboards()
        return redirect(url_for('buttons_list'))
    
    return render_template('edit_button.html', button=button)

@app.route('/delete_button/<key>')
@login_required
def delete_button_route(key):
    btn = get_button_by_key(key)
    if btn and btn[6] and os.path.exists(btn[6]):
        try:
            os.remove(btn[6])
        except:
            pass
    delete_button(key)
    update_all_keyboards()
    return redirect(url_for('buttons_list'))

@app.route('/photo/<filename>')
@login_required
def serve_photo(filename):
    return send_from_directory(PHOTOS_DIR, filename)

@app.route('/broadcast', methods=['GET', 'POST'])
@login_required
def broadcast():
    result = None
    if request.method == 'POST':
        msg_text = request.form.get('message', '').strip()
        if msg_text:
            users = get_all_users()
            success, fail = 0, 0
            for user in users:
                try:
                    bot.send_message(user[1], f"📢 ব্রডকাস্ট:\n\n{msg_text}")
                    success += 1
                except:
                    fail += 1
            result = f"✅ সফল: {success}, ব্যর্থ: {fail}"
    return render_template('broadcast.html', total_users=get_user_count(), result=result)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# ========== মেইন ফাংশন ==========
def run_bot():
    print("🤖 Bot is starting...")
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.infinity_polling(timeout=10, long_polling_timeout=10)
    except Exception as e:
        print(f"Bot Error: {e}")

def run_web():
    port = int(os.environ.get("PORT", 5000))
    print(f"🌐 Web Dashboard starting on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    print("🚀 Starting Telegram Bot + Web Dashboard...")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print("🌐 Web Panel: https://new-bot1-1.onrender.com")
    print("🔑 Password: admin123")
    
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    time.sleep(2)
    run_web()
