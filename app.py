import os
import requests
import logging
from flask import Flask, request, send_from_directory
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler, PicklePersistence
from telegram.ext import Updater

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load configuration from environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
CHANNEL_ID = os.getenv('CHANNEL_ID')
SHORTENER_API_KEY = os.getenv('SHORTENER_API_KEY')  # API key for publicearn
SHORTENER_ALIAS = os.getenv('SHORTENER_ALIAS')  # Custom alias if needed

# Log the configuration values
logger.debug(f"SHORTENER_API_KEY: {SHORTENER_API_KEY}")
logger.debug(f"SHORTENER_ALIAS: {SHORTENER_ALIAS}")

# Check required environment variables
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
def shorten_url_with_publicearn(url):
    api_key = SHORTENER_API_KEY
    alias = SHORTENER_ALIAS
    shortener_url = f"https://publicearn.com/api?api={api_key}&url={url}&alias={alias}"
    try:
        response = requests.get(shortener_url)
        response.raise_for_status()
        data = response.json()
        return data.get('shortened_url', url)  # Fallback to original URL if not found
    except Exception as e:
        logger.error(f"Error shortening URL: {e}")
        raise

# Define conversation states
URL, FILE_NAME = range(2)

# Define the start command handler
def start(update: Update, context: CallbackContext):
    update.message.reply_text('Send me a URL to shorten and post.')
    return URL

def shorten_url(update: Update, context: CallbackContext):
    url = update.message.text
    try:
        short_url = shorten_url_with_publicearn(url)
        context.user_data['short_url'] = short_url
        update.message.reply_text('Please provide a file name:')
        logger.info(f'URL shortened successfully: {short_url}')
        return FILE_NAME
    except Exception as e:
        update.message.reply_text(f'Error shortening URL: {e}')
        logger.error(f'Error shortening URL: {e}')
        return ConversationHandler.END

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
    return ConversationHandler.END

# Define the conversation handler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        URL: [MessageHandler(Filters.text & ~Filters.command, shorten_url)],
        FILE_NAME: [MessageHandler(Filters.text & ~Filters.command, get_file_name)],
    },
    fallbacks=[],
    conversation_timeout=600,  # Optional: set a timeout for the conversation
)

# Add handlers to dispatcher
dispatcher.add_handler(conv_handler)

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
