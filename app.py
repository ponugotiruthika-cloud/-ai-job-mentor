"""
╔══════════════════════════════════════════════════════════════════════╗
║          AI Job Mentor for Informal Workers - Flask Backend          ║
║          Powered by IBM Watsonx.ai with Granite Models               ║
╚══════════════════════════════════════════════════════════════════════╝

AGENT_INSTRUCTIONS
==================
This section controls ALL behavior of the AI Job Mentor agent.
Edit the values below to customize without touching application logic.

--- TONE & PERSONALITY ---
AGENT_TONE = "friendly, empathetic, and encouraging"
AGENT_PERSONALITY = "a supportive career mentor who understands the challenges
    of informal workers, daily wage earners, artisans, and gig workers"

--- LANGUAGE PREFERENCES ---
SUPPORTED_LANGUAGES = ["en", "hi", "te"]   # English, Hindi, Telugu
DEFAULT_LANGUAGE = "en"
MULTILINGUAL_GREETING = {
    "en": "Hello! I'm your AI Job Mentor. How can I help you today?",
    "hi": "नमस्ते! मैं आपका AI जॉब मेंटर हूं। आज मैं आपकी कैसे मदद कर सकता हूं?",
    "te": "నమస్కారం! నేను మీ AI జాబ్ మెంటర్. ఈరోజు నేను మీకు ఎలా సహాయం చేయగలను?"
}

--- JOB RECOMMENDATION RULES ---
JOB_RECOMMENDATION_PRIORITY = [
    "1. Match user skills to available local jobs",
    "2. Prioritize jobs within NEARBY_RADIUS_KM (default: 50km)",
    "3. Consider user's preferred work type (daily wage / gig / permanent)",
    "4. Factor in minimum wage requirements by state",
    "5. Highlight government scheme eligibility alongside jobs",
    "6. Suggest skill upgrades when no direct match found",
]
MAX_RECOMMENDATIONS_PER_QUERY = 5
PREFER_VERIFIED_EMPLOYERS = True
SHOW_SALARY_RANGE = True

--- CAREER GUIDANCE RULES ---
GUIDANCE_FOCUS_AREAS = [
    "skill development and certification paths",
    "government welfare schemes and subsidies",
    "entrepreneurship and self-employment options",
    "digital literacy and online gig opportunities",
    "financial literacy and savings schemes",
]
ENCOURAGE_UPSKILLING = True
SUGGEST_FREE_COURSES = True        # Prefer PMKVY, Skill India, NSDC courses
HIGHLIGHT_PMKVY = True             # Always mention PMKVY when relevant
HIGHLIGHT_PM_SVANIDHI = True       # Mention PM SVANidhi for street vendors

--- TARGET WORKER PROFILES ---
WORKER_TYPES = [
    "daily_wage",       # Construction, agriculture, manual labor
    "artisan",          # Handicrafts, weaving, pottery, carpentry
    "gig_worker",       # Delivery, ride-share, freelance tasks
    "self_employed",    # Small vendors, home-based businesses
    "domestic_worker",  # Household help, cooks, caregivers
]

--- RESPONSE FORMATTING ---
MAX_RESPONSE_LENGTH = 500          # tokens
ALWAYS_INCLUDE_ACTIONABLE_STEP = True
USE_NUMBERED_LISTS = True
INCLUDE_SCHEME_LINKS = True
"""

import os
import json
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, jsonify,
    session, redirect, url_for, flash
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# ── Load environment variables ─────────────────────────────────────────────
load_dotenv()

# ── IBM Watsonx.ai import (graceful fallback) ──────────────────────────────
try:
    from ibm_watsonx_ai import Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference
    from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
    WATSONX_AVAILABLE = True
except ImportError:
    WATSONX_AVAILABLE = False
    print("[WARN] ibm-watsonx-ai not installed. AI features will use mock mode.")

