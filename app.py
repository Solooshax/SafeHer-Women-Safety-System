from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'women_safety_secret_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///women_safety.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'recordings')

db = SQLAlchemy(app)

# ─────────────────────────────────────────
# DATABASE MODELS
# ─────────────────────────────────────────

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    contacts = db.relationship('EmergencyContact', backref='user', lazy=True, cascade='all, delete-orphan')
    alerts = db.relationship('AlertHistory', backref='user', lazy=True, cascade='all, delete-orphan')

class EmergencyContact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    relationship = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AlertHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)
    alert_message = db.Column(db.Text, nullable=False)
    location_lat = db.Column(db.Float, nullable=True)
    location_lng = db.Column(db.Float, nullable=True)
    location_link = db.Column(db.String(300), nullable=True)
    contact_name = db.Column(db.String(100), nullable=True)
    contact_phone = db.Column(db.String(20), nullable=True)
    audio_file = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(50), default='Delivered Successfully')
    triggered_by = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ─── NEW MODEL ───────────────────────────
class Notification(db.Model):
    """
    Jab koi SOS trigger kare aur emergency contact registered user ho,
    toh us contact ke account mein yeh notification save hoti hai.
    """
    id = db.Column(db.Integer, primary_key=True)
    recipient_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # contact ka account
    sender_name = db.Column(db.String(100), nullable=False)   # alert bhejne wali user ka naam
    sender_phone = db.Column(db.String(20), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)
    alert_message = db.Column(db.Text, nullable=False)
    location_link = db.Column(db.String(300), nullable=True)
    audio_file = db.Column(db.String(200), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    recipient = db.relationship('User', backref='notifications', foreign_keys=[recipient_user_id])
# ─────────────────────────────────────────


# ─────────────────────────────────────────
# NLP / AI LOGIC
# ─────────────────────────────────────────

DISTRESS_KEYWORDS = [
    'help', 'save me', 'emergency', 'bachao', 'mujhe bachao',
    'danger', 'scared', 'attack', 'threat', 'unsafe', 'kidnap',
    'following', 'stalking', 'harass', 'hurt', 'rape', 'abuse',
    'run', 'escape', 'please help', 'sos', 'call police',
    'maaro', 'maar', 'khatra', 'darao', 'dara', 'chod do',
    'chordo', 'chodo', 'chhodo', 'let me go', 'leave me'
]

UNSAFE_PHRASES = [
    'following me', 'stalking me', 'feels unsafe', 'feel unsafe',
    'scared', 'someone behind', 'being chased', 'threatening me',
    'grabbed', 'attacked', 'hit me', 'pushed me', 'feels dangerous',
    'suspicious man', 'suspicious person', 'dark alley', 'alone at night',
    'strange man', 'strange person', 'help me', 'please help',
    'mujhe dar', 'dar lag raha', 'koi hai', 'koi peeche', 'bachao',
    'harassing', 'molesting', 'hurting', 'threatening', 'abusing',
    'stranded', 'lost', 'no one around', 'nobody around'
]

SAFE_PHRASES = [
    'going to work', 'travelling to work', 'on my way home',
    'shopping', 'with friends', 'with family', 'all good',
    'safe', 'reached safely', 'fine', 'okay', 'ok',
    'just going out', 'normal day', 'college', 'office'
]

def analyze_text_safety(text):
    text_lower = text.lower().strip()
    unsafe_score = 0
    safe_score = 0
    matched_phrases = []
    for phrase in UNSAFE_PHRASES:
        if phrase in text_lower:
            unsafe_score += 2
            matched_phrases.append(phrase)
    for phrase in SAFE_PHRASES:
        if phrase in text_lower:
            safe_score += 1
    danger_words = ['danger', 'help', 'scared', 'fear', 'threat', 'attack',
                    'run', 'escape', 'afraid', 'hurt', 'bachao', 'khatra']
    for word in danger_words:
        if word in text_lower:
            unsafe_score += 1
    is_unsafe = unsafe_score > safe_score
    confidence = min(95, 60 + (abs(unsafe_score - safe_score) * 8))
    recommendation = (
        "⚠️ Distress signals detected in your message. Please trigger SOS if you are in danger."
        if is_unsafe else
        "✅ Your situation appears safe. Stay aware of your surroundings."
    )
    return {
        'is_unsafe': is_unsafe,
        'label': 'UNSAFE' if is_unsafe else 'SAFE',
        'confidence': confidence,
        'matched_phrases': matched_phrases[:3],
        'recommendation': recommendation
    }

def generate_emergency_message(situation_text, user_name, location_link=None):
    situation_summary = situation_text[:120] if len(situation_text) > 120 else situation_text
    message = (
        f"🚨 EMERGENCY ALERT 🚨\n\n"
        f"{user_name} may be in DANGER and requires IMMEDIATE assistance!\n\n"
        f"Situation: {situation_summary}\n"
        f"Time: {datetime.now().strftime('%d %B %Y, %I:%M %p')}\n"
    )
    if location_link:
        message += f"Live Location: {location_link}\n"
    message += "\nPlease call her immediately or contact local authorities. This is an automated emergency alert."
    return message

def check_distress_keywords(speech_text):
    text_lower = speech_text.lower()
    detected = []
    for kw in DISTRESS_KEYWORDS:
        if kw in text_lower:
            detected.append(kw)
    return detected


# ─────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        phone = data.get('phone', '').strip()
        password = data.get('password', '')
        if not all([name, email, phone, password]):
            return jsonify({'success': False, 'message': 'All fields are required.'})
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': 'Email already registered.'})
        user = User(name=name, email=email, phone=phone,
                    password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Registration successful!'})
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Invalid email or password.'})
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)


# ─────────────────────────────────────────
# EMERGENCY CONTACTS API
# ─────────────────────────────────────────

@app.route('/api/contacts', methods=['GET'])
def get_contacts():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    contacts = EmergencyContact.query.filter_by(user_id=session['user_id']).all()
    return jsonify({'success': True, 'contacts': [
        {'id': c.id, 'name': c.name, 'relationship': c.relationship,
         'phone': c.phone, 'is_primary': c.is_primary} for c in contacts
    ]})

@app.route('/api/contacts', methods=['POST'])
def add_contact():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    existing = EmergencyContact.query.filter_by(user_id=session['user_id']).count()
    if existing >= 5:
        return jsonify({'success': False, 'message': 'Maximum 5 contacts allowed.'})
    data = request.get_json()
    contact = EmergencyContact(
        user_id=session['user_id'], name=data['name'],
        relationship=data['relationship'], phone=data['phone'],
        is_primary=(existing == 0)
    )
    db.session.add(contact)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Contact added successfully.'})

@app.route('/api/contacts/<int:contact_id>', methods=['PUT'])
def update_contact(contact_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    contact = EmergencyContact.query.filter_by(id=contact_id, user_id=session['user_id']).first()
    if not contact:
        return jsonify({'success': False, 'message': 'Contact not found.'})
    data = request.get_json()
    contact.name = data.get('name', contact.name)
    contact.relationship = data.get('relationship', contact.relationship)
    contact.phone = data.get('phone', contact.phone)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Contact updated successfully.'})

@app.route('/api/contacts/<int:contact_id>', methods=['DELETE'])
def delete_contact(contact_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    contact = EmergencyContact.query.filter_by(id=contact_id, user_id=session['user_id']).first()
    if not contact:
        return jsonify({'success': False, 'message': 'Contact not found.'})
    was_primary = contact.is_primary
    db.session.delete(contact)
    db.session.commit()
    if was_primary:
        next_contact = EmergencyContact.query.filter_by(user_id=session['user_id']).first()
        if next_contact:
            next_contact.is_primary = True
            db.session.commit()
    return jsonify({'success': True, 'message': 'Contact deleted.'})

@app.route('/api/contacts/<int:contact_id>/set-primary', methods=['POST'])
def set_primary_contact(contact_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    EmergencyContact.query.filter_by(user_id=session['user_id']).update({'is_primary': False})
    contact = EmergencyContact.query.filter_by(id=contact_id, user_id=session['user_id']).first()
    if not contact:
        return jsonify({'success': False, 'message': 'Contact not found.'})
    contact.is_primary = True
    db.session.commit()
    return jsonify({'success': True, 'message': f'{contact.name} set as primary contact.'})


# ─────────────────────────────────────────
# EMERGENCY / SOS API  ← UPDATED
# ─────────────────────────────────────────

@app.route('/api/sos', methods=['POST'])
def trigger_sos():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    data = request.get_json()
    lat = data.get('lat')
    lng = data.get('lng')
    alert_type = data.get('alert_type', 'SOS')
    triggered_by = data.get('triggered_by', 'Manual SOS Button')
    audio_file = data.get('audio_file', None)  # yeh '/recordings/filename.webm' hoga

    location_link = f"https://www.google.com/maps?q={lat},{lng}" if lat and lng else None
    user = User.query.get(session['user_id'])

    all_contacts = EmergencyContact.query.filter_by(user_id=session['user_id']).all()
    primary = next((c for c in all_contacts if c.is_primary), None) or (all_contacts[0] if all_contacts else None)

    message = generate_emergency_message(f"SOS triggered by {user.name}", user.name, location_link)

    alert = AlertHistory(
        user_id=session['user_id'],
        alert_type=alert_type,
        alert_message=message,
        location_lat=lat, location_lng=lng,
        location_link=location_link,
        contact_name=primary.name if primary else 'N/A',
        contact_phone=primary.phone if primary else 'N/A',
        audio_file=audio_file,  # store as-is
        triggered_by=triggered_by,
        status='Delivered Successfully'
    )
    db.session.add(alert)

    # ── ONLY PRIMARY CONTACT ko notify karo ──
    notifications_sent = []
    if primary:
        primary_phone_clean = primary.phone.replace(' ', '').replace('-', '').replace('+91', '')
        registered_contact = None
        for u in User.query.all():
            u_phone_clean = u.phone.replace(' ', '').replace('-', '').replace('+91', '')
            if u_phone_clean == primary_phone_clean and u.id != session['user_id']:
                registered_contact = u
                break

        if registered_contact:
            notif = Notification(
                recipient_user_id=registered_contact.id,
                sender_name=user.name,
                sender_phone=user.phone,
                alert_type=alert_type,
                alert_message=message,
                location_link=location_link,
                audio_file=audio_file,  # same path pass karo
                is_read=False
            )
            db.session.add(notif)
            notifications_sent.append(registered_contact.name)

    db.session.commit()

    return jsonify({
        'success': True,
        'alert_id': alert.id,
        'message': message,
        'contact_name': primary.name if primary else 'N/A',
        'contact_phone': primary.phone if primary else 'N/A',
        'location_link': location_link,
        'audio_file': audio_file,
        'timestamp': alert.created_at.strftime('%d %b %Y, %I:%M %p'),
        'notifications_sent_to': notifications_sent
    })

# ─────────────────────────────────────────
# NOTIFICATIONS API  ← NEW
# ─────────────────────────────────────────

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    """Logged-in user ke liye saari notifications."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    notifs = Notification.query.filter_by(recipient_user_id=session['user_id'])\
        .order_by(Notification.created_at.desc()).all()
    return jsonify({'success': True, 'notifications': [
        {
            'id': n.id,
            'sender_name': n.sender_name,
            'sender_phone': n.sender_phone,
            'alert_type': n.alert_type,
            'alert_message': n.alert_message,
            'location_link': n.location_link,
            'audio_file': n.audio_file,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%d %b %Y, %I:%M %p')
        } for n in notifs
    ]})

@app.route('/api/notifications/unread-count', methods=['GET'])
def unread_count():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    count = Notification.query.filter_by(
        recipient_user_id=session['user_id'], is_read=False
    ).count()
    return jsonify({'success': True, 'count': count})

@app.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
def mark_read(notif_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    notif = Notification.query.filter_by(id=notif_id, recipient_user_id=session['user_id']).first()
    if notif:
        notif.is_read = True
        db.session.commit()
    return jsonify({'success': True})

@app.route('/api/notifications/mark-all-read', methods=['POST'])
def mark_all_read():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    Notification.query.filter_by(
        recipient_user_id=session['user_id'], is_read=False
    ).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})


# ─────────────────────────────────────────
# AI FEATURES API
# ─────────────────────────────────────────

@app.route('/api/ai/analyze-text', methods=['POST'])
def analyze_text():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    data = request.get_json()
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'success': False, 'message': 'Text is required.'})
    result = analyze_text_safety(text)
    return jsonify({'success': True, **result})

@app.route('/api/ai/generate-alert', methods=['POST'])
def generate_alert():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    data = request.get_json()
    situation = data.get('situation', '')
    lat = data.get('lat')
    lng = data.get('lng')
    location_link = f"https://www.google.com/maps?q={lat},{lng}" if lat and lng else None
    user = User.query.get(session['user_id'])
    message = generate_emergency_message(situation, user.name, location_link)
    return jsonify({'success': True, 'message': message})

@app.route('/api/ai/voice-distress', methods=['POST'])
def voice_distress_check():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    data = request.get_json()
    speech_text = data.get('text', '')
    detected = check_distress_keywords(speech_text)
    return jsonify({'success': True, 'distress_detected': len(detected) > 0, 'keywords': detected})

@app.route('/api/ai/save-recording', methods=['POST'])
def save_recording():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    if 'audio' not in request.files:
        return jsonify({'success': False, 'message': 'No audio file received.'})
    audio = request.files['audio']
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"recording_{session['user_id']}_{timestamp}.webm"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    audio.save(filepath)
    url_path = f'/recordings/{filename}'
    return jsonify({
        'success': True,
        'filename': filename,
        'filepath': url_path,   # ← yahi SOS mein pass karna hai
        'url': url_path
    })

@app.route('/recordings/<filename>')
def serve_recording(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ─────────────────────────────────────────
# ALERT HISTORY API
# ─────────────────────────────────────────
@app.route('/api/recordings', methods=['GET'])
def get_recordings():
    """User ki saari saved recordings return karo."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    recordings = AlertHistory.query.filter_by(user_id=session['user_id'])\
        .filter(AlertHistory.audio_file.isnot(None))\
        .order_by(AlertHistory.created_at.desc()).all()
    
    # Manual recordings bhi dhundho (jo SOS se attached nahi hain)
    upload_folder = app.config['UPLOAD_FOLDER']
    manual_files = []
    if os.path.exists(upload_folder):
        for fname in sorted(os.listdir(upload_folder), reverse=True):
            if fname.startswith(f"recording_{session['user_id']}_") and fname.endswith('.webm'):
                filepath = f'/recordings/{fname}'
                fpath_full = os.path.join(upload_folder, fname)
                size = os.path.getsize(fpath_full) if os.path.exists(fpath_full) else 0
                manual_files.append({
                    'filename': fname,
                    'filepath': filepath,
                    'size_kb': round(size / 1024, 1),
                    'created_at': datetime.fromtimestamp(os.path.getctime(fpath_full)).strftime('%d %b %Y, %I:%M %p') if os.path.exists(fpath_full) else 'Unknown'
                })
    
    return jsonify({
        'success': True,
        'recordings': manual_files
    })

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    alerts = AlertHistory.query.filter_by(user_id=session['user_id'])\
        .order_by(AlertHistory.created_at.desc()).limit(50).all()
    return jsonify({'success': True, 'alerts': [
        {
            'id': a.id, 'alert_type': a.alert_type,
            'alert_message': a.alert_message,
            'location_link': a.location_link,
            'contact_name': a.contact_name,
            'contact_phone': a.contact_phone,
            'audio_file': a.audio_file,
            'status': a.status,
            'triggered_by': a.triggered_by,
            'created_at': a.created_at.strftime('%d %b %Y, %I:%M %p')
        } for a in alerts
    ]})

@app.route('/api/user/stats', methods=['GET'])
def get_user_stats():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    total_alerts = AlertHistory.query.filter_by(user_id=session['user_id']).count()
    total_contacts = EmergencyContact.query.filter_by(user_id=session['user_id']).count()
    sos_alerts = AlertHistory.query.filter_by(user_id=session['user_id'], alert_type='SOS').count()
    voice_alerts = AlertHistory.query.filter_by(user_id=session['user_id'], alert_type='VoiceGuard').count()
    return jsonify({
        'success': True,
        'total_alerts': total_alerts,
        'total_contacts': total_contacts,
        'sos_alerts': sos_alerts,
        'voice_alerts': voice_alerts
    })


# ─────────────────────────────────────────
# INIT DB
# ─────────────────────────────────────────

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)