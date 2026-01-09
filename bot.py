import os
import telebot
from telebot import types
from dotenv import load_dotenv
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import database as db
from flask import Flask
import threading

load_dotenv()

# Настройки из ENV
TOKEN = os.getenv("TG_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
PAY_PHONE = os.getenv("PAYMENT_PHONE")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
user_steps = {} # Для временного хранения данных регистрации

@app.route('/')
def health(): return "STEEL CORE ALIVE", 200

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def check_gap(t1, t2):
    try:
        fmt = '%H:%M'
        diff = datetime.strptime(t2, fmt) - datetime.strptime(t1, fmt)
        return diff.total_seconds() / 3600 >= 4
    except: return True

# --- КОМАНДЫ ---
@bot.message_handler(commands=['start'])
def start(message):
    db.init_db()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Начать путь 🚀")
    bot.send_message(message.chat.id, 
        "Привет. Ты зашел в **STEEL CORE**. Это система для тех, кто готов созидать себя и выходить из толпы.\n\n"
        "Я буду контролировать твое питание и тренировки. Правила жесткие. Готов?", 
        parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Начать путь 🚀")
def registration(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Похудение", "Набор массы", "Поддержание")
    bot.send_message(message.chat.id, "Выбери цель:", reply_markup=markup)
    bot.register_next_step_handler(message, process_goal)

def process_goal(message):
    user_steps[message.chat.id] = {'goal': message.text}
    bot.send_message(message.chat.id, "Твой возраст:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, process_age)

def process_age(message):
    user_steps[message.chat.id]['age'] = message.text
    bot.send_message(message.chat.id, "Твой текущий вес (кг):")
    bot.register_next_step_handler(message, process_weight)

def process_weight(message):
    user_steps[message.chat.id]['weight'] = message.text
    bot.send_message(message.chat.id, "Время завтрака (08:00):")
    bot.register_next_step_handler(message, process_breakfast)

def process_breakfast(message):
    user_steps[message.chat.id]['b'] = message.text
    bot.send_message(message.chat.id, "Время обеда (не менее 4ч после завтрака):")
    bot.register_next_step_handler(message, process_lunch)

def process_lunch(message):
    l_time = message.text
    b_time = user_steps[message.chat.id]['b']
    if not check_gap(b_time, l_time):
        bot.send_message(message.chat.id, "⚠️ Между завтраком и обедом меньше 4 часов. Не рекомендую, но ты хозяин.")
    user_steps[message.chat.id]['l'] = l_time
    bot.send_message(message.chat.id, "Время ужина:")
    bot.register_next_step_handler(message, process_dinner)

def process_dinner(message):
    user_steps[message.chat.id]['d'] = message.text
    bot.send_message(message.chat.id, "Время тренировки (или 'Без тренировок'):")
    bot.register_next_step_handler(message, process_finish)

def process_finish(message):
    cid = message.chat.id
    u = user_steps[cid]
    trial_end = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    data = (cid, message.from_user.username, u['goal'], u['age'], u['weight'], 0, 
            u['b'], u['l'], u['d'], message.text, trial_end)
    db.save_user(data)
    
    bot.send_message(cid, "🔥 Ты в системе! 7 дней бесплатно. Далее 349р/мес. Не пропадай.")

# --- ОПЛАТА ---
@bot.message_handler(commands=['pay'])
def pay(message):
    bot.send_message(message.chat.id, 
        f"Для оплаты 349р переведи по номеру `{PAY_PHONE}` (СБП) и пришли скрин чека сюда.", 
        parse_mode="Markdown")
    bot.register_next_step_handler(message, check_pay)

def check_pay(message):
    if not message.photo:
        bot.send_message(message.chat.id, "Нужен скриншот.")
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Да", callback_data=f"ok_{message.chat.id}"),
               types.InlineKeyboardButton("❌ Нет", callback_data=f"no_{message.chat.id}"))
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id, 
                   caption=f"Чек от @{message.from_user.username}", reply_markup=markup)
    bot.send_message(message.chat.id, "Чек на проверке.")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('ok_', 'no_')))
def admin_res(call):
    action, uid = call.data.split('_')
    if action == 'ok':
        db.update_subscription(uid, 30)
        bot.send_message(uid, "✅ Подписка продлена на 30 дней!")
    else:
        bot.send_message(uid, "❌ Чек отклонен.")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# --- ДОНАТ ---
@bot.message_handler(commands=['donate'])
def donate(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("50р", callback_data="d_50"),
               types.InlineKeyboardButton("200р", callback_data="d_200"))
    bot.send_message(message.chat.id, "Поддержи создателя:", reply_markup=markup)

# --- СТАТИСТИКА В КОНЦЕ ДНЯ ---
@bot.message_handler(commands=['stats'])
def stats(message):
    logs = db.get_daily_calories(message.chat.id)
    total = sum([l[1] for l in logs])
    report = "\n".join([f"{l[0]}: {l[1]} ккал" for l in logs])
    bot.send_message(message.chat.id, f"Твой отчет сегодня:\n{report}\nВсего: {total} ккал.")

# --- ПЛАНИРОВЩИК (Уведомления) ---
def run_scheduler():
    scheduler = BackgroundScheduler()
    # Здесь должна быть логика проверки времени из БД
    # В скелете мы просто запускаем поток
    scheduler.start()

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling()
