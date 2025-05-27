from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify
import sqlite3
import os
import subprocess
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Используем временную директорию /tmp для Vercel
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
db_dir = '/tmp/USERS'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(db_dir, exist_ok=True)
db_path = os.path.join(db_dir, 'users.db')

def initialize_database():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        full_name TEXT,
                        phone TEXT,
                        email TEXT,
                        is_admin BOOLEAN NOT NULL CHECK (is_admin IN (0, 1))
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS appointments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        doctor TEXT NOT NULL,
                        date TEXT NOT NULL,
                        time TEXT NOT NULL,
                        policy TEXT,
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )''')
    # Add admin user if not exists
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)", ('admin', 'Qq12345', 1))
    conn.commit()
    conn.close()

# Initialize the database
initialize_database()

def get_db_connection():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

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
        try:
            conn.execute('INSERT INTO users (username, password, full_name, phone, email, is_admin) VALUES (?, ?, ?, ?, ?, 0)', (username, password, full_name, phone, email))
            conn.commit()
            user_id = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()['id']
            session['user_id'] = user_id
            session['username'] = username
            session['full_name'] = full_name
            session['phone'] = phone
            session['email'] = email
        except sqlite3.IntegrityError:
            return 'Логин уже существует'
        finally:
            conn.close()
        print("Session Data after registration:", dict(session))
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
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
    users = conn.execute('SELECT * FROM users WHERE is_admin = 0').fetchall()
    appointments = conn.execute('''
        SELECT a.*, u.full_name, u.username 
        FROM appointments a
        JOIN users u ON a.user_id = u.id
    ''').fetchall()
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
        conn.execute('''
            UPDATE users SET username = ?, password = ?, full_name = ?, phone = ?, email = ?
            WHERE id = ?
        ''', (username, password, full_name, phone, email, user_id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_panel'))
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
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
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
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
    
    # Проверка на существование дубликатов
    conn = get_db_connection()
    existing_appointment = conn.execute('SELECT * FROM appointments WHERE user_id = ? AND doctor = ? AND date = ? AND time = ?',
                                        (session.get('user_id'), specialist, date, time)).fetchone()
    if existing_appointment:
        return jsonify({'status': 'error', 'message': 'Запись на это время уже существует'})

    # Сохранение данных в базе данных
    conn.execute('INSERT INTO appointments (user_id, doctor, date, time, policy) VALUES (?, ?, ?, ?, ?)',
                 (session.get('user_id'), specialist, date, time, policy))
    conn.commit()
    
    # Удаление дубликатов после вставки
    conn.execute('DELETE FROM appointments WHERE rowid NOT IN (SELECT MIN(rowid) FROM appointments GROUP BY user_id, doctor, date, time)')
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success', 'message': 'Запись на прием успешно сохранена'})

@app.route('/view_appointments/<int:user_id>', methods=['GET'])
def view_appointments(user_id):
    conn = get_db_connection()
    appointments = conn.execute('SELECT * FROM appointments WHERE user_id = ?', (user_id,)).fetchall()
    conn.close()
    return render_template('view_appointments.html', appointments=appointments)

@app.route('/clear_appointments', methods=['POST'])
def clear_appointments():
    conn = get_db_connection()
    conn.execute('DELETE FROM appointments')
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/delete_appointment/<int:appointment_id>', methods=['POST'])
def delete_appointment(appointment_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM appointments WHERE id = ?', (appointment_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/clear_all_appointments', methods=['POST'])
def clear_all_appointments():
    conn = get_db_connection()
    conn.execute('DELETE FROM appointments')
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/delete_selected_appointments', methods=['POST'])
def delete_selected_appointments():
    appointment_ids = request.json.get('appointmentIds', [])
    print(f'Received appointment IDs for deletion: {appointment_ids}')
    if not appointment_ids:
        return jsonify({'status': 'error', 'message': 'No appointment IDs provided'})
    
    conn = get_db_connection()
    try:
        conn.executemany('DELETE FROM appointments WHERE id = ?', [(appointment_id,) for appointment_id in appointment_ids])
        conn.commit()
        print(f'Successfully deleted appointments: {appointment_ids}')
    except Exception as e:
        print(f'Error deleting appointments: {e}')
        return jsonify({'status': 'error', 'message': 'Failed to delete appointments'})
    finally:
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

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'mp4', 'avi', 'mov', 'mkv'}

if __name__ == '__main__':
    app.run()
