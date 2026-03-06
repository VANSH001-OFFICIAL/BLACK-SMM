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

try:
    with open('services.json', 'r') as f: services = json.load(f)
except: services = {"instagram": [], "youtube": [], "telegram": []}

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
        return await update.message.reply_text("❌ **Join Channel First!**", reply_markup=InlineKeyboardMarkup(kb))
    
    kb = [["SERVICES", "ADD FUND"], ["MY ACCOUNT", "SUPPORT"]]
    await update.message.reply_text("🔥 **SMM PANEL ACTIVE**", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def my_account(update, context):
    c.execute("SELECT balance FROM users WHERE user_id=?", (update.effective_user.id,))
    res = c.fetchone()
    bal = res[0] if res else 0
    await update.message.reply_text(f"👤 ID: `{update.effective_user.id}`\n💰 Balance: {bal} RS", parse_mode='Markdown')

# --- SMART ORDER FUNCTION (FIXED) ---
async def order(update, context):
    args = context.args
    if len(args) < 3:
        return await update.message.reply_text("❌ **Usage:** `/order [id] [link] [qty]`\nExample: `/order 369 https://t.me/link 100`", parse_mode='Markdown')

    try:
        # Strict parsing to avoid "ID/Qty must be numbers" error
        sid = int(args[0])
        link = str(args[1])
        qty = int(args[2])

        found = None
        for cat in services.values():
            for s in cat:
                if s['id'] == sid:
                    found = s
                    break
        
        if not found: return await update.message.reply_text(f"❌ Service ID `{sid}` not found!")

        total = (found['price_per_1000'] / 1000) * qty
        c.execute("SELECT balance FROM users WHERE user_id=?", (update.effective_user.id,))
        res = c.fetchone()
        bal = res[0] if res else 0
        
        if bal < total: return await update.message.reply_text(f"❌ Low Balance!\nCost: {total} RS\nYour Balance: {bal} RS")

        # API Request
        resp = requests.post(API_URL, data={'key': API_KEY, 'action': 'add', 'service': sid, 'link': link, 'quantity': qty}).json()
        
        if 'order' in resp:
            c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (total, update.effective_user.id))
            conn.commit()
            await update.message.reply_text(f"✅ **Order Success!**\n🆔 ID: `{resp['order']}`\n💰 Cost: {total} RS", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ **Panel Error:** {resp.get('error', 'Unknown Error')}")
    except ValueError:
        await update.message.reply_text("❌ **Error:** ID aur Quantity sirf number hone chahiye!")
    except Exception as e:
        await update.message.reply_text(f"❌ **System Error:** {str(e)}")

# --- ADMIN ADD BALANCE (FIXED SEQUENCE) ---
async def admin_add(update, context):
    if update.effective_user.id != ADMIN_ID: return
    try:
        # Format: /add [user_id] [amount]
        uid = int(context.args[0])
        amt = float(context.args[1])
        c.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (uid,))
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, uid))
        conn.commit()
        await update.message.reply_text(f"✅ Added {amt} RS to {uid}")
        await context.bot.send_message(uid, f"💰 **{amt} RS** added to your account!")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ **Usage:** `/add [user_id] [amount]`\nExample: `/add 7117775366 100`")

# --- CONVERSATION HANDLERS ---
async def add_fund_start(update, context):
    await update.message.reply_text("💳 UPI: `vansh59rt@fam`", 
                                   reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("SEND SS ✅", callback_data="ask_ss")]]))
    return WAITING_FOR_SS

async def ask_ss(update, context):
    await update.callback_query.edit_message_text("📸 Send Screenshot now:")
    return WAITING_FOR_SS

async def receive_ss(update, context):
    photo = update.message.photo[-1].file_id
    admin_kb = [[InlineKeyboardButton("Approve ✅", callback_data=f"app_{update.effective_user.id}")]]
    await context.bot.send_photo(ADMIN_ID, photo, caption=f"Deposit Request: `{update.effective_user.id}`", reply_markup=InlineKeyboardMarkup(admin_kb))
    await update.message.reply_text("✅ Sent to admin!")
    return ConversationHandler.END

async def approve_cb(update, context):
    uid = int(update.callback_query.data.split("_")[1])
    c.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (uid,))
    c.execute("UPDATE users SET balance = balance + 100 WHERE user_id = ?", (uid,))
    conn.commit()
    await update.callback_query.message.reply_text(f"✅ Approved 100 RS for {uid}")
    await context.bot.send_message(uid, "💰 **100 RS** added to your account by Admin!")

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot = ApplicationBuilder().token(TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^ADD FUND$"), add_fund_start)],
        states={WAITING_FOR_SS: [CallbackQueryHandler(ask_ss, pattern="^ask_ss$"), MessageHandler(filters.PHOTO, receive_ss)]},
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
