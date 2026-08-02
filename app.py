"""
Oracle Fusion Cloud – Ad-hoc SQL Query Tool
Version: 1.7 (Open registration + Admin approval + Email notifications)
"""

import streamlit as st
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
ALLOWED_EMAIL_DOMAIN = None  # No domain restriction – anybody can register
ADMIN_USERNAME = os.environ.get("FUSION_ADMIN_USERNAME", "chandra")
ADMIN_EMAIL = os.environ.get("FUSION_ADMIN_EMAIL", "chandra@oradayforce.com")

# Gmail SMTP (for notifications) – set these in .env or environment (do not hardcode secrets)
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
    """Send email via Gmail SMTP. Returns True on success."""
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
        # Do not break registration/approval if email fails
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

        # Notify Admin about new registration
        admin_body = (
            f"A new user has registered and is waiting for approval.\n\n"
            f"Full Name : {full_name or '-'}\n"
            f"Username  : {username}\n"
            f"Email     : {email}\n\n"
            f"Please login to the Fusion SQL Tool and approve this user from:\n"
            f"Admin – Approve Users"
        )
        send_email(ADMIN_EMAIL, "Fusion SQL Tool – New user pending approval", admin_body)
        # Also notify the Gmail owner (you)
        send_email(SMTP_USER, "Fusion SQL Tool – New user pending approval", admin_body)

        return True, "Registration successful. Please wait for Admin approval before login. Admin has been notified by email."
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
# Page config
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Fusion SQL Query Tool",
    page_icon="🗃️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Auth pages
# -----------------------------------------------------------------------------
def show_login_page():
    st.title("🔐 Login - Fusion SQL Query Tool")
    st.caption("Version 1.7.1 | Company controlled access")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login", type="primary"):
            ok, result = verify_user(username, password)
            if ok:
                st.session_state.logged_in = True
                st.session_state.username = result["username"]
                st.session_state.is_admin = result["is_admin"]
                st.session_state.email = result["email"]
                st.rerun()
            else:
                st.error(result)

    st.markdown("---")
    st.info("Registration is open to everyone. New accounts require **Admin approval** before login.")
    if st.button("Don't have an account? Register here"):
        st.session_state.show_register = True
        st.rerun()


def show_register_page():
    st.title("📝 Register - Fusion SQL Query Tool")
    st.caption("Anyone can register. Admin approval is required before login.")

    with st.form("register_form"):
        full_name = st.text_input("Full Name")
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        if st.form_submit_button("Register", type="primary"):
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

    if st.button("← Back to Login"):
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
        return "<p>No data</p>"
    html = ['<table style="border-collapse:collapse;width:100%;font-family:monospace;font-size:14px;">']
    html.append("<tr>")
    for col in columns:
        html.append(f'<th style="border:1px solid #ccc;padding:6px 10px;background:#f0f0f0;text-align:left;">{escape(str(col))}</th>')
    html.append("</tr>")
    for row in rows:
        html.append("<tr>")
        for col in columns:
            val = row.get(col, "")
            html.append(f'<td style="border:1px solid #ccc;padding:6px 10px;">{escape(str(val) if val is not None else "")}</td>')
        html.append("</tr>")
    html.append("</table>")
    return "".join(html)


# -----------------------------------------------------------------------------
# Main App
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

# ---- Logged-in area ----
st.sidebar.title("Fusion SQL Tool")
st.sidebar.caption(f"Logged in as: **{st.session_state.username}**")
if st.session_state.is_admin:
    st.sidebar.caption("Role: **Admin**")
st.sidebar.caption("Version 1.7.1")

