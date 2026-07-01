import os
import sys
sys.dont_write_bytecode = True
import sqlite3
import json
import hashlib
import secrets
import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from chatbot import ChatBot
from tax_engine import TaxEngine

# ---------------------------------------------------------------------------
# App Configuration
# ---------------------------------------------------------------------------

app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

if os.environ.get('VERCEL'):
    app.config['DATABASE'] = '/tmp/taxbot.db'
else:
    app.config['DATABASE'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'taxbot.db')

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# ---------------------------------------------------------------------------
# Database Helpers
# ---------------------------------------------------------------------------


def get_db():
    """Return a sqlite3 connection with Row factory for dict-like access."""
    db = sqlite3.connect(app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    if not os.environ.get('VERCEL'):
        db.execute('PRAGMA journal_mode=WAL')
    return db


def init_db():
    """Create all required tables if they do not exist."""
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            otp TEXT,
            otp_expiry TEXT,
            is_verified INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tax_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_data TEXT,
            marital_status TEXT,
            total_income REAL,
            tax_old_regime REAL,
            tax_new_regime REAL,
            recommended_regime TEXT,
            savings REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            msg_type TEXT DEFAULT 'text',
            msg_data TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES tax_sessions(id)
        );
    ''')
    db.commit()
    db.close()

# Initialize database on application import
init_db()

# ---------------------------------------------------------------------------
# Password Helpers
# ---------------------------------------------------------------------------


def hash_password(password):
    """Hash a password with a random salt using SHA-256."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password, stored_hash):
    """Verify a password against a stored salt:hash string."""
    salt, hashed = stored_hash.split(':')
    return hashlib.sha256((salt + password).encode()).hexdigest() == hashed

# ---------------------------------------------------------------------------
# OTP Helpers
# ---------------------------------------------------------------------------


def generate_otp():
    """Generate a 6-digit random OTP."""
    return ''.join(random.choices(string.digits, k=6))


def send_otp_email(email, otp):
    """Send an OTP verification email. Falls back to console in demo mode."""
    try:
        smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        smtp_user = os.environ.get('SMTP_USER', '')
        smtp_pass = os.environ.get('SMTP_PASS', '')

        if not smtp_user or not smtp_pass:
            print(f'[DEMO MODE] OTP for {email}: {otp}')
            return True

        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = email
        msg['Subject'] = 'TaxBot - Your Verification OTP'

        body = f"""
        <html><body style="font-family: Arial; background: #0a0e27; color: white; padding: 20px;">
        <div style="max-width: 500px; margin: auto; background: linear-gradient(135deg, #667eea, #764ba2); padding: 30px; border-radius: 15px;">
        <h2 style="text-align: center;">\U0001f916 TaxBot Verification</h2>
        <p>Your verification code is:</p>
        <h1 style="text-align: center; letter-spacing: 10px; font-size: 36px;">{otp}</h1>
        <p>This code expires in 10 minutes.</p>
        <p style="color: #ccc; font-size: 12px;">If you didn't request this, please ignore this email.</p>
        </div></body></html>
        """
        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f'Email sending failed: {e}')
        print(f'[DEMO MODE] OTP for {email}: {otp}')
        return True

# ---------------------------------------------------------------------------
# Auth Decorator
# ---------------------------------------------------------------------------


def login_required(f):
    """Decorator that returns 401 if the user is not logged in."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

# ---------------------------------------------------------------------------
# Instantiate ChatBot
# ---------------------------------------------------------------------------

chatbot = ChatBot()

# ---------------------------------------------------------------------------
# Routes — Pages
# ---------------------------------------------------------------------------


@app.route('/')
def index():
    """Serve the main single-page application."""
    return render_template('index.html')

# ---------------------------------------------------------------------------
# Routes — Auth
# ---------------------------------------------------------------------------


@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user with email and password. Sends OTP for verification."""
    data = request.get_json()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password', '')

    # Validate email (basic)
    if not email or '@' not in email or '.' not in email.split('@')[-1]:
        return jsonify({'success': False, 'message': 'Please enter a valid email address.'}), 400

    # Validate password
    if len(password) < 6:
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters.'}), 400

    db = get_db()
    try:
        existing = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            return jsonify({'success': False, 'message': 'An account with this email already exists.'}), 409

        otp = generate_otp()
        otp_expiry = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        pwd_hash = hash_password(password)

        db.execute(
            'INSERT INTO users (email, password_hash, otp, otp_expiry, is_verified) VALUES (?, ?, ?, ?, 0)',
            (email, pwd_hash, otp, otp_expiry)
        )
        db.commit()

        send_otp_email(email, otp)

        return jsonify({
            'success': True,
            'message': 'OTP sent to your email. Please verify to complete registration.',
            'otp': otp  # Included for demo/testing purposes
        })
    finally:
        db.close()


@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    """Verify the OTP sent during registration."""
    data = request.get_json()
    email = (data.get('email') or '').strip().lower()
    otp = (data.get('otp') or '').strip()

    db = get_db()
    try:
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if not user:
            return jsonify({'success': False, 'message': 'User not found.'}), 404

        if user['otp'] != otp:
            return jsonify({'success': False, 'message': 'Invalid OTP. Please try again.'}), 400

        # Check expiry
        if user['otp_expiry']:
            expiry = datetime.fromisoformat(user['otp_expiry'])
            if datetime.utcnow() > expiry:
                return jsonify({'success': False, 'message': 'OTP has expired. Please register again.'}), 400

        db.execute(
            'UPDATE users SET is_verified = 1, otp = NULL, otp_expiry = NULL WHERE id = ?',
            (user['id'],)
        )
        db.commit()

        session['user_id'] = user['id']
        session['user_email'] = email
        session.permanent = True

        return jsonify({'success': True, 'message': 'Email verified successfully! Welcome to TaxBot.'})
    finally:
        db.close()


@app.route('/api/login', methods=['POST'])
def login():
    """Log in with email and password."""
    data = request.get_json()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password', '')

    db = get_db()
    try:
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if not user:
            return jsonify({'success': False, 'message': 'Invalid email or password.'}), 401

        if not verify_password(password, user['password_hash']):
            return jsonify({'success': False, 'message': 'Invalid email or password.'}), 401

        if not user['is_verified']:
            return jsonify({'success': False, 'message': 'Please verify your email first.'}), 403

        session['user_id'] = user['id']
        session['user_email'] = email
        session.permanent = True

        return jsonify({'success': True, 'message': 'Login successful!', 'email': email})
    finally:
        db.close()


@app.route('/api/logout', methods=['POST'])
def logout():
    """Log out the current user."""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully.'})


@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    """Check if the current session is authenticated."""
    if 'user_id' in session:
        return jsonify({'authenticated': True, 'email': session.get('user_email')})
    return jsonify({'authenticated': False, 'email': None})

# ---------------------------------------------------------------------------
# Routes — Chat
# ---------------------------------------------------------------------------


@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """Process a chat message and return the bot's response."""
    data = request.get_json()
    message = (data.get('message') or '').strip()

    if not message:
        return jsonify({'success': False, 'message': 'Message cannot be empty.'}), 400

    user_id = session['user_id']

    # Get or initialize chat state
    chat_state = session.get('chat_state')
    if not chat_state:
        chat_state = chatbot.get_initial_state()

    # Ensure a tax_session exists in the DB
    tax_session_id = session.get('tax_session_id')
    db = get_db()
    try:
        if not tax_session_id:
            cursor = db.execute(
                'INSERT INTO tax_sessions (user_id, session_data) VALUES (?, ?)',
                (user_id, json.dumps(chat_state))
            )
            db.commit()
            tax_session_id = cursor.lastrowid
            session['tax_session_id'] = tax_session_id

        # Process the message through the chatbot
        result = chatbot.process_message(message, chat_state)

        # Store user message
        db.execute(
            'INSERT INTO chat_messages (session_id, role, content, msg_type, msg_data) VALUES (?, ?, ?, ?, ?)',
            (tax_session_id, 'user', message, 'text', None)
        )

        # Store bot response
        db.execute(
            'INSERT INTO chat_messages (session_id, role, content, msg_type, msg_data) VALUES (?, ?, ?, ?, ?)',
            (tax_session_id, 'bot', result['response'], result.get('type', 'text'),
             json.dumps(result.get('data')) if result.get('data') else None)
        )

        # If calculation is complete, update the tax_session record
        user_data = chat_state.get('user_data', {})
        comparison = user_data.get('comparison')
        if comparison:
            db.execute(
                '''UPDATE tax_sessions
                   SET session_data = ?,
                       marital_status = ?,
                       total_income = ?,
                       tax_old_regime = ?,
                       tax_new_regime = ?,
                       recommended_regime = ?,
                       savings = ?,
                       updated_at = ?
                   WHERE id = ?''',
                (
                    json.dumps(chat_state),
                    user_data.get('marital_status'),
                    user_data.get('gross_income'),
                    comparison.get('old_regime', {}).get('total_tax'),
                    comparison.get('new_regime', {}).get('total_tax'),
                    comparison.get('recommended'),
                    comparison.get('savings'),
                    datetime.utcnow().isoformat(),
                    tax_session_id
                )
            )
        else:
            db.execute(
                'UPDATE tax_sessions SET session_data = ?, updated_at = ? WHERE id = ?',
                (json.dumps(chat_state), datetime.utcnow().isoformat(), tax_session_id)
            )

        db.commit()

        # Persist chat state in the Flask session
        session['chat_state'] = chat_state

        return jsonify({
            'response': result['response'],
            'suggestions': result.get('suggestions', []),
            'type': result.get('type', 'text'),
            'data': result.get('data')
        })
    finally:
        db.close()


@app.route('/api/new-session', methods=['POST'])
@login_required
def new_session():
    """Start a fresh chat session."""
    user_id = session['user_id']
    chat_state = chatbot.get_initial_state()

    db = get_db()
    try:
        cursor = db.execute(
            'INSERT INTO tax_sessions (user_id, session_data) VALUES (?, ?)',
            (user_id, json.dumps(chat_state))
        )
        db.commit()
        tax_session_id = cursor.lastrowid
    finally:
        db.close()

    session['chat_state'] = chat_state
    session['tax_session_id'] = tax_session_id

    greeting = chatbot._get_greeting_response()

    return jsonify({
        'response': greeting['response'],
        'suggestions': greeting.get('suggestions', []),
        'type': greeting.get('type', 'text'),
        'data': greeting.get('data')
    })

# ---------------------------------------------------------------------------
# Routes — History
# ---------------------------------------------------------------------------


@app.route('/api/history', methods=['GET'])
@login_required
def history():
    """Return all past tax sessions for the current user."""
    user_id = session['user_id']
    db = get_db()
    try:
        rows = db.execute(
            '''SELECT id, marital_status, total_income, tax_old_regime, tax_new_regime,
                      recommended_regime, savings, created_at
               FROM tax_sessions
               WHERE user_id = ?
               ORDER BY created_at DESC''',
            (user_id,)
        ).fetchall()

        sessions_list = []
        for row in rows:
            created = row['created_at'] or ''
            date_str = ''
            time_str = ''
            if created:
                try:
                    dt = datetime.fromisoformat(created)
                    date_str = dt.strftime('%d %b %Y')
                    time_str = dt.strftime('%I:%M %p')
                except (ValueError, TypeError):
                    date_str = created
                    time_str = ''

            sessions_list.append({
                'id': row['id'],
                'date': date_str,
                'time': time_str,
                'marital_status': row['marital_status'],
                'total_income': row['total_income'],
                'tax_old_regime': row['tax_old_regime'],
                'tax_new_regime': row['tax_new_regime'],
                'recommended_regime': row['recommended_regime'],
                'savings': row['savings']
            })

        return jsonify({'success': True, 'sessions': sessions_list})
    finally:
        db.close()


@app.route('/api/session/<int:session_id>', methods=['GET'])
@login_required
def get_session(session_id):
    """Return the full chat history and summary for a specific tax session."""
    user_id = session['user_id']
    db = get_db()
    try:
        # Verify ownership
        tax_session = db.execute(
            'SELECT * FROM tax_sessions WHERE id = ? AND user_id = ?',
            (session_id, user_id)
        ).fetchone()

        if not tax_session:
            return jsonify({'success': False, 'message': 'Session not found.'}), 404

        # Get messages
        messages = db.execute(
            'SELECT role, content, msg_type, msg_data, timestamp FROM chat_messages WHERE session_id = ? ORDER BY id',
            (session_id,)
        ).fetchall()

        messages_list = []
        for msg in messages:
            msg_data = None
            if msg['msg_data']:
                try:
                    msg_data = json.loads(msg['msg_data'])
                except (json.JSONDecodeError, TypeError):
                    msg_data = None

            messages_list.append({
                'role': msg['role'],
                'content': msg['content'],
                'type': msg['msg_type'] or 'text',
                'data': msg_data,
                'timestamp': msg['timestamp']
            })

        # Parse session data for summary
        summary = None
        if tax_session['session_data']:
            try:
                summary = json.loads(tax_session['session_data'])
            except (json.JSONDecodeError, TypeError):
                summary = None

        return jsonify({
            'success': True,
            'messages': messages_list,
            'summary': summary
        })
    finally:
        db.close()

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    init_db()
    print('')
    print('[TaxBot] AI Tax Filing Assistant')
    print('=' * 40)
    print('Server running at: http://127.0.0.1:5000')
    print('=' * 40)
    print('')
    app.run(debug=True, port=5000)
