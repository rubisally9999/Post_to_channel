import os
import requests
import logging
from flask import Flask, request, send_from_directory
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext
import json

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load configuration from environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
CHANNEL_ID = os.getenv('CHANNEL_ID')
SHORTENER_API_KEY = os.getenv('SHORTENER_API_KEY')
SHORTENER_TYPE = os.getenv('SHORTENER_TYPE')

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is not set.")
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL environment variable is not set.")
if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID environment variable is not set.")
if not SHORTENER_API_KEY:
    raise ValueError("SHORTENER_API_KEY environment variable is not set.")
if not SHORTENER_TYPE:
    raise ValueError("SHORTENER_TYPE environment variable is not set.")

# Initialize Telegram bot
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

# Initialize URL shortener
def shorten_url(url, alias=None):
    try:
        if SHORTENER_TYPE == 'publicearn':
            shortener_url = f'https://publicearn.com/api?api={SHORTENER_API_KEY}&url={url}'
            if alias:
                shortener_url += f'&alias={alias}'
            response = requests.get(shortener_url)
            logger.info(f"Publicearn API Response: {response.text}")  # Log the raw response
            if response.status_code == 200:
                json_response = response.json()
                logger.info(f"Publicearn JSON Response: {json_response}")  # Log the JSON response
                short_url = json_response.get('short_url') or json_response.get('shortened_url')
                if short_url:
                    return short_url
                else:
                    logger.error("No shortened URL found in response.")
                    return None
            else:
                logger.error(f"Received non-200 status code: {response.status_code}")
                return None
        elif SHORTENER_TYPE == 'bitly':
            headers = {
                'Authorization': f'Bearer {SHORTENER_API_KEY}',
                'Content-Type': 'application/json'
            }
            data = json.dumps({"long_url": url})
            response = requests.post('https://api-ssl.bitly.com/v4/shorten', headers=headers, data=data)
            logger.info(f"Bitly API Response: {response.text}")  # Log the raw response
            if response.status_code == 200:
                json_response = response.json()
                logger.info(f"Bitly JSON Response: {json_response}")  # Log the JSON response
                short_url = json_response.get('link')
                if short_url:
                    return short_url
                else:
                    logger.error("No shortened URL found in Bitly response.")
                    return None
            else:
                logger.error(f"Received non-200 status code from Bitly: {response.status_code}")
                return None
        else:
            raise ValueError("Unsupported SHORTENER_TYPE. Use 'publicearn' or 'bitly'.")
    except Exception as e:
        logger.error(f"Error shortening URL: {e}")
        return None

# Define command and message handlers
def start(update: Update, context: CallbackContext):
    update.message.reply_text('Send me a URL to shorten and post.')

def handle_url(update: Update, context: CallbackContext):
    url = update.message.text
    alias = "CustomAlias"  # Example alias, modify as needed
    short_url = shorten_url(url, alias)
    if short_url:
        context.user_data['short_url'] = short_url
        update.message.reply_text('Please provide a file name:')
        logger.info(f'URL shortened successfully: {short_url}')
    else:
        update.message.reply_text('Failed to shorten the URL. Please try again.')

def get_file_name(update: Update, context: CallbackContext):
    context.user_data['file_name'] = update.message.text
    short_url = context.user_data.get('short_url')
    file_name = context.user_data.get('file_name')
    if short_url and file_name:
        post_message = (f"File Name: {file_name}\n"
                        f"Shortened URL: {short_url}\n"
                        f"How to open (Tutorial):\n"
                        f"Open the shortened URL in your Telegram browser.")
        try:
            bot.send_message(chat_id=CHANNEL_ID, text=post_message)
            update.message.reply_text('The information has been posted to the channel.')
            logger.info(f'Posted to channel: File Name: {file_name}, Shortened URL: {short_url}')
        except Exception as e:
            update.message.reply_text('Error posting to channel.')
            logger.error(f'Error posting to channel: {e}')
    else:
        update.message.reply_text('File name or shortened URL is missing.')

# Add handlers to dispatcher
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_url))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, get_file_name))

# Webhook route
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    logger.info('Received update from webhook')
    return 'ok', 200

# Home route
@app.route('/')
def home():
    return 'Hello, World!'

# Favicon route
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.getcwd(), 'favicon.ico')

# Webhook setup route
@app.route('/setwebhook', methods=['GET', 'POST'])
def setup_webhook():
    response = requests.post(
        f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook',
        data={'url': WEBHOOK_URL}
    )
    if response.json().get('ok'):
        logger.info('Webhook setup successfully')
        return "Webhook setup ok"
    else:
        logger.error('Webhook setup failed')
        return "Webhook setup failed"

if __name__ == '__main__':
    app.run(port=5000)
