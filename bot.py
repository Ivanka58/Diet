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
user_data = {} # Временная память для регистрации

@app.route('/')
def health(): return "STEEL CORE ACTIVE", 200

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def main_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📊 Статистика", callback_data="stats"))
    markup.add(types.InlineKeyboardButton("💳 Оплата", callback_data="pay"))
    markup.add(types.InlineKeyboardButton("🛑 Выход", callback_data="stop"))
    return markup

# --- КОМАНДЫ ---
@bot.message_handler(commands=['start'])
def start(message):
    db.init_db()
    bot.clear_step_handler_by_chat_id(message.chat.id)
    user = db.get_user(message.chat.id)
    
    if user:
        bot.send_message(message.chat.id, f"Ваня, ты снова в системе. Твой профиль активен.", reply_markup=main_menu())
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("НАЧАТЬ ПУТЬ 🚀", callback_data="reg_start"))
        bot.send_message(message.chat.id, "Добро пожаловать в **STEEL CORE**. Систему для тех, кто создает правила, а не следует им.", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    logs = db.get_daily_calories(message.chat.id)
    total = sum([l[0] for l in logs]) if logs else 0
    bot.send_message(message.chat.id, f"📊 Твой результат за сегодня: {total} ккал.")

@bot.message_handler(commands=['pay'])
def cmd_pay(message):
    bot.send_message(message.chat.id, f"Для активации переведи 349р на `{PAY_PHONE}` (СБП) и пришли фото чека.", parse_mode="Markdown")

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Я СДАЮСЬ (СЛАБАК)", callback_data="quit_confirm"))
    markup.add(types.InlineKeyboardButton("Я ОСТАЮСЬ (КРЕМЕНЬ)", callback_data="quit_cancel"))
    bot.send_message(message.chat.id, "Ты действительно хочешь вернуться в толпу?", reply_markup=markup)

# --- ОБРАБОТКА КНОПОК ---
@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    cid = call.message.chat.id

    mid = call.message.message_id

    if call.data == "reg_start":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Похудение", callback_data="goal_diet"))
        markup.add(types.InlineKeyboardButton("Масса", callback_data="goal_mass"))
        bot.edit_message_text("Выбери свою цель:", cid, mid, reply_markup=markup)

    elif call.data.startswith("goal_"):
        user_data[cid] = {'goal': call.data.split('_')[1]}
        bot.answer_callback_query(call.id)
        bot.send_message(cid, "Твой возраст:")
        bot.register_next_step_handler(call.message, reg_age)

    elif call.data == "stats":
        bot.answer_callback_query(call.id)
        cmd_stats(call.message)

    elif call.data == "pay":
        bot.answer_callback_query(call.id)
        cmd_pay(call.message)

    elif call.data == "stop":
        bot.answer_callback_query(call.id)
        cmd_stop(call.message)

    elif call.data == "quit_confirm":
        db.delete_user(cid)
        bot.edit_message_text("Система стерла тебя. Ты снова никто.", cid, mid)
        bot.answer_callback_query(call.id)

    elif call.data == "quit_cancel":
        bot.edit_message_text("Дисциплина восстановлена.", cid, mid, reply_markup=main_menu())
        bot.answer_callback_query(call.id)

# --- ЛОГИКА РЕГИСТРАЦИИ (ШАГИ) ---
def reg_age(message):
    user_data[message.chat.id]['age'] = message.text
    bot.send_message(message.chat.id, "Твой текущий вес:")
    bot.register_next_step_handler(message, reg_weight)

def reg_weight(message):
    cid = message.chat.id
    u = user_data[cid]
    trial = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    db.save_user(cid, message.from_user.username, u['goal'], u['age'], message.text, trial)
    bot.send_message(cid, "🔥 ТЫ В СИСТЕМЕ. Первая неделя — подарок. Твой путь начался.", reply_markup=main_menu())

# --- ПРИЕМ ЧЕКОВ ---
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"Чек от @{message.from_user.username}")
    bot.send_message(message.chat.id, "Чек передан администратору на проверку.")

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling()
