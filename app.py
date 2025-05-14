from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import os
import base64
import logging
import json
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.probability import FreqDist
import heapq
import threading
import time
import secrets
from functools import wraps
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env file

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = secrets.token_hex(16)  # Needed for sessions




# Configuration
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI')
GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
# SCOPES = ['https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/userinfo.email']
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/gmail.modify'
]

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER')
TWILIO_SANDBOX_CODE = os.getenv('TWILIO_SANDBOX_CODE')



# App configuration
CHECK_INTERVAL = 60  # seconds
MAX_RETRIES = 3
SUMMARY_LENGTH = 3  # sentences
MAX_WHATSAPP_CHARS = 1500

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Track active notification services for users
active_users = {}

# Download NLTK resources
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'credentials' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    flow = Flow.from_client_secrets_file(
        'client_secrets.json',
        scopes=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI
    )
    
    # authorization_url, state = flow.authorization_url(
    #     access_type='offline',
    #     include_granted_scopes='true',
    #     prompt='consent'
    # )
    authorization_url, state = flow.authorization_url(
    access_type='offline',
    prompt='consent'
)

    
    
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    state = session.get('state', None)
    
    flow = Flow.from_client_secrets_file(
        'client_secrets.json',
        scopes=SCOPES,
        state=state,
        redirect_uri=GOOGLE_REDIRECT_URI
    )
    
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    
    credentials = flow.credentials
    session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    
    # Get user email
    service = build('oauth2', 'v2', credentials=credentials)
    user_info = service.userinfo().get().execute()
    session['email'] = user_info.get('email')
    
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', 
                         email=session.get('email'),
                         twilio_number=TWILIO_WHATSAPP_NUMBER.replace('whatsapp:', ''),
                         sandbox_code=TWILIO_SANDBOX_CODE)