# ══════════════════════════════════════════════════════════════════════════════
#  AGENT CONFIGURATION  (mirrors AGENT_INSTRUCTIONS docstring above)
# ══════════════════════════════════════════════════════════════════════════════
AGENT_CONFIG = {
    "tone": "friendly, empathetic, and encouraging",
    "personality": (
        "a supportive career mentor who understands the challenges of "
        "informal workers, daily wage earners, artisans, and gig workers"
    ),
    "supported_languages": ["en", "hi", "te"],
    "default_language": os.getenv("DEFAULT_LANGUAGE", "en"),
    "greetings": {
        "en": "Hello! I'm your AI Job Mentor. How can I help you today?",
        "hi": "नमस्ते! मैं आपका AI जॉब मेंटर हूं। आज मैं आपकी कैसे मदद कर सकता हूं?",
        "te": "నమస్కారం! నేను మీ AI జాబ్ మెంటర్. ఈరోజు నేను మీకు ఎలా సహాయం చేయగలను?",
    },
    "max_recommendations": 5,
    "nearby_radius_km": int(os.getenv("NEARBY_RADIUS_KM", 50)),
    "prefer_verified_employers": True,
    "encourage_upskilling": True,
    "suggest_free_courses": True,
    "highlight_pmkvy": True,
    "highlight_pm_svanidhi": True,
    "max_response_tokens": 500,
    "always_include_actionable_step": True,
    "worker_types": [
        "daily_wage", "artisan", "gig_worker", "self_employed", "domestic_worker"
    ],
    "guidance_focus_areas": [
        "skill development and certification paths",
        "government welfare schemes and subsidies",
        "entrepreneurship and self-employment options",
        "digital literacy and online gig opportunities",
        "financial literacy and savings schemes",
    ],
}

# ══════════════════════════════════════════════════════════════════════════════
#  SYSTEM PROMPT  (built from AGENT_CONFIG)
# ══════════════════════════════════════════════════════════════════════════════
SYSTEM_PROMPT = f"""You are {AGENT_CONFIG['personality']}.
Your tone is {AGENT_CONFIG['tone']}.

Your primary users are informal workers in India including daily wage laborers,
artisans, gig workers, street vendors, domestic workers, and self-employed individuals.

Your responsibilities:
1. Provide personalized job opportunity recommendations based on skills and location.
2. Suggest government welfare schemes (PMKVY, PM SVANidhi, MGNREGS, ESIC, etc.).
3. Recommend skill development courses — always prefer FREE programs like PMKVY, Skill India, NSDC.
4. Give career guidance in a simple, encouraging manner.
5. Support queries in English, Hindi (हिन्दी), and Telugu (తెలుగు).
6. Always end every response with one concrete actionable next step.

Key rules:
- Keep responses under {AGENT_CONFIG['max_response_tokens']} tokens.
- Use numbered lists for clarity.
- If the user mentions street vending, always mention PM SVANidhi scheme.
- If the user asks about skills, always mention PMKVY certification.
- Recommend jobs within {AGENT_CONFIG['nearby_radius_km']}km radius when location is provided.
- Focus on: {', '.join(AGENT_CONFIG['guidance_focus_areas'])}.
- Be empathetic — many users face economic hardship. Never be dismissive.
"""

# ══════════════════════════════════════════════════════════════════════════════
#  FLASK APP SETUP
# ══════════════════════════════════════════════════════════════════════════════
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///job_mentor.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"

# ══════════════════════════════════════════════════════════════════════════════
#  DATABASE MODELS
# ══════════════════════════════════════════════════════════════════════════════
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(15))
    password_hash = db.Column(db.String(256), nullable=False)
    worker_type = db.Column(db.String(30), default="daily_wage")
    skills = db.Column(db.Text, default="")
    location = db.Column(db.String(200), default="")
    latitude = db.Column(db.Float, default=0.0)
    longitude = db.Column(db.Float, default=0.0)
    language_pref = db.Column(db.String(5), default="en")
    preferred_salary = db.Column(db.Integer, default=0)
    dark_mode = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    chats = db.relationship("ChatHistory", backref="user", lazy=True)
    saved_jobs = db.relationship("SavedJob", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.id)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False


