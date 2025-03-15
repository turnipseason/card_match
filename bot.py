import telebot
from telebot import types
import psycopg2
from data.db_connect import DatabaseConnection
from source.agent import agent
from dotenv import load_dotenv
import os

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# Загружаем переменные окружения
load_dotenv("config/ggc_env.env")

bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))

db_con = DatabaseConnection()

user_data = {}
user_chat_sessions = {}
error_counters = {}

bot.set_my_commands([
    telebot.types.BotCommand("start", "Запуск бота"),
    telebot.types.BotCommand("cards", "Показать список моих карт"),
    telebot.types.BotCommand("cashback", "Показать доступный по картам кэшбек"),
    telebot.types.BotCommand("match", "Начать час с умным помощником подбора карт"),
    telebot.types.BotCommand("exit", "Выйти из чата с помощником подбора карт"),
    telebot.types.BotCommand("help", "Показать список команд")
])

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('Новый пользователь', callback_data='registre')
    btn2 = types.InlineKeyboardButton('Уже зарегистрирован', callback_data='auth')
    markup.row(btn1, btn2)
    bot.reply_to(message, 'Вы зарегестрированы или нет?', reply_markup=markup)

@bot.message_handler(commands=['cards'])
def show_cards(message):
    """
    Обработчик команды /cards. Возвращает список карт пользователя.
    """
    chat_id = message.chat.id
    user = user_data.get(chat_id)  # Получаем данные пользователя

    if not user:
        bot.send_message(chat_id, "Вы не зарегистрированы.")
        return

    passport_id = user['passport_id']
    print(f"Паспорт: {passport_id}")  # Для отладки
    print(db_con.conn_params)  # Для отладки

    # Получаем карты клиента
    cards = db_con.get_client_cards(passport_id)
    print(f"Карты: {cards}")  # Для отладки

    if not cards:
        bot.send_message(chat_id, "У вас нет зарегистрированных карт.")
    else:
        response = "Ваши карты:\n"
        for card in cards:
            response += (
                f"\n🔹 {card['card_name']} ({card['bank_name']})\n"
                f"Процентная ставка: {int(card['client_rate'])}%\n"
                f"Годовая плата: {card['client_annual_fee']} руб.\n"
                f"ПСК: {card['client_psk'] if card['client_psk'] else 'Не указано'}%\n"
                f"Льготный период: {card['client_grace_period']} дней\n"
                f"Кредитный лимит: {card['credit_limit']} руб.\n"
                f"Максимальный бонус: {card['max_reward'] if card['max_reward'] else 0} руб.\n"
                f"Обычные покупки: {card['usual_purchase'] or 'Не указано'}\n"
            )
        bot.send_message(chat_id, response)


@bot.message_handler(commands=['cashback'])
def show_cashback(message):
    chat_id = message.chat.id
    user = user_data.get(chat_id)

    if not user:
        bot.send_message(chat_id, "Вы не зарегистрированы.")
        return

    passport_id = user['passport_id']

    cursor = db_con.connection.cursor()
    # Получаем список карт клиента
    cursor.execute("SELECT card_id FROM client_card WHERE passport_id = %s", (passport_id,))
    cards = cursor.fetchall()

    if not cards:
        bot.send_message(chat_id, "У вас нет зарегистрированных карт.")
        return

    response = "📢 Ваши категории кешбека:\n"

    for card in cards:
        card_id = card[0]  # Берем card_id из запроса

        cursor.execute(
            """
            SELECT 
                ccc.passport_id,
                ccc.card_id,
                c.name AS card_name,
                cb.name AS cashback_category_name,
                ccc.cashback_rate,
                ccc.created_at
            FROM client_card_cashback ccc
            JOIN cashback_category cb ON ccc.cashback_category_id = cb.id
            JOIN client_card cc ON ccc.passport_id = cc.passport_id AND ccc.card_id = cc.card_id
            JOIN card c ON cc.card_id = c.id
            WHERE ccc.passport_id = %s AND ccc.card_id = %s;
            """, (passport_id, card_id)
        )

        cashbacks = cursor.fetchall()

        if not cashbacks:
            response += f"\n💳 Карта : Нет кешбэка\n"
        else:
            response += f"\n💳 Карта {cashbacks[0][2]} :\n"
            for cashback in cashbacks:
                response += (f"🔹 {cashback[3]} — {cashback[4]}%\n")  # Категория + кешбэк%

    bot.send_message(chat_id, response)

