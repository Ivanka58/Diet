import os
import telebot
from telebot import types
from datetime import datetime, timedelta
import database as db
from flask import Flask
import threading

TOKEN = os.getenv("TG_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
PAY_PHONE = os.getenv("PAYMENT_PHONE")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
user_temp = {}

@app.route('/')
def health(): return "STEEL CORE ONLINE", 200

# Вспомогательная функция проверки времени
def check_gap(t1, t2):
    try:
        fmt = '%H:%M'
        d1 = datetime.strptime(t1, fmt)
        d2 = datetime.strptime(t2, fmt)
        return abs((d2 - d1).total_seconds()) / 3600 >= 4
    except: return True

# --- КОМАНДЫ ---

@bot.message_handler(commands=['start'])
def start_cmd(message):
    db.init_db()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Начать свой путь 🚀")
    bot.send_message(message.chat.id, 
        "Привет, Ваня. Ты в системе **STEEL CORE**.\n"
        "Этот бот — твой инструмент для выхода из толпы. Нажми кнопку, чтобы начать регистрацию.", 
        parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Начать свой путь 🚀")
def reg_start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Похудение", "Поддержание формы", "Набор мышечной массы", "Набор жировой массы")
    bot.send_message(message.chat.id, "В какой сфере вы хотите двигаться?", reply_markup=markup)
    bot.register_next_step_handler(message, reg_goal)

def reg_goal(message):
    user_temp[message.chat.id] = {'goal': message.text}
    bot.send_message(message.chat.id, "Твой возраст:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, reg_age)

def reg_age(message):
    user_temp[message.chat.id]['age'] = message.text
    bot.send_message(message.chat.id, "Твой текущий вес (кг):")
    bot.register_next_step_handler(message, reg_weight)

def reg_weight(message):
    user_temp[message.chat.id]['weight'] = message.text
    bot.send_message(message.chat.id, "Желаемый вес (кг):")
    bot.register_next_step_handler(message, reg_target)

def reg_target(message):
    user_temp[message.chat.id]['target'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Мужской", "Женский")
    bot.send_message(message.chat.id, "Твой пол:", reply_markup=markup)
    bot.register_next_step_handler(message, reg_sub_warn)

def reg_sub_warn(message):
    user_temp[message.chat.id]['gender'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Я согласен, идем дальше")
    bot.send_message(message.chat.id, 
        "⚠️ Первая неделя бесплатно. Далее — 349р/мес.\nАвтосписаний нет. Согласен?", reply_markup=markup)
    bot.register_next_step_handler(message, reg_breakfast)

def reg_breakfast(message):
    bot.send_message(message.chat.id, "Желаемое время завтрака (например, 08:00):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, reg_lunch)

def reg_lunch(message):
    user_temp[message.chat.id]['b'] = message.text
    bot.send_message(message.chat.id, "Время обеда (не ранее 4ч после завтрака):")
    bot.register_next_step_handler(message, reg_dinner)

def reg_dinner(message):
    cid = message.chat.id
    l_t = message.text
    if not check_gap(user_temp[cid]['b'], l_t):
        bot.send_message(cid, "⚠️ Время между завтраком и обедом меньше 4ч. Не рекомендуется.")
    user_temp[cid]['l'] = l_t
    bot.send_message(cid, "Время ужина:")
    bot.register_next_step_handler(message, reg_train)

def reg_train(message):
    user_temp[message.chat.id]['d'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Без тренировок")
    bot.send_message(message.chat.id, "Время тренировки:", reply_markup=markup)
    bot.register_next_step_handler(message, reg_final)

def reg_final(message):
    cid = message.chat.id
    u = user_temp[cid]
    sub_end = datetime.now() + timedelta(days=7)
    
    data = (cid, message.from_user.username, u['goal'], int(u['age']), float(u['weight']), 
            float(u['target']), u['gender'], u['b'], u['l'], u['d'], message.text, sub_end)
    
    db.save_user(data)
    bot.send_message(cid, "✅ Ты принят в диетический марафон! Путь начался.", reply_markup=types.ReplyKeyboardRemove())

# --- УПРАВЛЕНИЕ ---

@bot.message_handler(commands=['menu'])
def menu_cmd(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Изменить Завтрак", callback_data="m_edit"),
               types.InlineKeyboardButton("Изменить Обед", callback_data="m_edit"),
               types.InlineKeyboardButton("Изменить Ужин", callback_data="m_edit"))
    bot.send_message(message.chat.id, "Вы хотите перенести прием пищи?", reply_markup=markup)

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    rows = db.get_daily_stats(message.chat.id)
    total = sum(r[1] for r in rows)
    msg = f"📊 Твоя статистика сегодня:\n" + "\n".join([f"{r[0]}: {r[1]} ккал" for r in rows])
    bot.send_message(message.chat.id, f"{msg}\n\n**Всего: {total} ккал**", parse_mode="Markdown")

@bot.message_handler(commands=['pay'])
def pay_cmd(message):
    user = db.get_user(message.chat.id)
    bot.send_message(message.chat.id, f"Твоя подписка активна до: {user[11]}\n\nДля продления переведи 349р на `{PAY_PHONE}` (СБП) и пришли фото чека.", parse_mode="Markdown")

@bot.message_handler(commands=['donate'])
def donate_cmd(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("100р", callback_data="d_100"),
               types.InlineKeyboardButton("500р", callback_data="d_500"))
    bot.send_message(message.chat.id, "Поддержать создателя системы:", reply_markup=markup)

@bot.message_handler(commands=['stop'])
def stop_cmd(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("ДА, я слабак", "НЕТ, я остаюсь")
    bot.send_message(message.chat.id, "Ты уверен, что хочешь выбыть? Твой прогресс обнулится.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["ДА, я слабак", "НЕТ, я остаюсь"])
def stop_confirm(message):
    if "слабак" in message.text:
        db.delete_user(message.chat.id)
        bot.send_message(message.chat.id, "Ты удален. Возвращайся в толпу.", reply_markup=types.ReplyKeyboardRemove())
    else:
        bot.send_message(message.chat.id, "Правильно. Кремень не ломается.", reply_markup=types.ReplyKeyboardRemove())

# --- ОБРАБОТКА ЧЕКОВ (ДЛЯ АДМИНА) ---

@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Подтвердить 30 дней", callback_data=f"admin_ok_{message.chat.id}"))
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id, 
                   caption=f"Чек от @{message.from_user.username}", reply_markup=markup)
    bot.send_message(message.chat.id, "Чек отправлен Ване на проверку.")

# --- CALLBACKS ---

@bot.callback_query_handler(func=lambda call: True)
def callback_all(call):
    if call.data.startswith("admin_ok_"):
        uid = int(call.data.split("_")[2])
        db.update_subscription(uid, 30)
        bot.send_message(uid, "✅ Ваня подтвердил твою оплату! Доступ продлен на 30 дней.")
        bot.answer_callback_query(call.id, "Одобрено!")
    elif call.data == "m_edit":
        bot.send_message(call.message.chat.id, "Введи новое время (например 09:00):")
    elif call.data.startswith("d_"):
        bot.send_message(call.message.chat.id, f"Спасибо за поддержку! Перевод на `{PAY_PHONE}`.", parse_mode="Markdown")

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling()
