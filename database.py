import psycopg2
import os
from datetime import datetime, timedelta

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        chat_id BIGINT PRIMARY KEY,
        username TEXT,
        goal TEXT,
        age TEXT,
        weight TEXT,
        target_weight TEXT,
        gender TEXT,
        breakfast_time TEXT,
        lunch_time TEXT,
        dinner_time TEXT,
        train_time TEXT,
        subscription_end TIMESTAMP,
        is_active INTEGER DEFAULT 1
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS food_logs (
        id SERIAL PRIMARY KEY,
        chat_id BIGINT,
        calories INTEGER,
        meal_type TEXT,
        food_desc TEXT,
        date DATE DEFAULT CURRENT_DATE
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
        ON CONFLICT (chat_id) DO UPDATE SET is_active = 1, subscription_end = EXCLUDED.subscription_end, 
        breakfast_time=EXCLUDED.breakfast_time, lunch_time=EXCLUDED.lunch_time, dinner_time=EXCLUDED.dinner_time''', data)
    conn.commit()
    cursor.close()
    conn.close()

def update_sub(chat_id, days):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET subscription_end = subscription_end + interval %s WHERE chat_id = %s', 
                   (f'{days} days', chat_id))
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

def log_food(chat_id, calories, meal_type, desc):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO food_logs (chat_id, calories, meal_type, food_desc) VALUES (%s, %s, %s, %s)', 
                   (chat_id, calories, meal_type, desc))
    conn.commit()
    cursor.close()
    conn.close()

def get_daily_stats(chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT meal_type, calories FROM food_logs WHERE chat_id = %s AND date = CURRENT_DATE', (chat_id,))
    res = cursor.fetchall()
    cursor.close()
    conn.close()
    return res

def delete_user(chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE chat_id = %s', (chat_id,))
    conn.commit()
    cursor.close()
    conn.close()