class Job(db.Model):
    __tablename__ = "jobs"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(150))
    description = db.Column(db.Text)
    skills_required = db.Column(db.Text)
    location = db.Column(db.String(200))
    latitude = db.Column(db.Float, default=0.0)
    longitude = db.Column(db.Float, default=0.0)
    salary_min = db.Column(db.Integer, default=0)
    salary_max = db.Column(db.Integer, default=0)
    job_type = db.Column(db.String(30), default="daily_wage")
    worker_type = db.Column(db.String(30))
    is_verified = db.Column(db.Boolean, default=False)
    posted_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    contact_phone = db.Column(db.String(15))
    contact_email = db.Column(db.String(150))


class ChatHistory(db.Model):
    __tablename__ = "chat_history"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role = db.Column(db.String(10), nullable=False)   # 'user' or 'assistant'
    message = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(5), default="en")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class SavedJob(db.Model):
    __tablename__ = "saved_jobs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)


class GovernmentScheme(db.Model):
    __tablename__ = "government_schemes"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    eligibility = db.Column(db.Text)
    benefits = db.Column(db.Text)
    application_url = db.Column(db.String(300))
    worker_types = db.Column(db.Text)   # JSON list
    category = db.Column(db.String(100))


class SkillCourse(db.Model):
    __tablename__ = "skill_courses"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    provider = db.Column(db.String(150))
    description = db.Column(db.Text)
    duration = db.Column(db.String(50))
    is_free = db.Column(db.Boolean, default=True)
    url = db.Column(db.String(300))
    skill_tags = db.Column(db.Text)
    worker_types = db.Column(db.Text)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ══════════════════════════════════════════════════════════════════════════════
#  IBM WATSONX.AI CLIENT
# ══════════════════════════════════════════════════════════════════════════════
def get_watsonx_model():
    """Return a configured Granite model inference client."""
    if not WATSONX_AVAILABLE:
        return None
    api_key = os.getenv("IBM_API_KEY")
    project_id = os.getenv("IBM_PROJECT_ID")
    url = os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
    if not api_key or not project_id:
        return None
    credentials = Credentials(url=url, api_key=api_key)
    params = {
        GenParams.MAX_NEW_TOKENS: AGENT_CONFIG["max_response_tokens"],
        GenParams.TEMPERATURE: 0.7,
        GenParams.TOP_P: 0.9,
        GenParams.REPETITION_PENALTY: 1.1,
    }
    return ModelInference(
        model_id="ibm/granite-13b-chat-v2",
        credentials=credentials,
        project_id=project_id,
        params=params,
    )

WATSONX_MODEL = None   # lazy-initialised on first request

def query_watsonx(user_message: str, history: list, language: str = "en") -> str:
    """Send a message to Granite and return the response text."""
    global WATSONX_MODEL
    if WATSONX_MODEL is None:
        WATSONX_MODEL = get_watsonx_model()

    lang_note = ""
    if language == "hi":
        lang_note = "\n[Respond in Hindi (Devanagari script)]"
    elif language == "te":
        lang_note = "\n[Respond in Telugu (Telugu script)]"

    # Build conversation context
    prompt_parts = [f"<|system|>\n{SYSTEM_PROMPT}{lang_note}\n<|end|>"]
    for msg in history[-6:]:   # last 3 turns
        role_tag = "<|user|>" if msg["role"] == "user" else "<|assistant|>"
        prompt_parts.append(f"{role_tag}\n{msg['content']}\n<|end|>")
    prompt_parts.append(f"<|user|>\n{user_message}\n<|end|>\n<|assistant|>")
    prompt = "\n".join(prompt_parts)

    if WATSONX_MODEL is None:
        return _mock_response(user_message, language)

    try:
        result = WATSONX_MODEL.generate_text(prompt=prompt)
        return result.strip()
    except Exception as exc:
        print(f"[ERROR] Watsonx call failed: {exc}")
        return _mock_response(user_message, language)


