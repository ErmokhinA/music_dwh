from db_utils import get_connection


def load_source_to_staging():
    """Функция без входных параметров: переносит все данные из source в staging."""
    conn = get_connection()
    cur = conn.cursor()

    # Чистим staging перед загрузкой (чтобы не было дублей)
    cur.execute('DELETE FROM staging_music')

    # Переносим всё как есть
    cur.execute('''
        INSERT INTO staging_music (userID, Track, artist, genre, City, time, Day)
        SELECT userID, Track, artist, genre, City, time, Day FROM music_source
    ''')

    conn.commit()
    conn.close()
    print('STAGING обновлён (данные перенесены as is).')