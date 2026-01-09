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

TOKEN = os.getenv("TG_TOKEN")
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN") # Получается в BotFather
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Хранилище для регистрации
user_form = {}

# --- СЕРВЕР ДЛЯ RENDER ---
@app.route('/')
def health(): return "Ready", 200

def run_flask():
    bot_port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=bot_port)

# --- ЛОГИКА ПРОВЕРКИ ВРЕМЕНИ ---
def check_time_gap(t1, t2):
    fmt = '%H:%M'
    dt1 = datetime.strptime(t1, fmt)
    dt2 = datetime.strptime(t2, fmt)
    return abs((dt2 - dt1).total_seconds()) / 3600 >= 4

# --- ПРИВЕТСТВИЕ ---
@bot.message_handler(commands=['start'])
def start(message):
    cid = message.chat.id
    db.init_db()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Начать путь 🚀")
    bot.send_message(cid, 
        f"Добро пожаловать в систему трансформации тела и духа.\n\n"
        f"Этот бот — твой персональный надзиратель и наставник. "
        f"Я буду следить за каждым твоим приемом пищи и тренировкой. "
        f"Слабые уходят, сильные меняются.\n\n"
        f"Готов начать?", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Начать путь 🚀")
def ask_goal(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Похудение", callback_data="goal_diet"))
    markup.add(types.InlineKeyboardButton("Поддержание формы", callback_data="goal_norm"))
    markup.add(types.InlineKeyboardButton("Набор мышц", callback_data="goal_mass"))
    bot.send_message(message.chat.id, "Выбери свою цель:", reply_markup=markup)

# --- СБОР ДАННЫХ (FSM) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('goal_'))
def set_goal(call):
    user_form[call.message.chat.id] = {'goal': call.data}
    bot.send_message(call.message.chat.id, "Введите ваш возраст:")
    bot.register_next_step_handler(call.message, get_age)

def get_age(message):
    user_form[message.chat.id]['age'] = message.text
    bot.send_message(message.chat.id, "Ваш текущий вес (кг):")
    bot.register_next_step_handler(message, get_weight)

def get_weight(message):
    user_form[message.chat.id]['weight'] = message.text
    bot.send_message(message.chat.id, "Введите желаемое время завтрака (например, 08:00):")
    bot.register_next_step_handler(message, get_breakfast)

def get_breakfast(message):
    user_form[message.chat.id]['breakfast'] = message.text
    bot.send_message(message.chat.id, "Введите время обеда (не менее 4ч после завтрака):")
    bot.register_next_step_handler(message, get_lunch)

def get_lunch(message):
    b_time = user_form[message.chat.id]['breakfast']
    l_time = message.text
    if not check_time_gap(b_time, l_time):
        bot.send_message(message.chat.id, "⚠️ Между приемами пищи должно быть > 4 часов. Но если настаиваешь...")
    
    user_form[message.chat.id]['lunch'] = l_time
    bot.send_message(message.chat.id, "Введите время ужина:")
    bot.register_next_step_handler(message, get_dinner)

def get_dinner(message):
    user_form[message.chat.id]['dinner'] = message.text
    bot.send_message(message.chat.id, "Введите время тренировки (или напишите 'Без тренировок'):")
    bot.register_next_step_handler(message, finish_reg)

def finish_reg(message):
    cid = message.chat.id
    user_form[cid]['train'] = message.text
    
    # Расчет пробного периода (7 дней)
    end_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    data = (
        cid, user_form[cid]['goal'], user_form[cid]['age'], 
        user_form[cid]['weight'], 0, 'M', 
        user_form[cid]['breakfast'], user_form[cid]['lunch'], 
        user_form[cid]['dinner'], user_form[cid]['train'], end_date
    )
    db.save_user(data)
    
    bot.send_message(cid, 
        "✅ Регистрация завершена!\n\n"
        "Тебе предоставлена 1 бесплатная неделя. "
        "Далее подписка составит 349 руб/мес.\n\n"
        "Я начну присылать уведомления завтра. Не подведи меня.")

# --- ОПЛАТА И ДОНАТ ---
@bot.message_handler(commands=['donate'])
def donate(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("50 руб", callback_data="pay_50"))
    markup.add(types.InlineKeyboardButton("500 руб", callback_data="pay_500"))
    bot.send_message(message.chat.id, "Твоя поддержка поможет мне стать умнее. Выбери сумму:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('pay_'))
def send_invoice(call):
    amount = int(call.data.split('_')[1]) * 100 # В копейках
    bot.send_invoice(
        call.message.chat.id, 
        title="Поддержка проекта",
        description="Донат создателю системы",
        invoice_payload="donate_payload",
        provider_token=PAYMENT_TOKEN,
        currency="RUB",
        prices=[types.LabeledPrice("Донат", amount)]
    )

# --- ПЛАНИРОВЩИК ---
def send_reminders():
    # Здесь логика: бот берет из БД время, сравнивает с текущим и шлет сообщения
    # Реализуется через db.get_all_users()
    pass

scheduler = BackgroundScheduler()
scheduler.add_job(send_reminders, "interval", minutes=1)
scheduler.start()

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
