import sqlite3
import logging
import os
import asyncio
from flask import Flask
from telegram import *
from telegram.ext import *

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7117775366
CHANNEL = "@verifiedpaisabots"
PAYOUT_CHANNEL = "@blacksmm_payout"

logging.basicConfig(level=logging.INFO)

conn = sqlite3.connect("users.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, balance REAL)")
cur.execute("CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT,user INTEGER,service TEXT,link TEXT,qty INT,price REAL)")
conn.commit()

SERVICES = {
"Instagram Followers": {"price":0.25,"min":100},
"Instagram Likes":{"price":0.20,"min":50},
"Youtube Views":{"price":0.15,"min":100}
}

def get_balance(uid):
    cur.execute("SELECT balance FROM users WHERE id=?", (uid,))
    r=cur.fetchone()
    if r: return r[0]
    cur.execute("INSERT INTO users VALUES(?,?)",(uid,0))
    conn.commit()
    return 0

def set_balance(uid,b):
    cur.execute("UPDATE users SET balance=? WHERE id=?", (b,uid))
    conn.commit()

async def check_join(update,context):
    try:
        m=await context.bot.get_chat_member(CHANNEL,update.effective_user.id)
        if m.status in ["member","administrator","creator"]:
            return True
    except:
        pass
    kb=[[InlineKeyboardButton("Join Channel",url=f"https://t.me/{CHANNEL[1:]}")],
        [InlineKeyboardButton("Verify",callback_data="verify")]]
    await update.message.reply_text("Join channel first",reply_markup=InlineKeyboardMarkup(kb))
    return False

async def start(update,context):
    if not await check_join(update,context):
        return
    kb=[["Services","Add Fund"],["My Account","Orders"]]
    await update.message.reply_text(
        "*Welcome to SMM Panel Bot*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(kb,resize_keyboard=True)
    )

async def account(update,context):
    bal=get_balance(update.effective_user.id)
    await update.message.reply_text(f"Balance : ₹{bal}")

async def services(update,context):
    kb=[]
    for s in SERVICES:
        kb.append([InlineKeyboardButton(s,callback_data=f"srv_{s}")])
    await update.message.reply_text("Select Service",reply_markup=InlineKeyboardMarkup(kb))

async def service_click(update,context):
    q=update.callback_query
    await q.answer()
    s=q.data.split("_")[1]
    context.user_data["service"]=s
    await q.message.reply_text("Send link")

async def link(update,context):
    context.user_data["link"]=update.message.text
    await update.message.reply_text("Send quantity")

async def qty(update,context):
    q=int(update.message.text)
    s=context.user_data["service"]
    price=SERVICES[s]["price"]*q
    context.user_data["qty"]=q
    context.user_data["price"]=price

    kb=[[InlineKeyboardButton("Confirm",callback_data="confirm"),
         InlineKeyboardButton("Cancel",callback_data="cancel")]]

    txt=f"""
Order Preview

Service : {s}
Link : {context.user_data['link']}
Qty : {q}
Price : ₹{price}
"""
    await update.message.reply_text(txt,reply_markup=InlineKeyboardMarkup(kb))

async def confirm(update,context):
    q=update.callback_query
    await q.answer()

    uid=q.from_user.id
    price=context.user_data["price"]

    bal=get_balance(uid)

    if bal<price:
        await q.message.reply_text("Insufficient balance")
        return

    set_balance(uid,bal-price)

    cur.execute("INSERT INTO orders(user,service,link,qty,price) VALUES(?,?,?,?,?)",
    (uid,context.user_data["service"],context.user_data["link"],context.user_data["qty"],price))
    conn.commit()

    txt=f"""
NEW ORDER

User : {uid}
Service : {context.user_data['service']}
Link : {context.user_data['link']}
Qty : {context.user_data['qty']}
Price : {price}
"""
    await context.bot.send_message(PAYOUT_CHANNEL,txt)

    await q.message.reply_text("Order placed successfully")

async def addfund(update,context):
    await update.message.reply_text("Send amount")

async def amount(update,context):
    context.user_data["fund"]=update.message.text
    await update.message.reply_text("Send payment screenshot")

async def screenshot(update,context):
    uid=update.effective_user.id
    kb=[[InlineKeyboardButton("Approve",callback_data=f"payok_{uid}"),
         InlineKeyboardButton("Reject",callback_data=f"payno_{uid}")]]
    await context.bot.send_photo(
        ADMIN_ID,
        update.message.photo[-1].file_id,
        caption=f"Payment request\nUser {uid}\nAmount {context.user_data['fund']}",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    await update.message.reply_text("Payment sent for approval")

async def payapprove(update,context):
    q=update.callback_query
    await q.answer()
    uid=int(q.data.split("_")[1])
    amt=int(q.message.caption.split()[-1])

    bal=get_balance(uid)
    set_balance(uid,bal+amt)

    await context.bot.send_message(uid,"Payment approved")

async def addbal(update,context):
    if update.effective_user.id!=ADMIN_ID:
        return
    uid=int(context.args[0])
    amt=float(context.args[1])
    bal=get_balance(uid)
    set_balance(uid,bal+amt)
    await update.message.reply_text("Balance added")

async def removebal(update,context):
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

async def orders(update,context):
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

app=Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(CommandHandler("addbalance",addbal))
app.add_handler(CommandHandler("removebalance",removebal))
app.add_handler(CommandHandler("users",users))
app.add_handler(CommandHandler("orders",orders))
app.add_handler(CommandHandler("revenue",revenue))
app.add_handler(CommandHandler("broadcast",broadcast))

app.add_handler(MessageHandler(filters.Regex("Services"),services))
app.add_handler(MessageHandler(filters.Regex("My Account"),account))
app.add_handler(MessageHandler(filters.Regex("Add Fund"),addfund))

app.add_handler(CallbackQueryHandler(service_click,pattern="srv_"))
app.add_handler(CallbackQueryHandler(confirm,pattern="confirm"))
app.add_handler(CallbackQueryHandler(payapprove,pattern="payok_"))

app.run_polling()

