import sqlite3

DB_PATH = 'music_dwh.db'

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # ---------- SOURCE ----------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS music_source (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userID TEXT,
            Track TEXT,
            artist TEXT,
            genre TEXT,
            City TEXT,
            time TEXT,
            Day TEXT
        )
    ''')

    # ---------- STAGING ----------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS staging_music (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userID TEXT,
            Track TEXT,
            artist TEXT,
            genre TEXT,
            City TEXT,
            time TEXT,
            Day TEXT,
            load_dt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ---------- ODS ----------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS ods_music (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userID TEXT,
            Track TEXT,
            artist TEXT,
            genre TEXT,
            City TEXT,
            time TEXT,
            Day TEXT,
            dt DATE
        )
    ''')

    # ---------- DWH: измерения ----------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS dim_user (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_hash TEXT UNIQUE
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS dim_artist (
            artist_id INTEGER PRIMARY KEY AUTOINCREMENT,
            artist_name TEXT UNIQUE
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS dim_genre (
            genre_id INTEGER PRIMARY KEY AUTOINCREMENT,
            genre_name TEXT UNIQUE
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS dim_city (
            city_id INTEGER PRIMARY KEY AUTOINCREMENT,
            city_name TEXT UNIQUE
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS dim_day (
            day_id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_name TEXT UNIQUE
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS dim_time (
            time_id INTEGER PRIMARY KEY AUTOINCREMENT,
            time_value TEXT UNIQUE,
            hour INTEGER,
            minute INTEGER,
            second INTEGER
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS dim_date (
            date_id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE UNIQUE,
            day_of_week TEXT,
            month INTEGER,
            year INTEGER
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS dim_track (
            track_id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_name TEXT,
            artist_id INTEGER,
            genre_id INTEGER,
            FOREIGN KEY(artist_id) REFERENCES dim_artist(artist_id),
            FOREIGN KEY(genre_id) REFERENCES dim_genre(genre_id)
        )
    ''')

    # ---------- DWH: факт ----------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS fact_listening (
            listening_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            track_id INTEGER,
            date_id INTEGER,
            time_id INTEGER,
            city_id INTEGER,
            day_id INTEGER,
            measure INTEGER DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES dim_user(user_id),
            FOREIGN KEY(track_id) REFERENCES dim_track(track_id),
            FOREIGN KEY(date_id) REFERENCES dim_date(date_id),
            FOREIGN KEY(time_id) REFERENCES dim_time(time_id),
            FOREIGN KEY(city_id) REFERENCES dim_city(city_id),
            FOREIGN KEY(day_id) REFERENCES dim_day(day_id)
        )
    ''')

    conn.commit()
    conn.close()
    print('База данных инициализирована.')