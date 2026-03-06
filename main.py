import os, sqlite3, requests, threading
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIG ---
TOKEN = os.getenv('BOT_TOKEN')
API_KEY = os.getenv('API_KEY')
API_URL = "https://electrosmm.com/api/v2"

# --- DB SETUP ---
conn = sqlite3.connect('bot.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)')
conn.commit()

# --- FLASK (For Render) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot Online"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- FUNCTIONS ---
async def start(update, context):
    kb = [["SERVICES", "ADD FUND"], ["MY ACCOUNT", "SUPPORT"]]
    await update.message.reply_text("🔥 **SMM Panel Active**", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def my_account(update, context):
    c.execute("SELECT balance FROM users WHERE user_id=?", (update.effective_user.id,))
    res = c.fetchone()
    bal = res[0] if res else 0
    await update.message.reply_text(f"👤 ID: `{update.effective_user.id}`\n💰 Balance: {bal} RS", parse_mode='Markdown')

async def show_services(update, context):
    try:
        # Direct API call to fetch services
        resp = requests.post(API_URL, data={'key': API_KEY, 'action': 'services'}).json()
        msg = "🛒 **Available Services:**\n\n"
        for s in resp[:15]: # Show top 15
            msg += f"🆔 `{s['service']}` - {s['name']}\n💵 Rate: {s['rate']}\n\n"
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text("❌ API Error: Services load nahi ho rahi.")

async def order(update, context):
    if len(context.args) < 3: return await update.message.reply_text("❌ Usage: `/order [id] [link] [qty]`")
    
    sid, link, qty = context.args[0], context.args[1], context.args[2]
    
    # Balance Check
    c.execute("SELECT balance FROM users WHERE user_id=?", (update.effective_user.id,))
    res = c.fetchone()
    bal = res[0] if res else 0
    
    if bal <= 0: return await update.message.reply_text("❌ Low balance!")

    # API Order
    payload = {'key': API_KEY, 'action': 'add', 'service': sid, 'link': link, 'quantity': qty}
    resp = requests.post(API_URL, data=payload).json()
    
    if 'order' in resp:
        c.execute("UPDATE users SET balance = balance - 10 WHERE user_id = ?", (update.effective_user.id,)) # Adjust cost calculation
        conn.commit()
        await update.message.reply_text(f"✅ Order Placed! ID: {resp['order']}")
    else:
        await update.message.reply_text(f"❌ Error: {resp.get('error')}")

async def admin_add(update, context):
    if update.effective_user.id == 7117775366:
        uid, amt = int(context.args[0]), float(context.args[1])
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, uid))
        conn.commit()
        await update.message.reply_text(f"✅ {amt} added to {uid}")

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot = ApplicationBuilder().token(TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("order", order))
    bot.add_handler(CommandHandler("add", admin_add))
    bot.add_handler(MessageHandler(filters.Regex("^SERVICES$"), show_services))
    bot.add_handler(MessageHandler(filters.Regex("^MY ACCOUNT$"), my_account))
    bot.run_polling()
