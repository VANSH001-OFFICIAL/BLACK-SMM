import sqlite3
import logging
import os
import threading
import json
import asyncio
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
broadcast_mode = {} # Admin broadcast tracking ke liye

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

def get_all_users():
    cur.execute("SELECT id FROM users")
    return [row[0] for row in cur.fetchall()]

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

# ---------------- START & VERIFY ---------------- #

async def start(update, context):
    is_callback = update.callback_query is not None
    user = update.callback_query.from_user if is_callback else update.effective_user
    uid = user.id

    if not await joined(context.bot, uid):
        if is_callback:
            await update.callback_query.answer("❌ Join nahi kiya!", show_alert=True)
        else:
            await update.message.reply_text("⚠️ Please join the channel first", reply_markup=join_buttons())
        return

    if is_callback:
        await update.callback_query.answer("✅ Verified!")
        try: await update.callback_query.message.delete()
        except: pass

    kb = [
        ["🛒 Services", "💳 Add Fund"],
        ["👤 My Account", "📦 Orders"]
    ]

    msg = """
🔥 *WELCOME TO BLACK SMM PANEL* 🔥

🚀 Fastest Social Media Growth Services
━━━━━━━━━━━━━━━
📸 Instagram | ▶️ YouTube | ✈️ Telegram
━━━━━━━━━━━━━━━
👇 Select an option below to begin
"""
    await context.bot.send_message(uid, msg, parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

# ---------------- ADMIN COMMANDS ---------------- #

async def admin_stats(update, context):
    if update.effective_user.id != ADMIN_ID: return
    cur.execute("SELECT COUNT(*) FROM users")
    u_count = cur.fetchone()[0]
    cur.execute("SELECT SUM(balance) FROM users")
    total_bal = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM orders")
    total_orders = cur.fetchone()[0]
    await update.message.reply_text(f"📊 *Bot Stats*\n\nUsers: {u_count}\nOrders: {total_orders}\nTotal Bal: ₹{round(total_bal, 2)}", parse_mode="Markdown")

async def add_balance_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    try:
        user_id, amount = int(context.args[0]), float(context.args[1])
        set_balance(user_id, get_balance(user_id) + amount)
        await update.message.reply_text(f"✅ ₹{amount} added to {user_id}")
        await context.bot.send_message(user_id, f"🎁 Admin added ₹{amount} to your wallet!")
    except: await update.message.reply_text("❌ `/addbalance ID AMOUNT`")

async def remove_balance_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    try:
        user_id, amount = int(context.args[0]), float(context.args[1])
        set_balance(user_id, max(0, get_balance(user_id) - amount))
        await update.message.reply_text(f"✅ ₹{amount} removed from {user_id}")
    except: await update.message.reply_text("❌ `/removebalance ID AMOUNT`")

async def database_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    cur.execute("SELECT id, balance FROM users")
    rows = cur.fetchall()
    msg = "📑 *Database*\n\n"
    for r in rows:
        line = f"`{r[0]}` | ₹{r[1]}\n"
        if len(msg + line) > 4000:
            await update.message.reply_text(msg, parse_mode="Markdown")
            msg = ""
        msg += line
    if msg: await update.message.reply_text(msg, parse_mode="Markdown")

# ---------------- BROADCAST FEATURE ---------------- #

async def broadcast_cmd(update, context):
    if update.effective_user.id != ADMIN_ID: return
    broadcast_mode[ADMIN_ID] = True
    await update.message.reply_text("📣 *Broadcast Mode Active*\n\nAb jo bhi message (Text/Photo) aap bhejoge, wo saare users ko jayega.\n\nType `cancel` to stop.", parse_mode="Markdown")

# ---------------- TEXT HANDLER ---------------- #

async def text_handler(update, context):
    uid = update.effective_user.id
    text = update.message.text

    # BROADCAST LOGIC
    if uid == ADMIN_ID and broadcast_mode.get(uid):
        if text.lower() == "cancel":
            broadcast_mode[uid] = False
            await update.message.reply_text("❌ Broadcast cancelled.")
            return
        
        users = get_all_users()
        success = 0
        await update.message.reply_text(f"⏳ Sending to {len(users)} users...")
        
        for user in users:
            try:
                await context.bot.send_message(user, text, parse_mode="Markdown")
                success += 1
                await asyncio.sleep(0.05) # Flood wait bachne ke liye
            except: pass
        
        broadcast_mode[uid] = False
        await update.message.reply_text(f"✅ Broadcast Done!\nSent to: {success}/{len(users)}")
        return

    # FUND FLOW
    if uid in fund_stage and fund_stage[uid] == "amount":
        try:
            fund_data[uid] = {"amount": float(text)}
            fund_stage[uid] = "screenshot"
            await update.message.reply_text("📸 Send payment screenshot")
        except: await update.message.reply_text("❌ Send valid amount")
        return

    # MENU & ORDER FLOW
    if uid not in order_stage:
        if text == "🛒 Services":
            kb = [[InlineKeyboardButton("📸 Instagram", callback_data="cat_instagram")],
                  [InlineKeyboardButton("▶️ Youtube", callback_data="cat_youtube")],
                  [InlineKeyboardButton("✈️ Telegram", callback_data="cat_telegram")]]
            await update.message.reply_text("📦 *Select Category*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        elif text == "💳 Add Fund":
            fund_stage[uid] = "amount"
            await update.message.reply_text(f"💳 *Add Balance*\n\nUPI: `{UPI_ID}`\n\nSend amount paid.", parse_mode="Markdown")
        elif text == "👤 My Account":
            await update.message.reply_text(f"👤 *Account*\n💰 Balance: ₹{get_balance(uid)}", parse_mode="Markdown")
        elif text == "📦 Orders":
            cur.execute("SELECT service, qty, price FROM orders WHERE user=?", (uid,))
            rows = cur.fetchall()
            txt = "📦 *Orders*\n\n" + "\n".join([f"{r[0]} | {r[1]} | ₹{r[2]}" for r in rows]) if rows else "📭 No orders"
            await update.message.reply_text(txt, parse_mode="Markdown")
        return

    stage = order_stage[uid]
    if stage == "link":
        order_data[uid]["link"] = text; order_stage[uid] = "qty"
        await update.message.reply_text("🔢 Send quantity")
    elif stage == "qty":
        try:
            qty = int(text); service = order_data[uid]["service"]
            if qty < service["min_qty"]:
                await update.message.reply_text(f"⚠️ Min: {service['min_qty']}"); return
            price = round((qty / 1000) * service["price_per_1000"], 2)
            order_data[uid].update({"qty": qty, "price": price})
            kb = [[InlineKeyboardButton("✅ Confirm", callback_data="confirm"), InlineKeyboardButton("❌ Cancel", callback_data="cancel")]]
            await update.message.reply_text(f"🧾 *PREVIEW*\n\nSrv: {service['name']}\nQty: {qty}\nPrice: ₹{price}\n\nConfirm?", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
            order_stage[uid] = "confirm"
        except: await update.message.reply_text("❌ Valid qty bhejein")

# ---------------- PHOTO HANDLER ---------------- #

async def photo(update, context):
    uid = update.effective_user.id
    
    # BROADCAST PHOTO
    if uid == ADMIN_ID and broadcast_mode.get(uid):
        users = get_all_users()
        success = 0
        photo_id = update.message.photo[-1].file_id
        cap = update.message.caption or ""
        await update.message.reply_text(f"⏳ Broadcasting photo...")
        for user in users:
            try:
                await context.bot.send_photo(user, photo_id, caption=cap, parse_mode="Markdown")
                success += 1
                await asyncio.sleep(0.05)
            except: pass
        broadcast_mode[uid] = False
        await update.message.reply_text(f"✅ Photo Broadcast Done!\nSent to: {success}")
        return

    # PAYMENT SCREENSHOT
    if uid in fund_stage and fund_stage[uid] == "screenshot":
        amt = fund_data[uid]["amount"]
        kb = [[InlineKeyboardButton("✅ Approve", callback_data=f"payok_{uid}_{amt}"), InlineKeyboardButton("❌ Reject", callback_data=f"payno_{uid}")]]
        await context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id, caption=f"💳 *Request*\nUser: {uid}\nAmt: ₹{amt}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("✅ Sent to admin")
        fund_stage.pop(uid, None); fund_data.pop(uid, None)

# ---------------- CALLBACKS ---------------- #

async def category(update, context):
    q = update.callback_query; await q.answer()
    cat = q.data.split("_")[1]
    btn = [[InlineKeyboardButton(s["name"], callback_data=f"srv_{cat}_{i}")] for i, s in enumerate(SERVICES[cat])]
    await q.edit_message_text(f"📦 {cat.upper()} Services", reply_markup=InlineKeyboardMarkup(btn))

async def select_service(update, context):
    q = update.callback_query; await q.answer(); uid = q.from_user.id
    d = q.data.split("_"); cat, idx = d[1], int(d[2]); srv = SERVICES[cat][idx]
    order_stage[uid] = "link"; order_data[uid] = {"service": srv}
    await q.message.reply_text(f"📦 *{srv['name']}*\nPrice: ₹{srv['price_per_1000']}\n\n🔗 Send link", parse_mode="Markdown")

async def confirm(update, context):
    q = update.callback_query; uid = q.from_user.id
    if uid not in order_data: return
    ord = order_data[uid]; bal = get_balance(uid)
    if bal < ord["price"]:
        await q.answer("❌ Low Balance", show_alert=True); return
    set_balance(uid, bal - ord["price"])
    cur.execute("INSERT INTO orders(user,service,link,qty,price) VALUES(?,?,?,?,?)", (uid, ord["service"]["name"], ord["link"], ord["qty"], ord["price"]))
    conn.commit()
    await context.bot.send_message(PAYOUT_CHANNEL, f"🚀 *NEW*\nUser: {uid}\nSrv: {ord['service']['name']}\nPrice: ₹{ord['price']}", parse_mode="Markdown")
    await q.message.reply_text("✅ Order placed"); order_stage.pop(uid, None); order_data.pop(uid, None)

async def payok(update, context):
    _, target, amt = update.callback_query.data.split("_")
    set_balance(int(target), get_balance(int(target)) + float(amt))
    await context.bot.send_message(int(target), f"✅ ₹{amt} added!"); await update.callback_query.edit_message_caption("✅ Approved")

async def payno(update, context):
    uid = int(update.callback_query.data.split("_")[1])
    await context.bot.send_message(uid, "❌ Rejected"); await update.callback_query.edit_message_caption("❌ Rejected")

# ---------------- MAIN ---------------- #

def main():
    app_bot = Application.builder().token(TOKEN).build()
    
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("stats", admin_stats))
    app_bot.add_handler(CommandHandler("addbalance", add_balance_cmd))
    app_bot.add_handler(CommandHandler("removebalance", remove_balance_cmd))
    app_bot.add_handler(CommandHandler("database", database_cmd))
    app_bot.add_handler(CommandHandler("broadcast", broadcast_cmd))

    app_bot.add_handler(CallbackQueryHandler(category, pattern="cat_"))
    app_bot.add_handler(CallbackQueryHandler(select_service, pattern="srv_"))
    app_bot.add_handler(CallbackQueryHandler(confirm, pattern="confirm"))
    app_bot.add_handler(CallbackQueryHandler(payok, pattern="payok_"))
    app_bot.add_handler(CallbackQueryHandler(payno, pattern="payno_"))
    app_bot.add_handler(CallbackQueryHandler(start, pattern="verify"))

    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app_bot.add_handler(MessageHandler(filters.PHOTO, photo))

    threading.Thread(target=run).start()
    app_bot.run_polling()

if __name__ == "__main__":
    main()
