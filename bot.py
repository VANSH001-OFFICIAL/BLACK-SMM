import sqlite3
import logging
import os
import threading
import json
from flask import Flask
from telegram import *
from telegram.ext import *

TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 7117775366
FORCE_CHANNEL = "@verifiedpaisabots"
PAYOUT_CHANNEL = "@blacksmm_payout"

logging.basicConfig(level=logging.INFO)

# ---------------- DATABASE ---------------- #

conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,balance REAL)")
cur.execute("CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT,user INT,service TEXT,link TEXT,qty INT,price REAL)")
conn.commit()

# ---------------- FLASK SERVER ---------------- #

app = Flask(__name__)

@app.route("/")
def home():
    return "SMM BOT RUNNING"

def run():
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)

# ---------------- LOAD SERVICES ---------------- #

with open("services.json","r") as f:
    SERVICES=json.load(f)

# ---------------- MEMORY ---------------- #

order_stage={}
order_data={}
fund_stage={}
fund_data={}

# ---------------- DATABASE FUNCTIONS ---------------- #

def get_balance(uid):

    cur.execute("SELECT balance FROM users WHERE id=?",(uid,))
    r=cur.fetchone()

    if r:
        return r[0]

    cur.execute("INSERT INTO users VALUES(?,?)",(uid,0))
    conn.commit()

    return 0

def set_balance(uid,b):

    cur.execute("UPDATE users SET balance=? WHERE id=?",(b,uid))
    conn.commit()

# ---------------- JOIN CHECK ---------------- #

async def joined(bot,uid):

    try:
        m=await bot.get_chat_member(FORCE_CHANNEL,uid)
        return m.status in ["member","administrator","creator"]
    except:
        return False

def join_buttons():

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel",url="https://t.me/verifiedpaisabots")],
        [InlineKeyboardButton("✅ Verify",callback_data="verify")]
    ])

# ---------------- START ---------------- #

async def start(update,context):

    uid=update.effective_user.id

    if not await joined(context.bot,uid):

        await update.message.reply_text(
            "⚠️ Please join the channel first",
            reply_markup=join_buttons()
        )
        return

    kb=[
        ["🛒 Services","💳 Add Fund"],
        ["👤 My Account","📦 Orders"]
    ]

    await update.message.reply_text(
        "🚀 Welcome to *Black SMM Panel*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(kb,resize_keyboard=True)
    )

# ---------------- ACCOUNT ---------------- #

async def account(update,context):

    bal=get_balance(update.effective_user.id)

    await update.message.reply_text(
        f"👤 *Your Account*\n\n💰 Balance : ₹{bal}",
        parse_mode="Markdown"
    )

# ---------------- SERVICES ---------------- #

