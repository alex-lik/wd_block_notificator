import requests
from requests import sessions
import json
import re
# import datetime
from time import sleep
import police
import taxi_data

from loguru import logger
# from icecream import ic
# from alive_progress import alive_bar
from threading import Thread
import firebirdsql as fdb
# import pytelegrambotapi
import telebot
from bs4 import BeautifulSoup 
from datetime import timedelta, datetime, time
import re
import database

DEBUG = False

token = '5005136355:AAE8e8rNV71_7d1MXuNw4eR3GWY2xgjWmr8'
bot = telebot.TeleBot(token)


def send_message(text, chat_id):
	try:
		sleep(5)
		bot.send_message(chat_id, text)
	except Exception as EX:
		logger.exception(EX)

class evos():
	host = '10.0.15.5'
	database = 'C:/taxi/DB/TAXI.GDB'
	user = 'SYSDBA'
	password = 'masterkey'

def log(text):
	if DEBUG:
		logger.add('log.log', level='DEBUG')
		logger.debug(text)


@logger.catch
def get_tn_data(taxi):
	return taxi_data.get_tn_data(taxi)
	# if taxi == 'Fly': return '10.0.15.5', 'C:/taxi/DB/TAXI.GDB', 'Флай', -1002045607452
	# elif taxi == 'Jet': return '10.0.15.105', 'C:/taxi/DB/TAXI.GDB', "Джет", -1002079543913
	# elif taxi == 'Magdack': return '94.130.249.244', 'C:/taxi/DB/TAXI.GDB', "МагДак", -1002063633603
	# elif taxi == '898': return '136.243.171.165', 'C:/taxikiev/db/taxi.gdb', "898", -1002022041862
	# elif taxi == 'Allo': return '188.40.143.60', 'D:/AlloTaxi/DB/taxi.GDB', 'Алло',-1001998084745


	
@logger.catch

def get_cardata(host, database):
	''' Получение курсора, выполнение запроса с возвращением результата, если надо то комит , после закрытие курсора и подключения '''
	try:
		connect = fdb.connect(host=host, database=database, user=evos.user, password=evos.password, charset='UTF8')
		# connect = fdb.connect(host=evos.host, database=evos.database, user=evos.user, password=evos.password, charset='UTF8')
		cur = connect.cursor()
		# sql = 'select "Car_No", "Marka", "Year", "Color", "Signal" from "Cars"'
		sql = '''WITH FirstQuery AS (
    SELECT "Car_No", "Marka", "Year", "Color", "Signal"
    FROM "Cars"
),
SecondQuery AS (
    SELECT "Signal", "Open_Time", "Duty", "Driver_No"
    FROM "DriverCar"
    WHERE "Signal" IN (SELECT "Signal" FROM FirstQuery)
)
SELECT sq."Signal", fq."Car_No", fq."Marka", fq."Year", fq."Color", sq."Open_Time", sq."Duty", d."F", d."I", d."O", d."Phone1", d."Phone2", d."MPhone"
FROM SecondQuery sq
JOIN FirstQuery fq ON sq."Signal" = fq."Signal"
JOIN "Drivers" d ON sq."Driver_No" = d."Driver_No";

'''
		cur.execute(sql)            				# Выполняем запрос
		result = cur.fetchall() 				# Получаем результат
		cur.close()                 				# Закрываем курсор
		connect.close()								# Закрываем подключение
		cars = {}
		for signal, number, marka, year, color, open_time, balans, f,i,o, phone3, phone2, phone1 in result:
			cars[number] = {'marka':marka, 'year':year, 'color':color, 'signal':signal, 'f':f, 'i':i, 'o':o, 'balans':balans, 'open_time':open_time, 'phone1':phone1, 'phone2':phone2, 'phone3':phone3}
		return cars
	except Exception as EX:
		logger.exception(EX)
		connect.rollback()
		connect.close()


##################################################################################################
@logger.catch
def get_session(login, password):
	''' Авторизация на WD '''
	url_auth = 'http://wd.soz.in.ua/Account/LogOn?ReturnUrl=%2f'                    # Url страницы авторизации
	data_auth = {'username': login, 'password': password, 'RememberMe': 'true'}   # Авторизационные данные
	# Делаем пост запрос на авторизацию и в рамках сессии
	with requests.Session() as session:
		session.post(url_auth, data=data_auth)  #
		return session


