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
        return abs(diff.total_seconds() / 3600) >= 4
    except: return True

# --- КОМАНДА /START ---
@bot.message_handler(commands=['start'])
def start(message):
    db.init_db()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Начать путь 🚀")
    bot.send_message(message.chat.id, 
        "Привет. Ты в системе **STEEL CORE**. Это бот-наставник для тех, кто готов выйти из толпы и созидать своё тело.\n\n"
        "Я буду контролировать твоё питание, тренировки и дисциплину.\n"
        "Слабакам здесь не место. Чтобы начать, жми кнопку ниже.", 
        parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Начать путь 🚀")
def reg_goal(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Похудение", "Поддержание формы", "Набор мышечной массы", "Набор жировой массы")
    bot.send_message(message.chat.id, "В какой сфере вы хотите двигаться?", reply_markup=markup)
    bot.register_next_step_handler(message, reg_age)

def reg_age(message):
    user_steps[message.chat.id] = {'goal': message.text}
    bot.send_message(message.chat.id, "Введите ваш возраст:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, reg_weight)

def reg_weight(message):
    user_steps[message.chat.id]['age'] = message.text
    bot.send_message(message.chat.id, "Ваш текущий вес (кг):")
    bot.register_next_step_handler(message, reg_target_weight)

def reg_target_weight(message):
    user_steps[message.chat.id]['weight'] = message.text
    bot.send_message(message.chat.id, "Ваш желаемый вес (кг):")
    bot.register_next_step_handler(message, reg_gender)

def reg_gender(message):
    user_steps[message.chat.id]['target'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Мужской", "Женский")
    bot.send_message(message.chat.id, "Ваш пол:", reply_markup=markup)
    bot.register_next_step_handler(message, reg_sub_warning)

def reg_sub_warning(message):
    user_steps[message.chat.id]['gender'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Я согласен(а)")
    bot.send_message(message.chat.id, 
        "⚠️ **ПРЕДУПРЕЖДЕНИЕ**\n\nПервая неделя бесплатная. Далее подписка составит **349 рублей в месяц**.\n"
        "Автосписаний нет, я буду напоминать об оплате.\n"
        "Согласны продолжать?", parse_mode="Markdown", reply_markup=markup)
    bot.register_next_step_handler(message, reg_breakfast)

def reg_breakfast(message):
    bot.send_message(message.chat.id, "Введите желаемое время ЗАВТРАКА (например, 08:00):", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, reg_lunch)

def reg_lunch(message):
    user_steps[message.chat.id]['b'] = message.text
    bot.send_message(message.chat.id, "Введите время ОБЕДА (не менее 4ч после завтрака):")
    bot.register_next_step_handler(message, reg_dinner)

def reg_dinner(message):
    l_time = message.text
    b_time = user_steps[message.chat.id]['b']
    if not check_gap(b_time, l_time):
        bot.send_message(message.chat.id, "⚠️ Время между завтраком и обедом меньше 4 часов. Это не рекомендуется.")
    user_steps[message.chat.id]['l'] = l_time
    bot.send_message(message.chat.id, "Введите время УЖИНА (не менее 4ч после обеда):")
    bot.register_next_step_handler(message, reg_train)

def reg_train(message):
    user_steps[message.chat.id]['d'] = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Без тренировок")
    bot.send_message(message.chat.id, "Введите время ТРЕНИРОВКИ (или нажмите кнопку ниже):", reply_markup=markup)
    bot.register_next_step_handler(message, reg_finish)

def reg_finish(message):
    cid = message.chat.id
    train = message.text
    if train == "Без тренировок":
        bot.send_message(cid, "⚠️ Вы уверены? Без тренировок диета малоэффективна.")
    
    u = user_steps[cid]
    trial_end = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    # Сохранение в базу
    data = (cid, message.from_user.username, u['goal'], int(u['age']), float(u['weight']), 
            float(u['target']), u['gender'], u['b'], u['l'], u['d'], train, trial_end)
    db.save_user(data)
    
    bot.send_message(cid, "🔥 **Вы приняты в диетический марафон!**\n\nЯ начну контролировать тебя завтра утром. Подготовь волю.", parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())

# --- КОМАНДЫ ПОДДЕРЖКИ ---
@bot.message_handler(commands=['pay'])
def cmd_pay(message):
    user = db.get_user(message.chat.id)
    if user:
        bot.send_message(message.chat.id, 
            f"Ваш пробный период/подписка до: {user[10]}\n\n"
            f"Для продления переведите 349р на `{PAY_PHONE}` и пришлите скрин чека.", parse_mode="Markdown")
        bot.register_next_step_handler(message, handle_receipt)

def handle_receipt(message):
    if not message.photo:
        bot.send_message(message.chat.id, "Пришлите фото чека.")
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Одобрить", callback_data=f"ok_{message.chat.id}"))
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"Чек от @{message.from_user.username}", reply_markup=markup)
    bot.send_message(message.chat.id, "Чек на проверке.")

@bot.message_handler(commands=['donate'])
def cmd_donate(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("100р", callback_data="d_100"), 
               types.InlineKeyboardButton("500р", callback_data="d_500"))
    bot.send_message(message.chat.id, "Хотите поддержать создателя?", reply_markup=markup)

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("ДА, я слабак", "НЕТ, я остаюсь")
    bot.send_message(message.chat.id, "Вы уверены, что хотите выбыть? Весь процесс сбросится.", reply_markup=markup)
    bot.register_next_step_handler(message, confirm_stop)

def confirm_stop(message):
    if message.text == "ДА, я слабак":
        db.delete_user(message.chat.id)
        bot.send_message(message.chat.id, "Вы выбыли из системы. Возвращайтесь в толпу.", reply_markup=types.ReplyKeyboardRemove())
    else:
        bot.send_message(message.chat.id, "Правильный выбор. Продолжаем.", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(commands=['menu'])
def cmd_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Перенос Завтрака", callback_data="edit_b"),
               types.InlineKeyboardButton("Перенос Обеда", callback_data="edit_l"),
               types.InlineKeyboardButton("Перенос Ужина", callback_data="edit_d"))
    bot.send_message(message.chat.id, "Что вы хотите изменить?", reply_markup=markup)

@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    logs = db.get_daily_calories(message.chat.id)
    total = sum([l[1] for l in logs])
    bot.send_message(message.chat.id, f"📊 Отчет за сегодня:\nВсего калорий: {total}")

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data.startswith('ok_'):
        uid = call.data.split('_')[1]
        db.update_subscription(int(uid), 30)
        bot.send_message(uid, "✅ Подписка продлена!")
        bot.answer_callback_query(call.id, "Готово")
    elif call.data.startswith('d_'):
        bot.send_message(call.message.chat.id, f"Переведите сумму на `{PAY_PHONE}`. Спасибо за поддержку!", parse_mode="Markdown")

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling()