@app.route('/api/verify-whatsapp', methods=['POST'])
@login_required
def verify_whatsapp():
    data = request.get_json()
    whatsapp_number = data.get('whatsapp_number')
    
    if not whatsapp_number or not re.match(r'^\+[0-9]{10,15}$', whatsapp_number):
        return jsonify({'status': 'error', 'message': 'Invalid WhatsApp number format'})
    
    # Store in session
    session['whatsapp_number'] = whatsapp_number
    
    # Test message to verify
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body="Welcome to Email to WhatsApp Notifier! Your WhatsApp is now connected.",
            from_=TWILIO_WHATSAPP_NUMBER,
            to=f"whatsapp:{whatsapp_number}"
        )
        return jsonify({'status': 'success', 'message': 'WhatsApp number verified'})
    except TwilioRestException as e:
        logger.error(f"Twilio error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/start-service', methods=['POST'])
@login_required
def start_service():
    email = session.get('email')
    whatsapp_number = session.get('whatsapp_number')
    credentials_dict = session.get('credentials')
    
    if not email or not whatsapp_number or not credentials_dict:
        return jsonify({'status': 'error', 'message': 'Missing required information'})
    
    # Stop existing service if any
    if email in active_users:
        active_users[email]['active'] = False
    
    # Create credentials object
    credentials = Credentials(
        token=credentials_dict['token'],
        refresh_token=credentials_dict['refresh_token'],
        token_uri=credentials_dict['token_uri'],
        client_id=credentials_dict['client_id'],
        client_secret=credentials_dict['client_secret'],
        scopes=credentials_dict['scopes']
    )
    
    # Store user config
    active_users[email] = {
        'credentials': credentials,
        'whatsapp_number': whatsapp_number,
        'active': True,
        'last_check': datetime.now()
    }
    
    # Start background thread for this user
    thread = threading.Thread(target=email_check_worker, args=(email,))
    thread.daemon = True
    thread.start()
    
    return jsonify({'status': 'success', 'message': 'Service started successfully'})

@app.route('/api/stop-service', methods=['POST'])
@login_required
def stop_service():
    email = session.get('email')
    
    if email in active_users:
        active_users[email]['active'] = False
        return jsonify({'status': 'success', 'message': 'Service stopped successfully'})
    
    return jsonify({'status': 'error', 'message': 'No active service found'})

@app.route('/api/check-now', methods=['POST'])
@login_required
def check_now():
    email = session.get('email')
    
    if email not in active_users:
        return jsonify({'status': 'error', 'message': 'Service not started'})
    
    # Perform check
    user_data = active_users[email]
    check_emails_for_user(email, user_data['credentials'], user_data['whatsapp_number'])
    user_data['last_check'] = datetime.now()
    
    return jsonify({
        'status': 'success', 
        'message': 'Email check completed',
        'last_check': user_data['last_check'].strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/status', methods=['GET'])
@login_required
def get_status():
    email = session.get('email')
    
    if email in active_users:
        user_data = active_users[email]
        return jsonify({
            'status': 'success',
            'active': user_data['active'],
            'last_check': user_data['last_check'].strftime('%Y-%m-%d %H:%M:%S'),
            'whatsapp_number': user_data['whatsapp_number']
        })
    
    return jsonify({
        'status': 'error',
        'active': False,
        'message': 'Service not started'
    })

@app.route('/logout')
def logout():
    email = session.get('email')
    
    # Stop service if running
    if email in active_users:
        active_users[email]['active'] = False
    
    # Clear session
    session.clear()
    return redirect(url_for('index'))

def email_check_worker(email):
    """Background worker to check emails periodically"""
    while email in active_users and active_users[email]['active']:
        try:
            user_data = active_users[email]
            check_emails_for_user(email, user_data['credentials'], user_data['whatsapp_number'])
            user_data['last_check'] = datetime.now()
            
            # Sleep for the interval
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            logger.error(f"Error in worker thread for {email}: {e}")
            time.sleep(CHECK_INTERVAL)

def check_emails_for_user(email, credentials, whatsapp_number):
    """Check for new emails and send notifications"""
    try:
        # Build the Gmail API service
        service = build('gmail', 'v1', credentials=credentials)
        
        # Get unread emails
        results = service.users().messages().list(
            userId='me',
            labelIds=['INBOX', 'UNREAD'],
            maxResults=3
        ).execute()
        messages = results.get('messages', [])
        
        if not messages:
            logger.info(f'No unread messages for {email}')
            return
        
        # Process each email
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            
            # Get email data
            headers = msg['payload']['headers']
            sender = next((header['value'] for header in headers if header['name'] == 'From'), 'Unknown')
            subject = next((header['value'] for header in headers if header['name'] == 'Subject'), 'No Subject')
            timestamp = datetime.fromtimestamp(int(msg['internalDate'])/1000).strftime('%Y-%m-%d %H:%M:%S')
            
            # Get and summarize email body
            complete_body = get_complete_email_body(service, message['id'])
            summary = summarize_text(complete_body)
            
            # Format message
            whatsapp_message = (
                f"📧 New Email\n"
                f"From: {sender}\n"
                f"Subject: {subject}\n"
                f"Time: {timestamp}\n"
                f"Summary: {summary}"
            )
            
            # Send WhatsApp message
            if send_whatsapp_message(whatsapp_message, f"whatsapp:{whatsapp_number}"):
                # Mark as read if successfully sent
                service.users().messages().modify(
                    userId='me',
                    id=message['id'],
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
                logger.info(f"Marked email {message['id']} as read for {email}")
    
    except Exception as e:
        logger.error(f"Error checking emails for {email}: {e}")

def get_complete_email_body(service, msg_id):
    """Get the complete email body"""
    try:
        message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        body_parts = []
        
        def extract_text_from_part(part):
            if 'parts' in part:
                for subpart in part['parts']:
                    extract_text_from_part(subpart)
            else:
                if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
                    text = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    body_parts.append(text)
        
        if 'payload' in message:
            if 'parts' in message['payload']:
                for part in message['payload']['parts']:
                    extract_text_from_part(part)
            elif 'body' in message['payload'] and 'data' in message['payload']['body']:
                text = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
                body_parts.append(text)
        
        complete_body = '\n'.join(body_parts)
        return complete_body if complete_body else "No body content available"
    
    except Exception as e:
        logger.error(f"Error getting email body: {e}")
        return "Error retrieving email body"

def summarize_text(text, num_sentences=SUMMARY_LENGTH):
    """Generate a summary using extractive summarization technique"""
    try:
        # Clean the text and remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Tokenize the text
        sentences = sent_tokenize(text)
        
        # If there are fewer sentences than requested summary length, return all sentences
        if len(sentences) <= num_sentences:
            return text
        
        # Tokenize words and remove stopwords
        stop_words = set(stopwords.words('english'))
        word_tokens = word_tokenize(text.lower())
        filtered_tokens = [word for word in word_tokens if word.isalnum() and word not in stop_words]
        
        # Calculate word frequencies
        word_freq = FreqDist(filtered_tokens)
        
        # Score sentences based on word frequencies
        sentence_scores = {}
        for i, sentence in enumerate(sentences):
            for word in word_tokenize(sentence.lower()):
                if word in word_freq:
                    if i in sentence_scores:
                        sentence_scores[i] += word_freq[word]
                    else:
                        sentence_scores[i] = word_freq[word]
        
        # Select top sentences
        top_sentences = heapq.nlargest(num_sentences, sentence_scores.items(), key=lambda x: x[1])
        top_sentences = sorted(top_sentences, key=lambda x: x[0])
        
        # Combine the selected sentences
        summary = ' '.join([sentences[i] for i, _ in top_sentences])
        
        return summary
    
    except Exception as e:
        logger.error(f"Error summarizing text: {e}")
        return "Could not summarize email content. Please check the original email."

def send_whatsapp_message(message_body, to_number, retry_count=0):
    """Send WhatsApp message using Twilio"""
    if retry_count >= MAX_RETRIES:
        logger.error(f"Max retries ({MAX_RETRIES}) reached for message")
        return False

    try:
        # Ensure message is within character limit
        if len(message_body) > MAX_WHATSAPP_CHARS:
            message_body = message_body[:MAX_WHATSAPP_CHARS-3] + "..."
        
        # Debug log for message length
        logger.info(f"Sending WhatsApp message with length: {len(message_body)} characters")
        
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=message_body,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=to_number
        )
        logger.info(f"WhatsApp message sent: {message.sid}")
        return True
    
    except TwilioRestException as e:
        logger.error(f"Twilio error: {e}")
        time.sleep(2 ** retry_count)  # Exponential backoff
        return send_whatsapp_message(message_body, to_number, retry_count + 1)
    
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {e}")
        return False

if __name__ == '__main__':
    app.run(debug=True)