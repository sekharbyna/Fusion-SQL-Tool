"""
Oracle Fusion Cloud – Ad-hoc SQL Query Tool
Version: 1.8 (Modern UI + Open registration + Admin approval + Email notifications)
"""

import streamlit as st
import streamlit.components.v1 as components
import requests
import base64
import csv
import io
import sqlite3
import hashlib
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from html import unescape, escape
import xml.etree.ElementTree as ET
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
ALLOWED_EMAIL_DOMAIN = None
ADMIN_USERNAME = os.environ.get("FUSION_ADMIN_USERNAME", "chandra")
ADMIN_EMAIL = os.environ.get("FUSION_ADMIN_EMAIL", "chandra@oradayforce.com")

SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")

BASE_DIR = Path(__file__).parent
BIP_DIR = BASE_DIR / "bip_objects"
DM_FILE = BIP_DIR / "DM_ARB.xdmz"
RP_FILE = BIP_DIR / "RP_ARB.xdoz"
DB_PATH = BASE_DIR / "users.db"

# -----------------------------------------------------------------------------
# Page config + Global CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Fusion SQL Query Tool",
    page_icon="🗃️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Keep sidebar open when possible
if "sidebar_state" not in st.session_state:
    st.session_state.sidebar_state = "expanded"


CUSTOM_CSS = """
<style>
/* ---------- Global ---------- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Hide Streamlit branding but KEEP sidebar toggle visible */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {
    background: transparent !important;
}
/* ===== Sidebar expand/collapse – force high visibility ===== */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapsedControl"] > button,
[data-testid="collapsedControl"] > button {
    visibility: visible !important;
    display: flex !important;
    opacity: 1 !important;
    background: #14B8A6 !important;
    background-color: #14B8A6 !important;
    color: #FFFFFF !important;
    border: 2px solid #99F6E4 !important;
    border-left: none !important;
    border-radius: 0 12px 12px 0 !important;
    box-shadow: 0 0 12px rgba(20, 184, 166, 0.7) !important;
    width: 2.5rem !important;
    height: 3rem !important;
    z-index: 2147483647 !important;
}
[data-testid="collapsedControl"] svg,
[data-testid="collapsedControl"] path,
[data-testid="collapsedControl"] *,
[data-testid="stSidebarCollapsedControl"] svg,
[data-testid="stSidebarCollapsedControl"] path,
[data-testid="stSidebarCollapsedControl"] * {
    color: #FFFFFF !important;
    fill: #FFFFFF !important;
    stroke: #FFFFFF !important;
    opacity: 1 !important;
}
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarCollapseButton"] svg,
button[kind="headerNoPadding"] svg,
[data-testid="stHeader"] button svg {
    color: #5EEAD4 !important;
    fill: #5EEAD4 !important;
}
[data-testid="stHeader"] {
    background: transparent !important;
}

/* Main background */
.stApp {
    background: linear-gradient(160deg, #0F172A 0%, #1E293B 40%, #0F172A 100%);
}

/* Content area card feel */
.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
    max-width: 1200px;
}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0B1220 0%, #111827 100%) !important;
    border-right: 1px solid rgba(13, 148, 136, 0.25);
}
[data-testid="stSidebar"] * {
    color: #E2E8F0 !important;
}
[data-testid="stSidebar"] .stRadio label {
    padding: 0.45rem 0.75rem;
    border-radius: 8px;
    margin-bottom: 2px;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(13, 148, 136, 0.15);
}

/* ---------- Buttons ---------- */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    border: none !important;
    transition: all 0.2s ease !important;
    padding: 0.5rem 1.25rem !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0D9488 0%, #14B8A6 100%) !important;
    color: white !important;
    box-shadow: 0 4px 14px rgba(13, 148, 136, 0.35);
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(13, 148, 136, 0.45);
}
.stButton > button[kind="secondary"] {
    background: rgba(255,255,255,0.08) !important;
    color: #E2E8F0 !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
}

/* ---------- Inputs ---------- */
.stTextInput > div > div > input,
.stTextArea textarea,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    background: rgba(15, 23, 42, 0.95) !important;
    border: 1px solid rgba(148, 163, 184, 0.25) !important;
    border-radius: 10px !important;
    color: #F1F5F9 !important;
    font-size: 0.95rem !important;
}
.stTextArea textarea {
    background-color: #0F172A !important;
    color: #E2E8F0 !important;
}
[data-testid="stExpander"] summary {
    background: rgba(30, 41, 59, 0.9) !important;
    color: #E2E8F0 !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span {
    color: #E2E8F0 !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #14B8A6 !important;
    box-shadow: 0 0 0 2px rgba(20, 184, 166, 0.25) !important;
}

/* Labels */
.stTextInput label, .stTextArea label, .stSelectbox label {
    color: #94A3B8 !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
}

/* ---------- Cards ---------- */
.fusion-card {
    background: rgba(30, 41, 59, 0.7);
    border: 1px solid rgba(148, 163, 184, 0.12);
    border-radius: 16px;
    padding: 1.75rem 2rem;
    backdrop-filter: blur(12px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.25);
}
.fusion-card-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1.25rem;
}
.fusion-card-header h2 {
    margin: 0;
    font-size: 1.35rem;
    font-weight: 700;
    color: #F8FAFC;
}
.fusion-badge {
    display: inline-block;
    padding: 0.2rem 0.65rem;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.03em;
}
.badge-teal { background: rgba(13,148,136,0.2); color: #5EEAD4; border: 1px solid rgba(13,148,136,0.35); }
.badge-amber { background: rgba(245,158,11,0.15); color: #FCD34D; border: 1px solid rgba(245,158,11,0.3); }
.badge-green { background: rgba(34,197,94,0.15); color: #86EFAC; border: 1px solid rgba(34,197,94,0.3); }
.badge-red { background: rgba(239,68,68,0.15); color: #FCA5A5; border: 1px solid rgba(239,68,68,0.3); }

/* Hero / login */
.login-hero {
    text-align: center;
    padding: 2rem 1rem 1.5rem;
}
.login-hero h1 {
    font-size: 2rem;
    font-weight: 700;
    color: #F8FAFC;
    margin: 0 0 0.35rem;
}
.login-hero p {
    color: #94A3B8;
    font-size: 0.95rem;
    margin: 0;
}
.login-logo {
    width: 56px;
    height: 56px;
    background: linear-gradient(135deg, #0D9488, #14B8A6);
    border-radius: 14px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 1.6rem;
    margin-bottom: 1rem;
    box-shadow: 0 8px 24px rgba(13,148,136,0.4);
}

/* Status bar */
.status-bar {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
    margin-bottom: 1.25rem;
}
.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.35rem 0.85rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 500;
    background: rgba(30,41,59,0.8);
    border: 1px solid rgba(148,163,184,0.15);
    color: #CBD5E1;
}
.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
}
.dot-green { background: #22C55E; box-shadow: 0 0 6px #22C55E; }
.dot-gray { background: #64748B; }

/* Result table */
.result-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
}
.result-table th {
    background: #0D9488;
    color: white;
    padding: 10px 14px;
    text-align: left;
    font-weight: 600;
    position: sticky;
    top: 0;
}
.result-table td {
    padding: 8px 14px;
    border-bottom: 1px solid rgba(148,163,184,0.12);
    color: #E2E8F0;
}
.result-table tr:nth-child(even) td {
    background: rgba(15, 23, 42, 0.4);
}
.result-table tr:hover td {
    background: rgba(13, 148, 136, 0.12);
}

/* Metrics */
.metric-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
}
.metric-box {
    flex: 1;
    background: rgba(30,41,59,0.6);
    border: 1px solid rgba(148,163,184,0.12);
    border-radius: 12px;
    padding: 1rem 1.25rem;
}
.metric-box .label { color: #94A3B8; font-size: 0.75rem; font-weight: 500; }
.metric-box .value { color: #F8FAFC; font-size: 1.4rem; font-weight: 700; margin-top: 0.2rem; }

/* Alerts override */
.stAlert {
    border-radius: 12px !important;
}

/* Divider */
hr {
    border: none;
    border-top: 1px solid rgba(148,163,184,0.15);
    margin: 1.25rem 0;
}

/* Caption / helper text */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #64748B !important;
}

/* Expander */
.streamlit-expanderHeader {
    background: rgba(30,41,59,0.5) !important;
    border-radius: 10px !important;
    color: #E2E8F0 !important;
}

/* Logout button in sidebar – always visible */
[data-testid="stSidebar"] button[kind="secondary"],
[data-testid="stSidebar"] .stButton > button {
    background: rgba(239, 68, 68, 0.15) !important;
    color: #FCA5A5 !important;
    border: 1px solid rgba(239, 68, 68, 0.35) !important;
    font-weight: 600 !important;
    margin-top: 0.5rem !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(239, 68, 68, 0.3) !important;
    color: #FEE2E2 !important;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Force collapsed-sidebar toggle colors on the PARENT page (iframe alone cannot style it)
components.html(
    """