@bot.message_handler(commands=['help'])
def help_command(message):
    commands = [
        "/start - Запуск бота",
        "/cards - Посмотреть список доступных карт",
        "/cashback - Посмотреть доступный по картам кэшбек",
        "/match - Начать чат с умным помощником подбора карт",
        "/exit - Выйти из чата с умным помощником подбора карт",
        "/help - Показать список команд"
    ]
    bot.send_message(message.chat.id, "📜 Доступные команды:\n" + "\n".join(commands))

@bot.callback_query_handler(func=lambda callback: True)
def callback_auth(callback):
    chat_id = callback.message.chat.id
    print(f"chat_id: {chat_id}")
    if callback.data == 'registre':
        bot.send_message(chat_id, "Введите ваши паспортные данные (Серия и номер без пробела):")
        bot.register_next_step_handler_by_chat_id(chat_id, get_passport)
    elif callback.data == 'auth':
        bot.send_message(chat_id, "Введите ваш паспортный номер для проверки:")
        bot.register_next_step_handler_by_chat_id(chat_id, check_user)
    elif callback.data in ['cashback', 'bonus', 'both', 'none']:
        save_preferences(callback)

def get_passport(message):
    chat_id = message.chat.id
    passport_id = message.text.strip()

    if len(passport_id) != 10 or not passport_id.isdigit():
        bot.send_message(chat_id, "Некорректный номер паспорта. Попробуйте еще раз.")
        return bot.register_next_step_handler_by_chat_id(chat_id, get_passport)

    user_data[chat_id] = {'passport_id': passport_id}
    bot.send_message(chat_id, "Введите ваше ФИО (Фамилия Имя Отчество):")
    bot.register_next_step_handler_by_chat_id(chat_id, get_full_name)


def get_full_name(message):
    chat_id = message.chat.id
    full_name = message.text.strip().split()

    if len(full_name) < 2:
        bot.send_message(chat_id, "Некорректное ФИО. Введите еще раз:")
        return bot.register_next_step_handler_by_chat_id(chat_id, get_full_name)

    user_data[chat_id].update({
        'last_name': full_name[0],
        'first_name': full_name[1],
        'middle_name': full_name[2] if len(full_name) > 2 else None
    })

    ask_preferences(chat_id)


def ask_preferences(chat_id):
    """Функция для отправки пользователю кнопок с вариантами выбора."""
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('Кешбек', callback_data='cashback')
    btn2 = types.InlineKeyboardButton('Бонусы', callback_data='bonus')
    btn3 = types.InlineKeyboardButton('Кешбек и бонусы', callback_data='both')
    btn4 = types.InlineKeyboardButton('Ничего', callback_data='none')
    markup.row(btn1, btn2)
    markup.row(btn3, btn4)

    bot.send_message(chat_id, "Что вы предпочитаете?", reply_markup=markup)

def save_preferences(callback):
    """Функция для сохранения предпочтений в БД."""
    chat_id = callback.message.chat.id
    choice = callback.data

    # Определяем значения для prefers_cashback и prefers_bonus
    preferences = {
        'cashback': (True, False),
        'bonus': (False, True),
        'both': (True, True),
        'none': (False, False)
    }

    prefers_cashback, prefers_bonus = preferences[choice]

    # Сохраняем в базу данных
    save_user_to_db(chat_id, prefers_cashback, prefers_bonus)


def save_user_to_db(chat_id, prefers_cashback, prefers_bonus):
    """Функция для сохранения данных пользователя в БД."""
    user = user_data.get(chat_id)
    if not user:
        return

    try:
        cursor = db_con.connection.cursor()
        cursor.execute(
            "INSERT INTO client (passport_id, first_name, last_name, middle_name, prefers_cashback, prefers_bonus) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (user['passport_id'], user['first_name'], user['last_name'], user['middle_name'], prefers_cashback, prefers_bonus)
        )
        db_con.connection.commit()
        bot.send_message(chat_id, "Поздравляю! 🎉 Вы успешно зарегистрированы в системе!")
    except psycopg2.IntegrityError:
        db_con.connection.rollback()
        bot.send_message(chat_id, "Ошибка: Этот паспорт уже зарегистрирован.")
    finally:
        user_data.pop(chat_id, None)

