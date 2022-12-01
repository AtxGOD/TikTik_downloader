import os, configparser, requests
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.utils import executor
from aiogram.utils.helper import Helper, HelperMode, ListItem
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import urllib.request
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from retry import retry
import sqlite3 as sq
from datetime import datetime
import time


config = configparser.ConfigParser()
config.read("settings.ini")
TOKEN = config["tgbot"]["token"]

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
driver = None


def start(link):
    global driver
    driver.get('https://ssstik.io/ru')
    time.sleep(2)
    elem = driver.find_element(By.ID, 'main_page_text')
    elem.send_keys(link)
    elem.send_keys(Keys.RETURN)


@retry(Exception, tries=15, delay=1)
def get_links():
    global driver
    elem = driver.find_element(By.CLASS_NAME, 'result_overlay')
    links = elem.find_elements(By.TAG_NAME, 'a')
    result_links = []
    for link in links:
        result_links.append(link.get_attribute("href"))
    return result_links


def main(link):
    global driver
    driver = webdriver.Safari()
    # options = webdriver.FirefoxOptions()
    # options.set_preference("dom.webdriver.enabled", False)
    # options.headless = True
    # s = Service("geckodriver.exe")
    # driver = webdriver.Firefox(service=s, options=options)
    try:
        start(link)
    except Exception as ex:
        print(f'Ошибка при инициализации: {ex}')

    result = None
    try:
        result = get_links()
    except Exception as ex:
        print(f'Таймаут 15 сек, ошибка: {ex}')
    driver.close()
    return result


if not os.path.exists('videos'):
    os.makedirs('videos')


def add_row_database(name):
    with sq.connect("data.db") as con:
        cur = con.cursor()
        cur.execute(f"INSERT INTO main VALUES('{name}', 1, '{datetime.today().strftime('%Y-%m-%d')}')")


@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await bot.send_message(chat_id=message.chat.id,
                           text=f"Добро пожаловать, {message['from']['first_name']}\n\n"
                                f"Здесь Вы сможете скачать видео из ТикТок, без значка и даже если автор отключил эту функцию\n\n"
                                f"Просто отправьте ссылку на видео из ТикТок:")


@dp.message_handler(commands=['stat'])
async def stat_count(message: types.Message):
    if config["tgbot"]["admin_id"] == str(message['from']['id']):
        with sq.connect("data.db") as con:
            cur = con.cursor()

            cur.execute("SELECT count(count_massages) FROM main WHERE date  BETWEEN "
                        "date('now', '-1 year') AND date('now', '+1 day')")
            count_year = cur.fetchall()[0][0]

            cur.execute("SELECT count(count_massages) FROM main WHERE date BETWEEN date('now', '-1 month') "
                        "AND date('now','+1 day')")
            count_month = cur.fetchall()[0][0]

            cur.execute("SELECT count(count_massages) FROM main WHERE date  BETWEEN date('now', '-7 day') "
                        "AND date('now', '+1 day')")
            count_last_week = cur.fetchall()[0][0]

            cur.execute("SELECT count(count_massages) FROM main WHERE date = date('now')")
            count_day = cur.fetchall()[0][0]

            await bot.send_message(chat_id=message.chat.id, text=f'За день: {count_day}\n'
                                                                 f'За последние 7 дней: {count_last_week}\n'
                                                                 f'За месяц: {count_month}\n'
                                                                 f'За год: {count_year}')
    else:
        await bot.send_message(chat_id=message.chat.id, text=f'Пишите менеджеру!')


@dp.message_handler(commands=['stat_users'])
async def stat_count_users(message: types.Message):
    if config["tgbot"]["admin_id"] == str(message['from']['id']):
        with sq.connect("data.db") as con:
            cur = con.cursor()

            cur.execute("SELECT DISTINCT name, sum(count_massages) FROM main WHERE date  BETWEEN "
                        "date('now', '-1 year') AND date('now', '+1 day') "
                        "GROUP BY name")
            people_count_year = cur.fetchall()
            count_year_people = ''
            for row in people_count_year:
                count_year_people += f'{row[0]} {row[1]}\n'

            cur.execute(
                "SELECT DISTINCT name, sum(count_massages) FROM main WHERE date  BETWEEN date('now', '-1 month') "
                "AND date('now','+1 day') GROUP BY name")
            people_count_month = cur.fetchall()
            count_month_people = ''
            for row in people_count_month:
                count_month_people += f'{row[0]} {row[1]}\n'

            cur.execute("SELECT DISTINCT name, sum(count_massages) FROM main WHERE date  BETWEEN date('now', '-7 day') "
                        "AND date('now', '+1 day') GROUP BY name")
            people_count_last_week = cur.fetchall()
            count_last_week_people = ''
            for row in people_count_last_week:
                count_last_week_people += f'{row[0]} {row[1]}\n'

            cur.execute("SELECT DISTINCT name, sum(count_massages) FROM main WHERE date = date('now') GROUP BY name")
            people_count_day = cur.fetchall()
            count_day_people = ''
            for row in people_count_day:
                count_day_people += f'{row[0]} {row[1]}\n'

            await bot.send_message(chat_id=message.chat.id, text=f'За день: \n{count_day_people}\n'
                                                                 f'За последние 7 дней: \n{count_last_week_people}\n'
                                                                 f'За месяц:\n{count_month_people}\n'
                                                                 f'За год:\n{count_year_people}')
    else:
        await bot.send_message(chat_id=message.chat.id, text=f'Пишите менеджеру!')


