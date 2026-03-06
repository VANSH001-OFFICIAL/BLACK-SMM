import json
from telegram import *
from telegram.ext import *
from config import *

with open("services.json") as f:
    services=json.load(f)

try:
    with open("database.json") as f:
        db=json.load(f)
except:
    db={"users":{}}


def save():
    with open("database.json","w") as f:
        json.dump(db,f,indent=4)


def get_user(uid):
    uid=str(uid)
    if uid not in db["users"]:
        db["users"][uid]={"balance":0,"orders":[]}
        save()
    return db["users"][uid]


def main_menu():

    keyboard=[
        [InlineKeyboardButton("💰 Add Funds",callback_data="addfunds")],
        [InlineKeyboardButton("📊 Services",callback_data="services")],
        [InlineKeyboardButton("👤 My Account",callback_data="account")],
        [InlineKeyboardButton("🛠 Support",callback_data="support")]
    ]

    return InlineKeyboardMarkup(keyboard)


async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "Welcome to SMM Bot 🚀",
        reply_markup=main_menu()
    )


async def button(update:Update,context:ContextTypes.DEFAULT_TYPE):

    query=update.callback_query
    await query.answer()

    data=query.data
    uid=query.from_user.id


    if data=="addfunds":

        keyboard=[
            [InlineKeyboardButton("📤 Submit Screenshot",callback_data="submit")],
            [InlineKeyboardButton("⬅ Back",callback_data="back")]
        ]

        await query.message.edit_text(
            f"Send payment to UPI:\n\n{UPI_ID}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    elif data=="submit":

        context.user_data["ss"]=True
        await query.message.reply_text("Send Payment Screenshot")


    elif data=="services":

        keyboard=[
            [InlineKeyboardButton("📸 Instagram",callback_data="cat_instagram")],
            [InlineKeyboardButton("▶ YouTube",callback_data="cat_youtube")],
            [InlineKeyboardButton("📢 Telegram",callback_data="cat_telegram")],
            [InlineKeyboardButton("⬅ Back",callback_data="back")]
        ]

        await query.message.edit_text(
            "Select Platform",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    elif data.startswith("cat_"):

        cat=data.split("_")[1]

        keyboard=[]

        for i,s in enumerate(services[cat]):

            keyboard.append([
                InlineKeyboardButton(
                    f"{s['name']} ₹{s['price_per_1000']}/1k",
                    callback_data=f"service_{cat}_{i}"
                )
            ])

        keyboard.append([InlineKeyboardButton("⬅ Back",callback_data="services")])

        await query.message.edit_text(
            "Select Service",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    elif data.startswith("service_"):

        _,cat,i=data.split("_")

        s=services[cat][int(i)]

        context.user_data["service"]=s

        await query.message.reply_text(
            f"{s['name']}\n\nSend Link"
        )


    elif data=="account":

        user=get_user(uid)

        await query.message.edit_text(
            f"👤 Your Account\n\nBalance: ₹{user['balance']}",
            reply_markup=main_menu()
        )


    elif data=="support":

        await query.message.edit_text(
            f"Contact Support: {SUPPORT}",
            reply_markup=main_menu()
        )


    elif data=="back":

        await query.message.edit_text(
            "Welcome to SMM Bot 🚀",
            reply_markup=main_menu()
        )


async def message(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid=update.message.from_user.id
    text=update.message.text

    user=get_user(uid)

    if context.user_data.get("service"):

        if "link" not in context.user_data:

            context.user_data["link"]=text
            await update.message.reply_text("Send Quantity")
            return


        s=context.user_data["service"]

        qty=int(text)

        if qty < s["min_qty"]:

            await update.message.reply_text(
                f"Minimum order: {s['min_qty']}"
            )
            return


        price=(qty/1000)*s["price_per_1000"]


        if user["balance"] < price:

            await update.message.reply_text("Insufficient Balance")
            return


        user["balance"] -= price


        order_text=f"""
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
            order_text
        )


        user["orders"].append(order_text)

        save()

        await update.message.reply_text(
            f"✅ Order Placed\n\nCost: ₹{price}"
        )

        context.user_data.clear()


async def photo(update:Update,context:ContextTypes.DEFAULT_TYPE):

    if context.user_data.get("ss"):

        photo=update.message.photo[-1].file_id
        uid=update.message.from_user.id

        keyboard=[
            [
                InlineKeyboardButton("Approve",callback_data=f"approve_{uid}"),
                InlineKeyboardButton("Reject",callback_data=f"reject_{uid}")
            ]
        ]

        await context.bot.send_photo(
            ADMIN_ID,
            photo,
            caption=f"Payment from {uid}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        await update.message.reply_text("Payment sent for approval")


def main():

    app=Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",start))

    app.add_handler(CallbackQueryHandler(button))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,message))

    app.add_handler(MessageHandler(filters.PHOTO,photo))

    app.run_polling()


main()
