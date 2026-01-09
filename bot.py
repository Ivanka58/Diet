import os
import telebot
from telebot import types
from dotenv import load_dotenv
from datetime import datetime, timedelta
import database as db
from flask import Flask
import threading

load_dotenv()

TOKEN = os.getenv("TG_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
PAY_PHONE = os.getenv("PAYMENT_PHONE")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
user_steps = {}

@app.route('/')
def health(): return "STEEL CORE ONLINE", 200

def check_gap(t1, t2):
    try:
        fmt = '%H:%M'
        diff = datetime.strptime(t2, fmt) - datetime.strptime(t1, fmt)
        return diff.total_seconds() / 3600 >= 4
    except: return True

@bot.message_handler(commands=['start'])
def start(message):
    db.init_db() # Инициализация таблиц в облаке
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Начать путь 🚀")
    bot.send_message(message.chat.id, 
        "Ты в системе **STEEL CORE**. Мы строим стержень, пока другие деградируют.\n\n"
        "Я — твой контроль. 7 дней бесплатно, далее — подписка. Готов?", 
        parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Начать путь 🚀")
def registration(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Похудение", "Набор массы", "Поддержание")
    bot.send_message(message.chat.id, "Твоя цель:", reply_markup=markup)
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
    bot.send_message(message.chat.id, "Время завтрака (например, 08:00):")
    bot.register_next_step_handler(message, process_breakfast)

def process_breakfast(message):
    user_steps[message.chat.id]['b'] = message.text
    bot.send_message(message.chat.id, "Время обеда (не менее 4ч после завтрака):")
    bot.register_next_step_handler(message, process_lunch)

def process_lunch(message):
    l_time = message.text
    b_time = user_steps[message.chat.id]['b']
    if not check_gap(b_time, l_time):

        bot.send_message(message.chat.id, "⚠️ Интервал меньше 4 часов. Это снижает эффективность.")
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
    
    data = (cid, message.from_user.username, u['goal'], int(u['age']), float(u['weight']), 0.0, 
            u['b'], u['l'], u['d'], message.text, trial_end)
    db.save_user(data)
    
    bot.send_message(cid, "🔥 Регистрация пройдена. Система запущена. Завтра жду отчеты.")

@bot.message_handler(commands=['pay'])
def pay(message):
    bot.send_message(message.chat.id, 
        f"💳 Для продления подписки (349р) переведи по СБП на номер: `{PAY_PHONE}`\n\n"
        "Пришли скриншот чека сюда.", parse_mode="Markdown")
    bot.register_next_step_handler(message, check_pay)

def check_pay(message):
    if not message.photo:
        bot.send_message(message.chat.id, "Ошибка. Пришли фото чека.")
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Одобрить", callback_data=f"ok_{message.chat.id}"),
               types.InlineKeyboardButton("❌ Отказать", callback_data=f"no_{message.chat.id}"))
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id, 
                   caption=f"Чек на подписку от @{message.from_user.username}", reply_markup=markup)
    bot.send_message(message.chat.id, "Твой чек отправлен Администратору.")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('ok_', 'no_')))
def admin_res(call):
    action, uid = call.data.split('_')
    if action == 'ok':
        db.update_subscription(int(uid), 30)
        bot.send_message(uid, "✅ Твоя подписка продлена на 30 дней! Работаем дальше.")
        bot.answer_callback_query(call.id, "Одобрено")
    else:
        bot.send_message(uid, "❌ Твой чек отклонен. Проверь данные или свяжись с @Ivanka58")
        bot.answer_callback_query(call.id, "Отклонено")
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.message_handler(commands=['stats'])
def stats(message):
    logs = db.get_daily_calories(message.chat.id)
    if not logs:
        bot.send_message(message.chat.id, "Сегодня записей еще нет.")
        return
    total = sum([l[1] for l in logs])
    report = "\n".join([f"🔹 {l[0]}: {l[1]} ккал" for l in logs])
    bot.send_message(message.chat.id, f"📊 Твой отчет за сегодня:\n\n{report}\n\nИТОГО: {total} ккал.")

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling()
