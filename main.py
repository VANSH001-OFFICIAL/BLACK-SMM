import os, json, sqlite3, threading, requests
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, CallbackQueryHandler, 
                          MessageHandler, filters, ContextTypes, ConversationHandler)

# --- CONFIG ---
TOKEN = os.getenv('BOT_TOKEN')
API_KEY = os.getenv('API_KEY')
ADMIN_ID = 7117775366
API_URL = "https://electrosmm.com/api/v2"
WAITING_FOR_SS = 1

# --- DB & SERVICES ---
with open('services.json', 'r') as f: services = json.load(f)
conn = sqlite3.connect('bot.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)')
conn.commit()

# --- FLASK (Render Port) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is live!"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- BOT LOGIC ---
async def start(update, context):
    kb = [["SERVICES", "ADD FUND"], ["SUPPORT"]]
    await update.message.reply_text("Welcome to Panel!\nJoin @VERIFIEDPAISABOTS", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def handle_services(update, context):
    kb = [[InlineKeyboardButton("Instagram", callback_data="cat_instagram")],
          [InlineKeyboardButton("YouTube", callback_data="cat_youtube")],
          [InlineKeyboardButton("Telegram", callback_data="cat_telegram")]]
    await update.message.reply_text("Select Category:", reply_markup=InlineKeyboardMarkup(kb))

async def category_callback(update, context):
    query = update.callback_query
    cat = query.data.split("_")[1]
    msg = f"Available {cat.upper()} Services:\n"
    for s in services[cat]:
        msg += f"ID: {s['id']} | {s['name']} | Rate: {s['price_per_1000']} RS/1k\n"
    await query.message.reply_text(msg + "\nFormat: /order [id] [link] [qty]")

async def order(update, context):
    try:
        sid, link, qty = int(context.args[0]), context.args[1], int(context.args[2])
        # 
        found = next((s for cat in services.values() for s in cat if s['id'] == sid), None)
        if not found: return await update.message.reply_text("Invalid ID!")
        
        total = (found['price_per_1000'] / 1000) * qty
        c.execute("SELECT balance FROM users WHERE user_id=?", (update.effective_user.id,))
        bal = c.fetchone()
        if not bal or bal[0] < total: return await update.message.reply_text("Low Balance!")
        
        resp = requests.post(API_URL, data={'key': API_KEY, 'action': 'add', 'service': sid, 'link': link, 'quantity': qty}).json()
        if 'order' in resp:
            c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (total, update.effective_user.id))
            conn.commit()
            await update.message.reply_text(f"Order Success! ID: {resp['order']}")
    except: await update.message.reply_text("Format: /order [id] [link] [qty]")

# --- CONVERSATION HANDLER (ADD FUND) ---
async def add_fund_start(update, context):
    await update.message.reply_text(f"UPI ID: `vansh59rt@fam`\nClick button to send screenshot:", 
                                   reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("SEND SS", callback_data="ask_ss")]]), parse_mode='Markdown')

async def ask_ss(update, context):
    await update.callback_query.edit_message_text("Send the screenshot now:", 
                                                 reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("CANCEL", callback_data="cancel_ss")]]))
    return WAITING_FOR_SS

async def receive_ss(update, context):
    photo_id = update.message.photo[-1].file_id
    await context.bot.send_photo(ADMIN_ID, photo_id, caption=f"Payment Request! User ID: {update.effective_user.id}", 
                                 reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Approve", callback_data=f"app_{update.effective_user.id}")]]))
    await update.message.reply_text("Screenshot sent to admin.")
    return ConversationHandler.END

async def cancel_ss(update, context):
    await update.callback_query.edit_message_text("Cancelled.")
    return ConversationHandler.END

async def approve_callback(update, context):
    query = update.callback_query
    user_id = query.data.split("_")[1]
    c.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
    c.execute("UPDATE users SET balance = balance + 100 WHERE user_id = ?", (user_id,))
    conn.commit()
    await query.message.reply_text("Approved! 100RS added.")

# --- MAIN ---
if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(entry_points=[MessageHandler(filters.Text("ADD FUND"), add_fund_start)],
                               states={WAITING_FOR_SS: [CallbackQueryHandler(ask_ss, pattern="ask_ss"), CallbackQueryHandler(cancel_ss, pattern="cancel_ss"), MessageHandler(filters.PHOTO, receive_ss)]},
                               fallbacks=[])
    
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("order", order))
    bot.add_handler(MessageHandler(filters.Text(["SERVICES", "SUPPORT"]), lambda u, c: handle_services(u, c) if u.message.text=="SERVICES" else u.message.reply_text("Contact: @black_Seller16")))
    bot.add_handler(conv)
    bot.add_handler(CallbackQueryHandler(category_callback, pattern="^cat_"))
    bot.add_handler(CallbackQueryHandler(approve_callback, pattern="^app_"))
    bot.run_polling()