def _mock_response(message: str, language: str = "en") -> str:
    """Fallback response when Watsonx is unavailable (dev/demo mode)."""
    responses = {
        "en": (
            "I'm your AI Job Mentor! 🌟\n\n"
            "Based on your query, here are my suggestions:\n"
            "1. **Explore local construction or agriculture jobs** — high demand in most areas.\n"
            "2. **Register on PM SVANidhi** if you're a street vendor (pmsvanidhi.mohua.gov.in).\n"
            "3. **Enroll in PMKVY** for free skill certification (pmkvyofficial.org).\n\n"
            "**Next step:** Tell me your skills and location so I can find jobs near you!"
        ),
        "hi": (
            "मैं आपका AI जॉब मेंटर हूं! 🌟\n\n"
            "आपकी query के आधार पर सुझाव:\n"
            "1. **स्थानीय निर्माण या कृषि नौकरियां देखें**\n"
            "2. **PM SVANidhi** में पंजीकरण करें (यदि आप street vendor हैं)\n"
            "3. **PMKVY** में मुफ्त कौशल प्रमाणन के लिए नामांकन करें\n\n"
            "**अगला कदम:** अपने कौशल और स्थान बताएं!"
        ),
        "te": (
            "నేను మీ AI జాబ్ మెంటర్! 🌟\n\n"
            "మీ ప్రశ్న ఆధారంగా సూచనలు:\n"
            "1. **స్థానిక నిర్మాణ లేదా వ్యవసాయ ఉద్యోగాలు చూడండి**\n"
            "2. **PM SVANidhi**లో నమోదు చేయండి (వీధి వర్తకులకు)\n"
            "3. **PMKVY**లో ఉచిత నైపుణ్య సర్టిఫికేషన్\n\n"
            "**తదుపరి దశ:** మీ నైపుణ్యాలు మరియు స్థానం చెప్పండి!"
        ),
    }
    return responses.get(language, responses["en"])

