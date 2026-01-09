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
def health(): return "STEEL CORE ACTIVE", 200

# --- ГЛАВНЫЕ КОМАНДЫ ---

@bot.message_handler(commands=['start'])
def start(message):
    db.init_db()
    bot.clear_step_handler_by_chat_id(message.chat.id) # Сброс зависших шагов
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Начать путь 🚀", callback_data="start_reg"))
    bot.send_message(message.chat.id, 
        "Ваня, привет. Ты в системе **STEEL CORE**.\n\n"
        "Либо ты строишь себя, либо мир ломает тебя. Выбор очевиден.", 
        parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['stats'])
def stats(message):
    logs = db.get_daily_calories(message.chat.id)
    if not logs:
        bot.send_message(message.chat.id, "Сегодня записей нет. Дисциплина хромает?")
        return
    total = sum([l[1] for l in logs])
    bot.send_message(message.chat.id, f"📊 Отчет за сегодня: {total} ккал.")

@bot.message_handler(commands=['pay'])
def pay(message):
    bot.send_message(message.chat.id, f"Для продления переведи 349р на `{PAY_PHONE}` и пришли скрин чека сюда.", parse_mode="Markdown")
    bot.register_next_step_handler(message, handle_receipt)

@bot.message_handler(commands=['stop'])
def stop(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("ДА, я сдаюсь", callback_data="confirm_stop"))
    markup.add(types.InlineKeyboardButton("НЕТ, я кремень", callback_data="cancel_stop"))
    bot.send_message(message.chat.id, "⚠️ Весь прогресс будет удален. Ты уверен?", reply_markup=markup)

# --- РЕГИСТРАЦИЯ ЧЕРЕЗ CALLBACK ---

@bot.callback_query_handler(func=lambda call: True)
def handle_calls(call):
    cid = call.message.chat.id
    if call.data == "start_reg":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Похудение", callback_data="goal_diet"))
        markup.add(types.InlineKeyboardButton("Масса", callback_data="goal_mass"))
        bot.edit_message_text("Выбери цель:", cid, call.message.message_id, reply_markup=markup)
    
    elif call.data.startswith("goal_"):

        user_steps[cid] = {'goal': call.data}
        bot.send_message(cid, "Введите возраст:")
        bot.register_next_step_handler(call.message, reg_age)
    
    elif call.data == "confirm_stop":
        db.delete_user(cid)
        bot.edit_message_text("Ты выбыл. Путь к посредственности открыт.", cid, call.message.message_id)
    
    elif call.data == "cancel_stop":
        bot.edit_message_text("Правильный выбор. Возвращаемся в строй.", cid, call.message.message_id)

def reg_age(message):
    user_steps[message.chat.id]['age'] = message.text
    bot.send_message(message.chat.id, "Твой вес:")
    bot.register_next_step_handler(message, reg_weight)

def reg_weight(message):
    user_steps[message.chat.id]['weight'] = message.text
    bot.send_message(message.chat.id, "Время завтрака (08:00):")
    bot.register_next_step_handler(message, reg_finish)

def reg_finish(message):
    cid = message.chat.id
    u = user_steps[cid]
    trial = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    data = (cid, message.from_user.username, u['goal'], u['age'], u['weight'], "0", "M", u['weight'], "13:00", "19:00", "Нет", trial)
    db.save_user(data)
    bot.send_message(cid, "✅ Система настроена. Завтра в бой.")

def handle_receipt(message):
    if message.photo:
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"Чек от @{message.from_user.username}")
        bot.send_message(message.chat.id, "Чек отправлен.")
    else: bot.send_message(message.chat.id, "Нужно фото.")

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling()
