from datetime import datetime
from db_utils import get_connection


def load_ods_to_dwh():
    conn = get_connection()
    cur = conn.cursor()

    # Чистим DWH перед загрузкой
    tables = [
        'fact_listening', 'dim_track', 'dim_user', 'dim_artist',
        'dim_genre', 'dim_city', 'dim_date', 'dim_time', 'dim_day'
    ]
    for tbl in tables:
        cur.execute(f'DELETE FROM {tbl}')

    # ---------- 1. Пользователи ----------
    cur.execute('SELECT DISTINCT userID FROM ods_music WHERE userID IS NOT NULL')
    for (user_hash,) in cur.fetchall():
        cur.execute('INSERT OR IGNORE INTO dim_user (user_hash) VALUES (?)', (user_hash,))

    # ---------- 2. Артисты ----------
    cur.execute('SELECT DISTINCT artist FROM ods_music WHERE artist IS NOT NULL')
    for (artist_name,) in cur.fetchall():
        cur.execute('INSERT OR IGNORE INTO dim_artist (artist_name) VALUES (?)', (artist_name,))

    # ---------- 3. Жанры ----------
    cur.execute('SELECT DISTINCT genre FROM ods_music WHERE genre IS NOT NULL')
    for (genre_name,) in cur.fetchall():
        cur.execute('INSERT OR IGNORE INTO dim_genre (genre_name) VALUES (?)', (genre_name,))

    # ---------- 4. Города ----------
    cur.execute('SELECT DISTINCT City FROM ods_music WHERE City IS NOT NULL')
    for (city_name,) in cur.fetchall():
        cur.execute('INSERT OR IGNORE INTO dim_city (city_name) VALUES (?)', (city_name,))

    # ---------- 5. Дни недели ----------
    cur.execute('SELECT DISTINCT Day FROM ods_music WHERE Day IS NOT NULL')
    for (day_name,) in cur.fetchall():
        cur.execute('INSERT OR IGNORE INTO dim_day (day_name) VALUES (?)', (day_name,))

    # ---------- 6. Время ----------
    cur.execute('SELECT DISTINCT time FROM ods_music WHERE time IS NOT NULL')
    for (time_val,) in cur.fetchall():
        try:
            h, m, s = map(int, time_val.split(':'))
            cur.execute('''
                INSERT OR IGNORE INTO dim_time (time_value, hour, minute, second)
                VALUES (?, ?, ?, ?)
            ''', (time_val, h, m, s))
        except ValueError:
            continue

    # ---------- 7. Даты ----------
    cur.execute('SELECT DISTINCT dt FROM ods_music WHERE dt IS NOT NULL')
    for (date_val,) in cur.fetchall():
        d = datetime.strptime(date_val, '%Y-%m-%d')
        day_of_week = d.strftime('%A')
        cur.execute('''
            INSERT OR IGNORE INTO dim_date (date, day_of_week, month, year)
            VALUES (?, ?, ?, ?)
        ''', (date_val, day_of_week, d.month, d.year))

    # ---------- 8. Треки ----------
    cur.execute('''
        SELECT DISTINCT o.Track, a.artist_id, g.genre_id
        FROM ods_music o
        JOIN dim_artist a ON o.artist = a.artist_name
        JOIN dim_genre g ON o.genre = g.genre_name
        WHERE o.Track IS NOT NULL
    ''')
    for track_name, artist_id, genre_id in cur.fetchall():
        cur.execute('''
            INSERT INTO dim_track (track_name, artist_id, genre_id)
            VALUES (?, ?, ?)
        ''', (track_name, artist_id, genre_id))

    # ---------- 9. Факты ----------
    cur.execute('''
        SELECT o.userID, o.Track, o.dt, o.time, o.City, o.Day
        FROM ods_music o
    ''')
    fact_rows = cur.fetchall()

    inserted = 0
    for userID, Track, dt, time_val, city, day in fact_rows:
        cur.execute('SELECT user_id FROM dim_user WHERE user_hash = ?', (userID,))
        r = cur.fetchone()
        if not r:
            continue
        user_id = r[0]

        cur.execute('SELECT track_id FROM dim_track WHERE track_name = ?', (Track,))
        r = cur.fetchone()
        if not r:
            continue
        track_id = r[0]

        cur.execute('SELECT date_id FROM dim_date WHERE date = ?', (dt,))
        r = cur.fetchone()
        if not r:
            continue
        date_id = r[0]

        cur.execute('SELECT time_id FROM dim_time WHERE time_value = ?', (time_val,))
        r = cur.fetchone()
        if not r:
            continue
        time_id = r[0]

        cur.execute('SELECT city_id FROM dim_city WHERE city_name = ?', (city,))
        r = cur.fetchone()
        if not r:
            continue
        city_id = r[0]

        cur.execute('SELECT day_id FROM dim_day WHERE day_name = ?', (day,))
        r = cur.fetchone()
        if not r:
            continue
        day_id = r[0]

        cur.execute('''
            INSERT INTO fact_listening (user_id, track_id, date_id, time_id, city_id, day_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, track_id, date_id, time_id, city_id, day_id))
        inserted += 1

    conn.commit()
    conn.close()
    print(f'Загружено {inserted} записей в fact_listening')