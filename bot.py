import sqlite3
import logging
import os
import threading
import json
from flask import Flask
from telegram import *
from telegram.ext import *

# ---------------- CONFIGURATION ---------------- #

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7117775366
FORCE_CHANNEL = "@verifiedpaisabots"
PAYOUT_CHANNEL = "@blacksmm_payout"
UPI_ID = "vansh59rt@fam"

logging.basicConfig(level=logging.INFO)

# ---------------- DATABASE ---------------- #

conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, balance REAL)")
cur.execute("CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT, user INT, service TEXT, link TEXT, qty INT, price REAL)")
conn.commit()

# ---------------- FLASK SERVER ---------------- #

app = Flask(__name__)

@app.route("/")
def home():
    return "SMM BOT RUNNING"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ---------------- LOAD SERVICES ---------------- #

with open("services.json", "r") as f:
    SERVICES = json.load(f)

# ---------------- MEMORY ---------------- #

order_stage = {}
order_data = {}
fund_stage = {}
fund_data = {}

# ---------------- DATABASE FUNCTIONS ---------------- #

def get_balance(uid):
    cur.execute("SELECT balance FROM users WHERE id=?", (uid,))
    r = cur.fetchone()
    if r:
        return r[0]
    cur.execute("INSERT INTO users VALUES(?,?)", (uid, 0))
    conn.commit()
    return 0

def set_balance(uid, b):
    cur.execute("UPDATE users SET balance=? WHERE id=?", (b, uid))
    conn.commit()

# ---------------- JOIN CHECK ---------------- #

async def joined(bot, uid):
    try:
        m = await bot.get_chat_member(FORCE_CHANNEL, uid)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

def join_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url="https://t.me/verifiedpaisabots")],
        [InlineKeyboardButton("✅ Verify", callback_data="verify")]
    ])

# ---------------- START ---------------- #

