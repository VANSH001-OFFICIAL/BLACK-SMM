import json
import sqlite3
import os
from flask import Flask
from threading import Thread

from telegram import *
from telegram.ext import *

TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = 123456789
CHANNEL = "@yourchannel"
UPI_ID = "vansh59rt@fam"

# ---------------- FLASK SERVER ---------------- #

app = Flask('')

@app.route('/')
def home():
    return "Bot Running"

def run():
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)

def keep_alive():
    t=Thread(target=run)
    t.start()

# ---------------- DATABASE ---------------- #

conn = sqlite3.connect("data.db",check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY,
balance REAL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS orders(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user INTEGER,
service TEXT,
link TEXT,
qty INTEGER,
price REAL,
status TEXT
)
""")

conn.commit()

# ---------------- BALANCE ---------------- #

def get_balance(uid):

    cur.execute("SELECT balance FROM users WHERE id=?",(uid,))
    r=cur.fetchone()

    if r:
        return r[0]

    cur.execute("INSERT INTO users VALUES(?,?)",(uid,0))
    conn.commit()

    return 0


def set_balance(uid,bal):

    cur.execute("UPDATE users SET balance=? WHERE id=?",(bal,uid))
    conn.commit()

# ---------------- JOIN CHECK ---------------- #

async def joined(bot,uid):

    try:
        m=await bot.get_chat_member(CHANNEL,uid)
        return m.status in ["member","administrator","creator"]
    except:
        return False

# ---------------- START ---------------- #

async def start(update,context):

    uid=update.effective_user.id

    if not await joined(context.bot,uid):

        kb=[[InlineKeyboardButton("Join Channel",url=f"https://t.me/{CHANNEL.replace('@','')}")],
            [InlineKeyboardButton("Verify",callback_data="verify")]]

        await update.message.reply_text(
            "Join channel to use bot",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    get_balance(uid)

    kb=[
        ["🛒 Services","💳 Add Fund"],
        ["👤 My Account","📦 Orders"]
    ]

    await update.message.reply_text(
        "Welcome to SMM Bot",
        reply_markup=ReplyKeyboardMarkup(kb,resize_keyboard=True)
    )

# ---------------- VERIFY ---------------- #

async def verify(update,context):

    q=update.callback_query
    await q.answer()

    uid=q.from_user.id

    if await joined(context.bot,uid):

        kb=[
            ["🛒 Services","💳 Add Fund"],
            ["👤 My Account","📦 Orders"]
        ]

        await q.message.reply_text(
            "Verification Successful",
            reply_markup=ReplyKeyboardMarkup(kb,resize_keyboard=True)
        )

    else:
        await q.answer("Join channel first",show_alert=True)

# ---------------- SERVICES ---------------- #

with open("services.json") as f:
    services=json.load(f)

async def services_menu(update,context):

    kb=[]

    for s in services:
        kb.append([InlineKeyboardButton(s,callback_data=f"service_{s}")])

    await update.message.reply_text(
        "Select Service",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ---------------- ORDER FLOW ---------------- #

order_data={}

async def select_service(update,context):

    q=update.callback_query
    await q.answer()

    service=q.data.split("_")[1]

    order_data[q.from_user.id]={"service":service}

    await q.message.reply_text("Send link")

    return 1


async def get_link(update,context):

    order_data[update.effective_user.id]["link"]=update.message.text

    await update.message.reply_text("Send quantity")

    return 2


async def get_qty(update,context):

    uid=update.effective_user.id
    qty=int(update.message.text)

    service=order_data[uid]["service"]
    price=services[service]["price"]*qty

    order_data[uid]["qty"]=qty
    order_data[uid]["price"]=price

    await update.message.reply_text(
        f"""
Service : {service}
Qty : {qty}
Price : ₹{price}
""",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Confirm",callback_data="confirm")]
        ])
    )

    return ConversationHandler.END


async def confirm(update,context):

    q=update.callback_query
    await q.answer()

    uid=q.from_user.id
    order=order_data.get(uid)

    if not order:
        return

    bal=get_balance(uid)

    if bal < order["price"]:
        await q.message.reply_text("Insufficient balance")
        return

    set_balance(uid,bal-order["price"])

    cur.execute("""
    INSERT INTO orders(user,service,link,qty,price,status)
    VALUES(?,?,?,?,?,?)
    """,(uid,order["service"],order["link"],order["qty"],order["price"],"Pending"))

    conn.commit()

    await q.message.reply_text("Order placed\nStatus : Pending")

# ---------------- ORDERS ---------------- #

async def my_orders(update,context):

    uid=update.effective_user.id

    cur.execute("SELECT service,qty,price,status FROM orders WHERE user=?",(uid,))
    rows=cur.fetchall()

    if not rows:
        await update.message.reply_text("No orders")
        return

    msg="Your Orders\n\n"

    for r in rows:
        msg+=f"{r[0]} | {r[1]} | ₹{r[2]} | {r[3]}\n"

    await update.message.reply_text(msg)

# ---------------- ACCOUNT ---------------- #

async def account(update,context):

    bal=get_balance(update.effective_user.id)

    await update.message.reply_text(f"Balance : ₹{bal}")

# ---------------- ADD FUND ---------------- #

async def add_fund(update,context):

    await update.message.reply_text(
        f"Send payment to\n{UPI_ID}\n\nThen send screenshot"
    )

# ---------------- ADMIN ---------------- #

async def stats(update,context):

    if update.effective_user.id != ADMIN_ID:
        return

    cur.execute("SELECT COUNT(*) FROM users")
    users=cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM orders")
    orders=cur.fetchone()[0]

    cur.execute("SELECT SUM(price) FROM orders")
    revenue=cur.fetchone()[0] or 0

    await update.message.reply_text(
        f"""
Users : {users}
Orders : {orders}
Revenue : ₹{revenue}
"""
    )

async def broadcast(update,context):

    if update.effective_user.id != ADMIN_ID:
        return

    msg=" ".join(context.args)

    cur.execute("SELECT id FROM users")
    users=cur.fetchall()

    sent=0

    for u in users:
        try:
            await context.bot.send_message(u[0],msg)
            sent+=1
        except:
            pass

    await update.message.reply_text(f"Sent to {sent}")

async def addbalance(update,context):

    if update.effective_user.id != ADMIN_ID:
        return

    uid=int(context.args[0])
    amount=float(context.args[1])

    bal=get_balance(uid)

    set_balance(uid,bal+amount)

    await update.message.reply_text("Balance added")

async def removebalance(update,context):

    if update.effective_user.id != ADMIN_ID:
        return

    uid=int(context.args[0])
    amount=float(context.args[1])

    bal=get_balance(uid)

    newbal=max(0,bal-amount)

    set_balance(uid,newbal)

    await update.message.reply_text("Balance removed")

# ---------------- DATABASE EXPORT ---------------- #

async def database(update,context):

    if update.effective_user.id != ADMIN_ID:
        return

    await context.bot.send_document(
        update.effective_chat.id,
        open("data.db","rb")
    )

# ---------------- MAIN ---------------- #

def main():

    keep_alive()

    app_bot=Application.builder().token(TOKEN).build()

    conv=ConversationHandler(

        entry_points=[CallbackQueryHandler(select_service,pattern="service_")],

        states={
            1:[MessageHandler(filters.TEXT,get_link)],
            2:[MessageHandler(filters.TEXT,get_qty)]
        },

        fallbacks=[]
    )

    app_bot.add_handler(CommandHandler("start",start))
    app_bot.add_handler(CallbackQueryHandler(verify,pattern="verify"))
    app_bot.add_handler(conv)
    app_bot.add_handler(CallbackQueryHandler(confirm,pattern="confirm"))

    app_bot.add_handler(MessageHandler(filters.TEXT & filters.Regex("Services"),services_menu))
    app_bot.add_handler(MessageHandler(filters.TEXT & filters.Regex("Orders"),my_orders))
    app_bot.add_handler(MessageHandler(filters.TEXT & filters.Regex("My Account"),account))
    app_bot.add_handler(MessageHandler(filters.TEXT & filters.Regex("Add Fund"),add_fund))

    app_bot.add_handler(CommandHandler("stats",stats))
    app_bot.add_handler(CommandHandler("broadcast",broadcast))
    app_bot.add_handler(CommandHandler("addbalance",addbalance))
    app_bot.add_handler(CommandHandler("removebalance",removebalance))
    app_bot.add_handler(CommandHandler("database",database))

    print("BOT STARTED")

    app_bot.run_polling()

if __name__=="__main__":
    main()