<script>
(function() {
  var doc = window.parent.document;
  function ensureStyle() {
    if (doc.getElementById('fusion-toggle-style')) return;
    var s = doc.createElement('style');
    s.id = 'fusion-toggle-style';
    s.textContent = `
      [data-testid="collapsedControl"],
      [data-testid="stSidebarCollapsedControl"],
      [data-testid="stSidebarCollapsedControl"] button,
      [data-testid="collapsedControl"] button {
        background: #14B8A6 !important;
        background-color: #14B8A6 !important;
        color: #FFFFFF !important;
        border: 2px solid #99F6E4 !important;
        border-left: none !important;
        border-radius: 0 12px 12px 0 !important;
        box-shadow: 0 0 14px rgba(20,184,166,0.75) !important;
        opacity: 1 !important;
        visibility: visible !important;
      }
      [data-testid="collapsedControl"] svg,
      [data-testid="collapsedControl"] path,
      [data-testid="collapsedControl"] *,
      [data-testid="stSidebarCollapsedControl"] svg,
      [data-testid="stSidebarCollapsedControl"] path,
      [data-testid="stSidebarCollapsedControl"] * {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
        stroke: #FFFFFF !important;
        opacity: 1 !important;
      }
    `;
    doc.head.appendChild(s);
  }
  function paint() {
    ensureStyle();
    var sels = [
      '[data-testid="collapsedControl"]',
      '[data-testid="stSidebarCollapsedControl"]',
      '[data-testid="stSidebarCollapsedControl"] button',
      '[data-testid="collapsedControl"] button'
    ];
    sels.forEach(function(sel) {
      doc.querySelectorAll(sel).forEach(function(el) {
        el.style.setProperty('background', '#14B8A6', 'important');
        el.style.setProperty('background-color', '#14B8A6', 'important');
        el.style.setProperty('color', '#FFFFFF', 'important');
        el.style.setProperty('border', '2px solid #99F6E4', 'important');
        el.style.setProperty('border-left', 'none', 'important');
        el.style.setProperty('opacity', '1', 'important');
        el.style.setProperty('visibility', 'visible', 'important');
        el.querySelectorAll('svg, path').forEach(function(c) {
          c.style.setProperty('fill', '#FFFFFF', 'important');
          c.style.setProperty('color', '#FFFFFF', 'important');
          c.style.setProperty('stroke', '#FFFFFF', 'important');
        });
      });
    });
  }
  paint();
  setInterval(paint, 300);
  try {
    new MutationObserver(paint).observe(doc.body, {childList:true, subtree:true});
  } catch (e) {}
})();
</script>
""",
    height=0,
    width=0,
)

# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            status TEXT DEFAULT 'pending',
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def send_email(to_email: str, subject: str, body: str) -> bool:
    if not SMTP_USER or not SMTP_PASSWORD:
        return False
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False


def register_user(username: str, email: str, password: str, full_name: str = "") -> tuple:
    email = email.strip().lower()
    username = username.strip().lower()

    if "@" not in email or "." not in email.split("@")[-1]:
        return False, "Please enter a valid email address."

    is_admin = 1 if username == ADMIN_USERNAME or email == ADMIN_EMAIL else 0
    status = "approved" if is_admin else "pending"

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (username, email, password_hash, full_name, status, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
            (username, email, hash_password(password), full_name, status, is_admin)
        )
        conn.commit()
        conn.close()

        if is_admin:
            return True, "Admin account created and approved. You can login now."

        admin_body = (
            f"A new user has registered and is waiting for approval.\n\n"
            f"Full Name : {full_name or '-'}\n"
            f"Username  : {username}\n"
            f"Email     : {email}\n\n"
            f"Please login to the Fusion SQL Tool and approve this user from:\n"
            f"Admin – Approve Users"
        )
        send_email(ADMIN_EMAIL, "Fusion SQL Tool – New user pending approval", admin_body)
        if SMTP_USER:
            send_email(SMTP_USER, "Fusion SQL Tool – New user pending approval", admin_body)

        return True, "Registration successful. Please wait for Admin approval before login."
    except sqlite3.IntegrityError:
        return False, "Username or Email already exists."


def verify_user(username: str, password: str) -> tuple:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT password_hash, status, is_admin, email FROM users WHERE username = ?",
        (username.strip().lower(),)
    )
    row = c.fetchone()
    conn.close()

    if not row:
        return False, "Invalid username or password."

    password_hash, status, is_admin, email = row
    if password_hash != hash_password(password):
        return False, "Invalid username or password."

    if status != "approved":
        return False, "Your account is pending Admin approval. Please contact Admin."

    return True, {"username": username.strip().lower(), "is_admin": bool(is_admin), "email": email}


def get_pending_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT id, username, email, full_name, created_at FROM users WHERE status = 'pending' ORDER BY created_at"
    )
    rows = c.fetchall()
    conn.close()
    return rows


def approve_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username, email, full_name FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    c.execute("UPDATE users SET status = 'approved' WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    if row:
        uname, uemail, full_name = row
        body = (
            f"Hello {full_name or uname},\n\n"
            f"Your account for the Fusion SQL Query Tool has been approved.\n\n"
            f"Username: {uname}\n"
            f"You can now login and use the tool.\n\n"
            f"Thank you."
        )
        send_email(uemail, "Fusion SQL Tool – Account Approved", body)


def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT id, username, email, full_name, status, is_admin, created_at FROM users ORDER BY created_at DESC"
    )
    rows = c.fetchall()
    conn.close()
    return rows


init_db()

# -----------------------------------------------------------------------------
# Auth pages
# -----------------------------------------------------------------------------
def show_login_page():
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown("""
        <div class="login-hero">
            <div class="login-logo">🗃️</div>
            <h1>Fusion SQL Tool</h1>
            <p>Ad-hoc SQL queries against Oracle Fusion Cloud</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="fusion-card">', unsafe_allow_html=True)
        st.markdown("#### Sign in")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
            if submitted:
                ok, result = verify_user(username, password)
                if ok:
                    st.session_state.logged_in = True
                    st.session_state.username = result["username"]
                    st.session_state.is_admin = result["is_admin"]
                    st.session_state.email = result["email"]
                    st.rerun()
                else:
                    st.error(result)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '<p style="text-align:center;color:#64748B;font-size:0.85rem;">'
            'New here? Accounts require admin approval before first login.</p>',
            unsafe_allow_html=True
        )
        if st.button("Create an account", use_container_width=True):
            st.session_state.show_register = True
            st.rerun()

        st.caption("Version 1.8")


