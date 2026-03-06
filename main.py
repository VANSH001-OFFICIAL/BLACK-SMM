import os, json, sqlite3, threading, requests
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CONFIG ---
TOKEN = os.getenv('BOT_TOKEN')
API_KEY = os.getenv('API_KEY')
ADMIN_ID = 7117775366
API_URL = "https://electrosmm.com/api/v2"

# --- DB & SERVICES ---
with open('services.json', 'r') as f: services = json.load(f)
conn = sqlite3.connect('bot.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)')
conn.commit()

# --- FLASK (Render Port Binding) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is running!"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- BOT LOGIC ---
async def start(update, context):
    kb = [["SERVICES", "ADD FUND"], ["SUPPORT"]]
    await update.message.reply_text("Welcome to Panel!\nJoin @VERIFIEDPAISABOTS", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def handle_services(update, context):
    text = "Select Category:\n1. Instagram\n2. YouTube\n3. Telegram\n\nCommand: /order [service_id] [link] [quantity]"
    await update.message.reply_text(text)

async def order(update, context):
    # args: [service_id, link, quantity]
    try:
        sid, link, qty = int(context.args[0]), context.args[1], int(context.args[2])
        # Find service in JSON
        found_service = None
        for cat in services.values():
            for s in cat:
                if s['id'] == sid: found_service = s
        
        if not found_service: return await update.message.reply_text("Invalid Service ID")
        
        total = (found_service['price_per_1000'] / 1000) * qty
        # Check Balance in DB
        c.execute("SELECT balance FROM users WHERE user_id=?", (update.effective_user.id,))
        bal = c.fetchone()
        
        if not bal or bal[0] < total: return await update.message.reply_text("Insufficient Balance!")
        
        # API CALL
        resp = requests.post(API_URL, data={'key': API_KEY, 'action': 'add', 'service': sid, 'link': link, 'quantity': qty}).json()
        if 'order' in resp:
            c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (total, update.effective_user.id))
            conn.commit()
            await update.message.reply_text(f"Order Successful! ID: {resp['order']}")
        else:
            await update.message.reply_text(f"Error: {resp.get('error')}")
    except Exception as e: await update.message.reply_text(f"Format: /order [id] [link] [qty]")

# --- ADMIN & PAYMENT ---
async def add_fund(update, context):
    await update.message.reply_text(f"Send Payment to: `vansh59rt@fam`\nSend screenshot here.")
    context.user_data['pending'] = True

async def screenshot_handler(update, context):
    if context.user_data.get('pending'):
        photo = update.message.photo[-1].file_id
        btn = [[InlineKeyboardButton("Approve", callback_data=f"app_{update.effective_user.id}")]]
        await context.bot.send_photo(ADMIN_ID, photo, caption=f"User: {update.effective_user.id}", reply_markup=InlineKeyboardMarkup(btn))
        await update.message.reply_text("Request sent to Admin.")
        context.user_data['pending'] = False

async def approve(update, context):
    query = update.callback_query
    user_id = query.data.split("_")[1]
    c.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
    c.execute("UPDATE users SET balance = balance + 100 WHERE user_id = ?", (user_id,))
    conn.commit()
    await query.message.reply_text("Approved!")

# --- EXECUTION ---
if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot = ApplicationBuilder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("order", order))
    bot.add_handler(MessageHandler(filters.PHOTO, screenshot_handler))
    bot.add_handler(CallbackQueryHandler(approve))
    bot.run_polling()
