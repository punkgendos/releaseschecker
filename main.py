#!/usr/bin/env python
# -*- coding: utf-8 -*-

import telebot
import vk_api
import logging
import traceback
import sqlite3
from datetime import datetime, timezone, timedelta
from sqlite3 import Error
from settings import BOT_TOKEN, MY_ACCOUNT, CLIENT_ID, CLIENT_SECRET, VK_ACCESS_TOKEN


BOT_TOKEN = BOT_TOKEN
tg = telebot.TeleBot(BOT_TOKEN)
CHANNEL_NAME = '@releasestoday'
MY_ACCOUNT = MY_ACCOUNT

LOGFILE = 'releaseschecker.log'

CLIENT_ID = CLIENT_ID
CLIENT_SECRET = CLIENT_SECRET

VK_ACCESS_TOKEN = VK_ACCESS_TOKEN
PUBLIC_ID = -23787907
FILENAME_VK = 'last_id.txt'

NOW = datetime.now(timezone.utc) + timedelta(hours=3, minutes=0)
TODAY = NOW.date()

vk = vk_api.VkApi(token=VK_ACCESS_TOKEN).get_api()


def convertDateToTimestamp(date_str):
    return int(datetime.strptime(date_str, '%Y-%m-%d').timestamp())


def replaceMonth(release_date):
    pos = 0
    for i in release_date:
        if i.isdigit():
            break
        pos += 1
    release_date = release_date[pos:]
    ru_month = release_date.split(' ')[1]
    if ru_month == 'января':
        month = '01'
    if ru_month == 'февраля':
        month = '02'
    if ru_month == 'марта':
        month = '03'
    if ru_month == 'апреля':
        month = '04'
    if ru_month == 'мая':
        month = '05'
    if ru_month == 'июня':
        month = '06'
    if ru_month == 'июля':
        month = '07'
    if ru_month == 'августа':
        month = '08'
    if ru_month == 'сентября':
        month = '09'
    if ru_month == 'октября':
        month = '10'
    if ru_month == 'ноября':
        month = '11'
    if ru_month == 'декабря':
        month = '12'

    return release_date.split(' ')[2] + '-' + month + '-' + release_date.split(' ')[0]


def sqlConnection():
    try:
        con = sqlite3.connect('releases.db')
        return con
    except Error:
        print(Error)


def sqlCreate(con):
    cur = con.cursor()
    cur.execute("CREATE TABLE releases(id integer PRIMARY KEY AUTOINCREMENT, artist text, title text, type text, date text)")
    con.commit()


def sqlCheck(con, entities):
    cur = con.cursor()
    date = cur.execute("SELECT date FROM releases WHERE artist=? AND title=? AND type=?",
                       (entities[0], entities[1], entities[2],))
    if date.fetchone():
        date = cur.execute("SELECT date FROM releases WHERE artist=? AND title=? AND type=?",
                           (entities[0], entities[1], entities[2],))
        date = date.fetchone()[0]
    info = cur.execute("SELECT artist, title FROM releases WHERE artist=? AND title=? AND type=?",
                       (entities[0], entities[1], entities[2],))
    if info.fetchone() is None:
        return None
    elif (date != entities[3]):
        id = cur.execute("SELECT id FROM releases WHERE artist=? AND title=? AND type=?",
                         (entities[0], entities[1], entities[2],))
        id = id.fetchone()[0]
        return id


def sqlInsert(con, entities):
    cur = con.cursor()
    id = sqlCheck(con, entities)
    if not(id):
        cur.execute("INSERT INTO releases (artist, title, type, date) VALUES(?,?,?,?)", entities)
        con.commit()
    else:
        cur.execute("UPDATE releases SET date=? WHERE id=?", (entities[3], id,))
        con.commit()


def sqlTable(entities):
    con = sqlConnection()
#    sqlCreate(con)
#    print('created')
#    input()
    sqlInsert(con, entities)
    con.close()


def getPosts(response, last_id):
    for item in response['items'][::-1]:

#        print(item['id'])
#        input()

        if item['id'] <= last_id:
            continue

        with open(FILENAME_VK, 'rt') as file2:
            current_last_id = int(file2.read())

        if item['id'] > current_last_id:
            with open(FILENAME_VK, 'wt') as file3:
                file3.write(str(item['id'] - 1))

        if not(item.get('copy_history')):
            if item['text'].strip()[0] == '#':
                post_text = item['text'].split('\n')
                release_type = post_text[0][1:post_text[0].find('#', 1)-1]
                release_type = release_type[0].upper() + release_type[1:len(release_type)]
                release_type = release_type.strip()
                artist_and_title = post_text[1].split(' - ')
                artist = artist_and_title[0].strip()
                if artist.find('[') != -1 and artist.find('|') != -1 and artist.find(']') != -1:
                    artist = artist[artist.find('|')+1:len(artist)-1]
                title = artist_and_title[1].strip()
#                release_date = post_text[3][post_text[3].find(':')+2:len(post_text[3])-1]
                release_date = post_text[3].strip()
                release_date = release_date.rstrip('.')
                release_date = replaceMonth(release_date)
                release_date = datetime.strptime(release_date, '%Y-%m-%d').date()
#                entities = (artist.strip(), title.strip(), release_type.strip(), round(release_date))
                entities = (artist, title, release_type, release_date)

                sqlTable(entities)

        if item['id'] > current_last_id:
            with open(FILENAME_VK, 'wt') as file3:
                file3.write(str(item['id']))

    return


def checkReleases():
    with open(FILENAME_VK, 'rt') as file:
        try:
            last_id = int(file.read())
        except:
            tg.send_message(MY_ACCOUNT, 'Файл ' + FILENAME_VK + ' пустой')
            return
    posts = vk.wall.get(owner_id=PUBLIC_ID, filter='owner', count=100, v=5.131)  # вернуть count=10 и убрать offset
    getPosts(posts, last_id)
    return


def sqlRead():
    con = sqlConnection()
    cur = con.cursor()
    results = cur.execute("SELECT artist, title, type FROM releases WHERE date=? ORDER BY artist", (TODAY,))
    results = results.fetchall()
    msg = ''
    emoji = ''
    for result in results:
        if result[2] == 'Single':
            emoji = '\U0001F3B5'
        if result[2] == 'EP':
            emoji = '\U0001F3B6'
        if result[2] == 'Album':
            emoji = '\U0001F4BF'
        msg = msg + emoji + '*' + result[0] + '*' + ' - ' + result[1] + ' \[' + result[2] + ']' + '\n'
    con.close()
    return msg


def sendMsg():
    msg = sqlRead()
    if msg:
        tg.send_message(CHANNEL_NAME, msg, parse_mode='Markdown')


def clearTable():
    today_list = str(TODAY).split('-')
    day = int(today_list[2]) - 1
    yesterday = today_list[0] + '-' + today_list[1] + '-' + str(day)
    con = sqlConnection()
    cur = con.cursor()
    ids = cur.execute("SELECT id FROM releases WHERE date=?", (yesterday,))
    ids = ids.fetchall()
    for id in ids:
        cur.execute("DELETE FROM releases WHERE id=?", (id[0],))
        con.commit()


if __name__ == '__main__':
    logging.basicConfig(format='[%(asctime)s] %(filename)s:%(lineno)d %(levelname)s - %(message)s', filename=LOGFILE,
                        level=logging.INFO, datefmt='%d.%m.%Y %H:%M:%S')
    try:
        checkReleases()
        print('Done check')
        clearTable()
        print('Done clear')
#        sendMsg()
        print('Done msg')
        logging.info('Done')
    except Exception as e:
        logging.error(traceback.format_exc())
