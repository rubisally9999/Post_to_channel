import os
import requests
from flask import Flask, request, send_from_directory
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
import logging

app = Flask(__name__)

# Load configuration from environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
CHANNEL_ID = os.getenv('CHANNEL_ID')
TUTORIAL_LINK = os.getenv('TUTORIAL_LINK')

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is not set.")
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL environment variable is not set.")
if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID environment variable is not set.")
if not TUTORIAL_LINK:
    raise ValueError("TUTORIAL_LINK environment variable is not set.")

# Initialize Telegram bot
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define states for the conversation
URL, FILE_NAME = range(2)

# Start command handler
def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("🔗 Please send a URL.")
    logger.debug("Start command invoked")
    return URL

# Receive URL handler
def receive_url(update: Update, context: CallbackContext) -> int:
    context.user_data['url'] = update.message.text
    update.message.reply_text("📝 Please send the file name.")
    logger.debug("Received URL: %s", update.message.text)
    return FILE_NAME

# Receive file name and post to channel
def receive_file_name(update: Update, context: CallbackContext) -> int:
    file_name = update.message.text
    url = context.user_data['url']
    
    # Simple post text
    post_text = f"File Name: {file_name}\nLink: {url}"
    
    try:
        logger.debug("Posting message to channel %s", CHANNEL_ID)
        logger.debug("Message text: %s", post_text)
        
        # Post to channel
        response = context.bot.send_message(chat_id=CHANNEL_ID, text=post_text)
        
        logger.debug("Message posted to channel %s", CHANNEL_ID)
        logger.debug("Response from Telegram: %s", response)
        
        update.message.reply_text("✅ Your file has been posted to the channel!")
    except Exception as e:
        update.message.reply_text("❌ Failed to post the file to the channel.")
        logger.error("Error posting message to channel %s: %s", CHANNEL_ID, e, exc_info=True)
    
    return ConversationHandler.END

# Cancel command handler
def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('❌ Operation canceled.')
    logger.debug("Operation canceled by user")
    return ConversationHandler.END

# Set up conversation handler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        URL: [MessageHandler(Filters.text & ~Filters.command, receive_url)],
        FILE_NAME: [MessageHandler(Filters.text & ~Filters.command, receive_file_name)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)

# Add handlers to dispatcher
dispatcher.add_handler(conv_handler)

# Webhook route
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
        logger.debug("Webhook received update: %s", request.get_json(force=True))
        return 'ok', 200
    except Exception as e:
        logger.error("Error processing webhook update: %s", e, exc_info=True)
        return 'Internal Server Error', 500

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
    try:
        response = requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook',
            data={'url': WEBHOOK_URL}
        )
        if response.json().get('ok'):
            logger.debug("Webhook setup successful")
            return "Webhook setup ok"
        else:
            logger.error("Webhook setup failed: %s", response.json())
            return "Webhook setup failed"
    except Exception as e:
        logger.error("Error setting up webhook: %s", e, exc_info=True)
        return "Webhook setup failed"

if __name__ == '__main__':
    app.run(port=5000)
