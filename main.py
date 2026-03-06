import json, sqlite3, requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# CONFIGURATION
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_URL = "https://electrosmm.com/api/v2"
API_KEY = os.getenv('API_KEY')
ADMIN_ID = 7117775366
CHANNEL = "@VERIFIEDPAISABOTS"

# DATABASE SETUP
conn = sqlite3.connect('bot.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)')
conn.commit()

# LOAD SERVICES
with open('services.json', 'r') as f:
    services = json.load(f)

# HELPERS
def get_service_by_id(sid):
    for cat in services.values():
        for s in cat:
            if s['id'] == sid: return s
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Channel check logic yahan add karein...
    kb = [["SERVICES", "ADD FUND"], ["SUPPORT"]]
    await update.message.reply_text("Welcome! Service select karein:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def handle_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Logic: User select karta hai, Bot calculate karta hai
    # Total = (price_per_1000 / 1000) * quantity
    # Agar balance hai, toh API call:
    # requests.post(API_URL, data={'key': API_KEY, 'action': 'add', 'service': sid, 'link': link, 'quantity': qty})
    pass

# ADMIN APPROVAL FLOW
async def approve_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Admin button dabaye -> User ka balance update karein
    query = update.callback_query
    user_id = query.data.split("_")[1]
    c.execute("UPDATE users SET balance = balance + 100 WHERE user_id = ?", (user_id,))
    conn.commit()
    await query.message.reply_text("Balance Added!")

# App initialization
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(approve_payment))
app.run_polling()
