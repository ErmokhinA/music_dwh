import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from db_utils import init_db, get_connection
from load_source import load_csv_to_source
from staging import load_source_to_staging
from ods import clean_and_load_ods
from dwh import load_ods_to_dwh


st.set_page_config(page_title='Music DWH Lab', layout='wide')

# Инициализируем БД (создаём таблицы, если их нет)
init_db()

# ---------------- Боковое меню ----------------
page = st.sidebar.selectbox(
    'Выбери страницу',
    ['Исследовательский анализ данных', 'Загрузка в хранилище']
)


# =====================================================================
# СТРАНИЦА 1. ИССЛЕДОВАТЕЛЬСКИЙ АНАЛИЗ
# =====================================================================
if page == 'Исследовательский анализ данных':
    st.title('📊 Исследовательский анализ данных music_tracks')

    # Читаем CSV
    df = pd.read_csv('music_project.csv')
    if '' in df.columns:
        df = df.drop(columns=[''])
    df.columns = [c.strip() for c in df.columns]
    expected = ['userID', 'Track', 'artist', 'genre', 'City', 'time', 'Day']
    df = df[expected]

    # ---- Общие показатели ----
    st.header('1. Общие показатели')
    col1, col2, col3 = st.columns(3)
    col1.metric('Записей', df.shape[0])
    col2.metric('Атрибутов', df.shape[1])
    col3.metric('Полных дубликатов', int(df.duplicated().sum()))

    st.subheader('Типы данных')
    st.write(df.dtypes.astype(str))

    # ---- Заполненность ----
    st.header('2. Заполненность атрибутов')
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(2)
    miss_df = pd.DataFrame({
        'Пропуски': missing,
        'Доля, %': missing_pct
    })
    st.dataframe(miss_df)

    # ---- Уникальные значения ----
    st.header('3. Уникальные значения')
    st.write(df.nunique())

    # ---- Распределение категорий ----
    st.header('4. Распределения категориальных признаков')

    cat_col = st.selectbox(
        'Выбери категориальный признак',
        ['genre', 'City', 'Day', 'artist']
    )
    top_n = st.slider('Сколько топ-значений показать', 5, 30, 15)

    counts = df[cat_col].fillna('(пусто)').value_counts().head(top_n)
    fig, ax = plt.subplots(figsize=(10, 4))
    counts.plot(kind='bar', ax=ax)
    ax.set_title(f'Топ-{top_n} значений: {cat_col}')
    ax.set_ylabel('Количество')
    st.pyplot(fig)

    # ---- Анализ времени ----
    st.header('5. Анализ поля времени')
    time_df = df[['time']].dropna().copy()
    time_df['hour'] = time_df['time'].str.slice(0, 2)

    fig, ax = plt.subplots(figsize=(10, 4))
    time_df['hour'].value_counts().sort_index().plot(kind='bar', ax=ax)
    ax.set_title('Распределение записей по часам')
    ax.set_xlabel('Час')
    ax.set_ylabel('Количество')
    st.pyplot(fig)

    # ---- Выявленные проблемы ----
    st.header('6. Выявленные проблемы качества данных')

    problems = pd.DataFrame({
        'Проблема': [
            'Пропуск в Track',
            'Пропуск в artist',
            'Пропуск в genre',
            'Пропуск в City',
            'Полные дубликаты',
            'Несогласованный регистр genre',
            'Некорректный формат времени',
            'Лишние пробелы'
        ],
        'Критерий': [
            'NULL или пустая строка',
            'NULL или пустая строка',
            'NULL или пустая строка',
            'NULL или пустая строка',
            'Все поля совпадают',
            'rock / Rock / ROCK',
            'Не соответствует HH:MM:SS',
            'Пробелы в начале/конце'
        ],
        'Обработка': [
            'Удалить запись (ключевой атрибут)',
            'Заменить на Unknown Artist',
            'Заменить на unknown',
            'Заменить на Unknown',
            'Оставить одну запись',
            'Привести к нижнему регистру',
            'Удалить запись',
            'TRIM()'
        ]
    })
    st.dataframe(problems, use_container_width=True)

    # ---- Алгоритм очистки ----
    st.header('7. Предлагаемый алгоритм очистки данных')
    st.markdown('''
    1. **Удаление полных дубликатов** — оставляем одну запись.
    2. **Удаление записей без Track** — Track ключевой, без него запись бессмысленна.
    3. **Заполнение artist / City** — подставляем `Unknown Artist` / `Unknown`.
    4. **Заполнение genre** — подставляем `unknown`.
    5. **Нормализация genre** — приводим к нижнему регистру.
    6. **Обрезка пробелов** — `strip()` для всех текстовых полей.
    7. **Проверка формата времени** — если не `HH:MM:SS`, запись удаляется.
    8. **Генерация синтетической даты `dt`** — детерминированно по хешу `userID`,
       чтобы при повторной загрузке дата не менялась.
    ''')

    st.success('Анализ завершён. Переходи во вкладку "Загрузка в хранилище" в боковом меню.')


