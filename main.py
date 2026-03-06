import os, json, sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 7117775366
PAYOUT_CHANNEL = "@BLACKSMM_PAYOUT"

# Database
conn = sqlite3.connect('bot.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)')
conn.commit()

# Load Data
with open('services.json', 'r') as f: SERVICES = json.load(f)

# --- UTILS ---
def get_service_by_id(sid):
    for cat in SERVICES.values():
        for s in cat:
            if s['id'] == sid: return s
    return None

# --- HANDLERS ---
async def start(update, context):
    kb = [["SERVICES", "ADD FUND"], ["MY ACCOUNT", "SUPPORT"]]
    await update.message.reply_text("🔥 **SMM Panel Active**", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def show_services(update, context):
    kb = [[InlineKeyboardButton("Instagram 📸", callback_data="show_instagram")],
          [InlineKeyboardButton("YouTube 🎥", callback_data="show_youtube")],
          [InlineKeyboardButton("Telegram ✉️", callback_data="show_telegram")]]
    await update.message.reply_text("Select Category:", reply_markup=InlineKeyboardMarkup(kb))

async def show_category(update, context):
    cat = update.callback_query.data.split("_")[1]
    msg = f"🛒 **{cat.upper()} SERVICES:**\n"
    for s in SERVICES.get(cat, []):
        msg += f"🆔 `{s['id']}` - {s['name']} | 💵 {s['price_per_1000']} RS/1k (Min: {s['min_qty']})\n"
    await update.callback_query.message.edit_text(msg + "\nFormat: /order [id] [link] [qty]", parse_mode='Markdown')

async def order(update, context):
    if len(context.args) < 3: return await update.message.reply_text("❌ Format: `/order [id] [link] [qty]`")
    sid, link, qty = int(context.args[0]), str(context.args[1]), int(context.args[2])
    
    s = get_service_by_id(sid)
    if not s or qty < s['min_qty']: return await update.message.reply_text("❌ Invalid ID ya Min Qty kam hai!")
    
    cost = (s['price_per_1000'] / 1000) * qty
    c.execute("SELECT balance FROM users WHERE user_id=?", (update.effective_user.id,))
    bal = c.fetchone()
    bal = bal[0] if bal else 0
    
    if bal < cost: return await update.message.reply_text(f"❌ Low balance! Cost: {cost:.2f} RS, Your: {bal} RS")
    
    c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (cost, update.effective_user.id))
    conn.commit()
    await context.bot.send_message(PAYOUT_CHANNEL, f"📩 **New Order**\nUser: `{update.effective_user.id}`\nID: `{sid}`\nQty: `{qty}`\nLink: `{link}`", parse_mode='Markdown')
    await update.message.reply_text(f"✅ Order done! {cost:.2f} RS deducted.")

# --- PAYMENT FLOW (Fixed) ---
async def add_fund(update, context):
    await update.message.reply_text("💳 UPI: `vansh59rt@fam`\nScreenshot bhejein:")
    return 1

async def receive_ss(update, context):
    photo = update.message.photo[-1].file_id
    kb = [[InlineKeyboardButton("Approve ✅", callback_data=f"ask_{update.effective_user.id}")]]
    await context.bot.send_photo(ADMIN_ID, photo, caption=f"Deposit req: `{update.effective_user.id}`", reply_markup=InlineKeyboardMarkup(kb))
    await update.message.reply_text("✅ Admin ko request bhej di gayi hai.")
    return ConversationHandler.END

async def ask_amt(update, context):
    uid = update.callback_query.data.split("_")[1]
    context.user_data['uid'] = uid
    await update.callback_query.message.reply_text(f"💰 Amount enter karein for {uid}:")
    return 2

async def process_amt(update, context):
    try:
        amt = float(update.message.text)
        uid = context.user_data.get('uid')
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, uid))
        conn.commit()
        await update.message.reply_text(f"✅ {amt} RS added.")
        await context.bot.send_message(uid, f"💰 {amt} RS added by Admin!")
        return ConversationHandler.END
    except:
        await update.message.reply_text("❌ Error! Amount number mein likhein.")
        return 2

if __name__ == '__main__':
    bot = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^ADD FUND$"), add_fund)],
        states={1: [MessageHandler(filters.PHOTO, receive_ss)], 2: [MessageHandler(filters.TEXT, process_amt)]},
        fallbacks=[]
    )
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("order", order))
    bot.add_handler(CallbackQueryHandler(show_category, pattern="^show_"))
    bot.add_handler(CallbackQueryHandler(ask_amt, pattern="^ask_"))
    bot.add_handler(MessageHandler(filters.Regex("^SERVICES$"), show_services))
    bot.add_handler(conv)
    bot.run_polling()
