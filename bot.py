import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = 123456789

CHANNEL = "@verifiedpaisabots"
ORDER_LOG_CHANNEL = "@blacksmm_payout"

users = {}
orders = []
revenue = 0

logging.basicConfig(level=logging.INFO)

# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    user_id = user.id

    users[user_id] = users.get(user_id, {"balance": 0})

    try:
        member = await context.bot.get_chat_member(CHANNEL, user_id)

        if member.status in ["member", "administrator", "creator"]:
            await main_menu(update)

        else:
            raise Exception()

    except:

        keyboard = [
            [InlineKeyboardButton("📢 JOIN CHANNEL", url="https://t.me/verifiedpaisabots")],
            [InlineKeyboardButton("✅ VERIFY", callback_data="verify")]
        ]

        await update.message.reply_text(
            "*🚫 Access Restricted*\n\n"
            "First join our official channel to use this bot.",
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ---------------- VERIFY ----------------

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    user_id = query.from_user.id

    try:
        member = await context.bot.get_chat_member(CHANNEL, user_id)

        if member.status in ["member", "administrator", "creator"]:
            await query.message.delete()
            await main_menu_query(query)

        else:
            await query.answer("Join the channel first!", show_alert=True)

    except:
        await query.answer("Join channel first!", show_alert=True)

# ---------------- MAIN MENU ----------------

async def main_menu(update: Update):

    keyboard = [
        [
            InlineKeyboardButton("🛒 SERVICES", callback_data="services"),
            InlineKeyboardButton("💳 ADD FUND", callback_data="fund")
        ],
        [
            InlineKeyboardButton("👤 MY ACCOUNT", callback_data="account"),
            InlineKeyboardButton("🎧 SUPPORT", url="https://t.me/your_support")
        ]
    ]

    text = (
        "*🚀 ULTIMATE SMM PANEL BOT*\n\n"
        "Fast Social Media Services\n"
        "Instant Orders • Cheap Price\n\n"
        "*Choose an option below:*"
    )

    await update.message.reply_text(
        text,
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def main_menu_query(query):

    keyboard = [
        [
            InlineKeyboardButton("🛒 SERVICES", callback_data="services"),
            InlineKeyboardButton("💳 ADD FUND", callback_data="fund")
        ],
        [
            InlineKeyboardButton("👤 MY ACCOUNT", callback_data="account"),
            InlineKeyboardButton("🎧 SUPPORT", url="https://t.me/your_support")
        ]
    ]

    text = (
        "*🚀 ULTIMATE SMM PANEL BOT*\n\n"
        "Fast Social Media Services\n"
        "Instant Orders • Cheap Price\n\n"
        "*Choose an option below:*"
    )

    await query.message.reply_text(
        text,
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------- SERVICES ----------------

async def services(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    text = (
        "*📦 AVAILABLE SERVICES*\n\n"
        "Instagram Followers\n"
        "Instagram Likes\n"
        "YouTube Views\n"
        "Telegram Members\n\n"
        "_Send link to place order_"
    )

    await query.message.reply_text(text, parse_mode="MarkdownV2")

# ---------------- ACCOUNT ----------------

async def account(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    user_id = query.from_user.id

    balance = users[user_id]["balance"]

    text = (
        "*👤 YOUR ACCOUNT*\n\n"
        f"*User ID:* `{user_id}`\n"
        f"*Balance:* ₹{balance}\n\n"
        "Use Add Fund to recharge"
    )

    await query.message.reply_text(text, parse_mode="MarkdownV2")

# ---------------- ADMIN COMMANDS ----------------

async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    user_id = int(context.args[0])
    amount = int(context.args[1])

    users[user_id]["balance"] += amount

    await update.message.reply_text("Balance added successfully")

async def remove_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    user_id = int(context.args[0])
    amount = int(context.args[1])

    users[user_id]["balance"] -= amount

    await update.message.reply_text("Balance removed")

async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(f"Total Users: {len(users)}")

async def orders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(f"Total Orders: {len(orders)}")

async def revenue_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(f"Revenue: ₹{revenue}")

# ---------------- BROADCAST ----------------

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    text = " ".join(context.args)

    sent = 0

    for user_id in users:

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="MarkdownV2"
            )

            sent += 1

        except:
            pass

    await update.message.reply_text(f"Broadcast sent to {sent} users")

# ---------------- HANDLERS ----------------

def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.add_handler(CommandHandler("addbalance", add_balance))
    app.add_handler(CommandHandler("removebalance", remove_balance))

    app.add_handler(CommandHandler("users", users_cmd))
    app.add_handler(CommandHandler("orders", orders_cmd))
    app.add_handler(CommandHandler("revenue", revenue_cmd))

    app.add_handler(CallbackQueryHandler(verify, pattern="verify"))
    app.add_handler(CallbackQueryHandler(services, pattern="services"))
    app.add_handler(CallbackQueryHandler(account, pattern="account"))

    print("BOT RUNNING")

    app.run_polling()

if __name__ == "__main__":
    main()

