import os
import requests
from requests import sessions
from time import sleep
from loguru import logger
import telebot
from typing import Optional, Dict, List
from urllib.parse import urljoin

# ===== БРАУЗЕР ЗАГОЛОВКИ =====
CHROME_HEADERS = {
	'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
	'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
	'Accept-Language': 'uk-UA,uk;q=0.9,en;q=0.8',
	'Accept-Encoding': 'gzip, deflate, br',
	'DNT': '1',
	'Connection': 'keep-alive',
	'Upgrade-Insecure-Requests': '1',
	'Sec-Fetch-Dest': 'document',
	'Sec-Fetch-Mode': 'navigate',
	'Sec-Fetch-Site': 'none',
	'Cache-Control': 'max-age=0',
}

# ===== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ =====
REQUEST_DELAY = float(os.getenv('REQUEST_DELAY', '2'))
REQUEST_TIMEOUT = float(os.getenv('REQUEST_TIMEOUT', '10'))
REQUEST_RETRIES = int(os.getenv('REQUEST_RETRIES', '3'))
PROXY_LIST = [p.strip() for p in os.getenv('PROXY_LIST', '').split(',') if p.strip()]
TELEGRAM_ERROR_BOT_TOKEN = os.getenv('TELEGRAM_ERROR_BOT_TOKEN')
TELEGRAM_ERROR_CHAT_ID = os.getenv('TELEGRAM_ERROR_CHAT_ID')

# ===== ERROR TELEGRAM BOT =====
error_bot = None
if TELEGRAM_ERROR_BOT_TOKEN and TELEGRAM_ERROR_CHAT_ID:
	try:
		error_bot = telebot.TeleBot(TELEGRAM_ERROR_BOT_TOKEN)
	except Exception as e:
		logger.error(f'Failed to initialize error bot: {e}')


def send_error_notification(title: str, message: str, error_type: str = 'ERROR'):
	"""Отправляет уведомление об ошибке в Telegram"""
	if not error_bot or not TELEGRAM_ERROR_CHAT_ID:
		logger.warning('Error bot not configured')
		return

	try:
		full_message = f"""🚨 *{error_type}*

*{title}*

```
{message}
```"""
		error_bot.send_message(TELEGRAM_ERROR_CHAT_ID, full_message, parse_mode='Markdown')
	except Exception as e:
		logger.exception(f'Failed to send error notification: {e}')


def parse_proxy_list(proxy_string: str) -> List[str]:
	"""Парсит строку с прокси-адресами (поддерживает авторизацию)"""
	if not proxy_string or not proxy_string.strip():
		return []
	proxies = [p.strip() for p in proxy_string.split(',') if p.strip()]

	# Валидируем и логируем прокси
	validated_proxies = []
	for proxy in proxies:
		if proxy.startswith('http://') or proxy.startswith('https://'):
			validated_proxies.append(proxy)
			# Проверяем авторизацию
			if '@' in proxy:
				logger.info(f'Proxy with auth configured: {proxy.split("@")[1]}')
			else:
				logger.info(f'Proxy configured: {proxy}')
		else:
			logger.warning(f'Invalid proxy format: {proxy} (should be http://... or https://...)')

	return validated_proxies


def make_request(
	method: str,
	url: str,
	session: Optional[sessions.Session] = None,
	use_proxy: bool = False,
	proxy_index: int = 0,
	**kwargs
) -> Optional[requests.Response]:
	"""
	Выполняет HTTP запрос с поддержкой прокси и повторных попыток

	Args:
		method: GET или POST
		url: URL для запроса
		session: requests.Session объект
		use_proxy: использовать ли прокси
		proxy_index: индекс прокси из списка
		**kwargs: дополнительные аргументы для requests

	Returns:
		Response объект или None при ошибке
	"""
	if session is None:
		session = requests.Session()

	# Добавляем браузерные заголовки если их нет
	if 'headers' not in kwargs:
		kwargs['headers'] = {}
	kwargs['headers'].update(CHROME_HEADERS)

	# Устанавливаем таймаут если не указан
	if 'timeout' not in kwargs:
		kwargs['timeout'] = REQUEST_TIMEOUT

	# Настраиваем прокси если нужно
	proxies = None
	if use_proxy and PROXY_LIST:
		if proxy_index < len(PROXY_LIST):
			proxy_url = PROXY_LIST[proxy_index]
			# Скрываем пароль в логах
			safe_proxy_url = proxy_url
			if '@' in proxy_url:
				parts = proxy_url.split('@')
				creds_part = parts[0]  # http://user:pass
				host_part = parts[1]   # proxy.com:port
				# Показываем только http://***:***@proxy.com:port
				safe_proxy_url = creds_part.split('://')[0] + '://***:***@' + host_part
			proxies = {
				'http': proxy_url,
				'https': proxy_url,
			}
			kwargs['proxies'] = proxies
			logger.info(f'Using proxy {proxy_index}: {safe_proxy_url}')

	for attempt in range(REQUEST_RETRIES):
		try:
			logger.debug(f'Making {method} request to {url} (attempt {attempt + 1}/{REQUEST_RETRIES})')

			if method.upper() == 'GET':
				response = session.get(url, **kwargs)
			elif method.upper() == 'POST':
				response = session.post(url, **kwargs)
			else:
				raise ValueError(f'Unsupported method: {method}')

			# Добавляем паузу после успешного запроса
			sleep(REQUEST_DELAY)

			return response

		except requests.exceptions.ProxyError as e:
			logger.warning(f'Proxy error on attempt {attempt + 1}: {e}')
			if use_proxy and proxy_index + 1 < len(PROXY_LIST):
				# Попробуем следующий прокси
				logger.info(f'Trying next proxy...')
				return make_request(
					method, url, session,
					use_proxy=True,
					proxy_index=proxy_index + 1,
					**kwargs
				)
			sleep(2 ** attempt)  # Exponential backoff

		except requests.exceptions.ConnectionError as e:
			logger.warning(f'Connection error on attempt {attempt + 1}: {e}')
			if attempt < REQUEST_RETRIES - 1:
				wait_time = 2 ** attempt
				logger.info(f'Retrying in {wait_time} seconds...')
				sleep(wait_time)

		except requests.exceptions.Timeout as e:
			logger.warning(f'Timeout error on attempt {attempt + 1}: {e}')
			if attempt < REQUEST_RETRIES - 1:
				wait_time = 2 ** attempt
				logger.info(f'Retrying in {wait_time} seconds...')
				sleep(wait_time)

		except Exception as e:
			logger.exception(f'Unexpected error on attempt {attempt + 1}: {e}')
			if attempt < REQUEST_RETRIES - 1:
				sleep(2 ** attempt)

	logger.error(f'Failed to make {method} request to {url} after {REQUEST_RETRIES} attempts')
	return None


