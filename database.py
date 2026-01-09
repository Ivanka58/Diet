import psycopg2
import os
from datetime import datetime, timedelta

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    # Пользователи
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        chat_id BIGINT PRIMARY KEY,
        username TEXT,
        goal TEXT,
        age INTEGER,
        weight REAL,
        target_weight REAL,
        gender TEXT,
        breakfast_time TEXT,
        lunch_time TEXT,
        dinner_time TEXT,
        train_time TEXT,
        subscription_end TEXT,
        strikes INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1
    )''')
    # Логи калорий
    cursor.execute('''CREATE TABLE IF NOT EXISTS food_logs (
        id SERIAL PRIMARY KEY,
        chat_id BIGINT,
        meal_type TEXT,
        calories INTEGER,
        date TEXT
    )''')
    conn.commit()
    cursor.close()
    conn.close()

def save_user(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO users 
        (chat_id, username, goal, age, weight, target_weight, gender, breakfast_time, lunch_time, dinner_time, train_time, subscription_end) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (chat_id) DO UPDATE SET
        goal=EXCLUDED.goal, age=EXCLUDED.age, weight=EXCLUDED.weight, target_weight=EXCLUDED.target_weight,
        breakfast_time=EXCLUDED.breakfast_time, lunch_time=EXCLUDED.lunch_time, 
        dinner_time=EXCLUDED.dinner_time, train_time=EXCLUDED.train_time, 
        subscription_end=EXCLUDED.subscription_end, is_active=1''', data)
    conn.commit()
    cursor.close()
    conn.close()

def get_user(chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE chat_id = %s', (chat_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def delete_user(chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_active = 0 WHERE chat_id = %s', (chat_id,))
    conn.commit()
    cursor.close()
    conn.close()

def update_subscription(chat_id, days):
    conn = get_connection()
    cursor = conn.cursor()
    new_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    cursor.execute('UPDATE users SET subscription_end = %s WHERE chat_id = %s', (new_date, chat_id))
    conn.commit()
    cursor.close()
    conn.close()

def log_food(chat_id, meal_type, calories):
    conn = get_connection()
    cursor = conn.cursor()
    date_now = datetime.now().strftime("%Y-%m-%d")
    cursor.execute('INSERT INTO food_logs (chat_id, meal_type, calories, date) VALUES (%s, %s, %s, %s)', 
                   (chat_id, meal_type, calories, date_now))
    conn.commit()
    cursor.close()
    conn.close()

def get_daily_calories(chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    date_now = datetime.now().strftime("%Y-%m-%d")
    cursor.execute('SELECT meal_type, calories FROM food_logs WHERE chat_id = %s AND date = %s', (chat_id, date_now))
    logs = cursor.fetchall()
    cursor.close()
    conn.close()
    return logs
