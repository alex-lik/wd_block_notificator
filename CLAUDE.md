# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

**wd_block_notificator** is a Telegram notification service that monitors blocked vehicles across multiple taxi dispatch servers. It:

1. Fetches blacklists from the WD dispatch system (SOZ) via HTTP
2. Queries taxi database servers (Firebird) for vehicle and driver details
3. Checks vehicle registration status via baza-gai.com.ua (police database)
4. Sends Telegram notifications to specific chat groups when blocked vehicles are detected
5. Maintains SQLite database to avoid duplicate notifications

**Language:** Russian (all comments, logs, and messages are in Russian)

**Stack:** Python 3.12, Firebird DB, SQLite, Telegram Bot API, BeautifulSoup4

## Quick Start

```bash
# Setup
python -m venv .venv
.venv\Scripts\activate  # Windows or source .venv/bin/activate (Linux)
pip install -r requirements.txt

# Create .env file with required variables (see Environment Setup section)
cp .env.example .env

# Run locally
python main.py

# Or run with Docker
docker-compose up -d
docker-compose logs -f
```

## Architecture

### Core Components

**main.py** - Main application loop and orchestration
- Entry point that runs an infinite loop (checks every 60 minutes)
- `get_black_list()` - Fetches list of blocked cars from WD servers
- `check()` - Cross-references blacklist against each taxi's vehicle database
- `send_message()` - Sends Telegram notifications with car details
- `get_cardata()` - Queries Firebird database for vehicle/driver info
- `get_session()` - Creates HTTP session for WD authentication

**database.py** - SQLite deduplication layer
- `Database` class manages `processed_cars.db`
- Prevents sending duplicate notifications for the same car to the same taxi
- Thread-safe using `threading.Lock` for concurrent access

**taxi_data.py** - Configuration management
- Loads taxi-specific connection details from `.env` file
- `get_tn_data()` - Returns (host, database_path, taxi_name, telegram_chat_id) tuples for each taxi

**police.py** - Web scraper for police database
- `check_in_police()` - Scrapes baza-gai.com.ua to get vehicle registration info
- Parses HTML to extract vehicle age and registration status

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Infinite Loop (every 60 minutes)                            │
└─────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────┐
│ get_black_list(session)                                     │
│ • HTTP POST to http://wd.soz.in.ua/CarInfoBlackByGroup/*  │
│ • Checks servers: 303, 296                                 │
│ • Returns {car_number: block_reason}                       │
└─────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────┐
│ check(black_list, session)                                  │
│ • For each taxi: Jet, Fly, Magdack, 898, Allo              │
│   ├─ get_cardata(host, db_path)                            │
│   │  └─ Query Firebird DB for vehicle/driver info          │
│   ├─ Iterate over blacklist cars                           │
│   ├─ Check if car exists in this taxi's fleet              │
│   ├─ Query SQLite to avoid duplicate notifications         │
│   ├─ check_in_police() for vehicle status                  │
│   └─ send_message() to Telegram chat group                 │
└─────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────┐
│ SQLite Database (processed_cars.db)                         │
│ • Records (taxi, carnum) to prevent duplicate alerts        │
└─────────────────────────────────────────────────────────────┘
```

### Firebird Database Queries

The application uses a complex SQL JOIN to fetch vehicle data:

```sql
WITH FirstQuery AS (
    SELECT "Car_No", "Marka", "Year", "Color", "Signal" FROM "Cars"
),
SecondQuery AS (
    SELECT "Signal", "Open_Time", "Duty", "Driver_No" FROM "DriverCar"
    WHERE "Signal" IN (SELECT "Signal" FROM FirstQuery)
)
SELECT sq."Signal", fq."Car_No", fq."Marka", fq."Year", fq."Color",
       sq."Open_Time", sq."Duty", d."F", d."I", d."O", d."Phone1", d."Phone2", d."MPhone"
FROM SecondQuery sq
JOIN FirstQuery fq ON sq."Signal" = fq."Signal"
JOIN "Drivers" d ON sq."Driver_No" = d."Driver_No"
```

Returns: (signal, car_no, marka, year, color, open_time, duty, firstname, middle, lastname, phone1, phone2, phone3)

### WD API Authentication

Credentials for WD dispatch system are hardcoded in `main.py`:
```python
login = 'fly'
password = '0933137532'
```

HTTP session is created via POST to `http://wd.soz.in.ua/Account/LogOn` with session cookies maintained.

