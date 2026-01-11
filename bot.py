import os
import telebot
from telebot import types
from datetime import datetime, timedelta
import database as db
from flask import Flask
import threading
import time
import re
import pytz # Для работы с Московским временем
from dotenv import load_dotenv
from gigachat import GigaChat

load_dotenv()

TOKEN = os.getenv("TG_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
PAY_PHONE = os.getenv("PAYMENT_PHONE")
os.getenv("GIGACHAT_CREDENTIALS") # Ключ от Сбера

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
user_temp = {}
moscow_tz = pytz.timezone('Europe/Moscow')

@app.route('/')
def health(): return "STEEL CORE LIVE", 200

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def validate_time(text):
    return re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', text)


# НАСТОЯЩИЙ ИИ GIGACHAT
def ai_calories(text):
    # Берем ключ из .env
    giga_key = os.getenv("GIGACHAT_CREDENTIALS")
    try:
        with GigaChat(credentials=giga_key, verify_ssl_certs=False) as giga:
            # Просим ИИ выдать только цифру
            prompt = f"Сколько калорий в этом приеме пищи: '{text}'? Напиши ТОЛЬКО ЦИФРУ. Если не знаешь, напиши 300."
            response = giga.chat(prompt)
            # Убираем всё лишнее, оставляем только цифры
            result = ''.join(filter(str.isdigit, response.choices[0].message.content))
            return int(result) if result else 300
    except Exception as e:
        print(f"Ошибка ИИ: {e}")
        return 300 # Если ИИ упал, запишем среднее


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
def reg_start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Похудение", "Поддержание формы", "Набор мышечной массы", "Набор жировой массы")
    bot.send_message(message.chat.id, "В какой сфере вы хотите двигаться?", reply_markup=markup)
    bot.register_next_step_handler(message, reg_goal)

# Регистрация возраста 
def reg_goal(message):
    user_temp[message.chat.id] = {'goal': message.text}
    bot.send_message(message.chat.id, "Твой возраст (минимум 10 лет):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, reg_age)

# Регистрация текущего веса
def reg_age(message):
    cid = message.chat.id
    try:
        age = int(message.text)
        if age < 10:
            bot.send_message(cid, "⚠️ Регистрация доступна только с 10 лет. Введи корректный возраст:")
            bot.register_next_step_handler(message, reg_age)
            return
        user_temp[cid]['age'] = age
        bot.send_message(cid, "Твой текущий вес (кг, минимум 25):")
        bot.register_next_step_handler(message, reg_weight)
    except:
        bot.send_message(cid, "Введи возраст числом:")
        bot.register_next_step_handler(message, reg_age)

# Регистрация желаемого веса
def reg_weight(message):
    cid = message.chat.id
    try:
        weight = float(message.text)
        if weight < 25:
            bot.send_message(cid, "⚠️ Вес должен быть не менее 25 кг. Введи заново:")
            bot.register_next_step_handler(message, reg_weight)
            return
        user_temp[cid]['weight'] = weight
        bot.send_message(cid, "Желаемый вес (кг):")
        bot.register_next_step_handler(message, reg_target)
    except:
        bot.send_message(cid, "Введи вес числом:")
        bot.register_next_step_handler(message, reg_weight)

# Регистрация пола 
def reg_target(message):
    cid = message.chat.id
    try:
        target = float(message.text)
        current = user_temp[cid]['weight']
        goal = user_temp[cid]['goal']
        
        # Ваня, тут твоя логика проверок:
        if goal == "Набор жировой массы" and target > current + 60:
            target = current + 60
            bot.send_message(cid, f"⚠️ Лимит набора жира — 60кг. Установлено: {target}кг")
        elif goal == "Набор мышечной массы" and target > current + 50:
            target = current + 50
            bot.send_message(cid, f"⚠️ Лимит набора мышц — 50кг. Установлено: {target}кг")
        elif goal == "Похудение" and target < current - 20:
            target = current - 20
            bot.send_message(cid, f"⚠️ Безопасный предел похудения — 20кг. Установлено: {target}кг")

        user_temp[cid]['target'] = target
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Мужской", "Женский")
        bot.send_message(cid, "Твой пол:", reply_markup=markup)
        bot.register_next_step_handler(message, reg_sub_warn)
    except:
        bot.send_message(cid, "Введи вес числом:")
        bot.register_next_step_handler(message, reg_target)

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
    cid = message.chat.id
    t = message.text
    if not validate_time(t):
        bot.send_message(cid, "⚠️ Неверный формат! Введи время как 08:30:")
        bot.register_next_step_handler(message, reg_lunch)
        return
    user_temp[cid]['breakfast'] = t
    bot.send_message(cid, "Время обеда (не ранее 4 часов после завтрака):")
    bot.register_next_step_handler(message, reg_dinner)

# Время ужина 
def reg_dinner(message):
    cid = message.chat.id
    lunch_time = message.text
    if not validate_time(lunch_time):
        bot.send_message(cid, "⚠️ Неверный формат! Введи время как 13:00:")
        bot.register_next_step_handler(message, reg_dinner)
        return
        
    breakfast_time = user_temp[cid]['breakfast']
    if not check_4h(breakfast_time, lunch_time):
        bot.send_message(cid, "⚠️ Время между завтраком и обедом меньше 4 часов. Не рекомендуется.")
        
    user_temp[cid]['lunch'] = lunch_time
    bot.send_message(cid, "Время ужина:")
    bot.register_next_step_handler(message, reg_train)


# Выбор времени тренировки
def reg_train(message):
    cid = message.chat.id
    # Сохраняем время ужина, которое пришло с прошлого шага
    user_temp[cid]['dinner'] = message.text
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Без тренировок")
    bot.send_message(cid, "Введи время тренировки (например, 18:00) или нажми кнопку:", reply_markup=markup)
    # ПЕРЕХОДИМ К ФИНАЛУ
    bot.register_next_step_handler(message, reg_final)

# Завершение регистрации
def reg_final(message):
    cid = message.chat.id
    train_time = message.text
    user_temp[cid]['train'] = train_time
    
    try:
        u = user_temp[cid]
        # Важно: время подписки
        sub_end = datetime.now() + timedelta(days=7)
        
        # Собираем данные. ПРОВЕРЬ, ЧТОБЫ В database.py save_user ПРИНИМАЛ ИМЕННО СТОЛЬКО АРГУМЕНТОВ
        data = (
            cid, 
            message.from_user.username or "User", 
            u.get('goal', 'Не указано'), 
            u.get('age', 0), 
            u.get('weight', 0), 
            u.get('target', 0), 
            u.get('gender', 'Не указан'), 
            u.get('breakfast', '08:00'), 
            u.get('lunch', '13:00'), 
            u.get('dinner', '19:00'), 
            train_time, 
            sub_end
        )
        
        db.save_user(data) # Пытаемся сохранить
        
        bot.send_message(cid, "✅ Твой путь в STEEL CORE начался! Данные сохранены.",
                         reply_markup=types.ReplyKeyboardRemove())
        print(f"Пользователь {cid} успешно зарегистрирован.")
        
    except Exception as e:
        # Если будет ошибка в базе - бот напишет её в консоль и тебе в чат
        print(f"ОШИБКА ПРИ СОХРАНЕНИИ: {e}")
        bot.send_message(cid, f"❌ Ошибка при сохранении данных: {e}. Обратись к админу.")
        
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
    cid = message.chat.id
    if "ДА" in message.text:
        db.delete_user(cid) # ВЫЗЫВАЕМ УДАЛЕНИЕ ИЗ database.py
        bot.send_message(cid, "Твои данные удалены. Ты вернулся в толпу.", 
                         reply_markup=types.ReplyKeyboardRemove())
    else:
        bot.send_message(cid, "Правильный выбор! Кремень не ломается. Продолжаем путь!", 
                         reply_markup=types.ReplyKeyboardRemove())

        
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
    bot.send_message(user_id, "🔍 Ваш платёж отклонён, обратитесь к администратору @Ivanka58.")
    bot.answer_callback_query(call.id, "Платеж отменён.")

# Составление меню
def get_ai_menu(chat_id, meal_type):
    user = db.get_user(chat_id) # Получаем данные юзера из базы
    if not user: return "Овсянка на воде"
    
    # Распаковываем данные (порядок как в твоей таблице)
    _, _, goal, age, weight, target, gender, _, _, _, _, _, _ = user
    
    giga_key = os.getenv("GIGACHAT_CREDENTIALS")
    try:
        with GigaChat(credentials=giga_key, verify_ssl_certs=False) as giga:
            prompt = (f"Ты диетолог STEEL CORE. Составь меню на {meal_type} для пользователя: "
                      f"Пол: {gender}, Возраст: {age}, Вес: {weight}кг, Цель: {goal} до {target}кг. "
                      f"Напиши ТОЛЬКО список продуктов и блюд, кратко, без лишних слов.")
            response = giga.chat(prompt)
            return response.choices[0].message.content
    except:
        return "Куриная грудка и гречка (ошибка ИИ)"


def process_meal_step(message):
    chat_id = message.chat.id
    food_description = message.text # Это то, что написал юзер (например, "3 яйца")
    
    bot.send_message(chat_id, "🔄 ИИ анализирует состав блюда...")
    
    # 1. Вызываем GigaChat (функцию ai_calories, которую мы добавили раньше)
    calories = ai_calories(food_description)
    
    # 2. Записываем в базу данных
    # Параметры: chat_id, калории, тип приема пищи, описание еды
    db.log_food(chat_id, calories, "Обычный прием", food_description)
    
    # 3. Отвечаем пользователю
    bot.send_message(chat_id, f"✅ Записано! По моим подсчетам это примерно {calories} ккал.\nТвой прогресс сохранен в базе.")

    
# --- CALLBACKS ---

@bot.callback_query_handler(func=lambda call: True)
def callback_all(call):
    chat_id = call.message.chat.id
    if call.data.startswith("change"):
        new_time_type = call.data.replace("change_", "")
        bot.send_message(chat_id, f"Введите новое время для {new_time_type}:")
        bot.register_next_step_handler_by_chat_id(chat_id, lambda m: process_new_time(m, new_time_type))
    elif call.data == "i_ate":
        bot.send_message(chat_id, "Отправь список того, что ты съел (например: 2 вареных яйца и стакан молока):")
    # Теперь мы регистрируем переход к функции process_meal_step
        bot.register_next_step_handler_by_chat_id(chat_id, process_meal_step)
    elif call.data.startswith("donation_"):
        amount = call.data.replace("donation_", "")
        bot.send_message(chat_id, f"Спасибо за поддержку! Переведи {amount} руб. на `{PAY_PHONE}`.", parse_mode="Markdown")
def process_new_time(message, time_type):
    bot.send_message(message.chat.id, f"Новый интервал для '{time_type}' установлен на {message.text}.")

# --- НАПОМИНАНИЯ (SCHEDULER) ---

def reminder_thread():
    while True:
        try:
            now = datetime.now(moscow_tz).strftime("%H:%M")
            hour_later = (datetime.now(moscow_tz) + timedelta(hours=1)).strftime("%H:%M")
            users = db.get_active_reminders()
            
            for u in users:
                cid, b, l, d, train, name = u
                # За час до еды
                if b == hour_later or l == hour_later or d == hour_later:
                    menu = get_ai_menu(cid, "завтрак") # или обед/ужин
                    bot.send_message(cid, f"🔔 {name}, через час прием пищи!\n\n🥗 РЕКОМЕНДОВАННОЕ МЕНЮ:\n{menu}")
                # Время еды
                if b == now or l == now or d == now:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("✅ Я поел", callback_data="i_ate"))
                    bot.send_message(cid, "🍴 Время еды! Нажми кнопку после приема:", reply_markup=markup)
            
            time.sleep(60)
        except Exception as e:
            print(f"Ошибка планировщика: {e}")
            time.sleep(60)

db.init_db() # Принудительное создание таблиц при запуске бота

if __name__ == '__main__':
    threading.Thread(target=reminder_thread, daemon=True).start()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling()