@dp.message_handler(commands=['stat_new'])
async def stat_new(message: types.Message):
    if config["tgbot"]["admin_id"] == str(message['from']['id']):
        with sq.connect("data.db") as con:
            cur = con.cursor()

            cur.execute("SELECT DISTINCT name FROM main")
            people_all = cur.fetchall()

            cur.execute("SELECT DISTINCT name FROM main WHERE date  BETWEEN "
                        "date('now', '-1 year') AND date('now', '+1 day') "
                        "GROUP BY name")
            people_count_last_year = cur.fetchall()
            people_count_last_year = len(set(people_all) & set(people_count_last_year))

            cur.execute("SELECT DISTINCT name FROM main WHERE date  BETWEEN "
                        "date('now', '-1 month') AND date('now','+1 day') "
                        "GROUP BY name")
            people_count_last_month = cur.fetchall()
            people_count_last_month = len(set(people_all) & set(people_count_last_month))

            cur.execute("SELECT DISTINCT name FROM main WHERE date  BETWEEN "
                        "date('now', '-7 day') AND date('now', '+1 day') GROUP BY name")
            people_count_last_week = cur.fetchall()
            people_count_last_week = len(set(people_all) & set(people_count_last_week))

            cur.execute("SELECT DISTINCT name FROM main WHERE date = date('now') GROUP BY name")
            people_count_last_day = cur.fetchall()
            people_count_last_day = len(set(people_all) & set(people_count_last_day))

            await bot.send_message(chat_id=message.chat.id, text=f'Новых за день: {people_count_last_day}\n'
                                                                 f'Новых за последние 7 дней: {people_count_last_week}\n'
                                                                 f'Новых за месяц: {people_count_last_month}\n'
                                                                 f'Новых за год: {people_count_last_year}')
    else:
        await bot.send_message(chat_id=message.chat.id, text=f'Пишите менеджеру!')


@dp.message_handler(commands=['stat_new_users'])
async def stat_new_users(message: types.Message):
    if config["tgbot"]["admin_id"] == str(message['from']['id']):
        with sq.connect("data.db") as con:
            cur = con.cursor()

            cur.execute("SELECT DISTINCT name FROM main")
            people_all = cur.fetchall()

            cur.execute("SELECT DISTINCT name FROM main WHERE date  BETWEEN "
                        "date('now', '-1 year') AND date('now', '+1 day') "
                        "GROUP BY name")
            people_count_last_year = cur.fetchall()
            people_count_last_year_names = ''
            for row in set(people_all) & set(people_count_last_year):
                people_count_last_year_names += f'{row[0]}\n'

            cur.execute("SELECT DISTINCT name FROM main WHERE date  BETWEEN "
                        "date('now', '-1 month') AND date('now','+1 day') "
                        "GROUP BY name")
            people_count_last_month = cur.fetchall()
            people_count_last_month_names = ''
            for row in set(people_all) & set(people_count_last_month):
                people_count_last_month_names += f'{row[0]}\n'

            cur.execute("SELECT DISTINCT name FROM main WHERE date  BETWEEN "
                        "date('now', '-7 day') AND date('now', '+1 day') GROUP BY name")
            people_count_last_week = cur.fetchall()
            people_count_last_week_names = ''
            for row in set(people_all) & set(people_count_last_week):
                people_count_last_week_names += f'{row[0]}\n'

            cur.execute("SELECT DISTINCT name FROM main WHERE date = date('now') GROUP BY name")
            people_count_last_day = cur.fetchall()
            people_count_last_day_names = ''
            for row in set(people_all) & set(people_count_last_day):
                people_count_last_day_names += f'{row[0]}\n'

            await bot.send_message(chat_id=message.chat.id, text=f'Новых за день: \n{people_count_last_day_names}\n'
                                                                 f'Новых за последние 7 дней: \n{people_count_last_week_names}\n'
                                                                 f'Новых за месяц: \n{people_count_last_month_names}\n'
                                                                 f'Новых за год: \n{people_count_last_year_names}')
    else:
        await bot.send_message(chat_id=message.chat.id, text=f'Пишите менеджеру!')