# ══════════════════════════════════════════════════════════════════════════════
#  SEED DATA
# ══════════════════════════════════════════════════════════════════════════════
def seed_database():
    """Populate initial jobs, schemes, and courses if tables are empty."""
    if Job.query.first():
        return

    jobs = [
        Job(title="Construction Helper", company="ABC Builders", location="Hyderabad, Telangana",
            latitude=17.385, longitude=78.4867, salary_min=500, salary_max=700,
            job_type="daily_wage", worker_type="daily_wage", is_verified=True,
            skills_required="physical strength, basic tools", contact_phone="9876543210",
            description="Daily wage construction work. 8 hours/day. Food provided."),
        Job(title="Delivery Partner", company="FastKart Logistics", location="Bangalore, Karnataka",
            latitude=12.9716, longitude=77.5946, salary_min=15000, salary_max=25000,
            job_type="gig", worker_type="gig_worker", is_verified=True,
            skills_required="bike riding, smartphone usage", contact_phone="9123456789",
            description="Flexible delivery gig. Earn per delivery. Own bike required."),
        Job(title="Handloom Weaver", company="Pochampally Cooperative", location="Pochampally, Telangana",
            latitude=17.3378, longitude=78.8194, salary_min=8000, salary_max=14000,
            job_type="permanent", worker_type="artisan", is_verified=True,
            skills_required="weaving, textile knowledge", contact_phone="9988776655",
            description="Skilled weaver for traditional Ikat textiles. Training provided."),
        Job(title="Agricultural Laborer", company="Green Farms", location="Guntur, Andhra Pradesh",
            latitude=16.3067, longitude=80.4365, salary_min=400, salary_max=600,
            job_type="daily_wage", worker_type="daily_wage", is_verified=False,
            skills_required="farming, irrigation", contact_phone="9876501234",
            description="Seasonal agricultural work. Accommodation available."),
        Job(title="Home-based Tailoring", company="Fashion Forward", location="Chennai, Tamil Nadu",
            latitude=13.0827, longitude=80.2707, salary_min=10000, salary_max=18000,
            job_type="gig", worker_type="self_employed", is_verified=True,
            skills_required="sewing, tailoring, stitching", contact_phone="9444555666",
            description="Work from home tailoring assignments. Material provided by company."),
        Job(title="Domestic Cook / Housekeeper", company="HomeHelp Agency", location="Pune, Maharashtra",
            latitude=18.5204, longitude=73.8567, salary_min=8000, salary_max=12000,
            job_type="permanent", worker_type="domestic_worker", is_verified=True,
            skills_required="cooking, cleaning, household management", contact_phone="9922334455",
            description="Full-time domestic worker. Live-out position. Meals provided."),
        Job(title="Plumber Helper", company="QuickFix Services", location="Delhi, NCR",
            latitude=28.6139, longitude=77.2090, salary_min=600, salary_max=900,
            job_type="daily_wage", worker_type="daily_wage", is_verified=True,
            skills_required="basic plumbing, pipe fitting", contact_phone="9811223344",
            description="Helper for licensed plumber. Learn while you earn."),
        Job(title="Street Food Vendor Assistant", company="Self-employed", location="Mumbai, Maharashtra",
            latitude=19.0760, longitude=72.8777, salary_min=5000, salary_max=9000,
            job_type="gig", worker_type="self_employed", is_verified=False,
            skills_required="cooking, customer service", contact_phone="9833445566",
            description="Assist established vendor. Learn business skills. Pathway to own stall."),
    ]
    db.session.bulk_save_objects(jobs)

    schemes = [
        GovernmentScheme(
            name="PM SVANidhi — PM Street Vendor's AtmaNirbhar Nidhi",
            description="Collateral-free working capital loans up to ₹50,000 for street vendors.",
            eligibility="Street vendors who were vending before March 24, 2020.",
            benefits="Loans of ₹10K → ₹20K → ₹50K; cashback on digital payments; social security coverage.",
            application_url="https://pmsvanidhi.mohua.gov.in",
            worker_types='["self_employed"]', category="Financial Support",
        ),
        GovernmentScheme(
            name="PMKVY — Pradhan Mantri Kaushal Vikas Yojana",
            description="Free skill development training with government certification recognized across India.",
            eligibility="Indian youth aged 15–45 with minimum education. Priority to informal workers.",
            benefits="Free training, certification, placement assistance, ₹8,000 reward on completion.",
            application_url="https://pmkvyofficial.org",
            worker_types='["daily_wage","artisan","gig_worker","self_employed","domestic_worker"]',
            category="Skill Development",
        ),
        GovernmentScheme(
            name="MGNREGS — Mahatma Gandhi NREGS",
            description="100 days of guaranteed wage employment per year for rural households.",
            eligibility="Adult rural household members willing to do unskilled manual work.",
            benefits="₹200–₹350/day (state-wise), unemployment allowance if work not provided within 15 days.",
            application_url="https://nrega.nic.in",
            worker_types='["daily_wage"]', category="Employment Guarantee",
        ),
        GovernmentScheme(
            name="ESIC — Employees' State Insurance Scheme",
            description="Health insurance and social security for workers earning up to ₹21,000/month.",
            eligibility="Workers in factories/establishments with 10+ employees earning ≤₹21,000/month.",
            benefits="Medical care for entire family, cash benefits during illness, maternity, disability.",
            application_url="https://esic.in",
            worker_types='["daily_wage","gig_worker"]', category="Social Security",
        ),
        GovernmentScheme(
            name="PM Vishwakarma — Support for Artisans & Craftspeople",
            description="Comprehensive support scheme for 18 traditional trades — tools, training, credit.",
            eligibility="Artisans/craftspeople working in 18 designated trades (blacksmith, carpenter, etc.).",
            benefits="Free toolkit, ₹1–2L collateral-free credit, skill training, digital payment onboarding.",
            application_url="https://pmvishwakarma.gov.in",
            worker_types='["artisan"]', category="Artisan Support",
        ),
        GovernmentScheme(
            name="PM Ujjwala Yojana",
            description="Free LPG connection for Below Poverty Line (BPL) households.",
            eligibility="Adult women from BPL households without existing LPG connection.",
            benefits="Free LPG connection, subsidized refills, benefit of clean cooking fuel.",
            application_url="https://pmuy.gov.in",
            worker_types='["daily_wage","domestic_worker","self_employed"]', category="Welfare",
        ),
    ]
    db.session.bulk_save_objects(schemes)

    courses = [
        SkillCourse(name="Basic Construction & Safety Skills", provider="PMKVY / NSDC",
                    duration="3 months", is_free=True, url="https://nsdcindia.org",
                    skill_tags="construction,safety,tools",
                    worker_types='["daily_wage"]',
                    description="Learn construction basics, safety protocols, and tool handling."),
        SkillCourse(name="Smartphone & Digital Literacy for Gig Workers", provider="DigiLocker / CSC",
                    duration="2 weeks", is_free=True, url="https://csc.gov.in",
                    skill_tags="digital,smartphone,apps,payment",
                    worker_types='["gig_worker","self_employed"]',
                    description="Use UPI, delivery apps, and online marketplaces."),
        SkillCourse(name="Handloom & Textile Weaving Certification", provider="PMKVY / NHDC",
                    duration="6 months", is_free=True, url="https://pmkvyofficial.org",
                    skill_tags="weaving,textile,handloom,ikat",
                    worker_types='["artisan"]',
                    description="Traditional weaving techniques with NSDC certification."),
        SkillCourse(name="Home-based Food Business & FSSAI Registration", provider="Skill India",
                    duration="1 month", is_free=True, url="https://skillindia.gov.in",
                    skill_tags="cooking,food,business,fssai",
                    worker_types='["self_employed","domestic_worker"]',
                    description="Start a food business from home — licensing, hygiene, marketing."),
        SkillCourse(name="Domestic Worker Rights & Skill Enhancement", provider="Domestic Workers Sector Skill Council",
                    duration="2 months", is_free=True, url="https://nsdcindia.org",
                    skill_tags="domestic,housekeeping,cooking,childcare",
                    worker_types='["domestic_worker"]',
                    description="Professional skills + awareness of worker rights and social security."),
        SkillCourse(name="Basic Plumbing & Electrical Work", provider="ITI / PMKVY",
                    duration="4 months", is_free=False, url="https://dgt.gov.in",
                    skill_tags="plumbing,electrical,repair,maintenance",
                    worker_types='["daily_wage","artisan"]',
                    description="Certified ITI short course. Opens opportunities in construction & maintenance."),
    ]
    db.session.bulk_save_objects(courses)
    db.session.commit()
    print("[INFO] Database seeded with sample jobs, schemes, and courses.")

# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — Public
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/")
def index():
    jobs = Job.query.filter_by(is_verified=True).order_by(Job.posted_at.desc()).limit(6).all()
    schemes = GovernmentScheme.query.limit(4).all()
    return render_template("index.html", jobs=jobs, schemes=schemes,
                           agent_config=AGENT_CONFIG)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        worker_type = request.form.get("worker_type", "daily_wage")
        skills = request.form.get("skills", "")
        location = request.form.get("location", "")
        language_pref = request.form.get("language_pref", "en")

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for("register"))

        user = User(name=name, email=email, phone=phone,
                    worker_type=worker_type, skills=skills,
                    location=location, language_pref=language_pref)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Welcome! Your account has been created.", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES — Protected
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/dashboard")
@login_required
def dashboard():
    user_jobs = Job.query.filter(
        Job.worker_type == current_user.worker_type
    ).order_by(Job.posted_at.desc()).limit(6).all()
    schemes = GovernmentScheme.query.filter(
        GovernmentScheme.worker_types.contains(current_user.worker_type)
    ).limit(3).all()
    courses = SkillCourse.query.filter(
        SkillCourse.worker_types.contains(current_user.worker_type)
    ).limit(3).all()
    return render_template("dashboard.html", jobs=user_jobs, schemes=schemes,
                           courses=courses, agent_config=AGENT_CONFIG)


