import sqlite3
import logging
import os
import threading
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
    return "Bot Running"

def run():
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)

# ---------------- SERVICES ---------------- #

SERVICES={
"Instagram Followers":{"price":0.25,"min":100},
"Instagram Likes":{"price":0.20,"min":50},
"Youtube Views":{"price":0.15,"min":100}
}

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
        [InlineKeyboardButton("JOIN CHANNEL",url="https://t.me/verifiedpaisabots")],
        [InlineKeyboardButton("VERIFY",callback_data="verify")]
    ])

# ---------------- START ---------------- #

async def start(update,context):

    uid=update.effective_user.id

    if not await joined(context.bot,uid):

        await update.message.reply_text(
            "Join channel first",
            reply_markup=join_buttons()
        )
        return

    kb=[["Services","Add Fund"],["My Account","Orders"]]

    await update.message.reply_text(
        "Welcome to SMM Panel Bot",
        reply_markup=ReplyKeyboardMarkup(kb,resize_keyboard=True)
    )

# ---------------- ACCOUNT ---------------- #

async def account(update,context):

    bal=get_balance(update.effective_user.id)

    await update.message.reply_text(f"Balance : ₹{bal}")

# ---------------- SERVICES ---------------- #

async def services(update,context):

    kb=[]

    for s in SERVICES:
        kb.append([InlineKeyboardButton(s,callback_data=f"srv_{s}")])

    await update.message.reply_text(
        "Select Service",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ---------------- SERVICE SELECT ---------------- #

async def select_service(update,context):

    q=update.callback_query
    await q.answer()

    uid=q.from_user.id
    service=q.data.split("_",1)[1]

    order_stage[uid]="link"
    order_data[uid]={"service":service}

    await q.message.reply_text("Send link")

# ---------------- TEXT HANDLER ---------------- #

async def text_handler(update,context):

    uid=update.effective_user.id
    text=update.message.text

# ---------- FUND FLOW ---------- #

    if uid in fund_stage:

        if fund_stage[uid]=="amount":

            fund_data[uid]={"amount":text}
            fund_stage[uid]="screenshot"

            await update.message.reply_text("Send payment screenshot")
            return

# ---------- ORDER FLOW ---------- #

    if uid not in order_stage:

        if text=="Services":
            await services(update,context)

        elif text=="Add Fund":

            fund_stage[uid]="amount"
            await update.message.reply_text("Send amount")

        elif text=="My Account":
            await account(update,context)

        elif text=="Orders":
            await orders(update,context)

        return

    stage=order_stage[uid]

    if stage=="link":

        order_data[uid]["link"]=text
        order_stage[uid]="qty"

        await update.message.reply_text("Send quantity")
        return

    if stage=="qty":

        qty=int(text)

        service=order_data[uid]["service"]
        price=SERVICES[service]["price"]*qty

        order_data[uid]["qty"]=qty
        order_data[uid]["price"]=price

        kb=[[InlineKeyboardButton("Confirm",callback_data="confirm"),
             InlineKeyboardButton("Cancel",callback_data="cancel")]]

        txt=f"""
ORDER PREVIEW

Service : {service}
Link : {order_data[uid]['link']}
Qty : {qty}

Price : ₹{price}
"""

        await update.message.reply_text(
            txt,
            reply_markup=InlineKeyboardMarkup(kb)
        )

        order_stage[uid]="confirm"

# ---------------- CONFIRM ORDER ---------------- #

async def confirm(update,context):

    q=update.callback_query
    await q.answer()

    uid=q.from_user.id
    order=order_data[uid]

    bal=get_balance(uid)

    if bal<order["price"]:

        await q.message.reply_text("Insufficient balance")
        return

    set_balance(uid,bal-order["price"])

    cur.execute(
    "INSERT INTO orders(user,service,link,qty,price) VALUES(?,?,?,?,?)",
    (uid,order["service"],order["link"],order["qty"],order["price"])
    )

    conn.commit()

    txt=f"""
NEW ORDER

User : {uid}

Service : {order['service']}
Link : {order['link']}
Qty : {order['qty']}
Price : {order['price']}
"""

    await context.bot.send_message(PAYOUT_CHANNEL,txt)

    await q.message.reply_text("Order placed successfully")

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

    await q.message.reply_text("Order cancelled")

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
            InlineKeyboardButton("Approve",callback_data=f"payok_{uid}_{amount}"),
            InlineKeyboardButton("Reject",callback_data=f"payno_{uid}")
        ]
    ]

    await context.bot.send_photo(
        ADMIN_ID,
        update.message.photo[-1].file_id,
        caption=f"Payment Request\nUser : {uid}\nAmount : {amount}",
        reply_markup=InlineKeyboardMarkup(kb)
    )

    await update.message.reply_text("Payment sent for approval")

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

    await context.bot.send_message(uid,f"Payment Approved\n₹{amount} added")

