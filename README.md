# Oracle Fusion Cloud – Ad-hoc SQL Query Tool

**Version:** 1.7.1  
**Author:** ChandraSekhar Byna

Streamlit app to run ad-hoc SQL against Oracle Fusion Cloud using BI Publisher (ExternalReportWSSService).

---

## Features

- Ad-hoc SQL queries against Fusion Cloud
- User registration with **Admin approval**
- Email notifications on register / approve
- One-click setup of required BIP objects (`DM_ARB` + `RP_ARB`)
- CSV export of query results

---

## Access Control

| Rule | Detail |
|------|--------|
| Registration | Open to anyone |
| Login | Only after Admin approval |
| Default Admin username | `chandra` |
| Default Admin email | `chandra@oradayforce.com` |

You can override admin identity with environment variables (see below).

---

## Quick Start (Windows)

```cmd
cd Fusion_SQL_Tool
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
notepad .env
streamlit run app.py
```

Open: http://localhost:8501

### Quick Start (Linux / Mac)

```bash
cd Fusion_SQL_Tool
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
streamlit run app.py
```

---

## Environment variables (`.env`)

Copy `.env.example` → `.env` and set:

```env
FUSION_ADMIN_USERNAME=chandra
FUSION_ADMIN_EMAIL=chandra@oradayforce.com

SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your.email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
```

> **Important:** Never commit the real `.env` file. It is already in `.gitignore`.

For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833), not your normal password.

---

## First-time Admin setup

1. Register with username `chandra` (or the value of `FUSION_ADMIN_USERNAME`)
2. Login as that user
3. Go to **Admin – Approve Users** to approve other registrations

---

## BIP Objects

The folder `bip_objects/` contains:

- `DM_ARB.xdmz` – Data Model
- `RP_ARB.xdoz` – Report

Use the in-app page **Setup BIP Objects** to upload them to any Fusion instance under:

`/Custom/Financials/`

The SQL Query page uses a fixed report path: `/Custom/Financials/RP_ARB.xdo`

---

## Notes

- Delete old `users.db` if upgrading from an earlier version
- Keep the `bip_objects` folder next to `app.py`
- Email sending fails silently if SMTP is not configured (registration still works)

---

## License

For internal / project use. Contact author for distribution terms.