def check_user(message):
    """Функция для проверки пользователя по паспортным данным."""
    chat_id = message.chat.id
    passport_id = message.text.strip()

    cursor = db_con.connection.cursor()
    cursor.execute("SELECT first_name, last_name, middle_name FROM client WHERE passport_id = %s", (passport_id,))
    user = cursor.fetchone()

    if user:
        bot.send_message(chat_id, f"Добро пожаловать, {user[1]} {user[0]}!")
        user_data[chat_id] = {'passport_id': passport_id}
        check_and_request_card_details(chat_id, passport_id)
    else:
        bot.send_message(chat_id, "Пользователь не найден. Попробуйте еще раз или зарегистрируйтесь.")

def check_and_request_card_details(chat_id, passport_id):
    cursor = db_con.connection.cursor()
    cursor.execute(
        """
        SELECT cc.card_id, c.name, c.bank_name 
        FROM client_card cc
        JOIN card c ON cc.card_id = c.id
        WHERE cc.passport_id = %s 
        AND (cc.rate IS NULL OR cc.annual_fee IS NULL OR cc.grace_period IS NULL OR cc.credit_limit IS NULL)
        """, (passport_id,)
    )
    incomplete_cards = cursor.fetchall()

    if incomplete_cards:
        user_data[chat_id] = {
            'passport_id': passport_id,
            'cards': [{'card_id': card[0], 'name': card[1], 'bank_name': card[2]} for card in incomplete_cards]
        }
        bot.send_message(chat_id, "У вас есть карты с незаполненными полями. Давайте их заполним!")
        request_card_details(chat_id)
    else:
        bot.send_message(chat_id, "Все данные по вашим картам уже заполнены.")

def request_card_details(chat_id):
    if not user_data.get(chat_id) or not user_data[chat_id]['cards']:
        bot.send_message(chat_id, "Все карты обновлены. Спасибо!")
        return

    card = user_data[chat_id]['cards'].pop(0)
    user_data[chat_id]['current_card'] = card['card_id']
    bot.send_message(chat_id, f"Заполняем данные для карты \"{card['name']}\" банка \"{card['bank_name']}\".")

    bot.send_message(chat_id, "Введите процентную ставку (например, 19.5):")
    bot.register_next_step_handler_by_chat_id(chat_id, get_rate)


def get_rate(message):
    chat_id = message.chat.id
    try:
        rate = float(message.text)
        user_data[chat_id]['rate'] = rate
        bot.send_message(chat_id, "Введите годовую плату (если нет, укажите 0):")
        bot.register_next_step_handler_by_chat_id(chat_id, get_annual_fee)
    except ValueError:
        bot.send_message(chat_id, "Некорректное значение. Введите процентную ставку снова:")
        bot.register_next_step_handler_by_chat_id(chat_id, get_rate)

def get_annual_fee(message):
    chat_id = message.chat.id
    try:
        annual_fee = int(message.text)
        user_data[chat_id]['annual_fee'] = annual_fee
        bot.send_message(chat_id, "Введите полную стоимость кредита (PSK) в процентах:")
        bot.register_next_step_handler_by_chat_id(chat_id, get_psk)
    except ValueError:
        bot.send_message(chat_id, "Некорректное значение. Введите годовую плату снова:")
        bot.register_next_step_handler_by_chat_id(chat_id, get_annual_fee)

def get_psk(message):
    chat_id = message.chat.id
    try:
        psk = float(message.text)
        user_data[chat_id]['psk'] = psk
        bot.send_message(chat_id, "Введите льготный период (в днях):")
        bot.register_next_step_handler_by_chat_id(chat_id, get_grace_period)
    except ValueError:
        bot.send_message(chat_id, "Некорректное значение. Введите PSK снова:")
        bot.register_next_step_handler_by_chat_id(chat_id, get_psk)

