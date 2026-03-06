import json
import logging
import os
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import *

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7117775366

FORCE_CHANNEL = "@verifiedpaisabots"
PAYOUT_CHANNEL = "@blacksmm_payout"

UPI_ID = "vansh59rt@fam"

logging.basicConfig(level=logging.INFO)

users = {}
order_stage = {}
order_data = {}
awaiting_ss = {}

# ---------------- PORT BINDING ---------------- #

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Running"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ---------------- MENU ---------------- #

def main_menu():

    keyboard = [
        [
            InlineKeyboardButton("🛒 SERVICES", callback_data="services"),
            InlineKeyboardButton("💳 ADD FUND", callback_data="fund")
        ],
        [
            InlineKeyboardButton("👤 MY ACCOUNT", callback_data="account"),
            InlineKeyboardButton("🛠 SUPPORT", url="https://t.me/black_seller16")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)

# ---------------- JOIN CHECK ---------------- #

async def joined(bot, uid):

    try:
        member = await bot.get_chat_member(FORCE_CHANNEL, uid)
        return member.status in ["member","administrator","creator"]
    except:
        return False

def join_buttons():

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("JOIN CHANNEL", url="https://t.me/verifiedpaisabots")],
        [InlineKeyboardButton("VERIFY", callback_data="verify")]
    ])

# ---------------- START ---------------- #

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id

    if uid not in users:
        users[uid] = {"balance":0}

    if not await joined(context.bot,uid):

        await update.message.reply_text(
            "⚠️ Join channel first",
            reply_markup=join_buttons()
        )
        return

    await update.message.reply_text(
        "🚀 Welcome to SMM Bot",
        reply_markup=main_menu()
    )

# ---------------- VERIFY ---------------- #

