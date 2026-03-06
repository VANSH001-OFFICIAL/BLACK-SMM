import os, sqlite3, threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, CallbackQueryHandler, 
                          MessageHandler, filters, ContextTypes, ConversationHandler)

# --- CONFIG ---
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 7117775366
CHANNEL = "@VERIFIEDPAISABOTS"
PAYOUT_CHANNEL = "@BLACKSMM_PAYOUT"
ASK_AMT = 2 

# --- FLASK (Render Port Binding Fix) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is Online!"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# --- DATABASE ---
conn = sqlite3.connect('bot.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)')
conn.commit()

# --- HELPERS ---
async def start(update, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL, update.effective_user.id)
        if member.status not in ['member', 'administrator', 'creator']:
            kb = [[InlineKeyboardButton("Join Channel 📢", url=f"https://t.me/{CHANNEL.strip('@')}")]];
            return await update.message.reply_text("❌ Pehle channel join karein!", reply_markup=InlineKeyboardMarkup(kb))
    except: return await update.message.reply_text(f"❌ Join {CHANNEL} first!")
    
    kb = [["SERVICES", "ADD FUND"], ["MY ACCOUNT", "SUPPORT"]]
    await update.message.reply_text("🔥 **SMM Panel Active**", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def my_account(update, context):
    c.execute("SELECT balance FROM users WHERE user_id=?", (update.effective_user.id,))
    res = c.fetchone()
    bal = res[0] if res else 0
    await update.message.reply_text(f"👤 ID: `{update.effective_user.id}`\n💰 Balance: {bal} RS", parse_mode='Markdown')

async def order(update, context):
    if len(context.args) < 3: return await update.message.reply_text("❌ Format: `/order [id] [link] [qty]`")
    c.execute("SELECT balance FROM users WHERE user_id=?", (update.effective_user.id,))
    bal = (c.fetchone() or (0,))[0]
    msg = f"📩 **New Order Request**\n\n🆔 User: `{update.effective_user.id}`\n📦 Service: `{context.args[0]}`\n🔗 Link: `{context.args[1]}`\n🔢 Qty: `{context.args[2]}`\n💰 Bal: {bal} RS"
    await context.bot.send_message(PAYOUT_CHANNEL, msg, parse_mode='Markdown')
    await update.message.reply_text("✅ Order request admin ko bhej di gayi hai!")

# --- ADD FUND CONVERSATION ---
async def add_fund_start(update, context):
    await update.message.reply_text("💳 UPI: `vansh59rt@fam`\nScreenshot send karein:")
    return 1

async def receive_ss(update, context):
    photo = update.message.photo[-1].file_id
    kb = [[InlineKeyboardButton("Approve ✅", callback_data=f"ask_amt_{update.effective_user.id}")]]
    await context.bot.send_photo(ADMIN_ID, photo, caption=f"Deposit req: `{update.effective_user.id}`", reply_markup=InlineKeyboardMarkup(kb))
    await update.message.reply_text("✅ Request sent to Admin!")
    return ConversationHandler.END

async def ask_amt(update, context):
    uid = update.callback_query.data.split("_")[2]
    context.user_data['target_uid'] = uid
    await update.callback_query.message.reply_text(f"💰 Kitna amount add karna hai ({uid})?")
    return ASK_AMT

async def process_dynamic_amt(update, context):
    amt = float(update.message.text)
    uid = context.user_data['target_uid']
    c.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (uid,))
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, uid))
    conn.commit()
    await update.message.reply_text(f"✅ {amt} RS added to {uid}")
    await context.bot.send_message(uid, f"💰 {amt} RS added by Admin!")
    return ConversationHandler.END

# --- EXECUTION ---
if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot = ApplicationBuilder().token(TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO, receive_ss)],
        states={1: [MessageHandler(filters.PHOTO, receive_ss)],
                ASK_AMT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_dynamic_amt)]},
        fallbacks=[]
    )
    
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("order", order))
    bot.add_handler(CallbackQueryHandler(ask_amt, pattern="^ask_amt_"))
    bot.add_handler(conv)
    bot.add_handler(MessageHandler(filters.Regex("^ADD FUND$"), add_fund_start))
    bot.add_handler(MessageHandler(filters.Regex("^MY ACCOUNT$"), my_account))
    bot.run_polling()
