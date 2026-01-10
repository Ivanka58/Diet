import os
import telebot
from telebot import types
from datetime import datetime, timedelta
import database as db
from flask import Flask
import threading
import time
import re
import pytz 
from dotenv import load_dotenv
from gigachat import GigaChat # Импортируем GigaChat

load_dotenv()

TOKEN = os.getenv("TG_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
PAY_PHONE = os.getenv("PAYMENT_PHONE")
GIGA_CREDS = os.getenv("GIGACHAT_CREDENTIALS") # Ключ от Сбера

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
    try:
        with GigaChat(credentials=GIGA_CREDS, verify_ssl_certs=False) as giga:
            prompt = f"Ты диетолог STEEL CORE. Посчитай калории в этом блюде: '{text}'. Выдай ТОЛЬКО ОДНО ЧИСЛО. Если не понимаешь, выдай 300."
            response = giga.chat(prompt)
            # Извлекаем только цифры из ответа
            result = ''.join(filter(str.isdigit, response.choices[0].message.content))
            return int(result) if result else 300
    except Exception as e:
        print(f"Ошибка GigaChat: {e}")
        return 0

def check_4h(t1, t2):
    try:
        fmt = '%H:%M'
        diff = abs((datetime.strptime(t2, fmt) - datetime.strptime(t1, fmt)).total_seconds()) / 3600
        return diff >= 4
    except: return True

# --- КОМАНДЫ ---

@bot.message_handler(commands=['start'])
def start_cmd(message):
    db.init_db()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Начать свой путь 🚀")
    bot.send_message(message.chat.id, 
                     "Привет. Ты в системе STEEL CORE.\n"
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
    bot.send_message(message.chat.id, "Твой возраст (минимум 10 лет):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, reg_age)

def reg_age(message):
    cid = message.chat.id
    try:
        age = int(message.text)
        if age < 10:
            bot.send_message(cid, "⚠️ Регистрация только с 10 лет. Введи возраст:")
            bot.register_next_step_handler(message, reg_age)
            return
        user_temp[cid]['age'] = age
        bot.send_message(cid, "Твой текущий вес (кг, минимум 25):")
        bot.register_next_step_handler(message, reg_weight)
    except:
        bot.send_message(cid, "Введи возраст числом:")
        bot.register_next_step_handler(message, reg_age)

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

def reg_target(message):
    cid = message.chat.id
    try:
        target = float(message.text)
        current = user_temp[cid]['weight']
        goal = user_temp[cid]['goal']
        
        if goal == "Набор жировой массы" and target > current + 60:
            target = current + 60
            bot.send_message(cid, f"⚠️ Лимит набора жира — 60кг. Установлено: {target}кг")
        elif goal == "Набор мышечной массы" and target > current + 50:
            target = current + 50
            bot.send_message(cid, f"⚠️ Лимит набора мышц — 50кг. Установлено: {target}кг")
        elif goal == "Похудение" and target < current - 20:
            target = current - 20
            bot.send_message(cid, f"⚠️ Предел похудения — 20кг. Установлено: {target}кг")

        user_temp[cid]['target'] = target
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Мужской", "Женский")
        bot.send_message(cid, "Твой пол:", reply_markup=markup)
        bot.register_next_step_handler(message, reg_sub_warn)
    except:
        bot.send_message(cid, "Введи вес числом:")
        bot.register_next_step_handler(message, reg_target)

def reg_sub_warn(message):
    user_temp[message.chat.id]['gender'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Я согласен, идем дальше")
    bot.send_message(message.chat.id, "⚠️ Первая неделя бесплатно. Далее — 349р/мес. Согласен?", reply_markup=markup)
    bot.register_next_step_handler(message, reg_breakfast)

def reg_breakfast(message):
    bot.send_message(message.chat.id, "Время завтрака (08:00):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, reg_lunch)

def reg_lunch(message):
    cid = message.chat.id
    if not validate_time(message.text):
        bot.send_message(cid, "Ошибка формата (ЧЧ:ММ). Введи время завтрака:")
        bot.register_next_step_handler(message, reg_lunch)
        return
    user_temp[cid]['breakfast'] = message.text
    bot.send_message(cid, "Время обеда:")
    bot.register_next_step_handler(message, reg_dinner)

def reg_dinner(message):
    cid = message.chat.id
    if not validate_time(message.text):
        bot.send_message(cid, "Ошибка формата. Введи время обеда:")
        bot.register_next_step_handler(message, reg_dinner)
        return
    user_temp[cid]['lunch'] = message.text
    bot.send_message(cid, "Время ужина:")
    bot.register_next_step_handler(message, reg_train)

# ИСПРАВЛЕННЫЙ ЭТАП ТРЕНИРОВКИ
def reg_train(message):
    cid = message.chat.id
    if not validate_time(message.text):
        bot.send_message(cid, "Ошибка формата. Введи время ужина:")
        bot.register_next_step_handler(message, reg_train)
        return
    user_temp[cid]['dinner'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Без тренировок")
    bot.send_message(cid, "Время тренировки или напиши 'Без тренировок':", reply_markup=markup)
    bot.register_next_step_handler(message, reg_final)

def reg_final(message):
    cid = message.chat.id
    user_temp[cid]['train'] = message.text
    
    # Сохранение в БД
    u = user_temp[cid]
    sub_end = datetime.now() + timedelta(days=7)
    data = (cid, message.from_user.username, u['goal'], str(u['age']), str(u['weight']), 
            str(u['target']), u['gender'], u['breakfast'], u['lunch'], u['dinner'], u['train'], sub_end)
    db.save_user(data)
    
    bot.send_message(cid, "✅ Регистрация завершена! Твой путь начался.", reply_markup=types.ReplyKeyboardRemove())

# --- УПРАВЛЕНИЕ ---

@bot.message_handler(commands=['menu'])
def menu_cmd(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Изменить Завтрак", callback_data="change_breakfast"),
               types.InlineKeyboardButton("Изменить Обед", callback_data="change_lunch"),
               types.InlineKeyboardButton("Изменить Ужин", callback_data="change_dinner"))
    bot.send_message(message.chat.id, "Изменить время?", reply_markup=markup)

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    res = db.get_daily_stats(message.chat.id)
    if not res: bot.send_message(message.chat.id, "Сегодня данных еще нет.")
    else:
        total = sum(r[1] for r in res)
        bot.send_message(message.chat.id, f"📊 Калории за сегодня: {total} ккал.")

@bot.message_handler(commands=['pay'])
def pay_cmd(message):
    bot.send_message(message.chat.id, f"Для продления переведи 349р на `{PAY_PHONE}` (СПБ) и отправь чек.", parse_mode="Markdown")

@bot.message_handler(commands=['donate'])
def donate_cmd(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("100₽", callback_data="donation_100"),
               types.InlineKeyboardButton("500₽", callback_data="donation_500"))
    bot.send_message(message.chat.id, "Поддержать проект:", reply_markup=markup)

@bot.message_handler(commands=['stop'])
def stop_cmd(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("ДА, я слабак", "НЕТ, я сильный")
    bot.send_message(message.chat.id, "Выйти из марафона?", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["ДА, я слабак", "НЕТ, я сильный"])
def stop_confirm(message):
    if "ДА" in message.text:
        db.delete_user(message.chat.id)
        bot.send_message(message.chat.id, "Ты выбыл.", reply_markup=types.ReplyKeyboardRemove())
    else:
        bot.send_message(message.chat.id, "Кремень!", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(content_types=['photo'])
def receipt(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Одобрить", callback_data=f"admin_ok_{message.chat.id}"),
               types.InlineKeyboardButton("❌ Отказать", callback_data=f"admin_no_{message.chat.id}"))
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"Чек от @{message.from_user.username}", reply_markup=markup)
    bot.send_message(message.chat.id, "Чек на проверке.")

# --- ОБРАБОТКА CALLBACK ЗАПРОСОВ (ВСЕ В ОДНОМ) ---

@bot.callback_query_handler(func=lambda call: True)
def callback_all(call):
    cid = call.message.chat.id
    if call.data.startswith("change"):
        bot.send_message(cid, "Введи новое время (ЧЧ:ММ):")
        bot.register_next_step_handler_by_chat_id(cid, lambda m: bot.send_message(cid, f"Время изменено на {m.text}"))
    elif call.data.startswith("donation_"):
        bot.send_message(cid, f"Переведи {call.data.split('_')[1]}р на {PAY_PHONE}")
    elif call.data.startswith("admin_ok_"):
        uid = int(call.data.split("_")[2])
        db.update_sub(uid, 30)
        bot.send_message(uid, "✅ Оплата подтверждена!")
        bot.answer_callback_query(call.id, "Одобрено")
    elif call.data.startswith("admin_no_"):
        uid = int(call.data.split("_")[2])
        bot.send_message(uid, "❌ Оплата отклонена.")
        bot.answer_callback_query(call.id, "Отклонено")
    elif call.data == "i_ate":
        bot.send_message(cid, "Что ты съел?")
        bot.register_next_step_handler_by_chat_id(cid, process_meal)

def process_meal(message):
    cals = ai_calories(message.text) # Работает ИИ
    db.log_food(message.chat.id, cals, "Meal", message.text)
    bot.send_message(message.chat.id, f"✅ Записано: {cals} ккал. Молодец!")

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
                    bot.send_message(cid, f"🔔 {name or 'Друг'}, через час прием пищи! Твое меню: [Заглушка]")
                # Время еды
                if b == now or l == now or d == now:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("✅ Я поел", callback_data="i_ate"))
                    bot.send_message(cid, "🍴 Время еды! Нажми кнопку после приема:", reply_markup=markup)
            
            time.sleep(60)
        except Exception as e:
            print(f"Ошибка планировщика: {e}")
            time.sleep(60)

if __name__ == '__main__':
    threading.Thread(target=reminder_thread, daemon=True).start()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling()
