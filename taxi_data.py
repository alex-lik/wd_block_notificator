import os
from dotenv import load_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv()

def get_wd_credentials():
	"""Получает учётные данные для WD dispatch системы"""
	return os.getenv('WD_LOGIN'), os.getenv('WD_PASSWORD')

def get_tn_data(taxi):
    if taxi == 'Fly':
        return (
            os.getenv('FLY_HOST'),
            os.getenv('FLY_DB'),
            os.getenv('FLY_NAME'),
            int(os.getenv('FLY_CHAT_ID'))
        )
    elif taxi == 'Jet':
        return (
            os.getenv('JET_HOST'),
            os.getenv('JET_DB'),
            os.getenv('JET_NAME'),
            int(os.getenv('JET_CHAT_ID'))
        )
    elif taxi == 'Magdack':
        return (
            os.getenv('MAGDACK_HOST'),
            os.getenv('MAGDACK_DB'),
            os.getenv('MAGDACK_NAME'),
            int(os.getenv('MAGDACK_CHAT_ID'))
        )
    elif taxi == '898':
        return (
            os.getenv('TAXI898_HOST'),
            os.getenv('TAXI898_DB'),
            os.getenv('TAXI898_NAME'),
            int(os.getenv('TAXI898_CHAT_ID'))
        )
    elif taxi == 'Allo':
        return (
            os.getenv('ALLO_HOST'),
            os.getenv('ALLO_DB'),
            os.getenv('ALLO_NAME'),
            int(os.getenv('ALLO_CHAT_ID'))
        )
    else:
        raise ValueError("Unknown taxi type")

# Пример использования
if __name__ == "__main__":
    taxi_info = get_tn_data('Fly')
    print(taxi_info)
