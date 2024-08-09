import os
import aiohttp
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

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is not set.")
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL environment variable is not set.")
if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID environment variable is not set.")
if not SHORTENER_API_KEY:
    raise ValueError("SHORTENER_API_KEY environment variable is not set.")

# Initialize Telegram bot
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

# Shorten URL using the publicearn.com API
async def shorten_url(url):
    try:
        async with aiohttp.ClientSession() as session:
            api_url = f"https://publicearn.com/api?api={SHORTENER_API_KEY}&url={url}&alias=CustomAlias&format=text"
            async with session.get(api_url) as response:
                if response.status == 200:
                    short_url = await response.text()
                    if short_url:
                        return short_url.strip()
                    else:
                        logger.error("No shortened URL found in response.")
                        return None
                else:
                    logger.error(f"Received non-200 status code: {response.status}")
                    return None
    except aiohttp.ClientError as e:
        logger.error(f"AIOHTTP ClientError occurred while shortening URL: {e}")
        return None
    except Exception as e:
        logger.error(f"Exception occurred while shortening URL: {e}")
        return None

# Define command and message handlers
def start(update: Update, context: CallbackContext):
    update.message.reply_text('Send me a URL to shorten and post.')
    context.user_data['awaiting_url'] = True

async def handle_message(update: Update, context: CallbackContext):
    if context.user_data.get('awaiting_url'):
        url = update.message.text
        short_url = await shorten_url(url)
        if short_url:
            context.user_data['short_url'] = short_url
            update.message.reply_text(f'Here is your shortened link: {short_url}\nPlease provide a file name:')
            context.user_data['awaiting_url'] = False
            context.user_data['awaiting_file_name'] = True
            logger.info(f'URL shortened successfully: {short_url}')
        else:
            update.message.reply_text('Failed to shorten the URL. Please try again.')
    elif context.user_data.get('awaiting_file_name'):
        context.user_data['file_name'] = update.message.text
        short_url = context.user_data.get('short_url')
        file_name = context.user_data.get('file_name')
        if short_url and file_name:
            post_message = (f"File Name: {file_name}\n"
                            f"Shortened URL: {short_url}\n"
                            f"How to open (Tutorial):\n"
                            f"Open the shortened URL in your Telegram browser.")
            try:
                response = bot.send_message(chat_id=CHANNEL_ID, text=post_message)
                logger.info(f'Telegram API Response: {response}')
                if response:
                    update.message.reply_text('The information has been posted to the channel.')
                else:
                    logger.error('Failed to receive a response from Telegram API')
                    update.message.reply_text('Failed to post to channel. Please try again.')
            except Exception as e:
                logger.error(f'Error posting to channel: {e}')
                update.message.reply_text('Error posting to channel.')
            finally:
                context.user_data['awaiting_file_name'] = False
        else:
            update.message.reply_text('File name or shortened URL is missing.')

# Add handlers to dispatcher
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

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