@app.route("/jobs")
def jobs():
    q = request.args.get("q", "")
    location = request.args.get("location", "")
    worker_type = request.args.get("worker_type", "")
    page = request.args.get("page", 1, type=int)

    query = Job.query
    if q:
        query = query.filter(
            db.or_(Job.title.ilike(f"%{q}%"), Job.skills_required.ilike(f"%{q}%"))
        )
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))
    if worker_type:
        query = query.filter(Job.worker_type == worker_type)

    jobs_paginated = query.order_by(Job.posted_at.desc()).paginate(
        page=page, per_page=9, error_out=False
    )
    return render_template("jobs.html", jobs=jobs_paginated, q=q,
                           location=location, worker_type=worker_type,
                           worker_types=AGENT_CONFIG["worker_types"])


@app.route("/chatbot")
@login_required
def chatbot():
    history = ChatHistory.query.filter_by(user_id=current_user.id)\
        .order_by(ChatHistory.timestamp.desc()).limit(20).all()
    history = list(reversed(history))
    greeting = AGENT_CONFIG["greetings"].get(current_user.language_pref, AGENT_CONFIG["greetings"]["en"])
    return render_template("chatbot.html", history=history, greeting=greeting,
                           agent_config=AGENT_CONFIG)


@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()
    language = data.get("language", current_user.language_pref)

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    # Save user message
    db.session.add(ChatHistory(user_id=current_user.id, role="user",
                               message=user_message, language=language))
    db.session.commit()

    # Build conversation history for context
    history_rows = ChatHistory.query.filter_by(user_id=current_user.id)\
        .order_by(ChatHistory.timestamp.desc()).limit(12).all()
    history = [{"role": r.role, "content": r.message} for r in reversed(history_rows)]

    # Inject user profile context
    profile_ctx = (
        f"\n[User profile: worker_type={current_user.worker_type}, "
        f"skills={current_user.skills}, location={current_user.location}]"
    )
    enriched_message = user_message + profile_ctx

    ai_response = query_watsonx(enriched_message, history[:-1], language)

    db.session.add(ChatHistory(user_id=current_user.id, role="assistant",
                               message=ai_response, language=language))
    db.session.commit()

    return jsonify({"response": ai_response, "language": language})


@app.route("/skills")
def skills():
    courses = SkillCourse.query.all()
    worker_type = request.args.get("worker_type", "")
    if worker_type:
        courses = SkillCourse.query.filter(
            SkillCourse.worker_types.contains(worker_type)
        ).all()
    return render_template("skills.html", courses=courses,
                           worker_types=AGENT_CONFIG["worker_types"],
                           selected_type=worker_type)


