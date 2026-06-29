# 🛡️ SafeHer – AI-Powered Women Safety & Emergency Alert System

A complete Flask web application for women's safety with AI-powered features including VoiceGuard distress detection, NLP text analysis, and emergency alert generation.

---

## 📁 Project Structure

```
women_safety/
├── app.py                    # Main Flask application & all routes
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── instance/
│   └── women_safety.db       # SQLite database (auto-created)
├── static/
│   ├── css/                  # Additional CSS files (if any)
│   ├── js/                   # Additional JS files (if any)
│   └── recordings/           # Saved audio evidence files
└── templates/
    ├── login.html            # Login page
    ├── register.html         # Registration page
    └── dashboard.html        # Main dashboard (all features)
```

---

## 🚀 Setup & Run

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/safeher-women-safety.git
cd safeher-women-safety
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python app.py
```

### 5. Open in Browser
```
http://localhost:5000
```

> **Note:** Use Google Chrome for full VoiceGuard AI functionality (Web Speech API support required).

---

## 🗄️ Database Schema

### Table: `user`
| Column        | Type    | Description               |
|---------------|---------|---------------------------|
| id            | INTEGER | Primary key               |
| name          | TEXT    | Full name                 |
| email         | TEXT    | Unique email address      |
| phone         | TEXT    | Phone number              |
| password_hash | TEXT    | Bcrypt hashed password    |
| created_at    | DATE    | Registration timestamp    |

### Table: `emergency_contact`
| Column       | Type    | Description               |
|--------------|---------|---------------------------|
| id           | INTEGER | Primary key               |
| user_id      | INTEGER | Foreign key → user.id     |
| name         | TEXT    | Contact full name         |
| relationship | TEXT    | Relationship type         |
| phone        | TEXT    | Contact phone number      |
| is_primary   | BOOLEAN | Is this the primary alert contact? |
| created_at   | DATE    | Timestamp                 |

### Table: `alert_history`
| Column        | Type    | Description                   |
|---------------|---------|-------------------------------|
| id            | INTEGER | Primary key                   |
| user_id       | INTEGER | Foreign key → user.id         |
| alert_type    | TEXT    | SOS / VoiceGuard / Text       |
| alert_message | TEXT    | Full emergency message        |
| location_lat  | FLOAT   | GPS latitude                  |
| location_lng  | FLOAT   | GPS longitude                 |
| location_link | TEXT    | Google Maps URL               |
| contact_name  | TEXT    | Notified contact name         |
| contact_phone | TEXT    | Notified contact phone        |
| audio_file    | TEXT    | Filename of audio evidence    |
| status        | TEXT    | Delivery status               |
| triggered_by  | TEXT    | Trigger source                |
| created_at    | DATE    | Alert timestamp               |

---

## ✨ Features

### Non-AI Features
| Feature | Description |
|---------|-------------|
| 🔐 Auth | Register/Login with secure password hashing |
| 👥 Contacts | Add up to 5 emergency contacts (CRUD) |
| ⭐ Primary Contact | Set preferred contact for first alert |
| 🆘 SOS Button | One-tap emergency alert with GPS |
| 📍 GPS Sharing | Browser Geolocation → Google Maps link |
| 📋 Alert History | Full log of all alerts with details |

### AI Features
| Feature | Technology |
|---------|-----------|
| 🎤 VoiceGuard AI | Web Speech API + keyword NLP detection |
| 🧠 Text Safety Analysis | NLP phrase matching + sentiment scoring |
| ⚡ Alert Generator | Rule-based professional message generation |
| 🎵 Audio Evidence | MediaRecorder API, auto-saves on distress |

---

## 🔑 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | User registration |
| POST | `/login` | User login |
| GET | `/logout` | Logout |
| GET | `/dashboard` | Main dashboard |
| GET | `/api/contacts` | List contacts |
| POST | `/api/contacts` | Add contact |
| PUT | `/api/contacts/<id>` | Edit contact |
| DELETE | `/api/contacts/<id>` | Delete contact |
| POST | `/api/contacts/<id>/set-primary` | Set primary |
| POST | `/api/sos` | Trigger SOS alert |
| POST | `/api/ai/analyze-text` | Text safety analysis |
| POST | `/api/ai/generate-alert` | Generate alert message |
| POST | `/api/ai/voice-distress` | Voice keyword check |
| POST | `/api/ai/save-recording` | Save audio evidence |
| GET | `/api/alerts` | Alert history |
| GET | `/api/user/stats` | Dashboard stats |

---

## 🎤 VoiceGuard Distress Keywords

English: `help`, `save me`, `emergency`, `danger`, `attack`, `scared`, `threat`, `run`, `escape`, `call police`, `let me go`

Hindi/Hinglish: `bachao`, `mujhe bachao`, `maaro`, `khatra`, `darao`

---

## 🛡️ Disclaimer

This is a **student academic demonstration project**. The alert system is **simulated** — no real SMS, WhatsApp, or phone calls are made. For a production system, integrate Twilio SMS, Firebase, or similar services.

---

## 👩‍💻 Tech Stack

- **Backend:** Python 3.x, Flask, Flask-SQLAlchemy
- **Database:** SQLite
- **Frontend:** HTML5, CSS3 (custom), Vanilla JavaScript
- **AI/NLP:** Python keyword NLP, Web Speech API, MediaRecorder API
- **APIs:** Browser Geolocation API, Google Maps link generation

---

## 📜 License

MIT License – Free for academic and educational use.