def show_register_page():
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown("""
        <div class="login-hero">
            <div class="login-logo">📝</div>
            <h1>Create account</h1>
            <p>Register to request access to the Fusion SQL Tool</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="fusion-card">', unsafe_allow_html=True)
        with st.form("register_form"):
            full_name = st.text_input("Full Name", placeholder="Your full name")
            username = st.text_input("Username", placeholder="Choose a username")
            email = st.text_input("Email", placeholder="you@company.com")
            password = st.text_input("Password", type="password", placeholder="Choose a password")
            confirm = st.text_input("Confirm Password", type="password", placeholder="Repeat password")
            submitted = st.form_submit_button("Register", type="primary", use_container_width=True)
            if submitted:
                if not username or not email or not password:
                    st.error("Username, Email and Password are required")
                elif password != confirm:
                    st.error("Passwords do not match")
                else:
                    ok, msg = register_user(username, email, password, full_name)
                    if ok:
                        st.success(msg)
                        st.session_state.show_register = False
                    else:
                        st.error(msg)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("← Back to Sign in", use_container_width=True):
            st.session_state.show_register = False
            st.rerun()


# -----------------------------------------------------------------------------
# BIP helpers
# -----------------------------------------------------------------------------
def create_folder(host, username, password, folder_path):
    url = f"https://{host}/xmlpserver/services/v2/CatalogService"
    soap = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:v2="http://xmlns.oracle.com/oxp/service/v2">
  <soapenv:Header/>
  <soapenv:Body>
    <v2:createFolder>
      <v2:folderAbsolutePathURL>{folder_path}</v2:folderAbsolutePathURL>
      <v2:userID>{username}</v2:userID>
      <v2:password>{password}</v2:password>
    </v2:createFolder>
  </soapenv:Body>
</soapenv:Envelope>"""
    headers = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""}
    resp = requests.post(url, data=soap.encode("utf-8"), headers=headers, timeout=60)
    return resp.status_code, resp.text