## Environment Setup

Create a `.env` file in the project root with the following variables. Each taxi requires 4 environment variables:

```env
# Fly taxi
FLY_HOST=10.0.15.5
FLY_DB=C:/taxi/DB/TAXI.GDB
FLY_NAME=Флай
FLY_CHAT_ID=-1002045607452

# Jet taxi
JET_HOST=10.0.15.105
JET_DB=C:/taxi/DB/TAXI.GDB
JET_NAME=Джет
JET_CHAT_ID=-1002079543913

# Magdack taxi
MAGDACK_HOST=94.130.249.244
MAGDACK_DB=C:/taxi/DB/TAXI.GDB
MAGDACK_NAME=МагДак
MAGDACK_CHAT_ID=-1002063633603

# 898 taxi
TAXI898_HOST=136.243.171.165
TAXI898_DB=C:/taxikiev/db/taxi.gdb
TAXI898_NAME=898
TAXI898_CHAT_ID=-1002022041862

# Allo taxi
ALLO_HOST=188.40.143.60
ALLO_DB=D:/AlloTaxi/DB/taxi.GDB
ALLO_NAME=Алло
ALLO_CHAT_ID=-1001998084745

# Telegram Bot Token (hardcoded in main.py line 24, but should move to .env)
TELEGRAM_BOT_TOKEN=5005136355:AAE8e8rNV71_7d1MXuNw4eR3GWY2xgjWmr8
```

**Note:** Chat IDs are negative supergroup/channel IDs. The bot token is currently hardcoded - consider moving it to `.env` for security.

## Common Commands

### Local Development

```bash
# Run the application directly
python main.py

# Run in Python interactive mode to test functions
python
>>> import main
>>> session = main.get_session('fly', '0933137532')
>>> black_list = main.get_black_list(session)
>>> print(black_list)

# Test database operations
python
>>> import database
>>> db = database.Database()
>>> db.check_record('AA4760EK', 'Jet')  # Returns True/False
>>> db.insert_record('Jet', 'AA4760EK')
```

### Docker Operations

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down

# Rebuild without cache (if requirements changed)
docker-compose build --no-cache && docker-compose up -d
```

### Testing Individual Functions

```bash
# Test Firebird connection
python
>>> import main
>>> cars = main.get_cardata('10.0.15.5', 'C:/taxi/DB/TAXI.GDB')
>>> print(cars)

# Test WD blacklist fetch
python
>>> import main
>>> session = main.get_session('fly', '0933137532')
>>> black_list = main.get_black_list(session)
>>> print(f"Found {len(black_list)} blocked cars")

# Test police database scraper
python
>>> import police
>>> result = police.check_in_police('AA4760EK')
>>> print(result)

# Test Telegram message sending
python
>>> import main
>>> main.send_message("Test message", -1002045607452)
```

## Key Implementation Details

### Phone Normalization

The `standart_phone()` function normalizes Ukrainian phone numbers:

```
380XXXXXXXXX → 0XXXXXXXXX  (remove country code)
80XXXXXXXXX  → 0XXXXXXXXX  (remove leading 8)
0XXXXXXXXX   → 0XXXXXXXXX  (already normalized)
XXXXXXXXX    → 0XXXXXXXXX  (add leading 0)
```

### Notification Message Format

Telegram messages include:
1. Car number + signal/call sign
2. Vehicle info (make, year, color)
3. Driver info (name and normalized phone numbers)
4. Account balance (Duty field)
5. Last activity date
6. Police database info (if available)
7. Block reason from SOZ

### Time-Based Execution Control

The `check_work_time()` function prevents notifications outside work hours (9:10 AM - 8:30 PM). The function returns `True` if it's outside work hours (skip notifications), `False` if within work hours (proceed).

### Deduplication Logic

The SQLite database tracks (taxi, carnum) pairs. Before sending a notification:
1. Check if record exists in `processed_cars.db`
2. If exists → skip (duplicate)
3. If not exists → insert record and send message

## Database Structure

### processed_cars.db

```sql
CREATE TABLE processed_cars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    taxi TEXT,                    -- Taxi name ('Fly', 'Jet', etc.)
    carnum TEXT                   -- Vehicle registration number
);
```

### Log Files

- `{TaxiName}.log` - Per-taxi log files (Fly.log, Jet.log, etc.)
- Logs are appended dynamically in the loop

## Dependencies

- **requests** - HTTP requests to WD and police databases
- **beautifulsoup4** - HTML parsing for police database scraper
- **loguru** - Structured logging
- **telebot** - Telegram Bot API client
- **firebirdsql** - Firebird database driver
- **python-dotenv** - Environment variable management

## Common Issues & Debugging

### Firebird Connection Errors

```
Error: "Firebird: *** IBPP::Exception ***
  Context: ... database = C:/taxi/DB/TAXI.GDB"