if st.sidebar.button("Logout"):
    for key in ["logged_in", "username", "is_admin", "email", "connected"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

nav_options = ["SQL Query Tool", "Setup BIP Objects"]
if st.session_state.is_admin:
    nav_options.append("Admin – Approve Users")

page = st.sidebar.radio("Navigation", nav_options)

# ====================== ADMIN PAGE ======================
if page == "Admin – Approve Users":
    st.title("👤 Admin – User Approval")
    st.caption("Approve pending users so they can access the tool")

    pending = get_pending_users()
    if not pending:
        st.success("No pending users.")
    else:
        st.warning(f"{len(pending)} user(s) waiting for approval")
        for uid, uname, email, full_name, created in pending:
            with st.container():
                cols = st.columns([2, 3, 2, 2, 1])
                cols[0].write(f"**{uname}**")
                cols[1].write(email)
                cols[2].write(full_name or "-")
                cols[3].write(str(created)[:19] if created else "-")
                if cols[4].button("Approve", key=f"approve_{uid}"):
                    approve_user(uid)
                    st.success(f"Approved {uname}")
                    st.rerun()

    st.markdown("---")
    st.subheader("All Users")
    all_users = get_all_users()
    if all_users:
        header = "| Username | Email | Full Name | Status | Admin | Created |\n|---|---|---|---|---|---|\n"
        rows_md = ""
        for uid, uname, email, full_name, status, is_adm, created in all_users:
            rows_md += f"| {uname} | {email} | {full_name or '-'} | {status} | {'Yes' if is_adm else 'No'} | {str(created)[:19] if created else '-'} |\n"
        st.markdown(header + rows_md)

# ====================== SQL QUERY TOOL ======================
elif page == "SQL Query Tool":
    st.title("🗃️ Oracle Fusion Cloud – Ad-hoc SQL Query Tool")
    st.caption("Version 1.7.1")

    with st.sidebar.expander("Fusion Connection", expanded=True):
        host = st.text_input("Fusion Host (no https://)", key="q_host")
        fus_user = st.text_input("Fusion Username", key="q_user")
        fus_pass = st.text_input("Fusion Password", type="password", key="q_pass")
        # BIP Report Path is fixed and hidden from users
        report_path = "/Custom/Financials/RP_ARB.xdo"

    if st.sidebar.button("Connect to Fusion", type="primary"):
        if host and fus_user and fus_pass:
            st.session_state.connected = True
            st.session_state.host = host.strip()
            st.session_state.fusion_user = fus_user.strip()
            st.session_state.fusion_pass = fus_pass
            st.session_state.report_path = report_path
            st.sidebar.success("Connected")
        else:
            st.sidebar.error("Fill all fields")

    EXAMPLES = {
        "— Select example —": "",
        "Simple Test": "SELECT sysdate FROM dual",
        "AP Invoices": "SELECT invoice_id, invoice_num, invoice_date, invoice_amount FROM ap_invoices_all FETCH FIRST 30 ROWS ONLY",
        "GL Balances": "SELECT period_name, code_combination_id, begin_balance_dr FROM gl_balances WHERE period_name = 'Jul-26' FETCH FIRST 30 ROWS ONLY",
    }

    selected = st.selectbox("Example", list(EXAMPLES.keys()))
    sql = st.text_area("SQL Query", value=EXAMPLES[selected], height=220)

    if st.button("▶ Run Query", type="primary"):
        if not st.session_state.get("connected"):
            st.error("Please connect first.")
        else:
            try:
                with st.spinner("Running query..."):
                    rows, columns = run_bip_sql(
                        st.session_state.host,
                        st.session_state.fusion_user,
                        st.session_state.fusion_pass,
                        sql,
                        st.session_state.report_path
                    )
                st.success(f"Returned **{len(rows)}** rows")
                if rows:
                    st.markdown(render_html_table(rows, columns), unsafe_allow_html=True)
                    csv_data = rows_to_csv(rows, columns)
                    st.download_button("⬇ Download CSV", data=csv_data, file_name="fusion_result.csv", mime="text/csv")
                else:
                    st.warning("No rows returned.")
            except Exception as e:
                st.error("Query failed")
                st.code(str(e))

# ====================== SETUP BIP OBJECTS ======================
else:
    st.title("⚙️ Setup BIP Objects")
    st.caption("Automatically create DM_ARB + RP_ARB in any Fusion instance")
    st.success("The required BIP definitions are already included in this package.")

    target_host = st.text_input("Target Fusion Host (no https://)")
    target_user = st.text_input("Target Username")
    target_pass = st.text_input("Target Password", type="password")

    if st.button("🚀 Create BIP Objects", type="primary"):
        if not all([target_host, target_user, target_pass]):
            st.error("Please fill Host, Username and Password.")
        elif not DM_FILE.exists() or not RP_FILE.exists():
            st.error("BIP object files are missing from the bip_objects folder.")
        else:
            host = target_host.strip().replace("https://", "").replace("http://", "")
            progress = st.progress(0)
            status = st.empty()
            try:
                status.info("Creating folder /Custom ...")
                create_folder(host, target_user, target_pass, "/Custom")
                progress.progress(15)
                status.info("Creating folder /Custom/Financials ...")
                create_folder(host, target_user, target_pass, "/Custom/Financials")
                progress.progress(30)
                status.info("Uploading Data Model (DM_ARB) ...")
                upload_object(host, target_user, target_pass, "/Custom/Financials/DM_ARB.xdm", "xdmz", DM_FILE.read_bytes())
                progress.progress(65)
                status.info("Uploading Report (RP_ARB) ...")
                code2, text2 = upload_object(host, target_user, target_pass, "/Custom/Financials/RP_ARB.xdo", "xdoz", RP_FILE.read_bytes())
                progress.progress(100)
                if code2 == 200:
                    st.success("✅ Successfully created DM_ARB and RP_ARB!")
                    st.balloons()
                else:
                    st.error("Finished with some errors:")
                    st.code(text2[:1500])
            except Exception as e:
                st.error(f"Creation failed: {str(e)}")
