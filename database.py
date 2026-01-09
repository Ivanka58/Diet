import sqlite3
from datetime import datetime, timedelta

DB_PATH = '/data/fitness.db' # Путь для Render Disk. Локально можно менять на 'fitness.db'

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    # Таблица пользователей
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        chat_id INTEGER PRIMARY KEY,
        username TEXT,
        goal TEXT,
        age INTEGER,
        weight REAL,
        target_weight REAL,
        breakfast_time TEXT,
        lunch_time TEXT,
        dinner_time TEXT,
        train_time TEXT,
        subscription_end TEXT,
        strikes INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1
    )''')
    # Таблица логов еды
    cursor.execute('''CREATE TABLE IF NOT EXISTS food_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        meal_type TEXT,
        calories INTEGER,
        date TEXT
    )''')
    conn.commit()
    conn.close()

def save_user(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''INSERT OR REPLACE INTO users 
        (chat_id, username, goal, age, weight, target_weight, breakfast_time, lunch_time, dinner_time, train_time, subscription_end) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', data)
    conn.commit()
    conn.close()

def get_user(chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE chat_id = ?', (chat_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def add_strike(chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET strikes = strikes + 1 WHERE chat_id = ?', (chat_id,))
    conn.commit()
    conn.close()

def update_subscription(chat_id, days):
    conn = get_connection()
    cursor = conn.cursor()
    new_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    cursor.execute('UPDATE users SET subscription_end = ? WHERE chat_id = ?', (chat_id, new_date))
    conn.commit()
    conn.close()

def log_food(chat_id, meal_type, calories):
    conn = get_connection()
    cursor = conn.cursor()
    date_now = datetime.now().strftime("%Y-%m-%d")
    cursor.execute('INSERT INTO food_logs (chat_id, meal_type, calories, date) VALUES (?, ?, ?, ?)', 
                   (chat_id, meal_type, calories, date_now))
    conn.commit()
    conn.close()

def get_daily_calories(chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    date_now = datetime.now().strftime("%Y-%m-%d")
    cursor.execute('SELECT meal_type, calories FROM food_logs WHERE chat_id = ? AND date = ?', (chat_id, date_now))
    logs = cursor.fetchall()
    conn.close()
    return logs
