import os, json, sqlite3, threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, CallbackQueryHandler, 
                          MessageHandler, filters, ContextTypes, ConversationHandler)

TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 7117775366
PAYOUT_CHANNEL = "@BLACKSMM_PAYOUT"
CHANNEL_USER = "@verifiedpaisabots"

# Database
conn = sqlite3.connect('bot.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)')
conn.commit()

# Flask for Render Port
app = Flask(__name__)
@app.route('/')
def home(): return "Bot Online"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

# Channel Check
async def is_joined(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USER, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except: return False

# Handlers
async def start(update, context):
    if not await is_joined(update.effective_user.id, context):
        kb = [[InlineKeyboardButton("Join Channel 📢", url=f"https://t.me/{CHANNEL_USER.strip('@')}"), 
               InlineKeyboardButton("Check Join ✅", callback_data="check_join")]]
        return await update.message.reply_text("❌ Pehle channel join karein!", reply_markup=InlineKeyboardMarkup(kb))
    
    kb = [["SERVICES", "ADD FUND"], ["MY ACCOUNT", "SUPPORT"]]
    await update.message.reply_text("🔥 **SMM Panel Active**", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def check_join(update, context):
    if await is_joined(update.effective_user.id, context):
        await update.callback_query.message.edit_text("✅ Join verified! /start type karein.")
    else:
        await update.callback_query.answer("❌ Abhi tak join nahi kiya!")

# Services UI
async def show_services(update, context):
    with open('services.json', 'r') as f: data = json.load(f)
    kb = [[InlineKeyboardButton("Instagram 📸", callback_data="show_instagram")],
          [InlineKeyboardButton("YouTube 🎥", callback_data="show_youtube")],
          [InlineKeyboardButton("Telegram ✉️", callback_data="show_telegram")]]
    await update.message.reply_text("Select Category:", reply_markup=InlineKeyboardMarkup(kb))

async def show_category(update, context):
    with open('services.json', 'r') as f: data = json.load(f)
    cat = update.callback_query.data.split("_")[1]
    msg = f"🛒 **{cat.upper()} SERVICES:**\n"
    for s in data.get(cat, []):
        msg += f"🆔 `{s['id']}` - {s['name']} | 💵 {s['price_per_1000']} RS/1k\n"
    await update.callback_query.message.edit_text(msg + "\nFormat: /order [id] [link] [qty]", parse_mode='Markdown')

# Admin & Account
async def admin_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    action, uid, amt = context.args[0], int(context.args[1]), float(context.args[2])
    if action == "add": c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, uid))
    elif action == "remove": c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amt, uid))
    conn.commit()
    await update.message.reply_text(f"✅ {action.upper()} successful for {uid}")

async def my_account(update, context):
    c.execute("SELECT balance FROM users WHERE user_id=?", (update.effective_user.id,))
    res = c.fetchone()
    await update.message.reply_text(f"👤 ID: `{update.effective_user.id}`\n💰 Balance: {res[0] if res else 0} RS")

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    bot = ApplicationBuilder().token(TOKEN).build()
    
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("admin", admin_cmd))
    bot.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
    bot.add_handler(CallbackQueryHandler(show_category, pattern="^show_"))
    bot.add_handler(MessageHandler(filters.Regex("^SERVICES$"), show_services))
    bot.add_handler(MessageHandler(filters.Regex("^MY ACCOUNT$"), my_account))
    bot.add_handler(MessageHandler(filters.Regex("^SUPPORT$"), lambda u,c: u.message.reply_text("📞 @BLACK_SELLER16")))
    
    bot.run_polling()
