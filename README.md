# 📬 Email to WhatsApp Notifier

This project is a Flask-based web application that connects your Gmail account with your WhatsApp number to send real-time email summaries via WhatsApp. It uses the Gmail API to fetch unread emails, summarizes them using NLP, and sends the summaries through WhatsApp using Twilio.

## 🚀 Features

- 🔐 Google OAuth2 authentication for secure access to Gmail
- 📥 Periodic checking of unread Gmail messages
- 🧠 NLP-based email summarization using NLTK
- 📲 WhatsApp notifications via Twilio API
- 🖥️ Dashboard for user interaction and control
- 🔁 Manual and automatic (background thread) email checks
- ♻️ Message retry logic for improved reliability

## 🛠️ Tech Stack

- **Backend**: Python, Flask
- **APIs**: Gmail API, Twilio API
- **NLP**: NLTK
- **OAuth**: Google OAuth2.0
- **Deployment**: Localhost (can be extended to cloud platforms)

## 📦 Installation

### 1. 📁 Clone the Repository

```bash
git clone https://github.com/yourusername/email-to-whatsapp-notifier.git
cd email-to-whatsapp-notifier
```

### 2. 🐍 Create and Activate Virtual Environment (optional but recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. 📦 Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. 🔑 Setup Google Credentials

- Create OAuth credentials in Google Cloud Console.
- Download `client_secrets.json` and place it in the root folder.

### 5. 📲 Configure Twilio

- Sign up at [Twilio](https://www.twilio.com/) and join the WhatsApp sandbox.
- Add your sandbox SID, Auth Token, and WhatsApp number in the code (`app.py`).

### 6. ▶️ Run the App

```bash
python app.py
```

Then, go to [http://localhost:5000](http://localhost:5000) in your browser.

## 📝 Notes

- ✅ Make sure NLTK resources (`punkt`, `stopwords`) are downloaded. The code handles this.
- 🔓 Ensure ports 5000 and the WhatsApp sandbox number are accessible.
- 📤 Twilio Sandbox code should be shared with the test WhatsApp number to initiate messages.




