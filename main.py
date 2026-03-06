import os, json, sqlite3, threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, CallbackQueryHandler, 
                          MessageHandler, filters, ContextTypes, ConversationHandler)

TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 7117775366
PAYOUT_CHANNEL = "@BLACKSMM_PAYOUT"

# Database & Data
conn = sqlite3.connect('bot.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)')
conn.commit()

with open('services.json', 'r') as f: SERVICES = json.load(f)

# Flask (Port Binding)
app = Flask(__name__)
@app.route('/')
def home(): return "Bot Online"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- LOGIC ---
async def start(update, context):
    kb = [["SERVICES", "ADD FUND"], ["MY ACCOUNT", "SUPPORT"]]
    await update.message.reply_text("🔥 **SMM Panel Active**", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def show_services(update, context):
    kb = [[InlineKeyboardButton("Instagram", callback_data="cat_insta")],
          [InlineKeyboardButton("YouTube", callback_data="cat_yt")],
          [InlineKeyboardButton("Telegram", callback_data="cat_tg")]]
    await update.message.reply_text("Select Category:", reply_markup=InlineKeyboardMarkup(kb))

async def cat_callback(update, context):
    query = update.callback_query
    cat = query.data.split("_")[1]
    msg = f"🛒 **{cat.upper()} SERVICES:**\n"
    for s in SERVICES.get(cat, []):
        msg += f"🆔 {s['id']} - {s['name']} - {s['price']*1000} RS/1k\n"
    await query.message.edit_text(msg + "\nFormat: `/order [id] [link] [qty]`")

async def order(update, context):
    if len(context.args) < 3: return await update.message.reply_text("❌ Format: `/order [id] [link] [qty]`")
    sid, link, qty = int(context.args[0]), str(context.args[1]), int(context.args[2])
    
    # Auto Calculation
    price = next((s['price'] for cat in SERVICES.values() for s in cat if s['id'] == sid), None)
    if not price: return await update.message.reply_text("❌ Invalid ID!")
    
    total = price * qty
    c.execute("SELECT balance FROM users WHERE user_id=?", (update.effective_user.id,))
    bal = c.fetchone()[0]
    
    if bal < total: return await update.message.reply_text(f"❌ Low balance! Required: {total} RS")
    
    c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (total, update.effective_user.id))
    conn.commit()
    await context.bot.send_message(PAYOUT_CHANNEL, f"📩 Order! User: {update.effective_user.id}\nID: {sid}\nQty: {qty}")
    await update.message.reply_text(f"✅ Order placed! {total} RS deducted.")

# --- PAYMENT ---
async def receive_ss(update, context):
    photo = update.message.photo[-1].file_id
    kb = [[InlineKeyboardButton("Approve", callback_data=f"ask_{update.effective_user.id}")]]
    await context.bot.send_photo(ADMIN_ID, photo, caption=f"Req from: {update.effective_user.id}", reply_markup=InlineKeyboardMarkup(kb))
    await update.message.reply_text("✅ Request sent!")
    return ConversationHandler.END

async def ask_amt(update, context):
    uid = update.callback_query.data.split("_")[1]
    context.user_data['target_uid'] = uid
    await update.callback_query.message.reply_text(f"💰 Amount for {uid}?")
    return 1

async def process_amt(update, context):
    amt = float(update.message.text)
    uid = context.user_data['target_uid']
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, uid))
    conn.commit()
    await update.message.reply_text(f"✅ {amt} added!")
    return ConversationHandler.END

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO, receive_ss)],
        states={1: [MessageHandler(filters.TEXT, process_amt)]}, fallbacks=[]
    )
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("order", order))
    bot.add_handler(CallbackQueryHandler(ask_amt, pattern="^ask_"))
    bot.add_handler(CallbackQueryHandler(cat_callback, pattern="^cat_"))
    bot.add_handler(conv)
    bot.add_handler(MessageHandler(filters.Regex("^SERVICES$"), show_services))
    bot.run_polling()
