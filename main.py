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

# --- FLASK SERVER (Render Port Binding) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is live!"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- BOT FUNCTIONS ---
async def start(update, context):
    kb = [["SERVICES", "ADD FUND"], ["SUPPORT"]]
    await update.message.reply_text("Welcome to Panel!\nJoin @VERIFIEDPAISABOTS", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def handle_services(update, context):
    kb = [
        [InlineKeyboardButton("Instagram", callback_data="cat_instagram")],
        [InlineKeyboardButton("YouTube", callback_data="cat_youtube")],
        [InlineKeyboardButton("Telegram", callback_data="cat_telegram")]
    ]
    await update.message.reply_text("Select Category:", reply_markup=InlineKeyboardMarkup(kb))

async def category_callback(update, context):
    query = update.callback_query
    cat = query.data.split("_")[1]
    msg = f"Available {cat.upper()} Services:\n"
    for s in services[cat]:
        msg += f"ID: {s['id']} | {s['name']} | Rate: {s['price_per_1000']} RS/1k\n"
    msg += "\nOrder format: /order [id] [link] [quantity]"
    await query.message.reply_text(msg)

async def order(update, context):
    try:
        sid, link, qty = int(context.args[0]), context.args[1], int(context.args[2])
        found = None
        for cat in services.values():
            for s in cat:
                if s['id'] == sid: found = s
        
        if not found: return await update.message.reply_text("Invalid ID!")
        
        # Min Quantity Check
        if qty < found.get('min_qty', 1000): return await update.message.reply_text(f"Min Qty: {found['min_qty']}")
        
        total = (found['price_per_1000'] / 1000) * qty
        c.execute("SELECT balance FROM users WHERE user_id=?", (update.effective_user.id,))
        bal = c.fetchone()
        if not bal or bal[0] < total: return await update.message.reply_text("Low Balance!")
        
        resp = requests.post(API_URL, data={'key': API_KEY, 'action': 'add', 'service': sid, 'link': link, 'quantity': qty}).json()
        if 'order' in resp:
            c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (total, update.effective_user.id))
            conn.commit()
            await update.message.reply_text(f"Order Success! ID: {resp['order']}")
    except: await update.message.reply_text("Usage: /order [id] [link] [qty]")

async def button_handler(update, context):
    text = update.message.text
    if text == "SERVICES": await handle_services(update, context)
    elif text == "ADD FUND": await update.message.reply_text("Pay to `vansh59rt@fam` & send screenshot.")
    elif text == "SUPPORT": await update.message.reply_text("Contact: @black_Seller16")

# --- EXECUTION ---
if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot = ApplicationBuilder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("order", order))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    bot.add_handler(CallbackQueryHandler(category_callback, pattern="^cat_"))
    bot.run_polling()