@dp.message_handler(content_types=['text'])
async def text(message: types.Message):
    print(message['from']['first_name'], message['from']['id'], message.text)
    if message.text.startswith('https://www.tiktok.com'):
        video_url = message.text
        try:
            await bot.send_message(chat_id=message.chat.id, text='>>> загружаю видео')
            path = f'./videos/result_{message.from_user.id}.mp4'
            links = main(video_url)
            if links is None:
                raise ValueError

            await bot.send_message(chat_id=message.chat.id, text='Вот вот 👇')

            with open(f'./videos/result_{message.from_user.id}.mp4', 'wb') as file:
                r = requests.get(links[0])
                file.write(r.content)

            with open(f'./videos/result_{message.from_user.id}.mp4', 'rb') as file:
                await bot.send_video(
                    chat_id=message.chat.id,
                    video=file,
                    caption='Скачано с помощью — @TTCGGBOT'
                    )
            add_row_database(message['from']['first_name'])
            os.remove(path)

        except Exception as exc:
            print(exc)
            await bot.send_message(chat_id=message.chat.id,
                                   text='Что-то пошло не так!\n\n'
                                        'Давайте попробуем ещё раз:')
    elif message.text.startswith('https://vm.tiktok.com') or message.text.startswith('http://vm.tiktok.com'):
        video_url = message.text
        try:
            await bot.send_message(chat_id=message.chat.id, text='>>> загружаю видео')
            path = f'./videos/result_{message.from_user.id}.mp4'
            links = main(video_url)
            if links is None:
                raise ValueError

            await bot.send_message(chat_id=message.chat.id, text='Вот вот 👇')

            with open(f'./videos/result_{message.from_user.id}.mp4', 'wb') as file:
                r = requests.get(links[0])
                file.write(r.content)

            with open(f'./videos/result_{message.from_user.id}.mp4', 'rb') as file:
                await bot.send_video(
                    chat_id=message.chat.id,
                    video=file,
                    caption='Скачано с помощью — @TTCGGBOT'
                )
            add_row_database(message['from']['first_name'])
            os.remove(path)

        except Exception as exc:
            print(exc)
            await bot.send_message(chat_id=message.chat.id,
                                   text='Что-то пошло не так!\n\n'
                                        'Давайте попробуем ещё раз:')
    else:
        await bot.send_message(chat_id=message.chat.id, text='Жду ссылку на видео 🙈')
if __name__ == "__main__":
    # Запускаем бота
    executor.start_polling(dp, skip_updates=True)


# За прошлый месяц SELECT count(count_massages) FROM main WHERE date  BETWEEN date('now', 'start of month', '-1 month') AND date('now', 'start of month','-1 day')
# За год SELECT DISTINCT name, sum(count_massages) FROM main WHERE date  BETWEEN date('now', 'start of year') AND date('now')  GROUP BY name
# За месяц SELECT count(count_massages) FROM main WHERE date  BETWEEN date('now', 'start of month') AND date('now', 'start of month','+1 month','-1 day')
# За последнюю последние 7 дней SELECT count(count_massages) FROM main WHERE date  BETWEEN date('now', '-7 day') AND date('now')
# За этот день  SELECT count(count_massages) FROM main WHERE date = date('now')

# SELECT DISTINCT name, sum(count_massages) FROM main WHERE date  BETWEEN date('now', 'start of month', '-1 month') AND date('now', 'start of month','-1 day') GROUP BY name
# Статистика по людям за месяц SELECT DISTINCT name, sum(count_massages) FROM main WHERE date  BETWEEN date('now', 'start of month') AND date('now', 'start of month','+1 month','-1 day') GROUP BY name
# Статистика по людям за помледние 7 дней SELECT DISTINCT name, sum(count_massages) FROM main WHERE date  BETWEEN date('now', '-7 day') AND date('now') GROUP BY name
# Статистика по людям за день SELECT DISTINCT name, sum(count_massages) FROM main WHERE date = date('now') GROUP BY name
