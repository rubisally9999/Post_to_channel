import os
import requests
from flask import Flask, request, send_from_directory
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler

app = Flask(__name__)

# Load configuration from environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
CHANNEL_ID = os.getenv('CHANNEL_ID')  # Add CHANNEL_ID environment variable

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is not set.")
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL environment variable is not set.")
if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID environment variable is not set.")

# Initialize Telegram bot
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

# Define states for the conversation
URL, FILE_NAME = range(2)

# Start command handler
def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("🔗 Please send a URL.")
    return URL

# Receive URL handler
def receive_url(update: Update, context: CallbackContext) -> int:
    context.user_data['url'] = update.message.text
    update.message.reply_text("📝 Please send the file name.")
    return FILE_NAME

# Receive file name and post to channel
def receive_file_name(update: Update, context: CallbackContext) -> int:
    file_name = update.message.text
    url = context.user_data['url']
    
    # Post format preparation
    post_text = f"""
    📂 *File Name:* _{file_name}_

    🌐 *Link is here:*
    [Click here]({url})

    💡 *How to Open (Tutorial):*
    [Tutorial Link](https://example.com/tutorial) 

    🚀 Enjoy exploring the content!
    """
    
    try:
        # Post to channel
        context.bot.send_message(chat_id=CHANNEL_ID, text=post_text, parse_mode='MarkdownV2')
        update.message.reply_text("✅ Your file has been posted to the channel!")
    except Exception as e:
        # Log the error
        update.message.reply_text("❌ Failed to post the file to the channel.")
        print(f"Error posting message: {e}")
    
    # End conversation
    return ConversationHandler.END

# Cancel command handler
def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('❌ Operation canceled.')
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
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
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
        return "Webhook setup ok"
    else:
        return "Webhook setup failed"

if __name__ == '__main__':
    app.run(port=5000)