async def services(update,context):

    kb=[
        [InlineKeyboardButton("📸 Instagram",callback_data="cat_instagram")],
        [InlineKeyboardButton("▶️ Youtube",callback_data="cat_youtube")],
        [InlineKeyboardButton("✈️ Telegram",callback_data="cat_telegram")]
    ]

    await update.message.reply_text(
        "📦 Select Category",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ---------------- CATEGORY ---------------- #

async def category(update,context):

    q=update.callback_query
    await q.answer()

    cat=q.data.split("_")[1]

    buttons=[]

    for i,s in enumerate(SERVICES[cat]):

        buttons.append([
            InlineKeyboardButton(
                s["name"],
                callback_data=f"srv_{cat}_{i}"
            )
        ])

    await q.edit_message_text(
        f"📦 {cat.upper()} Services",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ---------------- SERVICE SELECT ---------------- #

async def select_service(update,context):

    q=update.callback_query
    await q.answer()

    uid=q.from_user.id

    data=q.data.split("_")

    cat=data[1]
    index=int(data[2])

    service=SERVICES[cat][index]

    order_stage[uid]="link"
    order_data[uid]={"service":service}

    await q.message.reply_text(
        f"""
📦 {service['name']}

💰 Price /1000 : ₹{service['price_per_1000']}
📉 Min Order : {service['min_qty']}

🔗 Send link
"""
    )

# ---------------- TEXT HANDLER ---------------- #

async def text_handler(update,context):

    uid=update.effective_user.id
    text=update.message.text

# ---------- FUND FLOW ---------- #

    if uid in fund_stage:

        if fund_stage[uid]=="amount":

            try:
                amount=float(text)
            except:
                await update.message.reply_text("❌ Send valid amount")
                return

            fund_data[uid]={"amount":amount}
            fund_stage[uid]="screenshot"

            await update.message.reply_text("📸 Send payment screenshot")
            return

# ---------- MENU ---------- #

    if uid not in order_stage:

        if text=="🛒 Services":
            await services(update,context)

        elif text=="💳 Add Fund":

            fund_stage[uid]="amount"

            await update.message.reply_text("💳 Send payment amount")

        elif text=="👤 My Account":
            await account(update,context)

        elif text=="📦 Orders":
            await orders(update,context)

        return

    stage=order_stage[uid]

# ---------- LINK ---------- #

    if stage=="link":

        order_data[uid]["link"]=text
        order_stage[uid]="qty"

        await update.message.reply_text("🔢 Send quantity")
        return

# ---------- QTY ---------- #

    if stage=="qty":

        try:
            qty=int(text)
        except:
            await update.message.reply_text("❌ Send valid quantity")
            return

        service=order_data[uid]["service"]

        if qty < service["min_qty"]:

            await update.message.reply_text(
                f"⚠️ Minimum quantity {service['min_qty']}"
            )
            return

        price=(qty/1000)*service["price_per_1000"]

        order_data[uid]["qty"]=qty
        order_data[uid]["price"]=round(price,2)

        kb=[[InlineKeyboardButton("✅ Confirm",callback_data="confirm"),
             InlineKeyboardButton("❌ Cancel",callback_data="cancel")]]

        txt=f"""
🧾 *ORDER PREVIEW*

Service : {service['name']}
Link : {order_data[uid]['link']}
Quantity : {qty}

💰 Price : ₹{round(price,2)}
"""

        await update.message.reply_text(
            txt,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )

        order_stage[uid]="confirm"

# ---------------- CONFIRM ---------------- #

async def confirm(update,context):

    q=update.callback_query
    await q.answer()

    uid=q.from_user.id

    if uid not in order_data:
        return

    order=order_data[uid]

    bal=get_balance(uid)

    if bal<order["price"]:

        await q.message.reply_text("❌ Insufficient balance")
        return

    set_balance(uid,bal-order["price"])

    cur.execute(
    "INSERT INTO orders(user,service,link,qty,price) VALUES(?,?,?,?,?)",
    (uid,order["service"]["name"],order["link"],order["qty"],order["price"])
    )

    conn.commit()

    txt=f"""
🚀 *NEW ORDER*

User : {uid}

Service : {order['service']['name']}
Link : {order['link']}
Qty : {order['qty']}
Price : ₹{order['price']}
"""

    await context.bot.send_message(
        PAYOUT_CHANNEL,
        txt,
        parse_mode="Markdown"
    )

    await q.message.reply_text("✅ Order placed")

    del order_stage[uid]
    del order_data[uid]

# ---------------- CANCEL ---------------- #

async def cancel(update,context):

    q=update.callback_query
    await q.answer()

    uid=q.from_user.id

    if uid in order_stage:
        del order_stage[uid]

    if uid in order_data:
        del order_data[uid]

    await q.message.reply_text("❌ Order cancelled")

# ---------------- SCREENSHOT ---------------- #

async def photo(update,context):

    uid=update.effective_user.id

    if uid not in fund_stage:
        return

    if fund_stage[uid]!="screenshot":
        return

    amount=fund_data[uid]["amount"]

    kb=[
        [
            InlineKeyboardButton("✅ Approve",callback_data=f"payok_{uid}_{amount}"),
            InlineKeyboardButton("❌ Reject",callback_data=f"payno_{uid}")
        ]
    ]

    await context.bot.send_photo(
        ADMIN_ID,
        update.message.photo[-1].file_id,
        caption=f"💳 Payment\nUser:{uid}\nAmount:₹{amount}",
        reply_markup=InlineKeyboardMarkup(kb)
    )

    await update.message.reply_text("✅ Sent to admin")

    del fund_stage[uid]
    del fund_data[uid]

# ---------------- APPROVE ---------------- #

async def payok(update,context):

    q=update.callback_query
    await q.answer()

    data=q.data.split("_")

    uid=int(data[1])
    amount=float(data[2])

    bal=get_balance(uid)

    set_balance(uid,bal+amount)

    await context.bot.send_message(
        uid,
        f"✅ Payment approved\n₹{amount} added"
    )

# ---------------- REJECT ---------------- #

async def payno(update,context):

    q=update.callback_query
    await q.answer()

    uid=int(q.data.split("_")[1])

    await context.bot.send_message(uid,"❌ Payment rejected")

# ---------------- ORDERS ---------------- #

async def orders(update,context):

    uid=update.effective_user.id

    cur.execute("SELECT service,qty,price FROM orders WHERE user=?",(uid,))
    rows=cur.fetchall()

    if not rows:

        await update.message.reply_text("📭 No orders yet")
        return

    text="📦 *Your Orders*\n\n"

    for r in rows:

        text+=f"{r[0]} | {r[1]} | ₹{r[2]}\n"

    await update.message.reply_text(
        text,
        parse_mode="Markdown"
    )

# ---------------- MAIN ---------------- #

def main():

    application=Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start",start))

    application.add_handler(CallbackQueryHandler(category,pattern="cat_"))
    application.add_handler(CallbackQueryHandler(select_service,pattern="srv_"))
    application.add_handler(CallbackQueryHandler(confirm,pattern="confirm"))
    application.add_handler(CallbackQueryHandler(cancel,pattern="cancel"))
    application.add_handler(CallbackQueryHandler(payok,pattern="payok_"))
    application.add_handler(CallbackQueryHandler(payno,pattern="payno_"))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text_handler))
    application.add_handler(MessageHandler(filters.PHOTO,photo))

    threading.Thread(target=run).start()

    application.run_polling()

if __name__=="__main__":
    main()

