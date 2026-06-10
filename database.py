import sqlite3
from datetime import datetime, timedelta

DB_NAME = "bot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # ইউজার টেবিল
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER UNIQUE,
        username TEXT,
        first_name TEXT,
        joined_date TEXT,
        is_premium INTEGER DEFAULT 0,
        premium_expiry TEXT
    )''')
    
    # বাটন টেবিল
    c.execute('''CREATE TABLE IF NOT EXISTS buttons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE,
        text TEXT,
        emoji TEXT,
        response_type TEXT,
        response_text TEXT,
        photo_path TEXT,
        caption TEXT,
        sort_order INTEGER DEFAULT 999,
        is_active INTEGER DEFAULT 1
    )''')
    
    # অ্যাডমিন টেবিল
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY,
        password TEXT
    )''')
    
    # ডিফল্ট অ্যাডমিন পাসওয়ার্ড
    c.execute("SELECT * FROM admins WHERE id=1")
    if not c.fetchone():
        c.execute("INSERT INTO admins (id, password) VALUES (1, 'admin123')")
    
    # ডিফল্ট বাটন
    default_buttons = [
        ('premium', 'প্রিমিয়াম গ্রুপ', '😋', 'text', 'প্রিমিয়াম গ্রুপে যোগ দিতে চাইলে অ্যাডমিনকে বলুন।', '', '', 1, 1),
        ('demo', 'ডেমো ভিডিও', '🥵', 'text', 'ডেমো ভিডিও লিংক: https://t.me/example', '', '', 2, 1),
        ('support', 'সাপোর্ট', '📱', 'text', 'অ্যাডমিন: @username', '', '', 3, 1),
    ]
    
    for btn in default_buttons:
        c.execute("SELECT * FROM buttons WHERE key=?", (btn[0],))
        if not c.fetchone():
            c.execute("INSERT INTO buttons (key, text, emoji, response_type, response_text, photo_path, caption, sort_order, is_active) VALUES (?,?,?,?,?,?,?,?,?)", btn)
    
    conn.commit()
    conn.close()

def add_user(chat_id, username, first_name):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    joined_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        c.execute("INSERT INTO users (chat_id, username, first_name, joined_date) VALUES (?,?,?,?)",
                  (chat_id, username, first_name, joined_date))
        conn.commit()
    except:
        pass
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY joined_date DESC")
    users = c.fetchall()
    conn.close()
    return users

def get_user_count():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_today_joined():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE joined_date LIKE ?", (f"{today}%",))
    count = c.fetchone()[0]
    conn.close()
    return count

def make_premium(chat_id, days=30):
    expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET is_premium=1, premium_expiry=? WHERE chat_id=?", (expiry, chat_id))
    conn.commit()
    conn.close()

def remove_premium(chat_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET is_premium=0, premium_expiry=NULL WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()

def get_all_buttons():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM buttons ORDER BY sort_order")
    buttons = c.fetchall()
    conn.close()
    return buttons

def get_button_by_key(key):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM buttons WHERE key=?", (key,))
    button = c.fetchone()
    conn.close()
    return button

def add_button(key, text, emoji, response_type, response_text, photo_path, caption, sort_order):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO buttons (key, text, emoji, response_type, response_text, photo_path, caption, sort_order) VALUES (?,?,?,?,?,?,?,?)",
                  (key, text, emoji, response_type, response_text, photo_path, caption, sort_order))
        conn.commit()
    except:
        pass
    conn.close()

def update_button(key, text, emoji, response_type, response_text, photo_path, caption, is_active):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE buttons SET text=?, emoji=?, response_type=?, response_text=?, photo_path=?, caption=?, is_active=? WHERE key=?",
              (text, emoji, response_type, response_text, photo_path, caption, is_active, key))
    conn.commit()
    conn.close()

def delete_button(key):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM buttons WHERE key=?", (key,))
    conn.commit()
    conn.close()

def check_admin_password(password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT password FROM admins WHERE id=1")
    result = c.fetchone()
    conn.close()
    return result and result[0] == password

def update_admin_password(new_password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE admins SET password=? WHERE id=1", (new_password,))
    conn.commit()
    conn.close()

def get_admin_password():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT password FROM admins WHERE id=1")
    result = c.fetchone()
    conn.close()
    return result[0] if result else "admin123"