def get_grace_period(message):
    chat_id = message.chat.id
    try:
        grace_period = int(message.text)
        user_data[chat_id]['grace_period'] = grace_period
        bot.send_message(chat_id, "Введите кредитный лимит (например, 100000):")
        bot.register_next_step_handler_by_chat_id(chat_id, get_credit_limit)
    except ValueError:
        bot.send_message(chat_id, "Некорректное значение. Введите льготный период снова:")
        bot.register_next_step_handler_by_chat_id(chat_id, get_grace_period)

def get_credit_limit(message):
    chat_id = message.chat.id
    try:
        credit_limit = int(message.text)
        user_data[chat_id]['credit_limit'] = credit_limit
        save_card_details(chat_id)
    except ValueError:
        bot.send_message(chat_id, "Некорректное значение. Введите кредитный лимит снова:")
        bot.register_next_step_handler_by_chat_id(chat_id, get_credit_limit)

def save_card_details(chat_id):
    data = user_data.get(chat_id)
    if not data:
        return

    try:
        cursor = db_con.connection.cursor()
        cursor.execute(
            """
            UPDATE client_card
            SET rate = %s, annual_fee = %s, psk = %s, grace_period = %s, credit_limit = %s
            WHERE passport_id = %s AND card_id = %s
            """,
            (data['rate'], data['annual_fee'], data['psk'], data['grace_period'], data['credit_limit'], data['passport_id'], data['current_card'])
        )
        db_con.connection.commit()

        bot.send_message(chat_id, "Данные успешно сохранены! ✅")
        request_card_details(chat_id)
    except psycopg2.Error as e:
        db_con.connection.rollback()
        bot.send_message(chat_id, f"Ошибка при сохранении данных: {e}")

@bot.message_handler(commands=['match'])
def start_match(message):
    chat_id = message.chat.id
    print(f"Используем chat_id из msg_hndlr_match:{chat_id}")
    error_counters[chat_id] = 0
    thread_id = str(chat_id)  # Используем chat_id в качестве thread_id
    user_chat_sessions[chat_id] = thread_id
    print(f"Используем thread_id:{thread_id}")
    print(f"user_chat_sessions:{user_chat_sessions}")
    print(f"user_chat_sessions[chat_id]:{ user_chat_sessions[chat_id]}")
    bot.send_message(chat_id, "Напишите ваш запрос или отправьте /exit для выхода.")


@bot.message_handler(commands=['exit'])
def exit_match(message):
    chat_id = message.chat.id
    print(f"Используем chat_id из msg_hndlr_exit:{chat_id}")
    print(f"user_chat_sessions:{user_chat_sessions}")
    if chat_id in user_chat_sessions:
        del user_chat_sessions[chat_id]
        del error_counters[chat_id]  # Удаляем счетчик ошибок
        bot.send_message(chat_id, "Рад помочь!")
    else:
        print("Пользователь не находится в чате с агентом.")


@bot.message_handler(func=lambda message: message.chat.id in user_chat_sessions)
def chat_with_agent(message):
    chat_id = message.chat.id

    thread_id = user_chat_sessions[chat_id]
    print(f"thread_id:{thread_id}")
    user = user_data.get(chat_id)
    print(f"user:{user}")
    passport_id = user["passport_id"]

    print(f"Используем chat_id из msg_hndlr_exit:{chat_id}")
    print(f"user_chat_sessions:{user_chat_sessions}")

    config = {"configurable": {"thread_id": thread_id,"passport_id": passport_id}}
    print(f"\nPassport and thread config:{config}")
    try:
        context = AIMessage(content=f"Серия и номер паспорта пользователя:{passport_id}")
        print(f"context_message:{context}")
        response = agent.invoke({
            "messages": [
                context,
                ("user", message.text)
            ]
        }, config={"configurable": {"thread_id": thread_id}})

        bot.send_message(chat_id, response["messages"][-1].content)
        error_counters[chat_id] = 0

    except Exception as e:
        error_counters[chat_id] += 1
        print(f"Ошибка: {e}")
        bot.send_message(chat_id, f"🤖 Извините, технические неполадки! 🤖")
        print(f"num_consecutive_errors:{error_counters[chat_id]}")
        if error_counters[chat_id] >= 3:
            del user_chat_sessions[chat_id]
            del error_counters[chat_id]
            bot.send_message(chat_id, f"🤖 Всё совсем плохо :( \n Пожалуйста, вернитесь в режим подбора попозже! 🤖")

bot.polling(none_stop=True)