# ---------------- ORDERS ---------------- #

async def orders(update,context):

    uid=update.effective_user.id

    cur.execute("SELECT service,qty,price FROM orders WHERE user=?",(uid,))
    rows=cur.fetchall()

    if not rows:
        await update.message.reply_text("No orders yet")
        return

    text="Your Orders\n\n"

    for r in rows:

        text+=f"{r[0]} | {r[1]} | ₹{r[2]}\n"

    await update.message.reply_text(text)

# ---------------- ADMIN COMMANDS ---------------- #

async def addbalance(update,context):

    if update.effective_user.id!=ADMIN_ID:
        return

    uid=int(context.args[0])
    amt=float(context.args[1])

    bal=get_balance(uid)

    set_balance(uid,bal+amt)

    await update.message.reply_text("Balance added")

async def removebalance(update,context):

    if update.effective_user.id!=ADMIN_ID:
        return

    uid=int(context.args[0])
    amt=float(context.args[1])

    bal=get_balance(uid)

    set_balance(uid,bal-amt)

    await update.message.reply_text("Balance removed")

async def users(update,context):

    cur.execute("SELECT COUNT(*) FROM users")
    c=cur.fetchone()[0]

    await update.message.reply_text(f"Users : {c}")

async def orders_admin(update,context):

    cur.execute("SELECT COUNT(*) FROM orders")
    c=cur.fetchone()[0]

    await update.message.reply_text(f"Orders : {c}")

async def revenue(update,context):

    cur.execute("SELECT SUM(price) FROM orders")
    r=cur.fetchone()[0]

    await update.message.reply_text(f"Revenue ₹{r}")

async def broadcast(update,context):

    if update.effective_user.id!=ADMIN_ID:
        return

    msg=" ".join(context.args)

    cur.execute("SELECT id FROM users")

    for u in cur.fetchall():

        try:
            await context.bot.send_message(u[0],msg)
        except:
            pass

# ---------------- MAIN ---------------- #

def main():

    application=Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start",start))
    application.add_handler(CommandHandler("addbalance",addbalance))
    application.add_handler(CommandHandler("removebalance",removebalance))
    application.add_handler(CommandHandler("users",users))
    application.add_handler(CommandHandler("orders",orders_admin))
    application.add_handler(CommandHandler("revenue",revenue))
    application.add_handler(CommandHandler("broadcast",broadcast))

    application.add_handler(CallbackQueryHandler(select_service,pattern="srv_"))
    application.add_handler(CallbackQueryHandler(confirm,pattern="confirm"))
    application.add_handler(CallbackQueryHandler(cancel,pattern="cancel"))
    application.add_handler(CallbackQueryHandler(payok,pattern="payok_"))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text_handler))
    application.add_handler(MessageHandler(filters.PHOTO,photo))

    threading.Thread(target=run).start()

    application.run_polling()

if __name__=="__main__":
    main()