@app.route("/schemes")
def schemes():
    category = request.args.get("category", "")
    worker_type = request.args.get("worker_type", "")
    query = GovernmentScheme.query
    if category:
        query = query.filter(GovernmentScheme.category == category)
    if worker_type:
        query = query.filter(GovernmentScheme.worker_types.contains(worker_type))
    all_schemes = query.all()
    categories = db.session.query(GovernmentScheme.category).distinct().all()
    categories = [c[0] for c in categories]
    return render_template("schemes.html", schemes=all_schemes,
                           categories=categories,
                           worker_types=AGENT_CONFIG["worker_types"],
                           selected_category=category, selected_type=worker_type)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        current_user.name = request.form.get("name", current_user.name)
        current_user.phone = request.form.get("phone", current_user.phone)
        current_user.worker_type = request.form.get("worker_type", current_user.worker_type)
        current_user.skills = request.form.get("skills", current_user.skills)
        current_user.location = request.form.get("location", current_user.location)
        current_user.language_pref = request.form.get("language_pref", current_user.language_pref)
        current_user.preferred_salary = int(request.form.get("preferred_salary", 0) or 0)
        current_user.dark_mode = request.form.get("dark_mode") == "on"
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))
    saved = SavedJob.query.filter_by(user_id=current_user.id).all()
    return render_template("profile.html", saved_jobs=saved,
                           worker_types=AGENT_CONFIG["worker_types"])


@app.route("/api/save_job/<int:job_id>", methods=["POST"])
@login_required
def save_job(job_id):
    existing = SavedJob.query.filter_by(user_id=current_user.id, job_id=job_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"status": "removed"})
    db.session.add(SavedJob(user_id=current_user.id, job_id=job_id))
    db.session.commit()
    return jsonify({"status": "saved"})


@app.route("/api/jobs/nearby")
@login_required
def nearby_jobs():
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    radius = AGENT_CONFIG["nearby_radius_km"]

    if not lat or not lon:
        jobs = Job.query.filter_by(worker_type=current_user.worker_type).limit(6).all()
    else:
        # Approximate bounding box filter (fast, no external library)
        deg = radius / 111.0
        jobs = Job.query.filter(
            Job.latitude.between(lat - deg, lat + deg),
            Job.longitude.between(lon - deg, lon + deg),
        ).limit(10).all()

    result = [
        {
            "id": j.id, "title": j.title, "company": j.company,
            "location": j.location, "salary_min": j.salary_min,
            "salary_max": j.salary_max, "job_type": j.job_type,
            "is_verified": j.is_verified,
        }
        for j in jobs
    ]
    return jsonify(result)


@app.route("/api/recommendations")
@login_required
def recommendations():
    """AI-driven job recommendations based on user profile."""
    user_skills = current_user.skills.lower() if current_user.skills else ""
    skill_words = [s.strip() for s in user_skills.split(",") if s.strip()]

    query = Job.query.filter_by(worker_type=current_user.worker_type)
    if skill_words:
        filters = [Job.skills_required.ilike(f"%{w}%") for w in skill_words]
        query = Job.query.filter(db.or_(*filters))

    jobs = query.order_by(Job.is_verified.desc()).limit(
        AGENT_CONFIG["max_recommendations"]
    ).all()
    result = [
        {
            "id": j.id, "title": j.title, "company": j.company,
            "location": j.location, "salary_min": j.salary_min,
            "salary_max": j.salary_max, "is_verified": j.is_verified,
        }
        for j in jobs
    ]
    return jsonify(result)


# ══════════════════════════════════════════════════════════════════════════════
#  CONTEXT PROCESSORS & TEMPLATE FILTERS
# ══════════════════════════════════════════════════════════════════════════════
@app.context_processor
def inject_globals():
    return {
        "app_name": os.getenv("APP_NAME", "AI Job Mentor"),
        "current_year": datetime.utcnow().year,
        "supported_languages": AGENT_CONFIG["supported_languages"],
    }


@app.template_filter("currency_inr")
def currency_inr(value):
    if not value:
        return "₹0"
    if value >= 100000:
        return f"₹{value/100000:.1f}L"
    if value >= 1000:
        return f"₹{value/1000:.0f}K"
    return f"₹{value}"


# ══════════════════════════════════════════════════════════════════════════════
#  APP ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_database()
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=os.getenv("FLASK_DEBUG", "True") == "True",
    )