def upload_object(host, username, password, absolute_path, object_type, file_bytes):
    url = f"https://{host}/xmlpserver/services/v2/CatalogService"
    b64_data = base64.b64encode(file_bytes).decode("utf-8")
    soap = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:v2="http://xmlns.oracle.com/oxp/service/v2">
  <soapenv:Header/>
  <soapenv:Body>
    <v2:uploadObject>
      <v2:reportObjectAbsolutePathURL>{absolute_path}</v2:reportObjectAbsolutePathURL>
      <v2:objectType>{object_type}</v2:objectType>
      <v2:objectZippedData>{b64_data}</v2:objectZippedData>
      <v2:userID>{username}</v2:userID>
      <v2:password>{password}</v2:password>
    </v2:uploadObject>
  </soapenv:Body>
</soapenv:Envelope>"""
    headers = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""}
    resp = requests.post(url, data=soap.encode("utf-8"), headers=headers, timeout=120)
    return resp.status_code, resp.text


def findall_ignore_ns(root, tag):
    results = []
    for elem in root.iter():
        if elem.tag.endswith("}" + tag) or elem.tag == tag:
            results.append(elem)
    return results


def find_ignore_ns(root, tag):
    results = findall_ignore_ns(root, tag)
    return results[0] if results else None


def run_bip_sql(host, username, password, sql, report_path):
    host = host.replace("https://", "").replace("http://", "").rstrip("/")
    url = f"https://{host}/xmlpserver/services/ExternalReportWSSService"
    sql_clean = sql.strip().rstrip(";")

    soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
               xmlns:pub="http://xmlns.oracle.com/oxp/service/PublicReportService">
  <soap:Header/>
  <soap:Body>
    <pub:runReport>
      <pub:reportRequest>
        <pub:reportAbsolutePath>{report_path}</pub:reportAbsolutePath>
        <pub:attributeFormat>html</pub:attributeFormat>
        <pub:sizeOfDataChunkDownload>-1</pub:sizeOfDataChunkDownload>
        <pub:parameterNameValues>
          <pub:item>
            <pub:name>p_sql</pub:name>
            <pub:values>
              <pub:item>{sql_clean}</pub:item>
            </pub:values>
          </pub:item>
        </pub:parameterNameValues>
      </pub:reportRequest>
    </pub:runReport>
  </soap:Body>
</soap:Envelope>"""

    headers = {"Content-Type": "application/soap+xml; charset=UTF-8", "SOAPAction": ""}
    response = requests.post(
        url, data=soap_body.encode("utf-8"), headers=headers,
        auth=(username, password), timeout=180
    )

    if response.status_code != 200:
        raise Exception(f"HTTP {response.status_code}: {response.text[:1200]}")

    root = ET.fromstring(response.content)
    report_bytes_node = find_ignore_ns(root, "reportBytes")
    if report_bytes_node is None or not report_bytes_node.text:
        raise Exception("No reportBytes found in response.\n" + response.text[:800])

    html_content = base64.b64decode(report_bytes_node.text).decode("utf-8", errors="ignore")
    clean_text = re.sub(r'<[^>]+>', ' ', html_content)
    clean_text = unescape(clean_text)

    match = re.search(r'<ROWSET.*?</ROWSET>', clean_text, re.DOTALL | re.IGNORECASE)
    if not match:
        return [{"RESULT": "Could not parse data from response."}], ["RESULT"]

    try:
        rowset_root = ET.fromstring(match.group(0).encode("utf-8"))
        rows, columns = [], []
        for row in findall_ignore_ns(rowset_root, "ROW"):
            row_data = {}
            for child in row:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                row_data[tag] = child.text if child.text is not None else ""
                if tag not in columns:
                    columns.append(tag)
            if row_data:
                rows.append(row_data)
        return rows, columns
    except Exception as e:
        return [{"RESULT": f"Parse error: {str(e)}"}], ["RESULT"]