def check_wd_availability(session: Optional[sessions.Session] = None) -> tuple[bool, Optional[int], str]:
	"""
	Проверяет доступность WD сервера

	Returns:
		(is_available, status_code, message)
	"""
	test_url = 'http://wd.soz.in.ua/Account/LogOn'

	if session is None:
		session = requests.Session()

	try:
		response = make_request('GET', test_url, session)

		if response is None:
			return False, None, 'No response from server'

		if response.status_code == 200:
			return True, 200, 'OK'

		elif response.status_code == 503:
			logger.warning('WD server returned 503 - Service Unavailable')
			return False, 503, 'Service Unavailable (trying with proxy)'

		else:
			logger.warning(f'WD server returned {response.status_code}')
			return False, response.status_code, f'HTTP {response.status_code}'

	except Exception as e:
		logger.exception(f'Error checking WD availability: {e}')
		return False, None, str(e)


def get_session_with_auth(login: str, password: str) -> Optional[sessions.Session]:
	"""
	Создаёт аутентифицированную сессию с WD

	Args:
		login: Логин для WD
		password: Пароль для WD

	Returns:
		Session объект или None при ошибке
	"""
	url_auth = 'http://wd.soz.in.ua/Account/LogOn?ReturnUrl=%2f'
	data_auth = {'username': login, 'password': password, 'RememberMe': 'true'}

	session = requests.Session()

	try:
		# Проверяем доступность сервера
		available, status_code, message = check_wd_availability(session)

		if not available:
			error_msg = f'WD server not available: {message}'
			logger.error(error_msg)

			if status_code == 503:
				# Пробуем с прокси
				if PROXY_LIST:
					logger.info(f'Attempting to authenticate through proxy... (total proxies: {len(PROXY_LIST)})')
					response = make_request(
						'POST', url_auth, session,
						data=data_auth,
						use_proxy=True
					)
					if response:
						logger.info(f'Proxy request completed with status: {response.status_code}')
					else:
						logger.error('Proxy request failed (no response)')
				else:
					logger.error('No proxies configured, cannot retry')
					send_error_notification(
						'WD Server 503 - No Proxies',
						'WD returned 503 but no proxies configured in PROXY_LIST',
						'ERROR'
					)
					return None
			else:
				send_error_notification(
					'WD Dispatch System Unavailable',
					error_msg,
					'WARNING'
				)
				return None
		else:
			response = make_request('POST', url_auth, session, data=data_auth)

		if response is None or response.status_code >= 400:
			error_msg = f'Authentication failed: {response.status_code if response else "No response"}'
			logger.error(error_msg)
			send_error_notification(
				'WD Authentication Failed',
				error_msg,
				'ERROR'
			)
			return None

		logger.info('WD session created successfully')
		return session

	except Exception as e:
		error_msg = f'Failed to create WD session: {str(e)}'
		logger.exception(error_msg)
		send_error_notification(
			'WD Session Creation Error',
			error_msg,
			'ERROR'
		)
		return None


def get_firebird_connection_error_message(error: Exception) -> str:
	"""Преобразует ошибку Firebird в читаемое сообщение"""
	error_str = str(error)

	if 'CreateFile' in error_str:
		return 'Database file not found or not accessible'
	elif 'invalid user name' in error_str.lower():
		return 'Invalid Firebird credentials (SYSDBA/password)'
	elif 'socket' in error_str.lower():
		return 'Network connection error to Firebird server'
	elif 'timeout' in error_str.lower():
		return 'Firebird server timeout'
	else:
		return error_str


if __name__ == '__main__':
	# Test
	print('Utils module loaded successfully')
	print(f'Proxy list: {PROXY_LIST}')
	print(f'Request delay: {REQUEST_DELAY}s')
	print(f'Error bot configured: {error_bot is not None}')
