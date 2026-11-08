# 🤝 AI Job Mentor for Informal Workers

**Powered by IBM Watsonx.ai with Granite Models**

An AI-powered web application providing personalised career guidance, job discovery, government scheme finder, and skill development for India's informal workers — daily wage laborers, artisans, gig workers, and self-employed individuals.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 **AI Career Chatbot** | IBM Granite model-powered chat in English, Hindi & Telugu |
| 🔍 **Smart Job Search** | Filter by skill, location, worker type with voice search |
| 📍 **Nearby Jobs** | GPS-based location recommendations within 50km radius |
| 🏛️ **Govt Scheme Finder** | PMKVY, PM SVANidhi, MGNREGS, PM Vishwakarma, ESIC |
| 📚 **Skill Development** | Free PMKVY/NSDC courses with learning pathways |
| 👤 **Worker Profile** | Personalised dashboard with AI job recommendations |
| 🌙 **Dark Mode** | Full dark mode support across all pages |
| 🎤 **Voice Search** | Speech-to-text job search in EN/HI/TE |
| 📱 **Mobile Responsive** | Bootstrap 5 responsive design for all screen sizes |

---

## 🏗️ Project Structure

```
job_mentor_app/
├── app.py                    # Main Flask application + AI agent config
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
├── .env                      # Your actual config (DO NOT commit)
├── instance/
│   └── job_mentor.db         # SQLite database (auto-created)
├── templates/
│   ├── base.html             # Base layout with navbar + footer
│   ├── index.html            # Landing page
│   ├── dashboard.html        # User dashboard
│   ├── chatbot.html          # AI chat interface
│   ├── jobs.html             # Job search & listing
│   ├── skills.html           # Skill courses
│   ├── schemes.html          # Government schemes
│   ├── profile.html          # User profile management
│   ├── login.html            # Login page
│   └── register.html         # Registration page
└── static/
    ├── css/style.css         # Main stylesheet (dark mode, animations)
    └── js/app.js             # Frontend JavaScript
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- IBM Cloud account with Watsonx.ai project
- pip

### 1. Clone / Download the project

```bash
cd job_mentor_app
```

### 2. Create a virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```env
IBM_API_KEY=your_ibm_cloud_api_key_here
IBM_PROJECT_ID=your_watsonx_project_id_here
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
SECRET_KEY=your-super-secret-flask-key
FLASK_ENV=development
```

### 5. Run the application

```bash
python app.py
```

Visit **http://localhost:5000** in your browser.

---

## 🔑 Getting IBM Watsonx.ai Credentials

1. Create an [IBM Cloud account](https://cloud.ibm.com/registration)
2. Go to **IBM Watsonx** → [watsonx.ai](https://www.ibm.com/watsonx)
3. Create a **Project** → copy the **Project ID**
4. Go to **IBM Cloud → Manage → Access (IAM) → API keys** → Create API key
5. Copy both into your `.env` file

---

## 🤖 Customizing the AI Agent

The `AGENT_INSTRUCTIONS` section at the top of [`app.py`](app.py) controls all AI behavior:

```python
# In app.py — AGENT_CONFIG dictionary

AGENT_CONFIG = {
    "tone": "friendly, empathetic, and encouraging",    # Change agent tone
    "max_recommendations": 5,                           # Jobs per recommendation
    "nearby_radius_km": 50,                             # Search radius
    "suggest_free_courses": True,                       # Prefer free PMKVY courses
    "highlight_pmkvy": True,                            # Always mention PMKVY
    "highlight_pm_svanidhi": True,                      # Mention PM SVANidhi for vendors
    "max_response_tokens": 500,                         # Response length
    ...
}
```

**To change the AI's language defaults**, edit:
```python
"default_language": "te",   # Change to "hi" for Hindi or "te" for Telugu
```

**To change job recommendation priorities**, edit `JOB_RECOMMENDATION_PRIORITY` in the docstring.

---

## 🗄️ Database

SQLite is used by default (zero configuration). For production:

```env
# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/jobmentor

# MySQL
DATABASE_URL=mysql+pymysql://user:password@localhost/jobmentor
```

The database is auto-created and seeded with sample jobs, schemes, and courses on first run.

---

## 🌐 Deployment

### Option 1: Gunicorn (Linux/macOS)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 "app:app"
```

### Option 2: IBM Cloud Code Engine

1. Build a container image:
```bash
docker build -t job-mentor-app .
docker push your-registry/job-mentor-app
```

2. Deploy on [IBM Cloud Code Engine](https://cloud.ibm.com/codeengine)

### Option 3: Heroku / Railway

```bash
# Procfile
echo "web: gunicorn app:app" > Procfile
git push heroku main
```

### Option 4: Docker

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
```

```bash
docker build -t job-mentor .
docker run -p 5000:5000 --env-file .env job-mentor
```

---

## 🔧 Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `IBM_API_KEY` | ✅ | IBM Cloud API Key |
| `IBM_PROJECT_ID` | ✅ | Watsonx.ai Project ID |
| `IBM_WATSONX_URL` | ✅ | Watsonx.ai endpoint URL |
| `SECRET_KEY` | ✅ | Flask secret key (use a long random string) |
| `FLASK_ENV` | - | `development` or `production` |
| `DATABASE_URL` | - | DB connection string (default: SQLite) |
| `DEFAULT_LANGUAGE` | - | `en`, `hi`, or `te` (default: `en`) |
| `NEARBY_RADIUS_KM` | - | Job search radius in km (default: `50`) |
| `PORT` | - | Server port (default: `5000`) |

---

## 🎯 Target Users

- 👷 **Daily Wage Workers** — Construction, agriculture, manual labor
- 🎨 **Artisans & Craftspeople** — Weavers, potters, carpenters, blacksmiths
- 🛵 **Gig Workers** — Delivery, ride-share, freelance tasks
- 🏪 **Self-Employed** — Street vendors, home businesses
- 🏠 **Domestic Workers** — Household help, cooks, caregivers

---

## 🌍 Supported Languages

| Language | Code | Voice Search |
|---|---|---|
| English | `en` | ✅ en-IN |
| Hindi (हिन्दी) | `hi` | ✅ hi-IN |
| Telugu (తెలుగు) | `te` | ✅ te-IN |

---

## 📋 Key Government Schemes Covered

| Scheme | Benefit |
|---|---|
| **PMKVY** | Free skill training + ₹8,000 reward |
| **PM SVANidhi** | Up to ₹50,000 loan for street vendors |
| **MGNREGS** | 100 days guaranteed employment |
| **PM Vishwakarma** | Tools + credit for 18 artisan trades |
| **ESIC** | Health insurance for workers ≤₹21,000/month |
| **PM Ujjwala Yojana** | Free LPG for BPL households |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/multilingual-support`)
3. Commit your changes (`git commit -m 'Add new language support'`)
4. Push to the branch (`git push origin feature/multilingual-support`)
5. Open a Pull Request

---

## 📜 License

MIT License — Free to use, modify, and distribute.

---

## 🏆 Built With

- [Flask](https://flask.palletsprojects.com/) — Python web framework
- [IBM Watsonx.ai](https://www.ibm.com/watsonx) — Granite AI models
- [Bootstrap 5](https://getbootstrap.com/) — Responsive UI framework
- [SQLAlchemy](https://sqlalchemy.org/) — Database ORM
- [Bootstrap Icons](https://icons.getbootstrap.com/) — Icon library

---

*Empowering India's 450 million informal workers with AI-powered career guidance.*
