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


# Команда /start
@bot.message_handler(commands=['start'])
def start_cmd(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Начать свой путь 🚀")
    bot.send_message(message.chat.id, 
                     "Привет. Ты в системе STEEL CORE.\n"
                     "Этот бот — твой инструмент для выхода из толпы. Нажми кнопку, чтобы начать регистрацию.",
                     parse_mode="Markdown", reply_markup=markup)
    
# Начало регистрации
@bot.message_handler(func=lambda m: m.text == "Начать свой путь 🚀")


# Выбор цели
def reg_start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Похудение", "Поддержание формы", "Набор мышечной массы", "Набор жировой массы")
    bot.send_message(message.chat.id, "В какой сфере вы хотите двигаться?", reply_markup=markup)
    bot.register_next_step_handler(message, reg_goal)


# Регистрация возраста 
def reg_goal(message):
    user_temp[message.chat.id] = {'goal': message.text}
    bot.send_message(message.chat.id, "Твой возраст:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, reg_age)


# Регистрация текущего веса
def reg_age(message):
    user_temp[message.chat.id]['age'] = message.text
    bot.send_message(message.chat.id, "Твой текущий вес (кг):")
    bot.register_next_step_handler(message, reg_weight)


# Регистрация желаемого веса
def reg_weight(message):
    user_temp[message.chat.id]['weight'] = message.text
    bot.send_message(message.chat.id, "Желаемый вес (кг):")
    bot.register_next_step_handler(message, reg_target)


# Регистрация пола 
def reg_target(message):
    user_temp[message.chat.id]['target'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Мужской", "Женский")
    bot.send_message(message.chat.id, "Твой пол:", reply_markup=markup)
    bot.register_next_step_handler(message, reg_sub_warn)


# Предупреждение о подписке
def reg_sub_warn(message):
    user_temp[message.chat.id]['gender'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Я согласен, идем дальше")
    bot.send_message(message.chat.id, 
                     "⚠️ Первая неделя бесплатно. Далее — 349р/мес.\nАвтосписаний нет. Согласен?",
                     reply_markup=markup)
    bot.register_next_step_handler(message, reg_breakfast)


# Время завтрака
def reg_breakfast(message):
    bot.send_message(message.chat.id, "Желаемое время завтрака (например, 08:00):",
                     reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, reg_lunch)


# Время обеда 
def reg_lunch(message):
    user_temp[message.chat.id]['breakfast'] = message.text
    bot.send_message(message.chat.id, "Время обеда (не ранее 4 часов после завтрака):")
    bot.register_next_step_handler(message, reg_dinner)


# Время ужина 
def reg_dinner(message):
    lunch_time = message.text
    breakfast_time = user_temp[message.chat.id]['breakfast']
    
    try:
        if not check_4h(breakfast_time, lunch_time):
            bot.send_message(message.chat.id, "⚠️ Время между завтраком и обедом меньше 4 часов. Не рекомендуется.")
        
        user_temp[message.chat.id]['lunch'] = lunch_time
        bot.send_message(message.chat.id, "Время ужина:")
        bot.register_next_step_handler(message, reg_train)
    except ValueError:
        bot.send_message(message.chat.id, "Некорректный формат времени. Повторите попытку.")


# Выбор времени тренировки
def reg_train(message):
    user_temp[message.chat.id]['dinner'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Без тренировок")
    bot.send_message(message.chat.id, "Время тренировки:", reply_markup=markup)
    bot.register_next_step_handler(message, reg_final)


# Завершение регистрации
def reg_final(message):
    train_time = message.text
    user_temp[message.chat.id]['train'] = train_time
    print(f"Пользователь завершил регистрацию: {user_temp}")
    bot.send_message(message.chat.id, "✅ Ты принят в диетический марафон! Путь начался.",
                     reply_markup=types.ReplyKeyboardRemove())


# --- УПРАВЛЕНИЕ ---


# Команда /menu
@bot.message_handler(commands=['menu'])
def menu_cmd(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Изменить Завтрак", callback_data="change_breakfast"),
        types.InlineKeyboardButton("Изменить Обед", callback_data="change_lunch"),
        types.InlineKeyboardButton("Изменить Ужин", callback_data="change_dinner")
    )
    bot.send_message(message.chat.id, "Вы хотите изменить время приема пищи?", reply_markup=markup)


# Команда /stats
@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    # Пока мы игнорируем статистику, поскольку база данных отсутствует
    bot.send_message(message.chat.id, "Эта команда станет доступна позже.")


# Команда /pay
@bot.message_handler(commands=['pay'])
def pay_cmd(message):
    bot.send_message(message.chat.id, f"Твоя подписка активна до: (дата).\n\nДля продления перевода 349 рублей на `{PAY_PHONE}` (СПБ) и отправь фото чека.",
                    parse_mode="Markdown")
    
    # Команда "/donate"
@bot.message_handler(commands=['donate'])
def donate_cmd(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("100₽", callback_data="donation_100"),
        types.InlineKeyboardButton("500₽", callback_data="donation_500")
    )
    bot.send_message(message.chat.id, "Поддержать проект:", reply_markup=markup)


# Команда /stop
@bot.message_handler(commands=['stop'])
def stop_cmd(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("ДА, я слабак", "НЕТ, я сильный")
    bot.send_message(message.chat.id, "Ты действительно хочешь выйти из марафона? Прогресс будет потерян!",
                     reply_markup=markup)




# Обработка выбора пользователя при выходе
@bot.message_handler(func=lambda m: m.text in ["ДА, я слабак", "НЕТ, я сильный"])
def stop_confirm(message):
    if "ДА, я слабак" in message.text:
        # Здесь должна быть логика удаления пользователя из базы данных
        bot.send_message(message.chat.id, "Ты выбыл. Возвращайся в толпу. ", reply_markup=types.ReplyKeyboardRemove())
    else:
        bot.send_message(message.chat.id, "Правильный выбор, кремень не ломается! ", reply_markup=types.ReplyKeyboardRemove())


@bot.message_handler(content_types=['photo'])
def receipt(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Подтвердить платеж", callback_data=f"confirm_payment_{message.chat.id}"),
        types.InlineKeyboardButton("❌ Отменить платеж", callback_data=f"cancel_payment_{message.chat.id}")
    )
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"Чек от @{message.from_user.username}", reply_markup=markup)
    bot.send_message(message.chat.id, "Ваш чек отправлен на проверку администратору.")

# Обработчик подтверждения платежа администратором
@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_payment_"))
def confirm_payment(call):
    user_id = int(call.data.split("_")[2])
    bot.send_message(user_id, "✅ Ваша оплата подтверждена! Доступ продлен на 30 дней.")
    bot.answer_callback_query(call.id, "Оплата подтверждена!")

# Обработчик отмены платежа администратором
@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_payment_"))
def cancel_payment(call):
    user_id = int(call.data.split("_")[2])
    bot.send_message(user_id, "🔍 Ваш платёж отклонён администратором.")
    bot.answer_callback_query(call.id, "Платеж отменён.")

# Обработка callback запросов
@bot.callback_query_handler(func=lambda call: True)
def callback_all(call):
    chat_id = call.message.chat.id
    if call.data.startswith("change"):
        new_time_type = call.data.replace("change_", "")
        bot.send_message(chat_id, f"Введите новое время для {new_time_type}:")
        bot.register_next_step_handler_by_chat_id(chat_id, lambda m: process_new_time(m, new_time_type))
    elif call.data.startswith("donation_"):
        amount = call.data.replace("donation_", "")
        bot.send_message(chat_id, f"Спасибо за поддержку! Переведи {amount} руб. на `{PAY_PHONE}`.", parse_mode="Markdown")


# Обработка нового времени приема пищи
def process_new_time(message, time_type):
    user_temp[message.chat.id][time_type] = message.text
    bot.send_message(message.chat.id, f"Новый временной интервал для '{time_type}' установлен на {message.text}.")


if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling()