@logger.catch
def parse_data(result):
	''' Разбор полученных данных '''
	cars = {}
	for row in result['rows']:
		# Определяем такси, откуда заказ
		TaxiFrom = (row['cell'][10])[:-11].strip()
		# Определяем такси, откуда машина
		TaxiTo = (row['cell'][11])[:-11].strip()
		Pozivnoi = (row['cell'][14])									# Позывной
		CarNumber = (row['cell'][15])          							# Номер машины
		MarkModel = (row['cell'][16]).replace(
			"'", "").replace('"', "")  # Марка и модель машины
		cars.update({CarNumber:MarkModel})
	return 


@logger.catch
def check_number_on_block_by_soz(session, server_id, black_list):
	""" Проверяем номер авто на предмет блокировки по одному серверу """
	try:
		check_data = {"Group.Id":server_id,"_search":"true","rows":"5000","page":"1","sidx":"Id","sord":"asc","User.FullName":"СОЗ"}
		response = session.get('http://wd.soz.in.ua/CarInfoBlackByGroup/SearchData/', data=check_data)
		result = response.json()
		if result['total'] > 0:								# Если колчество результатов больше 0
			for row in result['rows']:
				carnum = row['cell'][0]
				description = row['cell'][1]
				black_list[carnum] = description
		return black_list

	except Exception as err:
		logger.info('_________________________________________________________________________________________')
		logger.opt(exception=True).error(err)
		return None
	
@logger.catch
def get_id_in_server(server_id, taxi_name, session):
	"""Получение айди службы в списке служб сервера"""
	result = session.get(f'http://wd.soz.in.ua/TaxiGroup/SelectByGroup?group={server_id}').json()
	for id in result: 
		if taxi_name in result[id]: return id

@logger.catch
def get_driver_statistics(session, servers, car_num, taxi_name):
	''' Получение статистики соз по номеру авто '''
	try:

		if str(type(servers)) == "<class 'dict'>":
			server_list = servers
		elif str(type(servers)) == "<class 'list'>":
			server_list = {}
			for server, server_id in servers:
				server_list.update({server:server_id})
		else:
			return None

		finish = datetime.now().strftime('%d.%m.%Y')            # Завтра (конечная дата месяц а)
		start = (datetime.now() - timedelta(days=30)).strftime('%d.%m.%Y')            # Завтра (конечная дата месяц а)
		period = f"{start}+-+{finish}"
		work_in_taxi = []
		pozivnoi = None

		for server in server_list:
			taxi_id_in_server = get_id_in_server(server_list[server], taxi_name, session)
			data = {'group':server_list[server], '_search':'true', 'rows':10000, 'page':1, 'sidx':'ReqStartTime', 'ReqStartTime':period, 'TaxiIdFrom':taxi_id_in_server, 'CarNo':car_num}
			# ic(data)
			result = session.get('http://wd.soz.in.ua/Order/SearchData', data=data).json()
			if int(result['total']) > 0:
				for row in result['rows']:
					taxi_from_car = row['cell'][11]
					work_in_taxi.append(taxi_from_car)
					if taxi_name in taxi_from_car:
						our_car = True
						pozivnoi = row['cell'][14]
						car = row['cell'][16]
						color = row['cell'][17]
		if pozivnoi:
			new_data = []
			work_in_taxi = list(set(work_in_taxi))
			for val in work_in_taxi:
				for server in servers:
					val = val.replace(' ' + server, '')
				new_data.append(val)
			firms = ''
			for firm in list(set(new_data)): firms += firm + ', '
			
			return pozivnoi, firms[:-2]
		else:
			return None
	except Exception as err:
		logger.info('_________________________________________________________________________________________')
		logger.opt(exception=True).error(err)
		return None
	

