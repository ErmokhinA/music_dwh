import hashlib
from datetime import datetime, timedelta
from db_utils import get_connection


def clean_and_load_ods(p_sdt, p_edt):
    """
    Инкрементальная загрузка STAGING → ODS с очисткой.
    p_sdt, p_edt — строки в формате 'YYYY-MM-DD'.
    """
    conn = get_connection()
    cur = conn.cursor()

    # 1. Удаляем из ODS данные за указанный период
    cur.execute('DELETE FROM ods_music WHERE dt BETWEEN ? AND ?', (p_sdt, p_edt))

    # 2. Читаем всё из staging
    cur.execute('SELECT userID, Track, artist, genre, City, time, Day FROM staging_music')
    rows = cur.fetchall()

    cleaned = []
    seen = set()

    for row in rows:
        userID, Track, artist, genre, City, time, Day = row

        # 1) Track обязательно должен быть непустым
        if not Track or str(Track).strip() == '':
            continue

        # 2) Обрезаем пробелы и подставляем значения по умолчанию
        userID = str(userID).strip() if userID else ''
        Track = str(Track).strip()
        artist = str(artist).strip() if artist else 'Unknown Artist'
        genre = str(genre).strip().lower() if genre else 'unknown'
        City = str(City).strip() if City else 'Unknown'
        time = str(time).strip() if time else ''
        Day = str(Day).strip() if Day else 'Unknown'

        # 3) Проверка формата времени
        try:
            datetime.strptime(time, '%H:%M:%S')
        except (ValueError, TypeError):
            continue

        # 4) Удаляем дубликаты
        key = (userID, Track, artist, genre, City, time, Day)
        if key in seen:
            continue
        seen.add(key)

        # 5) Генерация синтетической даты dt
        if userID == '':
            hash_val = 0
        else:
            hash_val = int(hashlib.md5(userID.encode()).hexdigest(), 16)

        start = datetime.strptime(p_sdt, '%Y-%m-%d')
        end = datetime.strptime(p_edt, '%Y-%m-%d')
        days_range = (end - start).days
        if days_range <= 0:
            days_range = 1

        offset = hash_val % days_range
        dt = (start + timedelta(days=offset)).strftime('%Y-%m-%d')

        cleaned.append((userID, Track, artist, genre, City, time, Day, dt))

    # 3. Загружаем очищенные данные в ODS
    cur.executemany('''
        INSERT INTO ods_music (userID, Track, artist, genre, City, time, Day, dt)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', cleaned)

    conn.commit()
    conn.close()
    print(f'Загружено {len(cleaned)} записей в ODS за период {p_sdt} – {p_edt}')