async def verify(update:Update,context:ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    uid = query.from_user.id

    if not await joined(context.bot,uid):
        await query.answer("Join first",show_alert=True)
        return

    await query.message.delete()

    await context.bot.send_message(
        uid,
        "✅ Verified",
        reply_markup=main_menu()
    )

# ---------------- SERVICES ---------------- #

async def services(update:Update,context:ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    with open("services.json") as f:
        data=json.load(f)

    keyboard=[]

    for cat in data:
        keyboard.append(
            [InlineKeyboardButton(cat.upper(),callback_data=f"cat_{cat}")]
        )

    await query.message.reply_text(
        "📦 Select Category",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------- CATEGORY ---------------- #

async def category(update:Update,context:ContextTypes.DEFAULT_TYPE):

    query=update.callback_query
    await query.answer()

    cat=query.data.split("_")[1]

    with open("services.json") as f:
        data=json.load(f)

    keyboard=[]

    for s in data[cat]:

        keyboard.append([
            InlineKeyboardButton(
                s["name"],
                callback_data=f"service_{s['id']}"
            )
        ])

    await query.message.reply_text(
        f"{cat.upper()} SERVICES",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------- SELECT SERVICE ---------------- #

async def select_service(update:Update,context:ContextTypes.DEFAULT_TYPE):

    query=update.callback_query
    await query.answer()

    uid=query.from_user.id
    sid=query.data.split("_")[1]

    order_data[uid]={"service":sid}
    order_stage[uid]="link"

    await query.message.reply_text("Send link")

# ---------------- TEXT HANDLER ---------------- #

async def text_handler(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid=update.effective_user.id
    text=update.message.text

    if uid not in order_stage:
        return

    stage=order_stage[uid]

    if stage=="link":

        order_data[uid]["link"]=text
        order_stage[uid]="qty"

        await update.message.reply_text("Send quantity")
        return

    if stage=="qty":

        qty=int(text)
        order_data[uid]["qty"]=qty

        with open("services.json") as f:
            data=json.load(f)

        service=None

        for cat in data:
            for s in data[cat]:
                if str(s["id"])==order_data[uid]["service"]:
                    service=s

        price=(qty/1000)*service["price_per_1000"]

        order_data[uid]["price"]=price
        order_data[uid]["name"]=service["name"]

        preview=f"""
ORDER PREVIEW

Service: {service['name']}
Link: {order_data[uid]['link']}
Qty: {qty}

Price: ₹{price}
"""

        keyboard=[
            [
                InlineKeyboardButton("CONFIRM",callback_data="confirm"),
                InlineKeyboardButton("CANCEL",callback_data="cancel")
            ]
        ]

        await update.message.reply_text(
            preview,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        order_stage[uid]="confirm"

# ---------------- CONFIRM ORDER ---------------- #

async def confirm(update:Update,context:ContextTypes.DEFAULT_TYPE):

    query=update.callback_query
    await query.answer()

    uid=query.from_user.id
    order=order_data[uid]

    text=f"""
NEW ORDER

User: {uid}

Service: {order['name']}
Link: {order['link']}
Qty: {order['qty']}

Price: ₹{order['price']}
"""

    await context.bot.send_message(
        chat_id=PAYOUT_CHANNEL,
        text=text
    )

    await query.message.edit_text("✅ Order Placed")

    del order_stage[uid]
    del order_data[uid]

# ---------------- CANCEL ORDER ---------------- #

async def cancel(update:Update,context:ContextTypes.DEFAULT_TYPE):

    query=update.callback_query
    await query.answer()

    uid=query.from_user.id

    if uid in order_stage:
        del order_stage[uid]

    if uid in order_data:
        del order_data[uid]

    await query.message.edit_text("Order Cancelled")

# ---------------- ADD FUND ---------------- #

async def fund(update:Update,context:ContextTypes.DEFAULT_TYPE):

    query=update.callback_query
    await query.answer()

    keyboard=[
        [InlineKeyboardButton("Submit Screenshot",callback_data="ss")]
    ]

    text=f"""
ADD FUND

Send UPI payment to:

{UPI_ID}
"""

    await query.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------- SCREENSHOT ---------------- #

async def ss(update:Update,context:ContextTypes.DEFAULT_TYPE):

    query=update.callback_query
    await query.answer()

    awaiting_ss[query.from_user.id]=True

    await query.message.reply_text("Send screenshot")

async def photo(update:Update,context:ContextTypes.DEFAULT_TYPE):

    uid=update.effective_user.id

    if uid not in awaiting_ss:
        return

    photo=update.message.photo[-1].file_id

    await context.bot.send_photo(
        PAYOUT_CHANNEL,
        photo,
        caption=f"Payment SS from {uid}"
    )

    del awaiting_ss[uid]

    await update.message.reply_text("Submitted")

# ---------------- ACCOUNT ---------------- #

async def account(update:Update,context:ContextTypes.DEFAULT_TYPE):

    query=update.callback_query
    await query.answer()

    uid=query.from_user.id

    if uid not in users:
        users[uid]={"balance":0}

    bal=users[uid]["balance"]

    await query.message.reply_text(
        f"User: {uid}\nBalance: ₹{bal}"
    )

# ---------------- ADMIN COMMANDS ---------------- #

async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    try:
        uid = int(context.args[0])
        amount = int(context.args[1])
    except:
        await update.message.reply_text("Usage:\n/addbalance USERID AMOUNT")
        return

    if uid not in users:
        users[uid] = {"balance": 0}

    users[uid]["balance"] += amount

    await update.message.reply_text(
        f"✅ Balance Added\nUser: {uid}\nAmount: ₹{amount}"
    )

async def remove_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    try:
        uid = int(context.args[0])
        amount = int(context.args[1])
    except:
        await update.message.reply_text("Usage:\n/removebalance USERID AMOUNT")
        return

    if uid not in users:
        users[uid] = {"balance": 0}

    users[uid]["balance"] -= amount

    await update.message.reply_text(
        f"❌ Balance Removed\nUser: {uid}\nAmount: ₹{amount}"
    )

# ---------------- MAIN ---------------- #

def main():

    application=Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start",start))

    application.add_handler(CallbackQueryHandler(verify,pattern="verify"))
    application.add_handler(CallbackQueryHandler(services,pattern="services"))
    application.add_handler(CallbackQueryHandler(category,pattern="cat_"))
    application.add_handler(CallbackQueryHandler(select_service,pattern="service_"))
    application.add_handler(CallbackQueryHandler(confirm,pattern="confirm"))
    application.add_handler(CallbackQueryHandler(cancel,pattern="cancel"))
    application.add_handler(CallbackQueryHandler(fund,pattern="fund"))
    application.add_handler(CallbackQueryHandler(ss,pattern="ss"))
    application.add_handler(CallbackQueryHandler(account,pattern="account"))

    application.add_handler(CommandHandler("addbalance", add_balance))
    application.add_handler(CommandHandler("removebalance", remove_balance))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text_handler))
    application.add_handler(MessageHandler(filters.PHOTO,photo))

    import threading
    threading.Thread(target=run).start()

    application.run_polling()

if __name__=="__main__":
    main()

