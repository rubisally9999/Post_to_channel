import os
import requests
import logging
from flask import Flask, request, send_from_directory
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext
import pyshorteners

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load configuration from environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
CHANNEL_ID = os.getenv('CHANNEL_ID')  # Add CHANNEL_ID to your environment variables
SHORTENER_API_KEY = os.getenv('SHORTENER_API_KEY')  # Add SHORTENER_API_KEY to your environment variables
SHORTENER_TYPE = os.getenv('SHORTENER_TYPE', 'tinyurl')  # Default to 'tinyurl' if not specified

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is not set.")
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL environment variable is not set.")
if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID environment variable is not set.")
if not SHORTENER_API_KEY:
    raise ValueError("SHORTENER_API_KEY environment variable is not set.")

# Initialize Telegram bot and URL shortener
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

# Initialize URL shortener based on type
s = None
if SHORTENER_TYPE == 'tinyurl':
    s = pyshorteners.Shortener()
elif SHORTENER_TYPE == 'bitly':
    s = pyshorteners.Shortener(api_key=SHORTENER_API_KEY).bitly
else:
    raise ValueError("Unsupported SHORTENER_TYPE. Use 'tinyurl' or 'bitly'.")

# Define the start command handler
def start(update: Update, context: CallbackContext):
    update.message.reply_text('Send me a URL to shorten and post.')

def shorten_url(update: Update, context: CallbackContext):
    url = update.message.text
    try:
        short_url = s.short(url)
        context.user_data['short_url'] = short_url
        update.message.reply_text('Please provide a file name:')
        logger.info(f'URL shortened successfully: {short_url}')
    except Exception as e:
        update.message.reply_text(f'Error shortening URL: {e}')
        logger.error(f'Error shortening URL: {e}')

def get_file_name(update: Update, context: CallbackContext):
    context.user_data['file_name'] = update.message.text
    short_url = context.user_data.get('short_url')
    file_name = context.user_data.get('file_name')
    post_message = (f"File Name: {file_name}\n"
                    f"Shortened URL: {short_url}\n"
                    f"How to open (Tutorial):\n"
                    f"Open the shortened URL in your Telegram browser.")
    bot.send_message(chat_id=CHANNEL_ID, text=post_message)
    update.message.reply_text('The information has been posted to the channel.')
    logger.info(f'Posted to channel: File Name: {file_name}, Shortened URL: {short_url}')

# Add handlers to dispatcher
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, shorten_url))
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
