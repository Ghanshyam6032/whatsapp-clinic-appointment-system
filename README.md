# 🏥 WhatsApp Clinic Appointment System

An AI-powered WhatsApp Clinic Appointment Booking System built with **FastAPI, Mistral AI, WhatsApp Cloud API, Google Sheets, and Google Calendar**.

Patients can book, check, reschedule, and cancel appointments directly through WhatsApp without manual intervention.

## 🚀 Features

* 📅 Book appointments through WhatsApp
* 🔎 Check existing appointments
* 🔄 Reschedule appointments
* ❌ Cancel appointments
* 👨‍⚕️ Doctor selection
* 📆 Today / Tomorrow / Custom date
* ⏰ Appointment slot availability
* 🔒 Temporary slot locking
* 👤 Patient details management
* 📝 Reason for visit
* 📋 Appointment review before confirmation
* 🆔 Automatic Appointment ID generation
* 📊 Patient visit history
* 📄 Google Sheets appointment storage
* 📅 Google Calendar integration
* 🔔 Automatic WhatsApp appointment reminders
* 🤖 Mistral AI-powered validation
* 🔐 WhatsApp webhook verification
* 🛡️ Duplicate message protection
* ☁️ Railway deployment support

## 🏗️ Architecture

```text
Patient
   │
   ▼
WhatsApp
   │
   ▼
WhatsApp Cloud API
   │
   ▼
FastAPI Webhook
   │
   ▼
AI Appointment Agent
   │
   ├── Mistral AI
   │
   ├── Google Sheets
   │
   └── Google Calendar
   │
   ▼
WhatsApp Response
```

## 🛠️ Tech Stack

| Technology          | Purpose               |
| ------------------- | --------------------- |
| Python              | Backend Programming   |
| FastAPI             | Backend & Webhook     |
| Mistral AI          | AI Validation         |
| LangChain           | AI Integration        |
| WhatsApp Cloud API  | Patient Communication |
| Google Sheets API   | Appointment Storage   |
| Google Calendar API | Appointment Calendar  |
| APScheduler         | Automatic Reminders   |
| Docker              | Containerization      |
| Railway             | Cloud Deployment      |

## 📱 WhatsApp Demo

Scan the QR code below to start using the WhatsApp Clinic Appointment System.

<p align="center">
  <img src="QR.png" width="250" alt="WhatsApp Clinic Appointment QR Code">
</p>

<p align="center">
  📲 Scan the QR code and start booking your appointment.
</p>

## 📁 Project Structure

```text
whatsapp-clinic-appointment-system/
│
├── agent.py
├── api.py
├── app.py
├── config.py
├── google_tools.py
├── prompts.py
├── schemas.py
├── whatsapp_service.py
├── whatsapp_webhook.py
│
├── QR.png
├── requirements.txt
├── Dockerfile
├── .gitignore
└── README.md
```

## 💬 WhatsApp Appointment Flow

### Main Menu

```text
👋 Welcome to the Clinic AI Assistant.

Please select an option by replying with a number:

1️⃣ Book Appointment
2️⃣ Check Appointment
3️⃣ Reschedule Appointment
4️⃣ Cancel Appointment
```

### Booking Flow

```text
Select Doctor
      ↓
Select Date
      ↓
Select Available Time
      ↓
Enter Name
      ↓
Enter Mobile Number
      ↓
Enter Age
      ↓
Enter Reason
      ↓
Review Appointment
      ↓
Confirm
      ↓
Appointment Created
```

## 📊 Google Sheets

Confirmed appointments are stored with:

* Appointment ID
* Patient Name
* Mobile Number
* Age
* Doctor
* Date
* Time
* Duration
* Reason
* Status
* Created At
* Calendar Event ID
* Reminder Status

## 📅 Google Calendar

After an appointment is confirmed, the system automatically creates a calendar event.

When a patient reschedules an appointment, the calendar event is updated.

When a patient cancels an appointment, the calendar event is removed.

## 🔔 Automatic Appointment Reminders

The system automatically checks upcoming appointments and sends WhatsApp reminders.

Example:

```text
🔔 Appointment Reminder

Hello Patient 👋

Your appointment is today:

👨‍⚕️ Dr. Patel
⏰ 05:00 PM
📅 Appointment Date

Please arrive 10 minutes early.

Reply if you need to Reschedule or Cancel.
```

## 🔐 Environment Variables

The following environment variables are required for deployment:

```text
MISTRAL_API_KEY

GOOGLE_CREDENTIALS_JSON
GOOGLE_SHEET_ID
GOOGLE_CALENDAR_ID

WHATSAPP_ACCESS_TOKEN
WHATSAPP_PHONE_NUMBER_ID
WHATSAPP_VERIFY_TOKEN
WHATSAPP_BUSINESS_ACCOUNT_ID
WHATSAPP_APP_SECRET
```

### Google Service Account

Google Service Account credentials are stored securely through environment variables.

The credentials should **never be committed to GitHub**.

## ☁️ Deployment

The backend is designed for cloud deployment using **Railway**.

Required configuration:

* Railway project
* Environment variables
* Google Service Account
* Google Sheets access
* Google Calendar access
* WhatsApp Cloud API configuration
* WhatsApp webhook configuration

## 🔒 Security

* Secrets are stored using environment variables.
* WhatsApp access tokens are not hardcoded.
* Google credentials are not committed to the repository.
* Duplicate WhatsApp messages are protected.
* Appointment slots use temporary locking.
* Sensitive credentials are kept outside the source code.

## ⚙️ Local Development

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure the required environment variables and run the FastAPI application.

## 🐳 Docker

The project includes a Dockerfile for containerized deployment.

Docker can be used for:

* Local development
* Testing
* Cloud deployment
* Consistent Python environment

## 📌 Project Status

**Status: 🚀 Production Deployment**

This project provides an automated clinic appointment workflow through WhatsApp, reducing the need for manual appointment management.

## 👨‍💻 Developer

**Ghanshyam Prajapati**

---

⭐ If you find this project useful, consider giving the repository a star.
