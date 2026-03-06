import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv('BOT_TOKEN')

UPI_ID = "vansh59rt@fam"
SUPPORT = "@black_seller16"

user_balance = {}

# load services
with open("services.json") as f:
    services = json.load(f)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [InlineKeyboardButton("💰 Add Funds", callback_data="addfunds")],
        [InlineKeyboardButton("📊 Services", callback_data="services")],
        [InlineKeyboardButton("👤 My Account", callback_data="account")],
        [InlineKeyboardButton("🛠 Support", callback_data="support")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Welcome to SMM Bot", reply_markup=reply_markup)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "addfunds":

        keyboard = [
            [InlineKeyboardButton("📤 Submit SS", callback_data="submit_ss")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
        ]

        await query.message.reply_text(
            f"Send payment to UPI:\n\n{UPI_ID}\n\nAfter payment click Submit SS",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "submit_ss":
        await query.message.reply_text("Please send your payment screenshot.")
        context.user_data["awaiting_ss"] = True

    elif data == "services":

        keyboard = [
            [InlineKeyboardButton("📸 Instagram", callback_data="instagram")],
            [InlineKeyboardButton("▶ YouTube", callback_data="youtube")],
            [InlineKeyboardButton("📢 Telegram", callback_data="telegram")]
        ]

        await query.message.reply_text("Select Service", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data in ["instagram", "youtube", "telegram"]:

        text = f"Available {data.upper()} Services:\n\n"

        for s in services[data]:
            text += f"{s['name']}\nPrice per 1000: ₹{s['price_per_1000']}\nMin: {s['min_qty']}\n\n"

        await query.message.reply_text(text)

    elif data == "account":

        user_id = query.from_user.id
        balance = user_balance.get(user_id, 0)

        await query.message.reply_text(f"Your Balance: ₹{balance}")

    elif data == "support":

        await query.message.reply_text(f"Support: {SUPPORT}")

    elif data == "cancel":

        context.user_data["awaiting_ss"] = False
        await query.message.reply_text("Cancelled.")


async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if context.user_data.get("awaiting_ss"):

        photo = update.message.photo[-1].file_id

        ADMIN_ID = 123456789  # change to your telegram id

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo,
            caption=f"New Payment Screenshot\nUser: {update.message.from_user.id}"
        )

        await update.message.reply_text("Screenshot submitted. Wait for approval.")

        context.user_data["awaiting_ss"] = False


def main():

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.PHOTO, screenshot))

    app.run_polling()


if __name__ == "__main__":
    main()
