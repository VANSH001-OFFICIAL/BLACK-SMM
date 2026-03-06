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

# --- HANDLERS ---
async def start(update, context):
    kb = [["SERVICES", "ADD FUND"], ["MY ACCOUNT", "SUPPORT"]]
    await update.message.reply_text("🔥 **SMM Panel Active**", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def show_services(update, context):
    # Static Manual Services
    await update.message.reply_text("🛒 **OUR SERVICES:**\n\n🆔 2737 - Telegram Members\n💵 20 RS/1k\n\n🆔 2779 - Telegram Views\n💵 1 RS/1k\n\nFormat: /order [id] [link] [qty]")

async def add_fund_menu(update, context):
    kb = [[InlineKeyboardButton("SEND SS ✅", callback_data="send_ss")]]
    await update.message.reply_text("💳 UPI: `vansh59rt@fam`\nClick button to send Screenshot:", reply_markup=InlineKeyboardMarkup(kb))

async def handle_ss(update, context):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("📸 Please send the screenshot image now:")
    return 1

async def receive_ss(update, context):
    photo = update.message.photo[-1].file_id
    kb = [[InlineKeyboardButton("Approve ✅", callback_data=f"ask_amt_{update.effective_user.id}")]]
    await context.bot.send_photo(ADMIN_ID, photo, caption=f"Deposit req from: `{update.effective_user.id}`", reply_markup=InlineKeyboardMarkup(kb))
    await update.message.reply_text("✅ Admin ko request bhej di gayi hai!")
    return ConversationHandler.END

# --- DYNAMIC APPROVAL ---
async def ask_amt(update, context):
    uid = update.callback_query.data.split("_")[2]
    context.user_data['target_uid'] = uid
    await update.callback_query.message.reply_text(f"💰 {uid} ke liye kitna paisa add karna hai?")
    return 2

async def process_amt(update, context):
    amt = float(update.message.text)
    uid = context.user_data['target_uid']
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, uid))
    conn.commit()
    await update.message.reply_text(f"✅ {amt} RS added to {uid}")
    await context.bot.send_message(uid, f"💰 Admin ne {amt} RS add kar diye!")
    return ConversationHandler.END

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot = ApplicationBuilder().token(TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_ss, pattern="send_ss")],
        states={1: [MessageHandler(filters.PHOTO, receive_ss)], 2: [MessageHandler(filters.TEXT, process_amt)]},
        fallbacks=[]
    )
    
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(conv)
    bot.add_handler(CallbackQueryHandler(ask_amt, pattern="^ask_amt_"))
    bot.add_handler(MessageHandler(filters.Regex("^SERVICES$"), show_services))
    bot.add_handler(MessageHandler(filters.Regex("^ADD FUND$"), add_fund_menu))
    bot.run_polling()
