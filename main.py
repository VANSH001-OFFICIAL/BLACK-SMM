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

# --- DATABASE SETUP ---
conn = sqlite3.connect('bot.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)')
conn.commit()

# --- SERVICES JSON ---
try:
    with open('services.json', 'r') as f:
        services = json.load(f)
except Exception:
    services = {"instagram": [], "youtube": [], "telegram": []}

# --- FLASK (Render Support) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is Online!"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- HELPERS ---
async def is_subscribed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await context.bot.get_chat_member(CHANNEL, update.effective_user.id)
        return member.status in ['member', 'administrator', 'creator']
    except: return False

# --- CORE FUNCTIONS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_subscribed(update, context):
        kb = [[InlineKeyboardButton("Join Channel 📢", url=f"https://t.me/{CHANNEL.strip('@')}")]]
        return await update.message.reply_text("❌ **Access Denied!**\nPehle channel join karein.", reply_markup=InlineKeyboardMarkup(kb))
    
    kb = [["SERVICES", "ADD FUND"], ["MY ACCOUNT", "SUPPORT"]]
    await update.message.reply_text("🔥 **Welcome to SMM Panel**", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def my_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c.execute("SELECT balance FROM users WHERE user_id=?", (update.effective_user.id,))
    res = c.fetchone()
    bal = res[0] if res else 0
    await update.message.reply_text(f"👤 ID: `{update.effective_user.id}`\n💰 Balance: {bal} RS", parse_mode='Markdown')

async def handle_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("Instagram", callback_data="cat_instagram")],
          [InlineKeyboardButton("YouTube", callback_data="cat_youtube")],
          [InlineKeyboardButton("Telegram", callback_data="cat_telegram")]]
    await update.message.reply_text("Select Category:", reply_markup=InlineKeyboardMarkup(kb))

async def cat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat = query.data.split("_")[1]
    msg = f"🛒 **{cat.upper()} SERVICES:**\n\n"
    for s in services.get(cat, []):
        msg += f"🆔 `{s['id']}` - {s['name']}\n💵 {s['price_per_1000']} RS/1k\n\n"
    await query.message.reply_text(msg + "Format: `/order [id] [link] [qty]`", parse_mode='Markdown')

async def order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        return await update.message.reply_text("❌ `/order [id] [link] [qty]`")
    try:
        sid, link, qty = int(context.args[0]), str(context.args[1]), int(context.args[2])
        found = next((s for cat in services.values() for s in cat if s['id'] == sid), None)
        if not found: return await update.message.reply_text("❌ Invalid ID!")

        total = (found['price_per_1000'] / 1000) * qty
        c.execute("SELECT balance FROM users WHERE user_id=?", (update.effective_user.id,))
        bal = (c.fetchone() or (0,))[0]
        
        if bal < total: return await update.message.reply_text(f"❌ Low Balance! Cost: {total}")

        resp = requests.post(API_URL, data={'key': API_KEY, 'action': 'add', 'service': sid, 'link': link, 'quantity': qty}).json()
        if 'order' in resp:
            c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (total, update.effective_user.id))
            conn.commit()
            await update.message.reply_text(f"✅ Order Placed! ID: {resp['order']}")
        else:
            await update.message.reply_text(f"❌ Panel Error: {resp.get('error')}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# --- ADD FUND CONVERSATION ---
async def add_fund_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💳 UPI: `vansh59rt@fam` (Click to Copy)", 
                                   reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("SEND SS ✅", callback_data="ask_ss")]]), parse_mode='Markdown')
    return WAITING_FOR_SS

async def ask_ss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("📸 Send Screenshot now:")
    return WAITING_FOR_SS

async def receive_ss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1].file_id
    admin_kb = [[InlineKeyboardButton("Approve ✅", callback_data=f"app_{update.effective_user.id}")]]
    await context.bot.send_photo(ADMIN_ID, photo, caption=f"Deposit Req: `{update.effective_user.id}`", reply_markup=InlineKeyboardMarkup(admin_kb))
    await update.message.reply_text("✅ Sent to admin!")
    return ConversationHandler.END

# --- ADMIN ---
async def admin_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    uid, amt = int(context.args[0]), float(context.args[1])
    c.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (uid,))
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, uid))
    conn.commit()
    await update.message.reply_text(f"✅ Added {amt} to {uid}")

async def approve_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = int(update.callback_query.data.split("_")[1])
    c.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (uid,))
    c.execute("UPDATE users SET balance = balance + 100 WHERE user_id = ?", (uid,))
    conn.commit()
    await update.callback_query.message.reply_text("✅ Approved!")
    await context.bot.send_message(uid, "💰 100 RS Added!")

# --- MAIN ---
if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^ADD FUND$"), add_fund_start)],
        states={WAITING_FOR_SS: [CallbackQueryHandler(ask_ss, pattern="^ask_ss$"), MessageHandler(filters.PHOTO, receive_ss)]},
        fallbacks=[],
        per_message=True # Warning fixed
    )

    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("order", order))
    bot.add_handler(CommandHandler("add", admin_add))
    bot.add_handler(conv)
    bot.add_handler(MessageHandler(filters.Regex("^SERVICES$"), handle_services))
    bot.add_handler(MessageHandler(filters.Regex("^MY ACCOUNT$"), my_account))
    bot.add_handler(MessageHandler(filters.Regex("^SUPPORT$"), lambda u,c: u.message.reply_text("Support: @black_Seller16")))
    bot.add_handler(CallbackQueryHandler(cat_callback, pattern="^cat_"))
    bot.add_handler(CallbackQueryHandler(approve_cb, pattern="^app_"))

    bot.run_polling()
