from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import urllib.parse

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Используем временную директорию для загрузок (Vercel поддерживает только /tmp!)
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Получаем строку подключения к базе из переменной окружения
DATABASE_URL = os.environ.get('DATABASE_URL')
print("DATABASE_URL =", repr(DATABASE_URL))

def get_db_connection():
    result = urllib.parse.urlparse(DATABASE_URL)
    username = result.username
    password = urllib.parse.unquote(result.password)
    database = result.path[1:]
    hostname = result.hostname
    port = result.port
    return psycopg2.connect(
        dbname=database,
        user=username,
        password=password,
        host=hostname,
        port=port,
        cursor_factory=RealDictCursor
    )

def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT,
            phone TEXT,
            email TEXT,
            is_admin BOOLEAN NOT NULL DEFAULT FALSE
        );
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            doctor TEXT NOT NULL,
            date DATE NOT NULL,
            time TIME NOT NULL,
            policy TEXT
        );
    ''')
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO users (username, password, is_admin) VALUES (%s, %s, %s)",
            ('admin', 'Qq12345', True)
        )
    conn.commit()
    cursor.close()
    conn.close()

# --------- Роуты -----------
@app.route('/')
def index():
    return 'Приложение работает!'

# Здесь можешь дописывать остальные маршруты...

# ---------------------------

if __name__ == '__main__':
    initialize_database()
    app.run()