def rows_to_csv(rows, columns):
    output = io.StringIO()
    if not rows:
        return ""
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def render_html_table(rows, columns):
    if not rows:
        return "<p style='color:#94A3B8'>No data</p>"
    html = ['<div style="overflow-x:auto;border-radius:12px;border:1px solid rgba(148,163,184,0.15);">']
    html.append('<table class="result-table">')
    html.append("<tr>")
    for col in columns:
        html.append(f"<th>{escape(str(col))}</th>")
    html.append("</tr>")
    for row in rows:
        html.append("<tr>")
        for col in columns:
            val = row.get(col, "")
            html.append(f"<td>{escape(str(val) if val is not None else '')}</td>")
        html.append("</tr>")
    html.append("</table></div>")
    return "".join(html)


# -----------------------------------------------------------------------------
# Session init
# -----------------------------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "show_register" not in st.session_state:
    st.session_state.show_register = False
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

if not st.session_state.logged_in:
    if st.session_state.show_register:
        show_register_page()
    else:
        show_login_page()
    st.stop()

# -----------------------------------------------------------------------------
# Logged-in area
# -----------------------------------------------------------------------------
# Sidebar
st.sidebar.markdown("""
<div style="padding:0.5rem 0 0.75rem;">
  <div style="font-size:1.15rem;font-weight:700;color:#F8FAFC;">Fusion SQL Tool</div>
  <div style="font-size:0.75rem;color:#64748B;margin-top:2px;">Oracle Fusion Cloud</div>
</div>
""", unsafe_allow_html=True)