```

**Causes:**
- Database path incorrect or inaccessible
- Firebird server is down
- Network connectivity issue
- Credentials (SYSDBA/masterkey) are invalid

**Solution:** Check `taxi_data.py` for correct host and database paths. Verify network connectivity to Firebird servers.

### WD Session Authentication Failures

**Causes:**
- Hardcoded credentials are invalid
- WD server is down
- IP address is blacklisted

**Solution:** Verify credentials in `main.py` line 302-303. Check that the IP has access to `wd.soz.in.ua`.

### Telegram Message Failures

**Causes:**
- Bot token is invalid (line 24)
- Chat ID is wrong or bot is not member of the group
- Telegram API rate limit exceeded

**Solution:** Verify bot token and chat IDs in `.env`. Ensure bot is admin in the target Telegram groups.

### Police Database Scraper Returns None

The `check_in_police()` function uses regex patterns that are brittle:

```python
data = re.findall('связан с.*<', str(e))  # Looks for specific text
```

If baza-gai.com.ua changes their HTML structure, the scraper will break and return `None`.

**Solution:** Update regex patterns in `police.py` if website layout changes.

### Duplicate Notifications Still Appearing

If duplicates appear despite SQLite tracking, the issue is usually:
- Database is being reset/deleted
- Different taxi names in code vs `.env`
- SQLite corruption

**Solution:** Check `processed_cars.db` integrity. Delete and let it rebuild on next run.

## Development Notes

### Global Instructions

According to the user's CLAUDE.md (parent directory):
- Always respond in Russian
- Never add author signatures to commits
- Follow the monorepo pattern of the parent project

### Thread Safety

Database operations use `threading.Lock()` for thread-safe access in `database.py`. The main application is single-threaded (using `sleep(60 * 60)` between iterations), but the lock protects against concurrent access if future changes introduce threading.

### Logging Configuration

Loguru is configured dynamically:
```python
logger.add(f"{taxi}.log")  # Adds per-taxi log file
```

Logs are NOT removed between iterations, causing them to accumulate. Consider implementing log rotation or using loguru's rotation feature.

### Error Handling

Most functions use `@logger.catch` decorator for exception handling. This logs exceptions but continues execution. The main loop has a bare `except: pass` (line 310) which silently swallows all errors - consider adding specific exception handling.

## Performance Considerations

- **Network I/O:** Fetching from Firebird servers is the bottleneck (potentially multiple seconds per taxi)
- **Rate Limiting:** Telegram Bot API has rate limits; adding `sleep(5)` in `send_message()` provides throttling
- **Database Queries:** SQL JOIN in Firebird is complex but indexed on Signal
- **Cycle Time:** 60-minute sleep between checks is intentional to reduce server load

## Security Considerations

⚠️ **Credentials are hardcoded in main.py (lines 24, 273, 302)**. Consider moving to `.env`:
- Telegram bot token
- WD credentials
- Firebird credentials (already in `.env` via `taxi_data.py`)

The application connects to external databases and makes HTTP requests to untrusted sources (police database). Input validation is minimal.

## Future Improvements

1. Move hardcoded credentials to `.env` (telegram token, WD login/password)
2. Add proper logging rotation to prevent log files from growing indefinitely
3. Replace bare `except: pass` with specific exception handling
4. Add health check endpoint for monitoring
5. Consider async/await for parallel Firebird queries across taxis
6. Add database migrations system for schema changes
7. Implement proper configuration management (ConfigParser or Pydantic)
8. Add unit tests for police scraper and phone normalization



Всегда отвечай на русском языке