# =====================================================================
# СТРАНИЦА 2. ЗАГРУЗКА В ХРАНИЛИЩЕ
# =====================================================================
elif page == 'Загрузка в хранилище':
    st.title('💾 Загрузка данных в хранилище')

    st.markdown('''
    Порядок действий:
    1. Загрузить CSV в таблицу-источник.
    2. Перенести данные Source → STAGING (as is).
    3. Очистить и загрузить STAGING → ODS за период.
    4. Загрузить ODS → DWH (схема «снежинка»).
    ''')

    # --- 1 ---
    st.subheader('Шаг 1. Загрузить CSV в Source')
    if st.button('▶ Загрузить CSV → music_source'):
        try:
            load_csv_to_source()
            st.success('CSV загружен в music_source ✔')
        except Exception as e:
            st.error(f'Ошибка: {e}')

    # --- 2 ---
    st.subheader('Шаг 2. Source → STAGING (без параметров)')
    if st.button('▶ Перенести Source → STAGING'):
        try:
            load_source_to_staging()
            st.success('STAGING обновлён ✔')
        except Exception as e:
            st.error(f'Ошибка: {e}')

    # --- 3 ---
    st.subheader('Шаг 3. STAGING → ODS (инкрементально)')
    col1, col2 = st.columns(2)
    with col1:
        p_sdt = st.date_input('Начало периода (p_sdt)', value=pd.to_datetime('2023-01-01'))
    with col2:
        p_edt = st.date_input('Конец периода (p_edt)', value=pd.to_datetime('2023-12-31'))

    if st.button('▶ Очистить и загрузить STAGING → ODS'):
        try:
            clean_and_load_ods(p_sdt.strftime('%Y-%m-%d'), p_edt.strftime('%Y-%m-%d'))
            st.success('ODS обновлён ✔')
        except Exception as e:
            st.error(f'Ошибка: {e}')

    # --- 4 ---
    st.subheader('Шаг 4. ODS → DWH («снежинка»)')
    if st.button('▶ Загрузить ODS → DWH'):
        try:
            load_ods_to_dwh()
            st.success('DWH загружен ✔')
        except Exception as e:
            st.error(f'Ошибка: {e}')

    # --- Просмотр содержимого ---
    st.header('🔍 Проверка данных')

    conn = get_connection()

    if st.checkbox('Показать music_source'):
        try:
            st.dataframe(pd.read_sql('SELECT * FROM music_source LIMIT 10', conn))
        except Exception as e:
            st.warning(str(e))

    if st.checkbox('Показать staging_music'):
        try:
            st.dataframe(pd.read_sql('SELECT * FROM staging_music LIMIT 10', conn))
        except Exception as e:
            st.warning(str(e))

    if st.checkbox('Показать ods_music'):
        try:
            st.dataframe(pd.read_sql('SELECT * FROM ods_music LIMIT 10', conn))
        except Exception as e:
            st.warning(str(e))

    if st.checkbox('Показать dim_* измерения'):
        try:
            st.write('dim_user', pd.read_sql('SELECT * FROM dim_user LIMIT 5', conn))
            st.write('dim_artist', pd.read_sql('SELECT * FROM dim_artist LIMIT 5', conn))
            st.write('dim_genre', pd.read_sql('SELECT * FROM dim_genre LIMIT 5', conn))
            st.write('dim_track', pd.read_sql('SELECT * FROM dim_track LIMIT 5', conn))
            st.write('dim_city', pd.read_sql('SELECT * FROM dim_city LIMIT 5', conn))
            st.write('dim_date', pd.read_sql('SELECT * FROM dim_date LIMIT 5', conn))
            st.write('dim_time', pd.read_sql('SELECT * FROM dim_time LIMIT 5', conn))
            st.write('dim_day', pd.read_sql('SELECT * FROM dim_day LIMIT 5', conn))
        except Exception as e:
            st.warning(str(e))

    if st.checkbox('Показать fact_listening'):
        try:
            st.dataframe(pd.read_sql('SELECT * FROM fact_listening LIMIT 20', conn))
        except Exception as e:
            st.warning(str(e))

    conn.close()