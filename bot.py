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
    get_admin_password, make_premium, remove_premium,
)

# ── Config ─────────────────────────────────────────────────────────────────

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("TELEGRAM_ADMIN_ID", "0"))
BOT_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.join(BOT_DIR, "photos")
os.makedirs(PHOTOS_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Bot ────────────────────────────────────────────────────────────────────

if not TOKEN:
    print("⚠️  TELEGRAM_BOT_TOKEN পাওয়া যায়নি। বট শুরু হবে না।")
    bot = None
else:
    bot = telebot.TeleBot(TOKEN)

init_db()


def create_dynamic_keyboard(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    buttons = get_all_buttons()
    for btn in buttons:
        if btn[7] == 1:
            btn_text = f"{btn[3]} {btn[2]}".strip()
            markup.add(types.KeyboardButton(btn_text))
    if ADMIN_ID and message.chat.id == ADMIN_ID:
        markup.add(types.KeyboardButton("👑 অ্যাডমিন প্যানেল 👑"))
        markup.add(types.KeyboardButton("🔐 পাসওয়ার্ড পরিবর্তন 🔐"))
    return markup


if bot:
    @bot.message_handler(commands=["start"])
    def start(message):
        chat_id = message.chat.id
        username = message.chat.username
        first_name = message.chat.first_name
        add_user(chat_id, username, first_name)
        markup = create_dynamic_keyboard(message)
        welcome = "🔥 Welcome To My Bot 🔥"
        if ADMIN_ID and chat_id == ADMIN_ID:
            welcome += "\n\n👑 আপনি অ্যাডমিন\nনিচে অ্যাডমিন প্যানেল ও পাসওয়ার্ড পরিবর্তনের বাটন পাবেন।"
        bot.send_message(chat_id, welcome, reply_markup=markup)

    @bot.message_handler(commands=["admin"])
    def admin_command(message):
        if not ADMIN_ID or message.chat.id != ADMIN_ID:
            bot.reply_to(message, "❌ আপনি এই কমান্ড ব্যবহার করার অনুমতি পাননি।")
            return
        msg = bot.reply_to(message, "📢 ব্রডকাস্ট মেসেজ লিখুন:")
        bot.register_next_step_handler(msg, send_broadcast)

    def send_broadcast(message):
        if not ADMIN_ID or message.chat.id != ADMIN_ID:
            return
        users = get_all_users()
        success, fail = 0, 0
        bot.reply_to(message, f"⏳ {len(users)} জন ইউজারকে মেসেজ পাঠানো হচ্ছে...")
        for user in users:
            try:
                bot.send_message(user[1], f"📢 ব্রডকাস্ট:\n\n{message.text}")
                success += 1
            except Exception:
                fail += 1
        bot.reply_to(message, f"✅ সম্পন্ন!\nসফল: {success}\nব্যর্থ: {fail}")

    @bot.message_handler(commands=["help"])
    def help_command(message):
        help_text = (
            "📖 বটের সাহায্য\n\n"
            "/start - বট চালু করুন\n"
            "/myid - আপনার আইডি জানুন\n"
            "/admin - ব্রডকাস্ট (অ্যাডমিন)"
        )
        bot.reply_to(message, help_text)

    @bot.message_handler(commands=["myid"])
    def myid_command(message):
        bot.reply_to(message, f"🆔 আপনার টেলিগ্রাম আইডি: `{message.chat.id}`", parse_mode="Markdown")

    def admin_panel(message):
        if not ADMIN_ID or message.chat.id != ADMIN_ID:
            return
        domains = os.environ.get("REPLIT_DOMAINS", "")
        panel_url = f"https://{domains.split(',')[0]}" if domains else "http://localhost:5000"
        current_pass = get_admin_password()
        panel_text = (
            f"👑 অ্যাডমিন প্যানেল\n\n"
            f"🌐 লিংক: {panel_url}\n"
            f"🔑 পাসওয়ার্ড: {current_pass}\n\n"
            "💡 পাসওয়ার্ড পরিবর্তন করতে নিচের বাটন ব্যবহার করুন।"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🌐 প্যানেল ওপেন করুন", url=panel_url))
        bot.send_message(message.chat.id, panel_text, reply_markup=markup)

    def change_password_start(message):
        if not ADMIN_ID or message.chat.id != ADMIN_ID:
            return
        msg = bot.reply_to(message, "🔐 নতুন পাসওয়ার্ড লিখুন:\n(কমপক্ষে ৪ অক্ষর)")
        bot.register_next_step_handler(msg, change_password_process)

    def change_password_process(message):
        if not ADMIN_ID or message.chat.id != ADMIN_ID:
            return
        new_password = message.text.strip()
        if len(new_password) < 4:
            bot.reply_to(message, "❌ পাসওয়ার্ড কমপক্ষে ৪ অক্ষরের হতে হবে!")
            return
        update_admin_password(new_password)
        bot.reply_to(message, f"✅ পাসওয়ার্ড পরিবর্তন হয়েছে!\n🔑 নতুন পাসওয়ার্ড: `{new_password}`", parse_mode="Markdown")

    @bot.message_handler(func=lambda message: True)
    def handle_buttons(message):
        chat_id = message.chat.id
        text = message.text

        if ADMIN_ID and chat_id == ADMIN_ID:
            if text == "👑 অ্যাডমিন প্যানেল 👑":
                admin_panel(message)
                return
            if text == "🔐 পাসওয়ার্ড পরিবর্তন 🔐":
                change_password_start(message)
                return

        buttons = get_all_buttons()
        for btn in buttons:
            btn_display = f"{btn[3]} {btn[2]}".strip()
            if text == btn_display and btn[7] == 1:
                if btn[4] == "photo":
                    photo_path = btn[6]
                    caption = btn[8] or ""
                    try:
                        if photo_path and os.path.exists(photo_path):
                            with open(photo_path, "rb") as photo:
                                bot.send_photo(chat_id, photo, caption=caption)
                        else:
                            bot.send_message(chat_id, caption or "কন্টেন্ট পাওয়া যায়নি।")
                    except Exception as e:
                        bot.send_message(chat_id, f"❌ ফটো পাঠাতে সমস্যা হয়েছে।")
                else:
                    bot.send_message(chat_id, btn[5] or "")
                return

        bot.reply_to(message, "❓ দয়া করে নিচের বাটনগুলোর একটি সিলেক্ট করুন।")


# ── Flask web app ──────────────────────────────────────────────────────────

app = Flask(__name__, template_folder=os.path.join(BOT_DIR, "templates"))
app.secret_key = os.environ.get("SESSION_SECRET", "change-this-secret-key")


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/")
def home():
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if check_admin_password(request.form["password"]):
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="ভুল পাসওয়ার্ড! আবার চেষ্টা করুন।")
    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    all_buttons = get_all_buttons()
    return render_template(
        "dashboard.html",
        total_users=get_user_count(),
        today_joined=get_today_joined(),
        premium_users=sum(1 for u in get_all_users() if u[5] == 1),
        active_buttons=sum(1 for b in all_buttons if b[7] == 1),
        total_buttons=len(all_buttons),
    )


@app.route("/users")
@login_required
def users_list():
    users = get_all_users()
    return render_template("users.html", users=users, total_users=len(users))


@app.route("/make_premium", methods=["POST"])
@login_required
def make_premium_route():
    make_premium(int(request.form["chat_id"]))
    return redirect(url_for("users_list"))


@app.route("/remove_premium", methods=["POST"])
@login_required
def remove_premium_route():
    remove_premium(int(request.form["chat_id"]))
    return redirect(url_for("users_list"))


@app.route("/buttons")
@login_required
def buttons_list():
    return render_template("buttons.html", buttons=get_all_buttons())


@app.route("/add_button", methods=["POST"])
@login_required
def add_button_route():
    photo_path = ""
    if request.form.get("response_type") == "photo":
        file = request.files.get("photo")
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            photo_path = os.path.join(PHOTOS_DIR, filename)
            file.save(photo_path)

    add_button(
        request.form["key"],
        request.form["text"],
        request.form.get("emoji", ""),
        request.form.get("response_type", "text"),
        request.form.get("response_text", ""),
        photo_path,
        request.form.get("caption", ""),
        int(request.form.get("sort_order", 999)),
    )
    return redirect(url_for("buttons_list"))


@app.route("/edit_button/<key>", methods=["GET", "POST"])
@login_required
def edit_button_route(key):
    if request.method == "POST":
        photo_path = request.form.get("existing_photo", "")
        if request.form.get("response_type") == "photo":
            file = request.files.get("photo")
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                new_path = os.path.join(PHOTOS_DIR, filename)
                file.save(new_path)
                photo_path = new_path

        update_button(
            key,
            request.form.get("text"),
            request.form.get("emoji", ""),
            request.form.get("response_type"),
            request.form.get("response_text", ""),
            photo_path,
            request.form.get("caption", ""),
            1 if request.form.get("is_active") == "on" else 0,
        )
        return redirect(url_for("buttons_list"))

    return render_template("edit_button.html", button=get_button_by_key(key))


@app.route("/delete_button/<key>")
@login_required
def delete_button_route(key):
    btn = get_button_by_key(key)
    if btn and btn[6] and os.path.exists(btn[6]):
        try:
            os.remove(btn[6])
        except Exception:
            pass
    delete_button(key)
    return redirect(url_for("buttons_list"))


@app.route("/photo/<filename>")
@login_required
def serve_photo(filename):
    return send_from_directory(PHOTOS_DIR, filename)


@app.route("/broadcast", methods=["GET", "POST"])
@login_required
def broadcast():
    result = None
    if request.method == "POST":
        message_text = request.form.get("message", "").strip()
        if message_text and bot:
            users = get_all_users()
            success, fail = 0, 0
            for user in users:
                try:
                    bot.send_message(user[1], f"📢 ব্রডকাস্ট:\n\n{message_text}")
                    success += 1
                except Exception:
                    fail += 1
            result = f"✅ সফল: {success} জন পেয়েছেন। ব্যর্থ: {fail} জন।"
        elif not bot:
            result = "⚠️ বট চলছে না (TELEGRAM_BOT_TOKEN নেই)।"
    return render_template("broadcast.html", total_users=get_user_count(), result=result)


@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))


# ── Main ───────────────────────────────────────────────────────────────────

def run_bot():
    if not bot:
        print("⚠️  বট শুরু হয়নি — TELEGRAM_BOT_TOKEN সেট করুন।")
        return
    print("🤖 Bot is starting...")
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.infinity_polling(timeout=10, long_polling_timeout=10)
    except Exception as e:
        print(f"Bot error: {e}")


def run_web():
    port = int(os.environ.get("PORT", 5000))
    print(f"🌐 Web Dashboard starting on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    print("🚀 Starting Telegram Bot + Web Dashboard...")

    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    time.sleep(1)

    run_web()
