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
ADMIN_USER = os.getenv("ADMIN_USERNAME")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
user_steps = {}

# --- ИИ-МОДУЛЬ (Nutritionist Engine) ---
def ai_analyze_food(text):
    """Имитация ИИ-анализа. Позже сюда подключим API."""
    text = text.lower()
    calories = 300 # Значение по умолчанию
    if "яйц" in text: calories = 150
    if "грудк" in text or "кур" in text: calories = 250
    if "бургер" in text or "пицц" in text: calories = 800
    if "салат" in text: calories = 100
    if "каш" in text: calories = 200
    return calories

# --- СЕРВЕР ---
@app.route('/')
def health(): return "STEEL CORE ACTIVE", 200

# --- ОБРАБОТЧИКИ КОМАНД (ВВЕРХУ!) ---

@bot.message_handler(commands=['start'])
def start(message):
    db.init_db()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Начать путь 🚀")
    bot.send_message(message.chat.id, 
        "Привет. Ты в системе **STEEL CORE**.\n\n"
        "Я — твой персональный контроль. Я помогу тебе создать тело, о котором другие только мечтают.\n"
        "Слабакам здесь не место. Чтобы запустить систему, жми кнопку.", 
        parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['pay'])
def pay(message):
    user = db.get_user(message.chat.id)
    date_info = f"Твой доступ до: {user[11]}" if user else "У тебя нет активного профиля."
    bot.send_message(message.chat.id, 
        f"📊 {date_info}\n\n"
        f"Для продления подписки (349р) переведи по СБП на номер: `{PAY_PHONE}`\n"
        "Пришли скриншот чека в ответ на это сообщение.", parse_mode="Markdown")
    bot.register_next_step_handler(message, handle_receipt)

@bot.message_handler(commands=['stats'])
def stats(message):
    logs = db.get_daily_calories(message.chat.id)
    if not logs:
        bot.send_message(message.chat.id, "Сегодня ты еще ничего не ел. Или забыл мне доложить.")
        return
    total = sum([l[1] for l in logs])
    report = "\n".join([f"🔹 {l[0]}: {l[2]} ({l[1]} ккал)" for l in logs])
    bot.send_message(message.chat.id, f"📊 **Твой отчет за сегодня:**\n\n{report}\n\n**ИТОГО: {total} ккал.**", parse_mode="Markdown")

@bot.message_handler(commands=['stop'])
def stop(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("ДА, я слабак", "НЕТ, я остаюсь")
    bot.send_message(message.chat.id, "⚠️ **ВНИМАНИЕ**\nВыход из марафона обнулит весь твой прогресс. Ты действительно хочешь вернуться в толпу?", parse_mode="Markdown", reply_markup=markup)
    bot.register_next_step_handler(message, confirm_stop)

@bot.message_handler(commands=['menu'])
def menu_cmd(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Перенос Завтрака", callback_data="edit_b"))
    markup.add(types.InlineKeyboardButton("Перенос Обеда", callback_data="edit_l"))
    markup.add(types.InlineKeyboardButton("Перенос Ужина", callback_data="edit_d"))
    bot.send_message(message.chat.id, "Выбери прием пищи для изменения времени:", reply_markup=markup)

@bot.message_handler(commands=['donate'])
def donate(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("100р", callback_data="d_100"), 
               types.InlineKeyboardButton("500р", callback_data="d_500"))
    bot.send_message(message.chat.id, "Твоя поддержка делает систему STEEL CORE мощнее. Выбери сумму:", reply_markup=markup)

# --- ЛОГИКА РЕГИСТРАЦИИ ---

@bot.message_handler(func=lambda m: m.text == "Начать путь 🚀")
def reg_1(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Похудение", "Набор массы", "Поддержание")
    bot.send_message(message.chat.id, "Какова твоя цель?", reply_markup=markup)
    bot.register_next_step_handler(message, reg_2)

def reg_2(message):
    user_steps[message.chat.id] = {'goal': message.text}
    bot.send_message(message.chat.id, "Твой возраст:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, reg_3)

def reg_3(message):
    user_steps[message.chat.id]['age'] = message.text
    bot.send_message(message.chat.id, "Текущий вес (кг):")
    bot.register_next_step_handler(message, reg_4)

def reg_4(message):
    user_steps[message.chat.id]['weight'] = message.text
    bot.send_message(message.chat.id, "Желаемый вес (кг):")
    bot.register_next_step_handler(message, reg_5)

def reg_5(message):
    user_steps[message.chat.id]['target'] = message.text
    bot.send_message(message.chat.id, "Время завтрака (например, 08:30):")
    bot.register_next_step_handler(message, reg_6)

def reg_6(message):
    user_steps[message.chat.id]['b'] = message.text
    bot.send_message(message.chat.id, "Время обеда:")
    bot.register_next_step_handler(message, reg_7)

def reg_7(message):
    user_steps[message.chat.id]['l'] = message.text
    bot.send_message(message.chat.id, "Время ужина:")
    bot.register_next_step_handler(message, reg_8)

def reg_8(message):
    user_steps[message.chat.id]['d'] = message.text
    bot.send_message(message.chat.id, "Время тренировки (или 'Нет'):")
    bot.register_next_step_handler(message, reg_final)

def reg_final(message):
    cid = message.chat.id
    u = user_steps[cid]
    trial = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    data = (cid, message.from_user.username, u['goal'], int(u['age']), float(u['weight']), 
            float(u['target']), 'M', u['b'], u['l'], u['d'], message.text, trial)
    db.save_user(data)
    bot.send_message(cid, "🔥 Ты в системе. С завтрашнего дня я буду следить за тобой.")

# --- ОБРАБОТКА ФОТО (ЧЕКИ) ---
def handle_receipt(message):
    if not message.photo:
        bot.send_message(message.chat.id, "Это не фото чека. Попробуй снова /pay.")
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Одобрить", callback_data=f"ok_{message.chat.id}"))
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"Чек от @{message.from_user.username}", reply_markup=markup)
    bot.send_message(message.chat.id, "Чек отправлен на проверку.")

# --- ПОДТВЕРЖДЕНИЕ ВЫХОДА ---
def confirm_stop(message):
    if message.text == "ДА, я слабак":
        db.delete_user(message.chat.id)
        bot.send_message(message.chat.id, "Профиль удален. Ты снова часть толпы.", reply_markup=types.ReplyKeyboardRemove())
    else:
        bot.send_message(message.chat.id, "Хороший выбор. Продолжаем.", reply_markup=types.ReplyKeyboardRemove())

# --- CALLBACKS (Кнопки) ---
@bot.callback_query_handler(func=lambda call: True)
def calls(call):
    if call.data.startswith('ok_'):
        uid = int(call.data.split('_')[1])
        db.update_subscription(uid, 30)
        bot.send_message(uid, "✅ Твоя подписка продлена на 30 дней! Вперед!")
        bot.edit_message_caption("Одобрено", call.message.chat.id, call.message.message_id)
    elif call.data.startswith('edit_'):
        bot.send_message(call.message.chat.id, "Введи новое время (например, 09:00):")
    elif call.data.startswith('d_'):
        bot.send_message(call.message.chat.id, f"Спасибо. Перевод на `{PAY_PHONE}`. Напиши @{ADMIN_USER} после перевода.", parse_mode="Markdown")

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling()
