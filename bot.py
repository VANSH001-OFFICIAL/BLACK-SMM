import json
import logging
import os
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------------- CONFIG ---------------- #

TOKEN = "8677165936:AAH0D0urU-FRv3L0eL4BhxoWV8dIg7OL8Yw"
ADMIN_ID = 7117775366
FORCE_CHANNEL = "@verifiedpaisabots"
UPI_ID = "vansh59rt@fam"
ORDER_CHANNEL = "@blacksmm_payout"

# ---------------------------------------- #

logging.basicConfig(level=logging.INFO)

users = {}
orders = []
awaiting_screenshot = {}
broadcast_mode = False

# ---------- PORT BINDING (Render fix) ---------- #

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ---------- FORCE JOIN CHECK ---------- #

async def check_join(bot, user_id):
    try:
        member = await bot.get_chat_member(FORCE_CHANNEL, user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except:
        pass
    return False

def join_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url="https://t.me/verifiedpaisabots")],
        [InlineKeyboardButton("✅ Verify", callback_data="verify_join")]
    ])

# ---------- MAIN MENU ---------- #

def main_menu():
    keyboard = [
        [
            InlineKeyboardButton("🛒 SERVICES", callback_data="services"),
            InlineKeyboardButton("💳 ADD FUND", callback_data="addfund")
        ],
        [
            InlineKeyboardButton("👤 MY ACCOUNT", callback_data="account"),
            InlineKeyboardButton("🛠 SUPPORT", url="https://t.me/black_seller16")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ---------- START ---------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id

    if uid not in users:
        users[uid] = {"balance": 0}

    joined = await check_join(context.bot, uid)

    if not joined:
        await update.message.reply_text(
            "⚠️ *First join our channel to use the bot*",
            parse_mode="Markdown",
            reply_markup=join_keyboard()
        )
        return

    await update.message.reply_text(
        "🚀 *Welcome to SMM Bot*\n\nSelect an option:",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

# ---------- VERIFY ---------- #

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id

    joined = await check_join(context.bot, uid)

    if not joined:
        await query.answer("Join channel first", show_alert=True)
        return

    await query.message.delete()

    await context.bot.send_message(
        uid,
        "✅ *Verified Successfully*\n\nWelcome to the bot",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

# ---------- SERVICES ---------- #

async def services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    with open("services.json") as f:
        data = json.load(f)

    keyboard = []

    for category in data:
        keyboard.append([
            InlineKeyboardButton(category.upper(), callback_data=f"cat_{category}")
        ])

    await query.message.reply_text(
        "📦 *AVAILABLE SERVICES*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- SHOW CATEGORY ---------- #

async def category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat = query.data.split("_")[1]

    with open("services.json") as f:
        data = json.load(f)

    text = f"*{cat.upper()} SERVICES*\n\n"

    for s in data[cat]:
        text += f"• {s['name']}\nPrice: ₹{s['price_per_1000']} / 1000\nMin: {s['min_qty']}\n\n"

    text += "_Send link to place order_"

    await query.message.reply_text(text, parse_mode="Markdown")

# ---------- ADD FUND ---------- #

async def add_fund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("📤 Submit Screenshot", callback_data="submit_ss")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ]

    text = f"""
💳 *ADD FUNDS*

Send payment to UPI:

`{UPI_ID}`

After payment click *Submit Screenshot*
"""

    await query.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- SUBMIT SCREENSHOT ---------- #

async def submit_ss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    awaiting_screenshot[query.from_user.id] = True

    await query.message.reply_text(
        "📸 Send payment screenshot now\n\nPress /cancel to stop"
    )

# ---------- RECEIVE SCREENSHOT ---------- #

async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id

    if uid not in awaiting_screenshot:
        return

    photo = update.message.photo[-1].file_id

    await context.bot.send_photo(
        chat_id=ORDER_CHANNEL,
        photo=photo,
        caption=f"💰 Payment Screenshot\nUser: {uid}"
    )

    del awaiting_screenshot[uid]

    await update.message.reply_text("✅ Screenshot submitted for review")

# ---------- ACCOUNT ---------- #

async def account(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    uid = query.from_user.id
    balance = users[uid]["balance"]

    text = f"""
👤 *MY ACCOUNT*

User ID: `{uid}`
Balance: ₹{balance}

Use Add Fund to recharge
"""

    await query.message.reply_text(text, parse_mode="Markdown")

# ---------- BROADCAST ---------- #

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    global broadcast_mode
    broadcast_mode = True

    await update.message.reply_text("Send message to broadcast")

async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global broadcast_mode

    if not broadcast_mode:
        return

    for uid in users:
        try:
            await context.bot.send_message(uid, update.message.text)
        except:
            pass

    broadcast_mode = False

    await update.message.reply_text("Broadcast sent")

# ---------- ADMIN COMMANDS ---------- #

async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    uid = int(context.args[0])
    amt = int(context.args[1])

    users[uid]["balance"] += amt

    await update.message.reply_text("Balance added")

async def remove_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    uid = int(context.args[0])
    amt = int(context.args[1])

    users[uid]["balance"] -= amt

    await update.message.reply_text("Balance removed")

async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(f"Total users: {len(users)}")

# ---------- MAIN ---------- #

def main():

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("addbalance", add_balance))
    application.add_handler(CommandHandler("removebalance", remove_balance))
    application.add_handler(CommandHandler("users", users_cmd))

    application.add_handler(CallbackQueryHandler(verify, pattern="verify_join"))
    application.add_handler(CallbackQueryHandler(services, pattern="services"))
    application.add_handler(CallbackQueryHandler(category, pattern="cat_"))
    application.add_handler(CallbackQueryHandler(add_fund, pattern="addfund"))
    application.add_handler(CallbackQueryHandler(submit_ss, pattern="submit_ss"))

    application.add_handler(MessageHandler(filters.PHOTO, photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_send))

    import threading
    threading.Thread(target=run_web).start()

    application.run_polling()

if __name__ == "__main__":
    main()
