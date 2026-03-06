import json
import os
import threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# ===== CONFIG =====

BOT_TOKEN = "8677165936:AAH0D0urU-FRv3L0eL4BhxoWV8dIg7OL8Yw"

ADMIN_ID = 7117775366

UPI_ID = "vansh59rt@fam"

SUPPORT = "@black_seller16"

ORDER_CHANNEL = "@blacksmm_payout"
# ===== FLASK SERVER FOR RENDER =====

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Running"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

# ===== LOAD SERVICES =====

with open("services.json") as f:
    services = json.load(f)

try:
    with open("database.json") as f:
        db = json.load(f)
except:
    db = {"users": {}}

def save():
    with open("database.json", "w") as f:
        json.dump(db, f, indent=4)

def get_user(uid):
    uid = str(uid)
    if uid not in db["users"]:
        db["users"][uid] = {"balance": 0, "orders": []}
        save()
    return db["users"][uid]

def is_admin(uid):
    return uid == ADMIN_ID

# ===== MENU =====

def main_menu():

    keyboard = [
        [InlineKeyboardButton("💰 Add Funds", callback_data="addfunds")],
        [InlineKeyboardButton("📊 Services", callback_data="services")],
        [InlineKeyboardButton("👤 My Account", callback_data="account")],
        [InlineKeyboardButton("🛠 Support", callback_data="support")]
    ]

    return InlineKeyboardMarkup(keyboard)

# ===== START =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🚀 Welcome to SMM Bot",
        reply_markup=main_menu()
    )

# ===== BUTTONS =====

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = query.data
    uid = query.from_user.id

    if data == "addfunds":

        keyboard = [
            [InlineKeyboardButton("📤 Submit Screenshot", callback_data="submit")],
            [InlineKeyboardButton("⬅ Back", callback_data="back")]
        ]

        await query.message.edit_text(
            f"Send payment to:\n\nUPI: {UPI_ID}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "submit":

        context.user_data["ss"] = True
        await query.message.reply_text("Send Payment Screenshot")

    elif data == "services":

        keyboard = [
            [InlineKeyboardButton("📸 Instagram", callback_data="cat_instagram")],
            [InlineKeyboardButton("▶ YouTube", callback_data="cat_youtube")],
            [InlineKeyboardButton("📢 Telegram", callback_data="cat_telegram")],
            [InlineKeyboardButton("⬅ Back", callback_data="back")]
        ]

        await query.message.edit_text(
            "Select Platform",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("cat_"):

        cat = data.split("_")[1]

        keyboard = []

        for i, s in enumerate(services[cat]):

            keyboard.append([
                InlineKeyboardButton(
                    f"{s['name']} ₹{s['price_per_1000']}/1k",
                    callback_data=f"service_{cat}_{i}"
                )
            ])

        keyboard.append([InlineKeyboardButton("⬅ Back", callback_data="services")])

        await query.message.edit_text(
            "Select Service",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("service_"):

        _, cat, i = data.split("_")

        s = services[cat][int(i)]

        context.user_data["service"] = s

        await query.message.reply_text(
            f"{s['name']}\n\nSend Link"
        )

    elif data == "account":

        user = get_user(uid)

        await query.message.edit_text(
            f"👤 Account\n\nBalance: ₹{user['balance']}",
            reply_markup=main_menu()
        )

    elif data == "support":

        await query.message.edit_text(
            f"Contact Support: {SUPPORT}",
            reply_markup=main_menu()
        )

    elif data == "back":

        await query.message.edit_text(
            "🚀 Welcome to SMM Bot",
            reply_markup=main_menu()
        )

    # ===== ADMIN PAYMENT APPROVE =====

    elif data.startswith("approve_"):

        if not is_admin(uid):
            return

        user_id = data.split("_")[1]

        get_user(user_id)["balance"] += 100

        save()

        await query.message.reply_text("Payment Approved")

    elif data.startswith("reject_"):

        if not is_admin(uid):
            return

        await query.message.reply_text("Payment Rejected")

# ===== MESSAGE HANDLER =====

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.message.from_user.id
    text = update.message.text

    user = get_user(uid)

    if context.user_data.get("service"):

        if "link" not in context.user_data:

            context.user_data["link"] = text
            await update.message.reply_text("Send Quantity")
            return

        s = context.user_data["service"]

        qty = int(text)

        if qty < s["min_qty"]:

            await update.message.reply_text(
                f"Minimum order: {s['min_qty']}"
            )
            return

        price = (qty / 1000) * s["price_per_1000"]

        if user["balance"] < price:

            await update.message.reply_text("❌ Insufficient Balance")
            return

        user["balance"] -= price

        order = f"""
🚨 NEW ORDER

User: {uid}

Service: {s['name']}

Link:
{context.user_data['link']}

Quantity: {qty}

Price: ₹{price}
"""

        await context.bot.send_message(
            ORDER_CHANNEL,
            order
        )

        user["orders"].append(order)

        save()

        await update.message.reply_text(
            f"✅ Order Placed\n\nCost: ₹{price}"
        )

        context.user_data.clear()

# ===== SCREENSHOT HANDLER =====

async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if context.user_data.get("ss"):

        photo = update.message.photo[-1].file_id
        uid = update.message.from_user.id

        keyboard = [
            [
                InlineKeyboardButton("Approve", callback_data=f"approve_{uid}"),
                InlineKeyboardButton("Reject", callback_data=f"reject_{uid}")
            ]
        ]

        await context.bot.send_photo(
            ADMIN_ID,
            photo,
            caption=f"Payment from {uid}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        await update.message.reply_text("Payment sent for approval")

# ===== ADMIN COMMANDS =====

async def addbalance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.message.from_user.id):
        return

    try:
        user_id = context.args[0]
        amount = float(context.args[1])
    except:
        await update.message.reply_text("/addbalance user_id amount")
        return

    user = get_user(user_id)

    user["balance"] += amount

    save()

    await update.message.reply_text("Balance Added")

async def removebalance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.message.from_user.id):
        return

    try:
        user_id = context.args[0]
        amount = float(context.args[1])
    except:
        await update.message.reply_text("/removebalance user_id amount")
        return

    user = get_user(user_id)

    user["balance"] -= amount

    save()

    await update.message.reply_text("Balance Removed")

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.message.from_user.id):
        return

    await update.message.reply_text(
        f"Total Users: {len(db['users'])}"
    )

async def orders(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.message.from_user.id):
        return

    total = 0

    for u in db["users"]:
        total += len(db["users"][u]["orders"])

    await update.message.reply_text(
        f"Total Orders: {total}"
    )

async def revenue(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.message.from_user.id):
        return

    total = 0

    for u in db["users"]:
        for o in db["users"][u]["orders"]:
            if "Price:" in o:
                price = float(o.split("Price: ₹")[1])
                total += price

    await update.message.reply_text(
        f"Total Revenue: ₹{total}"
    )

# ===== MAIN =====

def main():

    keep_alive()

    bot = Application.builder().token(BOT_TOKEN).build()

    bot.add_handler(CommandHandler("start", start))

    bot.add_handler(CommandHandler("addbalance", addbalance))
    bot.add_handler(CommandHandler("removebalance", removebalance))
    bot.add_handler(CommandHandler("users", users))
    bot.add_handler(CommandHandler("orders", orders))
    bot.add_handler(CommandHandler("revenue", revenue))

    bot.add_handler(CallbackQueryHandler(button))

    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))

    bot.add_handler(MessageHandler(filters.PHOTO, photo))

    bot.run_polling()

main()