async def start(update, context):
    uid = update.effective_user.id
    if not await joined(context.bot, uid):
        await update.message.reply_text(
            "⚠️ Please join the channel first",
            reply_markup=join_buttons()
        )
        return

    kb = [
        ["🛒 Services", "💳 Add Fund"],
        ["👤 My Account", "📦 Orders"]
    ]

    msg = """
🔥 *WELCOME TO BLACK SMM PANEL* 🔥

🚀 Fastest Social Media Growth Services

📸 Instagram
▶️ YouTube
✈️ Telegram

━━━━━━━━━━━━━━━

⚡️ Instant Delivery  
💰 Cheapest Prices  
🔒 Secure Payments  
📊 Real Growth Services  

━━━━━━━━━━━━━━━

💳 Add balance using UPI  
📦 Place order instantly  

👇 Select an option below to begin
"""
    await update.message.reply_text(
        msg,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

# ---------------- ACCOUNT ---------------- #

async def account(update, context):
    bal = get_balance(update.effective_user.id)
    await update.message.reply_text(
        f"👤 *Your Account*\n\n💰 Balance : ₹{bal}",
        parse_mode="Markdown"
    )

# ---------------- SERVICES ---------------- #

async def services(update, context):
    kb = [
        [InlineKeyboardButton("📸 Instagram", callback_data="cat_instagram")],
        [InlineKeyboardButton("▶️ Youtube", callback_data="cat_youtube")],
        [InlineKeyboardButton("✈️ Telegram", callback_data="cat_telegram")]
    ]
    await update.message.reply_text(
        "📦 *Select Category*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ---------------- CATEGORY ---------------- #

async def category(update, context):
    q = update.callback_query
    await q.answer()
    cat = q.data.split("_")[1]
    buttons = []
    for i, s in enumerate(SERVICES[cat]):
        buttons.append([InlineKeyboardButton(s["name"], callback_data=f"srv_{cat}_{i}")])

    await q.edit_message_text(
        f"📦 {cat.upper()} Services",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ---------------- SERVICE SELECT ---------------- #

async def select_service(update, context):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data.split("_")
    cat, index = data[1], int(data[2])
    service = SERVICES[cat][index]

    order_stage[uid] = "link"
    order_data[uid] = {"service": service}

    await q.message.reply_text(
        f"📦 *{service['name']}*\n\n💰 Price /1000 : ₹{service['price_per_1000']}\n📉 Minimum Order : {service['min_qty']}\n\n🔗 Send your link",
        parse_mode="Markdown"
    )

# ---------------- ADMIN COMMANDS (NEW) ---------------- #

async def admin_stats(update, context):
    if update.effective_user.id != ADMIN_ID: return
    cur.execute("SELECT COUNT(*) FROM users")
    u_count = cur.fetchone()[0]
    cur.execute("SELECT SUM(balance) FROM users")
    total_bal = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM orders")
    total_orders = cur.fetchone()[0]
    
    await update.message.reply_text(
        f"📊 *Bot Statistics*\n\n👥 Total Users: {u_count}\n📦 Total Orders: {total_orders}\n💰 System Wallet: ₹{round(total_bal, 2)}",
        parse_mode="Markdown"
    )

async def add_balance_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    try:
        user_id = int(context.args[0])
        amount = float(context.args[1])
        set_balance(user_id, get_balance(user_id) + amount)
        await update.message.reply_text(f"✅ Added ₹{amount} to {user_id}")
        await context.bot.send_message(user_id, f"🎁 Admin added ₹{amount} to your wallet!")
    except:
        await update.message.reply_text("❌ Format: `/addbalance USERID AMOUNT`", parse_mode="Markdown")

async def remove_balance_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    try:
        user_id = int(context.args[0])
        amount = float(context.args[1])
        set_balance(user_id, max(0, get_balance(user_id) - amount))
        await update.message.reply_text(f"✅ Removed ₹{amount} from {user_id}")
    except:
        await update.message.reply_text("❌ Format: `/removebalance USERID AMOUNT`", parse_mode="Markdown")

async def database_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    cur.execute("SELECT id, balance FROM users")
    rows = cur.fetchall()
    if not rows:
        await update.message.reply_text("Database is empty.")
        return
    
    msg = "📑 *Full User Database*\n\n"
    for r in rows:
        line = f"ID: `{r[0]}` | Bal: ₹{r[1]}\n"
        if len(msg + line) > 4000:
            await update.message.reply_text(msg, parse_mode="Markdown")
            msg = ""
        msg += line
    if msg: await update.message.reply_text(msg, parse_mode="Markdown")

# ---------------- TEXT HANDLER ---------------- #

async def text_handler(update, context):
    uid = update.effective_user.id
    text = update.message.text

    # FUND FLOW
    if uid in fund_stage:
        if fund_stage[uid] == "amount":
            try:
                amount = float(text)
                fund_data[uid] = {"amount": amount}
                fund_stage[uid] = "screenshot"
                await update.message.reply_text("📸 Send payment screenshot")
            except:
                await update.message.reply_text("❌ Send valid amount")
            return

    # MENU
    if uid not in order_stage:
        if text == "🛒 Services": await services(update, context)
        elif text == "💳 Add Fund":
            fund_stage[uid] = "amount"
            await update.message.reply_text(f"💳 *Add Balance*\n\nSend payment to this UPI 👇\n\n`{UPI_ID}`\n\nAfter payment send the amount you paid.", parse_mode="Markdown")
        elif text == "👤 My Account": await account(update, context)
        elif text == "📦 Orders": await orders(update, context)
        return

    # ORDER STAGES
    stage = order_stage[uid]
    if stage == "link":
        order_data[uid]["link"] = text
        order_stage[uid] = "qty"
        await update.message.reply_text("🔢 Send quantity")
    elif stage == "qty":
        try:
            qty = int(text)
            service = order_data[uid]["service"]
            if qty < service["min_qty"]:
                await update.message.reply_text(f"⚠️ Minimum quantity {service['min_qty']}")
                return
            price = round((qty / 1000) * service["price_per_1000"], 2)
            order_data[uid].update({"qty": qty, "price": price})
            kb = [[InlineKeyboardButton("✅ Confirm", callback_data="confirm"), InlineKeyboardButton("❌ Cancel", callback_data="cancel")]]
            await update.message.reply_text(f"🧾 *ORDER PREVIEW*\n\nService: {service['name']}\nLink: {order_data[uid]['link']}\nQty: {qty}\nPrice: ₹{price}\n\nConfirm?", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
            order_stage[uid] = "confirm"
        except:
            await update.message.reply_text("❌ Send valid quantity")

# ---------------- CALLBACKS ---------------- #

async def confirm(update, context):
    q = update.callback_query
    uid = q.from_user.id
    if uid not in order_data: return
    order = order_data[uid]
    bal = get_balance(uid)
    if bal < order["price"]:
        await q.answer("❌ Insufficient balance", show_alert=True)
        return
    set_balance(uid, bal - order["price"])
    cur.execute("INSERT INTO orders(user,service,link,qty,price) VALUES(?,?,?,?,?)", (uid, order["service"]["name"], order["link"], order["qty"], order["price"]))
    conn.commit()
    await context.bot.send_message(PAYOUT_CHANNEL, f"🚀 *NEW ORDER*\nUser: {uid}\nService: {order['service']['name']}\nLink: {order['link']}\nQty: {order['qty']}\nPrice: ₹{order['price']}", parse_mode="Markdown")
    await q.message.reply_text("✅ Order placed")
    order_stage.pop(uid, None); order_data.pop(uid, None)

async def cancel(update, context):
    uid = update.callback_query.from_user.id
    order_stage.pop(uid, None); order_data.pop(uid, None)
    await update.callback_query.message.reply_text("❌ Order cancelled")

async def photo(update, context):
    uid = update.effective_user.id
    if uid in fund_stage and fund_stage[uid] == "screenshot":
        amt = fund_data[uid]["amount"]
        kb = [[InlineKeyboardButton("✅ Approve", callback_data=f"payok_{uid}_{amt}"), InlineKeyboardButton("❌ Reject", callback_data=f"payno_{uid}")]]
        await context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id, caption=f"💳 *Payment Request*\nUser: {uid}\nAmount: ₹{amt}\nUPI: {UPI_ID}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("✅ Sent to admin")
        fund_stage.pop(uid, None); fund_data.pop(uid, None)

async def payok(update, context):
    q = update.callback_query
    _, target, amt = q.data.split("_")
    set_balance(int(target), get_balance(int(target)) + float(amt))
    await context.bot.send_message(int(target), f"✅ Payment approved\n₹{amt} added")
    await q.edit_message_caption("✅ Approved")

async def payno(update, context):
    uid = int(update.callback_query.data.split("_")[1])
    await context.bot.send_message(uid, "❌ Payment rejected")
    await update.callback_query.edit_message_caption("❌ Rejected")

async def orders(update, context):
    cur.execute("SELECT service, qty, price FROM orders WHERE user=?", (update.effective_user.id,))
    rows = cur.fetchall()
    if not rows: await update.message.reply_text("📭 No orders yet"); return
    txt = "📦 *Your Orders*\n\n" + "\n".join([f"{r[0]} | {r[1]} | ₹{r[2]}" for r in rows])
    await update.message.reply_text(txt, parse_mode="Markdown")

# ---------------- MAIN ---------------- #

def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CommandHandler("addbalance", add_balance_cmd))
    application.add_handler(CommandHandler("removebalance", remove_balance_cmd))
    application.add_handler(CommandHandler("database", database_cmd))

    application.add_handler(CallbackQueryHandler(category, pattern="cat_"))
    application.add_handler(CallbackQueryHandler(select_service, pattern="srv_"))
    application.add_handler(CallbackQueryHandler(confirm, pattern="confirm"))
    application.add_handler(CallbackQueryHandler(cancel, pattern="cancel"))
    application.add_handler(CallbackQueryHandler(payok, pattern="payok_"))
    application.add_handler(CallbackQueryHandler(payno, pattern="payno_"))
    application.add_handler(CallbackQueryHandler(start, pattern="verify")) # Purana verify callback

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    application.add_handler(MessageHandler(filters.PHOTO, photo))

    threading.Thread(target=run).start()
    application.run_polling()

if __name__ == "__main__":
    main()

