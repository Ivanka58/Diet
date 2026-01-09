import sqlite3

def init_db():
    conn = sqlite3.connect('fitness.db', check_same_thread=False)
    cursor = conn.cursor()
    # Таблица пользователей
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        chat_id INTEGER PRIMARY KEY,
        goal TEXT,
        age INTEGER,
        weight REAL,
        target_weight REAL,
        gender TEXT,
        breakfast_time TEXT,
        lunch_time TEXT,
        dinner_time TEXT,
        train_time TEXT,
        join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        subscription_end TEXT,
        is_active INTEGER DEFAULT 1
    )''')
    conn.commit()
    conn.close()

def save_user(data):
    conn = sqlite3.connect('fitness.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT OR REPLACE INTO users 
        (chat_id, goal, age, weight, target_weight, gender, breakfast_time, lunch_time, dinner_time, train_time, subscription_end) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', data)
    conn.commit()
    conn.close()

def get_user(chat_id):
    conn = sqlite3.connect('fitness.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE chat_id = ?', (chat_id,))
    user = cursor.fetchone()
    conn.close()
    return user
