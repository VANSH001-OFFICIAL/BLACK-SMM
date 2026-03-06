import os, json, sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, CallbackQueryHandler, 
                          MessageHandler, filters, ConversationHandler)

# CONFIG
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 7117775366
CHANNEL = "@verifiedpaisabots"

# DB
conn = sqlite3.connect('bot.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)')
conn.commit()

with open('services.json', 'r') as f: SERVICES = json.load(f)

# --- BOT LOGIC ---
async def start(update, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL, update.effective_user.id)
        if member.status not in ['member', 'administrator', 'creator']:
            await update.message.reply_text(f"❌ Join {CHANNEL} first!")
            return
    except: pass
    
    kb = [["SERVICES", "ADD FUND"], ["MY ACCOUNT", "SUPPORT"]]
    await update.message.reply_text("🔥 **SMM Panel Active**", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def order(update, context):
    if len(context.args) < 3: return await update.message.reply_text("❌ Format: `/order [id] [link] [qty]`")
    sid, link, qty = int(context.args[0]), str(context.args[1]), int(context.args[2])
    
    # Auto Calc
    s = next((item for cat in SERVICES.values() for item in cat if item['id'] == sid), None)
    if not s: return await update.message.reply_text("❌ Invalid ID!")
    
    cost = (s['price_per_1000'] / 1000) * qty
    c.execute("SELECT balance FROM users WHERE user_id=?", (update.effective_user.id,))
    bal = c.fetchone()[0]
    
    if bal < cost: return await update.message.reply_text(f"❌ Low balance! Cost: {cost:.2f} RS")
    
    c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (cost, update.effective_user.id))
    conn.commit()
    await update.message.reply_text(f"✅ Order Placed! {cost:.2f} RS deducted.")

async def admin_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    action, uid, amt = context.args[0], int(context.args[1]), float(context.args[2])
    c.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (uid,))
    c.execute(f"UPDATE users SET balance = balance {'+' if action == 'add' else '-'} ? WHERE user_id = ?", (amt, uid))
    conn.commit()
    await update.message.reply_text(f"✅ {action.upper()} {amt} to {uid}")

# --- HANDLER SETUP ---
if __name__ == '__main__':
    bot = ApplicationBuilder().token(TOKEN).build()
    
    # Add handlers
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("order", order))
    bot.add_handler(CommandHandler("admin", admin_cmd))
    bot.add_handler(MessageHandler(filters.Regex("^SERVICES$"), lambda u,c: u.message.reply_text("Choose Category", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Insta", callback_data="show_instagram")]]))))
    bot.add_handler(MessageHandler(filters.Regex("^MY ACCOUNT$"), lambda u,c: c.bot.send_message(u.effective_chat.id, f"Balance: {c.bot.get_chat_member(u.effective_chat.id, u.effective_user.id)}"))) # Placeholder
    # (Add remaining standard handlers here)
    bot.run_polling()
