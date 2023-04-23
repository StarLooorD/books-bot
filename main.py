import json

import psycopg2
import requests
import telebot
from telebot import types

from book_recommendation_system import find_similar_books
from configs import DATABASE_URL, BOT_TOKEN, GOOGLE_MAP_API_TOKEN
from exceptions import IncorrectBookIndex

connection = psycopg2.connect(DATABASE_URL)

cursor = connection.cursor()

bot = telebot.TeleBot(token=BOT_TOKEN)

main_menu_keyboard = types.ReplyKeyboardMarkup(row_width=2)
btn1 = types.KeyboardButton(text='🪄 Порадити книгу')
btn2 = types.KeyboardButton(text='➕ Додати книгу в улюблені')
btn3 = types.KeyboardButton(text='➖ Видалити книгу з улюблених')
btn4 = types.KeyboardButton(text='🔝 Переглянути список улюблених книг')
btn5 = types.KeyboardButton(text='🏘️ Переглянути найближчі книжкові магазини')
main_menu_keyboard.add(btn1, btn2, btn3, btn4, btn5)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_name = message.from_user.first_name
    chat_id = message.chat.id
    cursor.execute(f'CREATE TABLE IF NOT EXISTS ratings_{str(chat_id)}  '
                   '(id serial PRIMARY KEY, book_title VARCHAR(50), book_author VARCHAR(50), book_rating REAL)')
    bot.send_message(message.chat.id, f'Привіт, {user_name}! 👋\n\n'
                                      f'Я бот для рекомендацій книжок. 📚\n\n'
                                      f'Поділися своїми вподобаннями, і я порекомендую тобі цікаву книгу, '
                                      f'використовуючи нейромережу. 💫\n\n'
                                      f'Ти можеш обрати одну з моїх функцій у меню внизу. 👇\n\n'
                                      f'Щоб отримати детальнішу інформацію про мене, використай команду /help ℹ️',
                     reply_markup=main_menu_keyboard)


@bot.message_handler(commands=['help'])
def send_help_info(message):
    bot.send_message(message.chat.id, ...)


@bot.message_handler(func=lambda message: message.text == '➕ Додати книгу в улюблені')
def add_book_to_favourite(message):
    bot_message = bot.send_message(message.chat.id,
                                   '👌 Окей! 👌\nВкажи назву книги, автора та оцінку від 0.0 до 5.0.\nНапр: Гарі Потер, Дж. К. Ролінг, 4.7')
    bot.register_next_step_handler(bot_message, add_book_to_db)


def add_book_to_db(message):
    book_title, book_author, book_rating = message.text.split(',')
    chat_id = message.chat.id
    cursor.execute(
        f"INSERT INTO ratings_{str(chat_id)} (book_title, book_author, book_rating) VALUES ('{book_title}', '{book_author}', {book_rating})")
    connection.commit()
    bot.send_message(message.chat.id, f'✅ Готово! ✅\nКнигу *"{book_title}"* додано до списку '
                                      f'улюблених.', parse_mode='Markdown')


@bot.message_handler(func=lambda message: message.text == '➖ Видалити книгу з улюблених')
def remove_book_from_favourite(message):
    bot_message = bot.send_message(message.chat.id, '👌 Окей! 👌\nВкажи назву книги, яку хочеш видалити із списку улюблених')
    bot.register_next_step_handler(bot_message, remove_book_from_db)


def remove_book_from_db(message):
    book_name_to_remove = message.text
    chat_id = message.chat.id
    cursor.execute(f"DELETE FROM ratings_{str(chat_id)} WHERE book_title = '{book_name_to_remove}'")
    connection.commit()
    bot.send_message(message.chat.id, f'✅ Готово! ✅\nКнигу "*{book_name_to_remove}*" видалено списку '
                                      f'улюблених.', parse_mode='Markdown')


@bot.message_handler(func=lambda message: message.text == '🔝 Переглянути список улюблених книг')
def get_favourite_books(message):
    chat_id = message.chat.id
    cursor.execute(f"SELECT * FROM ratings_{str(chat_id)} ORDER BY book_rating DESC LIMIT 10")
    top_books = cursor.fetchall()
    response = "*🫶 Мої улюблені книги:*\n\n"
    counter = 1
    for book in top_books:
        response += f"{counter}) 📖 *{book[1]}*\n    🤵{book[2]}\n    ⭐ {book[3]}\n\n"
        counter += 1
    # with open('images/istockphoto-1370405901-612x612.jpg', 'rb') as photo:
    #     bot.send_photo(message.chat.id, photo, caption=response, parse_mode='Markdown')
    bot.send_message(message.chat.id, response, parse_mode='Markdown')


@bot.message_handler(func=lambda message: message.text == '🪄 Порадити книгу')
def recommend_book(message):
    bot_message = bot.send_message(message.chat.id, '💪 Легко) 💪\nВкажи назву книги (англійською), яка тобі сподобалася і я підберу для тебе схожі 🪄')
    bot.register_next_step_handler(bot_message, get_recommendation)


def get_recommendation(message):
    book_name = message.text

    try:
        recommended_books = find_similar_books(book_name)
    except IncorrectBookIndex:
        bot.send_message(message.chat.id, "🛑Ой, а що трапилось... 🛑\nНазва книги неправильна, спробуй ще раз", parse_mode='Markdown')
    else:
        response = "*🔝 Найбільш схожі книги:*\n\n"
        counter = 1
        for key, value in recommended_books.items():
            response += f"{counter}) 📖 *{key}*\n ⭐ Схожість: {value}\n\n"
            counter += 1
        bot.send_message(message.chat.id, response, parse_mode='Markdown')


@bot.message_handler(func=lambda message: message.text == '🏘️ Переглянути найближчі книжкові магазини')
def get_user_location(message):
    bot_message = bot.send_message(message.chat.id, '📍 Для цього потрібна твоя локація 📍\nПоділися, будь ласка, своєю локацією')
    bot.register_next_step_handler(bot_message, get_nearest_book_stores)


def get_nearest_book_stores(message):
    user_lat = message.location.latitude
    user_lng = message.location.longitude
    google_map_api_url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={user_lat},{user_lng}&radius=3000&type=book_store&language=uk&key={GOOGLE_MAP_API_TOKEN}"
    google_map_api_response = requests.get(google_map_api_url)
    result = json.loads(google_map_api_response.text)
    bookstores = result["results"]
    bot_response = "*👇 Ось найближчі книжкові магазини:*\n\n"
    for bookstore in bookstores:
        name = bookstore["name"]
        address = bookstore["vicinity"]
        rating = bookstore["rating"] if "rating" in bookstore else "-"
        if "opening_hours" in bookstore:
            open_now = '🔓 Відчинено' if bookstore["opening_hours"]["open_now"] else '🔓 Зачинено'
        else:
            open_now = '🔓 -'
        bot_response += f"📚 Магазин: {name}\n 📍 Адреса: {address}\n ⭐ Рейтинг: {rating}\n {open_now}\n\n"
    bot.send_message(message.chat.id, bot_response, parse_mode='Markdown')


bot.polling(none_stop=True, interval=0)
