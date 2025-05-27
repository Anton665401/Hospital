from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify
import os
import urllib.parse
import psycopg2
from psycopg2.extras import RealDictCursor
import subprocess
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')

# Получаем URL подключения к базе из переменной окружения
DATABASE_URL = os.environ.get('DATABASE_URL')
print("DATABASE_URL =", os.environ.get('DATABASE_URL'))

def get_db_connection():
    # Разбираем URL подключения
    result = urllib.parse.urlparse(DATABASE_URL)
    username = result.username
    password = urllib.parse.unquote(result.password)
    database = result.path[1:]  # убираем первый слэш
    hostname = result.hostname
    port = result.port

    conn = psycopg2.connect(
        dbname=database,
        user=username,
        password=password,
        host=hostname,
        port=port,
        cursor_factory=RealDictCursor
    )
    return conn

def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Создаем таблицы, если они не существуют
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
    
    # Добавляем администратора, если его нет
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO users (username, password, is_admin) VALUES (%s, %s, %s)",
            ('admin', 'Qq12345', True)
        )
    
    conn.commit()
    cursor.close()
    conn.close()

# Инициализация базы данных
initialize_database()

@app.route('/')
def index():
    username = session.get('username')
    return render_template('index.html', username=username)

@app.route('/index.html')
def index_html():
    username = session.get('username')
    return render_template('index.html', username=username)

@app.route('/static/<path:filename>')
def custom_static(filename):
    return send_from_directory(os.path.join(app.root_path, 'static'), filename)

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
            
            user = cursor.fetchone()
            conn.commit()
            
            session['user_id'] = user['id']
            session['username'] = username
            session['full_name'] = full_name
            session['phone'] = phone
            session['email'] = email
            session['is_admin'] = False
            
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
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
        
        cursor.execute('''
            SELECT * FROM users 
            WHERE username = %s AND password = %s
        ''', (username, password))
        
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

@app.route('/login.html')
def login_html():
    return render_template('login.html')

@app.route('/register.html')
def register_html():
    return render_template('register.html')

@app.route('/admin')
def admin_panel():
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE is_admin = FALSE')
    users = cursor.fetchall()
    
    cursor.execute('''
        SELECT a.*, u.full_name, u.username 
        FROM appointments a
        JOIN users u ON a.user_id = u.id
    ''')
    appointments = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin.html', users=users, appointments=appointments)

@app.route('/specialists')
def specialists():
    return render_template('specialists.html')

@app.route('/other-doctors.html')
def other_doctors_html():
    return render_template('other-doctors.html')

@app.route('/creator.html')
def creator_html():
    return render_template('creator.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        phone = request.form['phone']
        email = request.form['email']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET username = %s, password = %s, 
                full_name = %s, phone = %s, email = %s
            WHERE id = %s
        ''', (username, password, full_name, phone, email, user_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return redirect(url_for('admin_panel'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return render_template('edit_user.html', user=user)

@app.route('/consultation')
def consultation():
    full_name = session.get('full_name', '')
    phone = session.get('phone', '')
    email = session.get('email', '')
    return render_template('consultation.html', full_name=full_name, phone=phone, email=email)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    return redirect(url_for('admin_panel'))

@app.route('/submit_appointment', methods=['POST'])
def submit_appointment():
    data = request.json
    fullname = data.get('fullname')
    phone = data.get('phone')
    specialist = data.get('specialist')
    date = data.get('date')
    time = data.get('time')
    comment = data.get('comment')
    policy = data.get('policy')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Проверка на существование дубликатов
    cursor.execute('''
        SELECT * FROM appointments 
        WHERE user_id = %s AND doctor = %s AND date = %s AND time = %s
    ''', (session.get('user_id'), specialist, date, time))
    
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'status': 'error', 'message': 'Запись на это время уже существует'})

    # Сохранение данных в базе данных
    cursor.execute('''
        INSERT INTO appointments (user_id, doctor, date, time, policy)
        VALUES (%s, %s, %s, %s, %s)
    ''', (session.get('user_id'), specialist, date, time, policy))
    
    conn.commit()
    
    # Удаление дубликатов
    cursor.execute('''
        DELETE FROM appointments
        WHERE ctid NOT IN (
            SELECT min(ctid)
            FROM appointments
            GROUP BY user_id, doctor, date, time
        )
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'status': 'success', 'message': 'Запись на прием успешно сохранена'})

@app.route('/view_appointments/<int:user_id>', methods=['GET'])
def view_appointments(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM appointments WHERE user_id = %s', (user_id,))
    appointments = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('view_appointments.html', appointments=appointments)

@app.route('/clear_appointments', methods=['POST'])
def clear_appointments():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM appointments')
    conn.commit()
    
    cursor.close()
    conn.close()
    
    return redirect(url_for('admin_panel'))

@app.route('/delete_appointment/<int:appointment_id>', methods=['POST'])
def delete_appointment(appointment_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM appointments WHERE id = %s', (appointment_id,))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    return redirect(url_for('admin_panel'))

@app.route('/clear_all_appointments', methods=['POST'])
def clear_all_appointments():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM appointments')
    conn.commit()
    
    cursor.close()
    conn.close()
    
    return redirect(url_for('admin_panel'))

@app.route('/delete_selected_appointments', methods=['POST'])
def delete_selected_appointments():
    appointment_ids = request.json.get('appointmentIds', [])
    
    if not appointment_ids:
        return jsonify({'status': 'error', 'message': 'No appointment IDs provided'})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        for appointment_id in appointment_ids:
            cursor.execute('DELETE FROM appointments WHERE id = %s', (appointment_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)})
    finally:
        cursor.close()
        conn.close()
    
    return jsonify({'status': 'success'})

@app.route('/upload_video', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'status': 'error', 'message': 'No video file part'}), 400

    file = request.files['video']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No video file selected'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Увеличение видео в 3 раза
        scaled_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f'scaled_{filename}')
        subprocess.run(['ffmpeg', '-i', filepath, '-vf', 'scale=iw*3:ih*3', scaled_filepath])

        return jsonify({'status': 'success', 'message': 'Video uploaded and scaled successfully'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Invalid file type'}), 400

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/services.html')
def services_html():
    return render_template('services.html')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'mp4', 'avi', 'mov', 'mkv'}

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

if __name__ == '__main__':
    initialize_database()
    app.run()
