import pandas as pd
from db_utils import get_connection


def load_csv_to_source(csv_path='music_project.csv'):
    # Читаем CSV
    df = pd.read_csv(csv_path)

    # Убираем первый безымянный столбец (индекс из файла)
    if '' in df.columns:
        df = df.drop(columns=[''])

    # Убираем возможные пробелы в названиях столбцов
    df.columns = [c.strip() for c in df.columns]

    # Ожидаемые столбцы
    expected_cols = ['userID', 'Track', 'artist', 'genre', 'City', 'time', 'Day']

    # Оставляем только нужные и в нужном порядке
    df = df[expected_cols]

    # Пишем в БД
    conn = get_connection()
    df.to_sql('music_source', conn, if_exists='append', index=False)
    conn.close()

    print(f'Загружено {len(df)} записей в music_source')