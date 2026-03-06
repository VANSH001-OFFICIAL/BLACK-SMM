import os, sqlite3, threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, CallbackQueryHandler, 
                          MessageHandler, filters, ContextTypes, ConversationHandler)

# --- CONFIG ---
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 7117775366
PAYOUT_CHANNEL = "@BLACKSMM_PAYOUT"

# --- FLASK (Render Port Fix) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot Online"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- DB ---
conn = sqlite3.connect('bot.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)')
conn.commit()

# --- SERVICES DATA ---
SERVICES_DATA = {
    "insta": "📸 **INSTAGRAM SERVICES:**\n\n🆔 3487 - REEL VIEWS - 2RS/10k\n🆔 2456 - REEL VIEWS+REACH - 5RS/1k\n🆔 3344 - LIKES - 10RS/1k\n🆔 3428 - FOLLOWERS - 35RS/1k",
    "yt": "🎥 **YOUTUBE SERVICES:**\n\n🆔 2015 - LIKES - 8RS/1k\n🆔 3371 - VIEWS [0 DROP] - 51RS/1k",
    "tg": "✉️ **TELEGRAM SERVICES:**\n\n🆔 2737 - MEMBERS [NON-DROP] - 20RS/1k\n🆔 2779 - VIEWS [SINGLE] - 1RS/1k\n🆔 3161 - VIEWS [LAST 5] - 1.5RS/1k\n🆔 369 - REACTS [POS] - 7RS/1k (Min:10)\n🆔 397 - REACTS [NEG] - 7RS/1k\n\n⚠️ *Baki sabka min: 1000*\nContact @BLACK_SELLER16 for others."
}

# --- HANDLERS ---
async def start(update, context):
    kb = [["SERVICES", "ADD FUND"], ["MY ACCOUNT", "SUPPORT"]]
    await update.message.reply_text("🔥 **SMM Panel Active**", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def show_services(update, context):
    kb = [
        [InlineKeyboardButton("Instagram 📸", callback_data="show_insta")],
        [InlineKeyboardButton("YouTube 🎥", callback_data="show_yt")],
        [InlineKeyboardButton("Telegram ✉️", callback_data="show_tg")]
    ]
    await update.message.reply_text("Select Category:", reply_markup=InlineKeyboardMarkup(kb))

async def category_callback(update, context):
    query = update.callback_query
    cat = query.data.split("_")[1]
    await query.answer()
    await query.message.edit_text(SERVICES_DATA.get(cat, "Error!"), parse_mode='Markdown')
    await query.message.reply_text("Format: `/order [id] [link] [qty]`")

# --- ORDER REQUEST ---
async def order(update, context):
    if len(context.args) < 3: return await update.message.reply_text("❌ Format: `/order [id] [link] [qty]`")
    c.execute("SELECT balance FROM users WHERE user_id=?", (update.effective_user.id,))
    bal = (c.fetchone() or (0,))[0]
    
    # Request forward to channel
    msg = f"📩 **New Order Request**\n\n🆔 User: `{update.effective_user.id}`\n📦 Service: `{context.args[0]}`\n🔗 Link: `{context.args[1]}`\n🔢 Qty: `{context.args[2]}`\n💰 Bal: {bal} RS"
    await context.bot.send_message(PAYOUT_CHANNEL, msg, parse_mode='Markdown')
    await update.message.reply_text("✅ Order request admin ko bhej di gayi hai!")

# --- ADD FUND ---
async def add_fund_menu(update, context):
    kb = [[InlineKeyboardButton("SEND SS ✅", callback_data="send_ss")]]
    await update.message.reply_text("💳 UPI: `vansh59rt@fam`\nClick button below:", reply_markup=InlineKeyboardMarkup(kb))

async def handle_ss(update, context):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("📸 Send Screenshot now:")
    return 1

async def receive_ss(update, context):
    photo = update.message.photo[-1].file_id
    kb = [[InlineKeyboardButton("Approve ✅", callback_data=f"ask_amt_{update.effective_user.id}")]]
    await context.bot.send_photo(ADMIN_ID, photo, caption=f"Deposit req: `{update.effective_user.id}`", reply_markup=InlineKeyboardMarkup(kb))
    await update.message.reply_text("✅ Admin ko request bhej di gayi hai!")
    return ConversationHandler.END

async def ask_amt(update, context):
    uid = update.callback_query.data.split("_")[2]
    context.user_data['target_uid'] = uid
    await update.callback_query.message.reply_text(f"💰 {uid} ke liye amount dalen:")
    return 2

async def process_amt(update, context):
    amt = float(update.message.text)
    uid = context.user_data['target_uid']
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, uid))
    conn.commit()
    await update.message.reply_text(f"✅ {amt} RS added!")
    await context.bot.send_message(uid, f"💰 Admin ne {amt} RS add kar diye!")
    return ConversationHandler.END

# --- RUN ---
if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot = ApplicationBuilder().token(TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_ss, pattern="send_ss")],
        states={1: [MessageHandler(filters.PHOTO, receive_ss)], 2: [MessageHandler(filters.TEXT, process_amt)]},
        fallbacks=[]
    )
    
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("order", order))
    bot.add_handler(CallbackQueryHandler(ask_amt, pattern="^ask_amt_"))
    bot.add_handler(CallbackQueryHandler(category_callback, pattern="^show_"))
    bot.add_handler(conv)
    bot.add_handler(MessageHandler(filters.Regex("^SERVICES$"), show_services))
    bot.add_handler(MessageHandler(filters.Regex("^ADD FUND$"), add_fund_menu))
    bot.run_polling()
