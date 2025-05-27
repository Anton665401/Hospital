from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify
import os
import subprocess
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Используем временную директорию /tmp для Vercel
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Получаем URL подключения к базе из переменной окружения (укажи в Vercel)
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Создаем таблицы, если их нет
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
    # Добавляем админа, если нет
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (username, password, is_admin) VALUES (%s, %s, %s)", ('admin', 'Qq12345', True))
    conn.commit()
    cursor.close()
    conn.close()

# Инициализация базы
initialize_database()

@app.route('/')
def index():
    username = session.get('username')
    return render_template('index.html', username=username)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        phone = request.form['phone']
        email = request.form['email']
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (username, password, full_name, phone, email, is_admin)
                VALUES (%s, %s, %s, %s, %s, FALSE)
                RETURNING id
            ''', (username, password, full_name, phone, email))
            user_id = cursor.fetchone()['id']
            conn.commit()

            session['user_id'] = user_id
            session['username'] = username
            session['full_name'] = full_name
            session['phone'] = phone
            session['email'] = email

        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            cursor.close()
            conn.close()
            return 'Логин уже существует'
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['phone'] = user['phone']
            session['email'] = user['email']
            session['is_admin'] = user['is_admin']
            if user['is_admin']:
                return redirect(url_for('admin_panel'))
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Неправильное имя пользователя или пароль')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Добавляй остальные маршруты по аналогии с get_db_connection() и cursor.execute() с %s

if __name__ == '__main__':
    app.run()
