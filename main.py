import os, json, sqlite3, threading, requests
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, CallbackQueryHandler, 
                          MessageHandler, filters, ContextTypes, ConversationHandler)

# --- CONFIG ---
TOKEN = os.getenv('BOT_TOKEN')
API_KEY = os.getenv('API_KEY')
ADMIN_ID = 7117775366
CHANNEL = "@VERIFIEDPAISABOTS"
API_URL = "https://electrosmm.com/api/v2"
WAITING_FOR_SS = 1

# --- DB & SERVICES ---
with open('services.json', 'r') as f: services = json.load(f)
conn = sqlite3.connect('bot.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)')
conn.commit()

# --- FLASK ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is live!"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- BOT LOGIC ---
async def start(update, context):
    # Check subscription logic...
    kb = [["SERVICES", "ADD FUND"], ["SUPPORT"]]
    await update.message.reply_text("Welcome! Service select karein:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def add_fund_start(update, context):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("SEND SS", callback_data="ask_ss")]])
    await update.message.reply_text("UPI: `vansh59rt@fam`\nClick to send SS:", reply_markup=kb, parse_mode='Markdown')
    return WAITING_FOR_SS

async def ask_ss(update, context):
    await update.callback_query.edit_message_text("Now send the screenshot image:", 
                                                 reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("CANCEL", callback_data="cancel_ss")]]))
    return WAITING_FOR_SS

async def receive_ss(update, context):
    photo = update.message.photo[-1].file_id
    await context.bot.send_photo(ADMIN_ID, photo, caption=f"Payment Request! User ID: {update.effective_user.id}", 
                                 reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Approve", callback_data=f"app_{update.effective_user.id}")]]))
    await update.message.reply_text("Screenshot sent to admin.")
    return ConversationHandler.END

async def cancel_ss(update, context):
    await update.callback_query.edit_message_text("Cancelled.")
    return ConversationHandler.END

# --- HANDLERS ---
async def button_handler(update, context):
    text = update.message.text
    if text == "SERVICES": 
        kb = [[InlineKeyboardButton("Instagram", callback_data="cat_instagram")],
              [InlineKeyboardButton("YouTube", callback_data="cat_youtube")]]
        await update.message.reply_text("Select:", reply_markup=InlineKeyboardMarkup(kb))
    elif text == "SUPPORT": await update.message.reply_text("Contact: @black_Seller16")

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot = ApplicationBuilder().token(TOKEN).build()
    
    # Corrected Handler (No per_callback argument)
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^ADD FUND$"), add_fund_start)],
        states={
            WAITING_FOR_SS: [
                CallbackQueryHandler(ask_ss, pattern="^ask_ss$"),
                CallbackQueryHandler(cancel_ss, pattern="^cancel_ss$"),
                MessageHandler(filters.PHOTO, receive_ss)
            ]
        },
        fallbacks=[]
    )
    
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(conv)
    bot.add_handler(MessageHandler(filters.Regex("^(SERVICES|SUPPORT)$"), button_handler))
    bot.run_polling()
