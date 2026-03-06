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

# --- DATABASE ---
conn = sqlite3.connect('bot.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)')
conn.commit()

# --- SERVICES JSON ---
try:
    with open('services.json', 'r') as f: services = json.load(f)
except: services = {"instagram": [], "youtube": [], "telegram": []}

# --- FLASK (Render Support) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is Online!"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- HELPERS ---
async def is_subscribed(update, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL, update.effective_user.id)
        return member.status in ['member', 'administrator', 'creator']
    except: return False

# --- MAIN FUNCTIONS ---
async def start(update, context):
    if not await is_subscribed(update, context):
        kb = [[InlineKeyboardButton("Join Channel 📢", url=f"https://t.me/{CHANNEL.strip('@')}")]]
        return await update.message.reply_text("❌ **Access Denied!**\n\nPehle channel join karein tabhi bot chalega.", 
                                               reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    
    kb = [["SERVICES", "ADD FUND"], ["MY ACCOUNT", "SUPPORT"]]
    await update.message.reply_text("🔥 **Welcome to SMM Panel**\nFast & Cheap Services!", 
                                   reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode='Markdown')

async def my_account(update, context):
    c.execute("SELECT balance FROM users WHERE user_id=?", (update.effective_user.id,))
    res = c.fetchone()
    bal = res[0] if res else 0
    await update.message.reply_text(f"👤 **User ID:** `{update.effective_user.id}`\n💰 **Balance:** {bal} RS", parse_mode='Markdown')

async def handle_services(update, context):
    kb = [[InlineKeyboardButton("Instagram 📸", callback_data="cat_instagram")],
          [InlineKeyboardButton("YouTube 🎥", callback_data="cat_youtube")],
          [InlineKeyboardButton("Telegram ✉️", callback_data="cat_telegram")]]
    await update.message.reply_text("Select Category:", reply_markup=InlineKeyboardMarkup(kb))

async def cat_callback(update, context):
    query = update.callback_query
    cat = query.data.split("_")[1]
    msg = f"🛒 **{cat.upper()} SERVICES:**\n\n"
    for s in services.get(cat, []):
        msg += f"🆔 `{s['id']}` - {s['name']}\n💵 {s['price_per_1000']} RS/1k\n\n"
    await query.message.reply_text(msg + "Format: `/order [id] [link] [qty]`", parse_mode='Markdown')

# --- FIXED ORDER FUNCTION ---
async def order(update, context):
    if len(context.args) < 3:
        return await update.message.reply_text("❌ **Format Galat Hai!**\nSahi Format: `/order [id] [link] [qty]`\nExample: `/order 369 https://t.me/link 100`", parse_mode='Markdown')

    try:
        sid, link, qty = int(context.args[0]), str(context.args[1]), int(context.args[2])
        found = next((s for cat in services.values() for s in cat if s['id'] == sid), None)
        
        if not found: return await update.message.reply_text("❌ Service ID invalid hai!")

        total = (found['price_per_1000'] / 1000) * qty
        c.execute("SELECT balance FROM users WHERE user_id=?", (update.effective_user.id,))
        res = c.fetchone()
        bal = res[0] if res else 0
        
        if bal < total: return await update.message.reply_text(f"❌ Low Balance! Cost: {total} RS\nYour Balance: {bal} RS")

        # API Request
        resp = requests.post(API_URL, data={'key': API_KEY, 'action': 'add', 'service': sid, 'link': link, 'quantity': qty}).json()
        
        if 'order' in resp:
            c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (total, update.effective_user.id))
            conn.commit()
            await update.message.reply_text(f"✅ **Order Placed!**\n🆔 Order ID: `{resp['order']}`\n💰 Cost: {total} RS", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ **Panel Error:** {resp.get('error', 'Unknown Error')}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: Check your inputs! (ID/Qty must be numbers)")

# --- ADD FUND ---
async def add_fund_start(update, context):
    await update.message.reply_text("💳 **UPI ID:** `vansh59rt@fam`\n\nPayment karne ke baad screenshot bhejne ke liye niche button dabayein:", 
                                   reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("SEND SS ✅", callback_data="ask_ss")]]), parse_mode='Markdown')
    return WAITING_FOR_SS

async def ask_ss(update, context):
    await update.callback_query.edit_message_text("📸 **Ab Screenshot Send Karein:**", 
                                                 reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("CANCEL ❌", callback_data="cancel_ss")]]), parse_mode='Markdown')
    return WAITING_FOR_SS

async def receive_ss(update, context):
    photo = update.message.photo[-1].file_id
    admin_kb = [[InlineKeyboardButton("Approve ✅", callback_data=f"app_{update.effective_user.id}")]]
    await context.bot.send_photo(ADMIN_ID, photo, caption=f"Deposit Req from `{update.effective_user.id}`", 
                                 reply_markup=InlineKeyboardMarkup(admin_kb), parse_mode='Markdown')
    await update.message.reply_text("✅ Admin ko screenshot bhej diya gaya hai!")
    return ConversationHandler.END

# --- ADMIN CMDS ---
async def admin_add(update, context):
    if update.effective_user.id != ADMIN_ID: return
    uid, amt = int(context.args[0]), float(context.args[1])
    c.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (uid,))
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, uid))
    conn.commit()
    await update.message.reply_text(f"✅ Added {amt} to {uid}")

async def approve_cb(update, context):
    uid = update.callback_query.data.split("_")[1]
    c.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (uid,))
    c.execute("UPDATE users SET balance = balance + 100 WHERE user_id = ?", (uid,))
    conn.commit()
    await update.callback_query.message.reply_text(f"Approved for {uid}")
    await context.bot.send_message(uid, "💰 **100 RS Added to your wallet!**", parse_mode='Markdown')

# --- START BOT ---
if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^ADD FUND$"), add_fund_start)],
        states={WAITING_FOR_SS: [CallbackQueryHandler(ask_ss, pattern="^ask_ss$"), 
                                 CallbackQueryHandler(lambda u,c: ConversationHandler.END, pattern="^cancel_ss$"),
                                 MessageHandler(filters.PHOTO, receive_ss)]},
        fallbacks=[]
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
