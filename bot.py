import os
import telebot
from telebot import types
from datetime import datetime, timedelta
import database as db
from flask import Flask
import threading
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TG_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
PAY_PHONE = os.getenv("PAYMENT_PHONE")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
user_temp = {}

@app.route('/')
def health(): return "STEEL CORE LIVE", 200

# ИИ для калорий (заглушка)
def ai_calories(text):
    text = text.lower()
    if "курица" in text or "грудка" in text: return 250
    if "яйцо" in text: return 150
    if "салат" in text: return 100
    return 300

def check_4h(t1, t2):
    try:
        fmt = '%H:%M'
        diff = abs((datetime.strptime(t2, fmt) - datetime.strptime(t1, fmt)).total_seconds()) / 3600
        return diff >= 4
    except: return True

# --- КОМАНДЫ ---

@bot.message_handler(commands=['start'])
def start_cmd(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Начать свой путь 🚀")
    bot.send_message(message.chat.id, 
                     "Привет, Ваня. Ты в системе STEEL CORE.\n"
                     "Этот бот — твой инструмент для выхода из толпы. Нажми кнопку, чтобы начать регистрацию.",
                     parse_mode="Markdown", reply_markup=markup)
    
@bot.message_handler(func=lambda m: m.text == "Начать свой путь 🚀")
def reg_1(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Похудение", "Поддержание формы", "Набор массы")
    bot.send_message(message.chat.id, "В какой сфере ты хочешь двигаться?", reply_markup=markup)
    bot.register_next_step_handler(message, reg_2)

def reg_2(message):
    user_temp[message.chat.id] = {'goal': message.text}
    bot.send_message(message.chat.id, "Твой возраст:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, reg_3)

def reg_3(message):
    user_temp[message.chat.id]['age'] = message.text
    bot.send_message(message.chat.id, "Твой вес (кг):")
    bot.register_next_step_handler(message, reg_4)

def reg_4(message):
    user_temp[message.chat.id]['weight'] = message.text
    bot.send_message(message.chat.id, "Желаемый вес (кг):")
    bot.register_next_step_handler(message, reg_5)

def reg_5(message):
    user_temp[message.chat.id]['target'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Я согласен, идем дальше")
    bot.send_message(message.chat.id, "⚠️ Первая неделя бесплатно. Далее 349р/мес. Согласен?", reply_markup=markup)
    bot.register_next_step_handler(message, reg_6)

def reg_6(message):
    bot.send_message(message.chat.id, "Время ЗАВТРАКА (08:00):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, reg_7)

def reg_7(message):
    user_temp[message.chat.id]['b'] = message.text
    bot.send_message(message.chat.id, "Время ОБЕДА (не менее 4ч разницы):")
    bot.register_next_step_handler(message, reg_8)

def reg_8(message):
    cid = message.chat.id
    l_t = message.text
    if not check_4h(user_temp[cid]['b'], l_t):
        bot.send_message(cid, "⚠️ Между завтраком и обедом меньше 4 часов. Не рекомендуется!")
    user_temp[cid]['l'] = l_t
    bot.send_message(cid, "Время УЖИНА:")
    bot.register_next_step_handler(message, reg_9)

def reg_9(message):
    user_temp[message.chat.id]['d'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Без тренировок")
    bot.send_message(message.chat.id, "Время тренировки:", reply_markup=markup)
    bot.register_next_step_handler(message, reg_final)

def reg_final(message):
    cid = message.chat.id
    u = user_temp[cid]
    sub = datetime.now() + timedelta(days=7)
    data = (cid, message.from_user.username, u['goal'], u['age'], u['weight'], u['target'], 'M', u['b'], u['l'], u['d'], message.text, sub)
    db.save_user(data)
    bot.send_message(cid, "✅ Ты принят в диетический марафон! Путь начался.", reply_markup=types.ReplyKeyboardRemove())

# --- УПРАВЛЕНИЕ ---

@bot.message_handler(commands=['menu'])
def menu_cmd(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Изменить Завтрак", callback_data="change_breakfast"),
        types.InlineKeyboardButton("Изменить Обед", callback_data="change_lunch"),
        types.InlineKeyboardButton("Изменить Ужин", callback_data="change_dinner")
    )
    bot.send_message(message.chat.id, "Вы хотите изменить время приема пищи?", reply_markup=markup)


@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    # Пока мы игнорируем статистику, поскольку база данных отсутствует
    bot.send_message(message.chat.id, "Эта команда станет доступна позже.")
    
@bot.message_handler(commands=['pay'])
def pay_cmd(message):
    bot.send_message(message.chat.id, f"Твоя подписка активна до: (дата).\n\nДля продления перевода 349 рублей на `{PAY_PHONE}` (СПБ) и отправь фото чека.",
                    parse_mode="Markdown")

@bot.message_handler(commands=['stop'])
def stop_cmd(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("ДА, я сдаюсь", "НЕТ, продолжаю")
    bot.send_message(message.chat.id, "Ты действительно хочешь выйти из марафона? Прогресс будет потерян!",
                     reply_markup=markup)


# Обработка выбора пользователя при выходе
@bot.message_handler(func=lambda m: m.text in ["ДА, я слабак", "НЕТ, я сильный"])
def stop_confirm(message):
    if "ДА, я сдаюсь" in message.text:
        # Здесь должна быть логика удаления пользователя из базы данных
        bot.send_message(message.chat.id, "Ты выбыл. Возвращайся в толпу. ", reply_markup=types.ReplyKeyboardRemove())
    else:
        bot.send_message(message.chat.id, "Правильный выбор, кремень не ломается! ", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(content_types=['photo'])
def receipt(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Подтвердить 30 дней", callback_data=f"admin_ok_{message.chat.id}"))
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"Чек от @{message.from_user.username}", reply_markup=markup)
    bot.send_message(message.chat.id, "Чек на проверке у администратора.")

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    if call.data.startswith("admin_ok_"):
        uid = int(call.data.split("_")[2])
        db.update_sub(uid, 30)
        bot.send_message(uid, "✅ Оплата подтверждена! Подписка +30 дней.")
        bot.answer_callback_query(call.id, "Готово")
    elif call.data.startswith("change_"):
        bot.send_message(call.message.chat.id, "Введи новое время (например 09:30):")

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling()