role_badge = "Admin" if st.session_state.get("is_admin") else "User"
uname = st.session_state.get("username", "user")
st.sidebar.markdown(
    f'<span class="fusion-badge badge-teal">{role_badge}</span> '
    f'<span style="color:#E2E8F0;font-size:0.9rem;margin-left:0.35rem;font-weight:600;">{uname}</span>',
    unsafe_allow_html=True
)

# Logout visible for ALL users (admin + normal)
if st.sidebar.button("Logout", key="btn_logout", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

st.sidebar.markdown("---")

nav_options = ["SQL Query", "About"]
if st.session_state.get("is_admin"):
    nav_options = ["SQL Query", "Setup BIP", "Admin", "About"]

page = st.sidebar.radio("Navigate", nav_options, label_visibility="collapsed")

st.sidebar.markdown("---")
st.sidebar.caption("v1.8")

# Top bar – always show who is logged in (visible even if sidebar is collapsed)
_uname = st.session_state.get("username", "") or "—"
_role = "Admin" if st.session_state.get("is_admin") else "User"
st.markdown(
    '<div style="display:flex;justify-content:flex-end;align-items:center;gap:0.75rem;'
    'margin-bottom:0.75rem;padding:0.35rem 0;">'
    '<span style="color:#94A3B8;font-size:0.85rem;">Signed in as</span> '
    '<span style="color:#F8FAFC;font-weight:700;font-size:0.95rem;">'
    + str(_uname) +
    '</span> '
    '<span class="fusion-badge badge-teal">' + _role + '</span>'
    '</div>',
    unsafe_allow_html=True,
)

# ====================== ADMIN ======================
if page == "Admin":
    st.markdown("""
    <div class="fusion-card-header">
        <h2>User management</h2>
        <span class="fusion-badge badge-teal">Admin</span>
    </div>
    """, unsafe_allow_html=True)

    pending = get_pending_users()
    if not pending:
        st.success("No users waiting for approval.")
    else:
        st.warning(f"{len(pending)} user(s) pending approval")
        for uid, uname, email, full_name, created in pending:
            c1, c2, c3, c4, c5 = st.columns([2, 3, 2, 2, 1.2])
            c1.markdown(f"**{uname}**")
            c2.write(email)
            c3.write(full_name or "—")
            c4.write(str(created)[:19] if created else "—")
            if c5.button("Approve", key=f"approve_{uid}", type="primary"):
                approve_user(uid)
                st.success(f"Approved {uname}")
                st.rerun()

    st.markdown("---")
    st.subheader("All users")
    all_users = get_all_users()
    if all_users:
        html = [
            '<div style="overflow-x:auto;border-radius:12px;border:1px solid rgba(148,163,184,0.2);">',
            '<table class="result-table">',
            "<tr>",
            "<th>Username</th><th>Email</th><th>Name</th><th>Status</th><th>Admin</th><th>Created</th>",
            "</tr>",
        ]
        for uid, uname, email, full_name, status, is_adm, created in all_users:
            status_color = "#FCD34D" if status == "pending" else "#86EFAC"
            admin_txt = "Yes" if is_adm else "No"
            created_txt = str(created)[:19] if created else "—"
            name_txt = full_name or "—"
            html.append("<tr>")
            html.append(f"<td><strong>{escape(str(uname))}</strong></td>")
            html.append(f"<td>{escape(str(email))}</td>")
            html.append(f"<td>{escape(str(name_txt))}</td>")
            html.append(f'<td style="color:{status_color};font-weight:600;">{escape(str(status))}</td>')
            html.append(f"<td>{admin_txt}</td>")
            html.append(f"<td>{escape(created_txt)}</td>")
            html.append("</tr>")
        html.append("</table></div>")
        st.markdown("".join(html), unsafe_allow_html=True)
    else:
        st.info("No users registered yet.")

# ====================== SQL QUERY ======================
elif page == "SQL Query":
    st.markdown("""
    <div class="fusion-card-header">
        <h2>SQL Query</h2>
        <span class="fusion-badge badge-teal">Ad-hoc</span>
    </div>
    """, unsafe_allow_html=True)

    # Connection status
    connected = st.session_state.get("connected", False)
    dot = "dot-green" if connected else "dot-gray"
    status_text = "Connected" if connected else "Not connected"
    host_display = st.session_state.get("host", "—") if connected else "—"

    st.markdown(f"""
    <div class="status-bar">
        <div class="status-pill"><span class="status-dot {dot}"></span> {status_text}</div>
        <div class="status-pill">Host: {host_display}</div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("Fusion connection", expanded=not connected):
        host = st.text_input(
            "Fusion Host",
            placeholder="xxx.fa.ocs.oraclecloud.com",
            key="q_host",
            help="Without https://",
        )
        c1, c2, c3 = st.columns([2, 2, 1.2])
        with c1:
            fus_user = st.text_input("Username", key="q_user")
        with c2:
            fus_pass = st.text_input("Password", type="password", key="q_pass")
        with c3:
            st.markdown("<br>", unsafe_allow_html=True)
            connect_clicked = st.button("Connect", type="primary", use_container_width=True)
        if connect_clicked:
            if host and fus_user and fus_pass:
                st.session_state.connected = True
                st.session_state.host = host.strip().replace("https://", "").replace("http://", "")
                st.session_state.fusion_user = fus_user.strip()
                st.session_state.fusion_pass = fus_pass
                st.session_state.report_path = "/Custom/Financials/RP_ARB.xdo"
                st.success("Connected to Fusion")
                st.rerun()
            else:
                st.error("Please fill Host, Username and Password")

    EXAMPLES = {
        "— Choose example —": "",
        "Simple test": "SELECT sysdate FROM dual",
        "AP Invoices (30 rows)": (
            "SELECT invoice_id, invoice_num, invoice_date, invoice_amount\n"
            "FROM ap_invoices_all\nFETCH FIRST 30 ROWS ONLY"
        ),
        "GL Balances sample": (
            "SELECT period_name, code_combination_id, begin_balance_dr\n"
            "FROM gl_balances\nWHERE period_name = 'Jul-26'\nFETCH FIRST 30 ROWS ONLY"
        ),
        "AR Customers sample": (
            "SELECT party_name, account_number, status\n"
            "FROM hz_cust_accounts hca\nJOIN hz_parties hp ON hca.party_id = hp.party_id\n"
            "FETCH FIRST 20 ROWS ONLY"
        ),
    }

    selected = st.selectbox("Examples", list(EXAMPLES.keys()))
    sql = st.text_area(
        "SQL",
        value=EXAMPLES[selected],
        height=200,
        placeholder="SELECT ... FROM ... FETCH FIRST 50 ROWS ONLY",
        label_visibility="collapsed",
    )

    run_col, _ = st.columns([1, 4])
    with run_col:
        run_clicked = st.button("▶  Run query", type="primary", use_container_width=True)

    if run_clicked:
        if not st.session_state.get("connected"):
            st.error("Connect to Fusion first.")
        elif not sql.strip():
            st.warning("Enter a SQL statement.")
        else:
            try:
                with st.spinner("Running query against Fusion…"):
                    rows, columns = run_bip_sql(
                        st.session_state.host,
                        st.session_state.fusion_user,
                        st.session_state.fusion_pass,
                        sql,
                        st.session_state.report_path,
                    )
                st.markdown(f"""
                <div class="metric-row">
                    <div class="metric-box">
                        <div class="label">ROWS RETURNED</div>
                        <div class="value">{len(rows)}</div>
                    </div>
                    <div class="metric-box">
                        <div class="label">COLUMNS</div>
                        <div class="value">{len(columns)}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if rows:
                    st.markdown(render_html_table(rows, columns), unsafe_allow_html=True)
                    csv_data = rows_to_csv(rows, columns)
                    st.download_button(
                        "⬇ Download CSV",
                        data=csv_data,
                        file_name="fusion_result.csv",
                        mime="text/csv",
                    )
                else:
                    st.info("Query returned no rows.")
            except Exception as e:
                st.error("Query failed")
                st.code(str(e))

# ====================== SETUP BIP ======================
elif page == "Setup BIP":
    if not st.session_state.is_admin:
        st.error("Admin access required.")
        st.stop()
    st.markdown("""
    <div class="fusion-card-header">
        <h2>Setup BIP objects</h2>
        <span class="fusion-badge badge-amber">Admin only</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <p style="color:#94A3B8;margin-bottom:1.25rem;">
    Upload the required Data Model and Report into your Fusion instance.
    This is a one-time setup (Admin only).
    </p>
    """, unsafe_allow_html=True)

    if DM_FILE.exists() and RP_FILE.exists():
        st.success("BIP package files found in this installation.")
    else:
        st.error("bip_objects folder is missing DM_ARB.xdmz or RP_ARB.xdoz.")

    c1, c2 = st.columns(2)
    with c1:
        target_host = st.text_input("Target Fusion Host", placeholder="xxx.fa.ocs.oraclecloud.com")
        target_user = st.text_input("Username")
    with c2:
        target_pass = st.text_input("Password", type="password")

    if st.button("Create BIP objects", type="primary"):
        if not all([target_host, target_user, target_pass]):
            st.error("Fill Host, Username and Password.")
        elif not DM_FILE.exists() or not RP_FILE.exists():
            st.error("BIP object files are missing.")
        else:
            host = target_host.strip().replace("https://", "").replace("http://", "")
            progress = st.progress(0)
            status = st.empty()
            try:
                status.info("Creating catalog folder…")
                create_folder(host, target_user, target_pass, "/Custom")
                progress.progress(20)
                status.info("Creating Financials folder…")
                create_folder(host, target_user, target_pass, "/Custom/Financials")
                progress.progress(40)
                status.info("Uploading Data Model (DM_ARB) …")
                upload_object(
                    host, target_user, target_pass,
                    "/Custom/Financials/DM_ARB.xdm", "xdmz", DM_FILE.read_bytes()
                )
                progress.progress(70)
                status.info("Uploading Report (RP_ARB) …")
                code2, text2 = upload_object(
                    host, target_user, target_pass,
                    "/Custom/Financials/RP_ARB.xdo", "xdoz", RP_FILE.read_bytes()
                )
                progress.progress(100)
                if code2 == 200:
                    st.success("DM_ARB and RP_ARB created successfully.")
                    st.balloons()
                else:
                    st.error("Finished with errors:")
                    st.code(text2[:1500])
            except Exception as e:
                st.error(f"Setup failed: {e}")

# ====================== ABOUT ======================
else:
    st.markdown("""
    <div class="fusion-card-header">
        <h2>About</h2>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="fusion-card">
        <p style="color:#E2E8F0;line-height:1.6;">
            <strong>Fusion SQL Query Tool</strong> lets you run ad-hoc SQL against
            Oracle Fusion Cloud using BI Publisher’s External Report service.
        </p>
        <ul style="color:#94A3B8;line-height:1.8;">
            <li>User registration with admin approval</li>
            <li>Email notifications on register / approve</li>
            <li>One-click BIP object setup</li>
            <li>CSV export of results</li>
        </ul>
        <p style="color:#64748B;font-size:0.85rem;margin-top:1rem;">
            Version 1.8 · Author: ChandraSekhar Byna
        </p>
    </div>
    """, unsafe_allow_html=True)
