import requests
import json
from bs4 import BeautifulSoup
import re
# from conect_to_db import mysql_select, mysql_insert, mysql_update

# def change_police_status(car_number, descr_of_the_police_site, year):                                                                  # Обновление статуса в бд(добавлено - 1 /удалено - 0 на соз)
#     if descr_of_the_police_site != 'none':
#         descr_of_the_police_site = descr_of_the_police_site.split(' ', 2)[2]
#     SQL = "UPDATE all_car SET police_check_status = '1', descr_of_the_police_site = \"" + descr_of_the_police_site + "\", year = \"" + year + "\"  WHERE car_number = \"" + car_number + "\""           # Формируем запрос
#     mysql_update(SQL) 


# Функция проверки года авто на сайте полиции
def check_in_police(CarNumber):
	data = {'digits': CarNumber}
	response = requests.get('https://baza-gai.com.ua/search?', data=data)
	result = response.text 																# Текст результата запроса
	soup = BeautifulSoup(result, 'html.parser')											# Парсим результат через BeautifulSoup 
	z = soup.prettify()																	# хз,надо
	e = soup.find_all('small')															# Берём то,что находится между тегами small
	data = re.findall('связан с.*<', str(e))											# Получаем год
	year = re.findall(' \d{4}\D{1}', str(data))											# ОЧищаем от мусора
	year = re.findall('\d{4}', str(year))												# Полностью очищаем от мусора
	try:
		year = int(year[0])																	# Вытаскиваем год из списка
		data = str(data[0])
		data = re.findall('.*\d{4}', str(data))                                            # Получаем год
		data = str(data[0])
		data = data.replace('связан с ', '')
		data = data.replace('(', '')
		data = data.replace(')', '')
#		print(str(data[9:]) + ' ' + str(year) ------ str(CarNumber) - str(description))
#		print(data)
		# print(CarNumber)


		return data

#			print('младше 15 лет' + str(year))
	except IndexError:
		return None


def work_with_number(car_number):
	result = check_in_police(car_number)
	print(result)
	if result:
		year, data = result
		police_descr = data.replace('связан с ', '')
	else:
		return None

# check_in_police('KA4230KK'))