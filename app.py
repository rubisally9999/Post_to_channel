import os
import requests
import logging
from flask import Flask, request, send_from_directory
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext

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

# Initialize Telegram bot and URL shortener
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

# Initialize URL shortener based on type
s = None
if SHORTENER_TYPE == 'publicearn':
    pass  # No specific initialization needed for PublicEarn in this case
else:
    raise ValueError("Unsupported SHORTENER_TYPE. Use 'publicearn'.")

def shorten_url(url):
    try:
        if SHORTENER_TYPE == 'publicearn':
            response = requests.get(f'https://publicearn.com/api?api={SHORTENER_API_KEY}&url={url}')
            if response.status_code == 200:
                json_response = response.json()
                return json_response.get('short_url') or json_response.get('shortened_url')
            else:
                raise ValueError("Error in PublicEarn response.")
        else:
            raise ValueError("Unsupported SHORTENER_TYPE. Use 'publicearn'.")
    except Exception as e:
        logger.error(f"Error shortening URL: {e}")
        return None

def shorten_url_handler(update: Update, context: CallbackContext):
    url = update.message.text
    short_url = shorten_url(url)
    if short_url:
        context.user_data['short_url'] = short_url
        update.message.reply_text('Please provide a file name:')
        logger.info(f'URL shortened successfully: {short_url}')
    else:
        update.message.reply_text('Failed to shorten the URL. Please try again.')
        logger.error('Failed to shorten URL')

def get_file_name(update: Update, context: CallbackContext):
    file_name = update.message.text
    short_url = context.user_data.get('short_url')
    
    if not file_name or not short_url:
        update.message.reply_text('Error: Missing file name or shortened URL. Please try again.')
        return

    post_message = (f"File Name: {file_name}\n"
                    f"Shortened URL: {short_url}\n"
                    f"How to open (Tutorial):\n"
                    f"Open the shortened URL in your Telegram browser.")
    
    try:
        bot.send_message(chat_id=CHANNEL_ID, text=post_message)
        update.message.reply_text('The information has been posted to the channel.')
        logger.info(f'Posted to channel: File Name: {file_name}, Shortened URL: {short_url}')
    except Exception as e:
        update.message.reply_text('Failed to post to the channel.')
        logger.error(f'Error posting to channel: {e}')

# Add handlers to dispatcher
dispatcher.add_handler(CommandHandler('start', lambda update, context: update.message.reply_text('Send me a URL to shorten and post.')))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, shorten_url_handler))
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
    response = requests.post(f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook', data={'url': WEBHOOK_URL})
    if response.json().get('ok'):
        logger.info('Webhook setup successfully')
        return "Webhook setup ok"
    else:
        logger.error('Webhook setup failed')
        return "Webhook setup failed"

if __name__ == '__main__':
    app.run(port=5000)
