import sqlite3
import threading

class Database:
	def __init__(self, db_name='processed_cars.db'):
		self.db_name = db_name
		self.lock = threading.Lock()  # Мьютекс для синхронизации доступа к базе данных
		self.conn = self.create_connection()
		self.cursor = self.conn.cursor()
		self.create_table()

	def create_connection(self):
		return sqlite3.connect(self.db_name)

	def create_table(self):
		try:
			create_table_query = '''
				CREATE TABLE IF NOT EXISTS processed_cars (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					taxi TEXT,
					carnum TEXT
				);
			'''
			self.cursor.execute(create_table_query)
			self.conn.commit()
			print("Table created successfully")
		except sqlite3.Error as e:
			print(f"Error creating table: {e}")

	def connect(self):
		try:
			self.conn = sqlite3.connect(self.db_name)
			self.cursor = self.conn.cursor()
			print(f"Successfully connected to {self.db_name}")
		except sqlite3.Error as e:
			print(f"Error connecting to database: {e}")


	def insert_record(self, taxi, carnum):
		try:
			insert_query = "INSERT INTO processed_cars (taxi, carnum) VALUES (?, ?)"
			self.cursor.execute(insert_query, (taxi, carnum))
			self.conn.commit()
			# print("Record inserted successfully")
		except sqlite3.Error as e:
			print(f"Error inserting record: {e}")

	def check_record(self, carnum, taxi):
		try:
			connection = sqlite3.connect(self.db_name)
			cursor = connection.cursor()

			check_query = "SELECT * FROM processed_cars WHERE carnum=? AND taxi=?"
			self.lock.acquire()  # Блокировка мьютекса

			cursor.execute(check_query, (carnum, taxi))
			existing_record = cursor.fetchone()

			if existing_record:
				# print(f"Record for carnum {carnum} and taxi {taxi} exists in the database.")
				return True
			else:
				# print(f"No record found for carnum {carnum} and taxi {taxi}.")
				return False

		except sqlite3.Error as e:
			print(f"Error checking record: {e}")

		finally:
			self.lock.release()  # Разблокировка мьютекса после выполнения запроса
			connection.close()  # Закрытие соединения с базой данных



	def close_connection(self):
		if self.conn:
			self.conn.close()
			print("Connection closed")

# Пример использования:
# db = Database()
# db.create_table()
# db.insert_record("Taxi1", "Signal1", "12345", "Reason1", "OtherTaxi1", 1)
# db.check_record("12345")
# db.close_connection()
if __name__ == '__main__':
	db = Database()
	db.create_table()
	jet = 'Jet', ['AA4760EK', 'KA9628HA', 'BM056CI', 'AA9530PM', 'AA5590AI']
	allo = 'Allo', ['AA8144TO', 'AA9739BM']
	fly =  'Fly', ['AA8732CC', 'AA0158HB', 'AI8991BT', '83923OK']
	magdack = 'Magdack', ['AA8732CC', 'AA3944EM', 'AH0334BM', 'KA9810HX', 'TEST', 'AA2956CH', 'AA8144TO', 'AA2203HE', 'CB9019EA', 'AI8991BT', 'AA2497CA', 'AA0429HH', 'AA6214XH', ]
	taxi898 = 898, ['KA2751IP1','KA2751IP', 'AH0334BM', 'KA9810HX', 'AI8067AC', 'AA8144TO', 'AA9282KI', 'AA5344IIK', 'BC5637BO', 'AA7477XH', 'AA8389EE', 'KAA6799IH', 'AA0429HH', 'KA2927IM', ]
	for taxi, cars in [jet, allo, fly, magdack, taxi898]:
		for car in cars:
			if not db.check_record(car, taxi):
				db.insert_record(taxi, car)
				print(taxi, car)