@logger.catch
def check(black_list, session):
	for taxi in ['Jet', 'Fly', 'Magdack', '898', 'Allo']:
		logger.add(f"{taxi}.log")
		log(f'Search blocked driver in taxi: {taxi}')
		host, database, taxi_name, chat_id = get_tn_data(taxi)
		cars = get_cardata(host, database)
		count = 0
		for carnum in black_list:
			if carnum in cars:
				try:
					if db.check_record(carnum, taxi): continue
					count += 1
					data = cars[carnum]
					contacts = ''
					if data.get('f'): contacts += f"{data['f']} "
					if data.get('i'): contacts += f"{data['i']} "
					if data.get('o'): contacts += f"{data['o']} "
					phones = []
					for phone in (data.get('phone1'), data.get('phone2'), data.get('phone3')):
						phone = standart_phone(phone)
						if not phone:continue
						if phone in phones: continue
						phones.append(phone)
					for phone in phones: contacts += f'\n{phone}'
					contacts += f"\nБаланс: {round(data['balans'],2)}"
					if data.get('open_time'):
						open_time = data.get('open_time')
						try:
							open_time_datetime = datetime.strptime(str(open_time), '%Y-%m-%d %H:%M:%S.%f')
							formatted_open_time = open_time_datetime.strftime('%Y-%m-%d')
							contacts += f"\nБыл в программе: {formatted_open_time}"

						except ValueError:
							if open_time:
								formatted_open_time = str(open_time)
								contacts += f"\nБыл в программе: {formatted_open_time}"

					message = f'''{carnum} - позывной: {data['signal']}, марка:  {data['marka']}, год: {data['year']}, цвет: {data['color']}\n\n{contacts}'''
					police_info = police.check_in_police(carnum)
					if police_info: message += '\n\nПо данным сайта baza-gai.com.ua: ' + police_info 
					else: message += '\n\nПо данным сайта baza-gai.com.ua: отсутствуют данные по номеру ' + carnum
					message += f"\n\nПричина блокировки - {black_list[carnum]}"
					logger.info(taxi + ' ||| ' + message)
					db.insert_record(taxi, carnum)
					# work_in_data = get_driver_statistics(session, servers, carnum, taxi_name)
					# if work_in_data:
					# 	_, work_in =  work_in_data
					# 	message += '\n' + 'Работает в ' + work_in
					send_message(message, chat_id)
				except Exception as EX:
					logger.exception(EX)
		logger.remove()
	

@logger.catch
def standart_phone(phone):
    """Нормализатор номеров"""
    
    phone = re.sub("\D", "", phone)                         # Удаляем из номера всё, кроме цифр
    if re.match(r'^[3][8][0][0-9]{9}$', phone): return phone[2:]                                    # Возвращаем номер без 380
    elif re.match(r'^[8][0][0-9]{9}$', phone):  return phone[1:]                                    # Возвращаем номер без 80
    elif re.match(r'^[0][0-9]{9}$', phone):     return phone                                        # Возвращаем номер без 0
    elif re.match(r'^[0-9]{9}$', phone):        return f"0{phone}"                                  # Возвращаем номер
    else: return phone                                                                              # Возвращаем ошибку


@logger.catch
def get_black_list(session=None):
	login, password, taxi_id = 'fly', '0933137532', 997
	servers = (303, 296)
	black_list = {}
	if not session: session = get_session(login, password)
	for server in servers:
		log(f"Download BlackList for server:{server}")
		black_list = check_number_on_block_by_soz(session, server, black_list)
	return black_list


def check2(black_list):
	pass


@logger.catch
def check_work_time():
	start = time(9,10)
	finish = time(20,30)
	now = datetime.now().time()

	if now > start and now < finish: 
		return False
	else: 
		log('No work_time',  now)
		return True
	
if __name__ == '__main__':
	db = database.Database()

	login, password, taxi_id = 'fly', '0933137532', 997
	session = get_session(login, password)
	servers = {'13+1 (Киев)': '298', '14+1 (Киев)': '297', '15+1 (Киев)': '295', 'Комфорт (15+1) (Киев)': '303', 'Стандарт (14плюс1) (Киев)': '296'}
	while True:
		try:
			black_list = get_black_list(session)
			if not check_work_time():	
				check(black_list, session)
		except: pass
		sleep(60 * 60)
	# check2(black_list)
