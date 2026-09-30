   import base64
import datetime
import hashlib
import hmac
import json
import logging
import random
import sqlite3
import string
import struct
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import telebot
from telebot import types

# Bot Configuration
TOKEN = "8833506125:AAF09XldZ6p-niAMMZjspnAfnYK1u8r9nNs"
ADMIN_CHAT_ID = 8444176616
SUPPORT_USERNAME = "@supekrsupper"
HELP_USERNAME = "@supekrsupper"
REQUIRED_CHANNEL = "@honestcrazy11"

# Task Rewards Configuration
FB_HOTMAIL_REWARD = 0.05
FB_COOKIES_REWARD = 0.04
HOTMAIL_10_PAGE_REWARD = 0.25
INSTAGRAM_2FA_REWARD = 0.034  # Updated to 0.034

bot = telebot.TeleBot(TOKEN)
logging.basicConfig(level=logging.INFO)

# Google Sheets Setup
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def log_to_google_sheet(
    task_type,
    username,
    chat_id,
    gen_name,
    gen_pass,
    uid,
    two_fa,
    cookies,
    full_token,
):
  try:
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "credentials.json", SCOPE
    )
    client = gspread.authorize(creds)
    sheet = client.open("EarlyLifeBotSubmissions").sheet1
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([
        current_time,
        task_type,
        f"@{username}" if username else "None",
        str(chat_id),
        str(gen_name),
        str(gen_pass),
        str(uid),
        str(two_fa),
        str(cookies),
        str(full_token),
    ])
  except Exception as e:
    logging.error(f"Google Sheet Error: {e}")


FIRST_NAMES = [
    "Shakib",
    "Fahim",
    "Mintu",
    "Rakib",
    "Nayeem",
    "Tanvir",
    "Sojib",
    "Imran",
    "Arman",
    "Sumon",
    "Ripon",
    "Juel",
    "Hridoy",
    "Mahmud",
    "Shohan",
    "Mehedi",
    "Nabil",
    "Joy",
    "Al-Amin",
    "Parvez",
]
LAST_NAMES = [
    "Ahmed",
    "Hasan",
    "Khan",
    "Ali",
    "Chowdhury",
    "Talukdar",
    "Sarker",
    "Mollah",
    "Bhuyan",
    "Mia",
    "Biswas",
    "Hawlader",
]


# Database Setup
def init_db():
  conn = sqlite3.connect("early_life_bot.db")
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0,
            total_submitted INTEGER DEFAULT 0,
            total_success INTEGER DEFAULT 0,
            review_pending INTEGER DEFAULT 0,
            admin_rejected INTEGER DEFAULT 0,
            bot_rejected INTEGER DEFAULT 0,
            referrals INTEGER DEFAULT 0,
            commission REAL DEFAULT 0.0,
            state TEXT,
            pending_reward REAL DEFAULT 0.0,
            gen_user TEXT,
            gen_pass TEXT,
            temp_uid TEXT,
            temp_2fa TEXT,
            temp_cookies TEXT,
            temp_token TEXT,
            withdraw_method TEXT,
            withdraw_amount REAL DEFAULT 0.0
        )
    """)
  conn.commit()
  conn.close()


init_db()


def get_user(chat_id):
  conn = sqlite3.connect("early_life_bot.db")
  cursor = conn.cursor()
  cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
  row = cursor.fetchone()

  if not row:
    cursor.execute(
        """
            INSERT INTO users (chat_id, balance, total_submitted, total_success, review_pending, admin_rejected, bot_rejected, referrals, commission, state, pending_reward)
            VALUES (?, 0.0, 0, 0, 0, 0, 0, 0, 0.0, NULL, 0.0)
        """,
        (chat_id,),
    )
    conn.commit()
    cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()

  conn.close()

  return {
      "chat_id": row[0],
      "balance": row[1],
      "total_submitted": row[2],
      "total_success": row[3],
      "review_pending": row[4],
      "admin_rejected": row[5],
      "bot_rejected": row[6],
      "referrals": row[7],
      "commission": row[8],
      "state": row[9],
      "pending_reward": row[10],
      "gen_user": row[11],
      "gen_pass": row[12],
      "temp_uid": row[13],
      "temp_2fa": row[14],
      "temp_cookies": row[15],
      "temp_token": row[16],
      "withdraw_method": row[17],
      "withdraw_amount": row[18],
  }


def update_user(chat_id, **kwargs):
  conn = sqlite3.connect("early_life_bot.db")
  cursor = conn.cursor()
  for key, value in kwargs.items():
    cursor.execute(
        f"UPDATE users SET {key} = ? WHERE chat_id = ?", (value, chat_id)
    )
  conn.commit()
  conn.close()


def generate_bangladeshi_credentials():
  first = random.choice(FIRST_NAMES)
  last = random.choice(LAST_NAMES)
  full_name = f"{first} {last}"
  letters = string.ascii_lowercase + string.digits
  rand_pass = "".join(random.choice(letters) for i in range(8))
  password = f"Pass_{rand_pass}"
  return full_name, password


def generate_totp(secret):
  try:
    key = base64.b32decode(
        secret.upper() + "=" * ((-len(secret)) % 8)
    )
    counter = struct.pack(">Q", int(datetime.datetime.now().timestamp() // 30))
    hmac_hash = hmac.new(key, counter, hashlib.sha1).digest()
    offset = hmac_hash[-1] & 0x0F
    code = (
        struct.unpack(">I", hmac_hash[offset : offset + 4])[0] & 0x7FFFFFFF
    ) % 1000000
    return f"{code:06d}"
  except Exception:
    return "123456"


def generate_random_base32():
  alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
  return "".join(random.choice(alphabet) for _ in range(16))


def check_subscription(chat_id):
  try:
    member = bot.get_chat_member(REQUIRED_CHANNEL, chat_id)
    if member.status in ["member", "administrator", "creator"]:
      return True
  except Exception:
    pass
  return False


def get_sub_markup():
  markup = types.InlineKeyboardMarkup(row_width=1)
  markup.add(
      types.InlineKeyboardButton(
          "📢 Join Channel",
          url=f"https://t.me/{REQUIRED_CHANNEL.replace('@', '')}",
      )
  )
  markup.add(
      types.InlineKeyboardButton(
          "✅ Joined / Check", callback_data="check_subscription"
      )
  )
  return markup


def get_main_menu():
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  markup.add(
      types.KeyboardButton("🚀 Start Work"),
      types.KeyboardButton("💰 Balance"),
      types.KeyboardButton("💸 Withdraw"),
      types.KeyboardButton("👥 Referrals"),
      types.KeyboardButton("🏆 Leaderboard"),
      types.KeyboardButton("📊 Statistics"),
      types.KeyboardButton("🎧 Support"),
      types.KeyboardButton("❓ Help"),
  )
  return markup


def get_cancel_markup():
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
  markup.add(types.KeyboardButton("❌ Cancel Process"))
  return markup


@bot.message_handler(commands=["start"])
def send_welcome(message):
  chat_id = message.chat.id
  get_user(chat_id)
  update_user(chat_id, state=None)

  if not check_subscription(chat_id):
    bot.send_message(
        chat_id,
        "⚠️ **Please join our update channel first to use Early Life Bot!**\n\nAfter"
        " joining, click the check button below.",
        reply_markup=get_sub_markup(),
        parse_mode="Markdown",
    )
    return

  welcome_text = (
      f"👋 Welcome to Early Life Bot, {message.from_user.first_name}!\n\n🤖 Earn"
      " money by completing tasks.\nPlease use the menu below to start working!"
  )
  bot.send_message(chat_id, welcome_text, reply_markup=get_main_menu())


@bot.message_handler(content_types=["text"])
def handle_messages(message):
  text = message.text
  chat_id = message.chat.id
  user = message.from_user
  u_data = get_user(chat_id)
  state = u_data.get("state", None)

  if text == "❌ Cancel Process":
    update_user(chat_id, state=None)
    bot.send_message(
        chat_id,
        "❌ Process Cancelled. Use the menu below to continue.",
        reply_markup=get_main_menu(),
    )
    return

  if not check_subscription(chat_id):
    bot.send_message(
        chat_id,
        "⚠️ Please join our channel first!",
        reply_markup=get_sub_markup(),
    )
    return

  if text == "🚀 Start Work":
    update_user(chat_id, state=None)
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(
            "📘 1. Facebook Tasks", callback_data="task_facebook"
        ),
        types.InlineKeyboardButton(
            "📷 2. Instagram Tasks", callback_data="task_instagram"
        ),
        types.InlineKeyboardButton(
            "📧 3. Gmail Task (Coming Soon)", callback_data="task_off_alert"
        ),
    )
    bot.send_message(
        chat_id,
        "📌 Please select a category to start working:",
        reply_markup=markup,
    )
    return

  elif text == "💰 Balance":
    update_user(chat_id, state=None)
    bot.send_message(
        chat_id, f"💰 Your Current Balance: ${u_data['balance']:.2f}"
    )
    return

  elif text == "💸 Withdraw":
    update_user(chat_id, state=None)
    if u_data["balance"] < 0.20:
      bot.send_message(
          chat_id,
          "⚠️ Insufficient balance for withdrawal. Minimum balance must be"
          " $0.20.",
      )
    else:
      markup = types.InlineKeyboardMarkup(row_width=1)
      markup.add(
          types.InlineKeyboardButton("Bkash", callback_data="wd_bkash"),
          types.InlineKeyboardButton("Binance", callback_data="wd_binance"),
          types.InlineKeyboardButton("BEP20 Address", callback_data="wd_bep20"),
      )
      bot.send_message(
          chat_id, "💳 Please select your payout method:", reply_markup=markup
      )
    return

  elif text == "👥 Referrals":
    update_user(chat_id, state=None)
    ref_link = f"https://t.me/{bot.get_me().username}?start={chat_id}"
    ref_text = (
        "👥 Referral Program\n\nInvite friends and earn lifetime commission on"
        f" their task earnings!\n\n🔗 Your Referral Link:\n{ref_link}\n\n📊 Total"
        f" Referrals: {u_data['referrals']}\n💰 Total Commission Earned:"
        f" ${u_data['commission']:.3f}"
    )
    bot.send_message(chat_id, ref_text)
    return

  elif text == "🏆 Leaderboard":
    update_user(chat_id, state=None)
    bot.send_message(
        chat_id, "🏆 Referral Earnings Leaderboard\n\nNo records yet."
    )
    return

  elif text == "📊 Statistics":
    update_user(chat_id, state=None)
    stats_text = (
        f"📊 Your Work Statistics\n\n📝 Total Submitted:"
        f" {u_data['total_submitted']}\n✅ Total Success:"
        f" {u_data['total_success']}\n⏳ Review Pending:"
        f" {u_data['review_pending']}\n❌ Admin Rejected:"
        f" {u_data['admin_rejected']}\n🤖 Bot Rejected:"
        f" {u_data['bot_rejected']}"
    )
    bot.send_message(chat_id, stats_text)
    return

  elif text == "🎧 Support":
    update_user(chat_id, state=None)
    bot.send_message(
        chat_id,
        f"🎧 For any help or issues, contact our support admin:\n👉"
        f" {SUPPORT_USERNAME}",
    )
    return

  elif text == "❓ Help":
    update_user(chat_id, state=None)
    bot.send_message(
        chat_id, f"ℹ️ For any assistance, contact our help desk:\n👉 {HELP_USERNAME}"
    )
    return

  elif state == "WAITING_IG_USERNAME":
    ig_user = text
    secret_key = generate_random_base32()
    live_code = generate_totp(secret_key)

    update_user(
        chat_id,
        state=None,
        total_submitted=u_data["total_submitted"] + 1,
        review_pending=u_data["review_pending"] + 1,
        pending_reward=INSTAGRAM_2FA_REWARD,
    )

    log_to_google_sheet(
        "Instagram 2FA",
        user.username,
        chat_id,
        ig_user,
        "N/A",
        "N/A",
        secret_key,
        "N/A",
        "N/A",
    )

    admin_msg = (
        f"🚨 New Instagram 2FA Task (${INSTAGRAM_2FA_REWARD})\n\n👤 Worker:"
        f" @{user.username or 'None'} ({chat_id})\n📸 IG Username:"
        f" {ig_user}\n🔑 Generated Secret: {secret_key}\n🔢 Current 2FA Code:"
        f" {live_code}"
    )
    send_admin_submission(admin_msg, chat_id)

  elif state == "WAITING_WITHDRAW_AMOUNT":
    try:
      amount = float(text)
    except ValueError:
      bot.send_message(
          chat_id, "⚠️ Please enter a valid number for the amount!"
      )
      return

    if amount < 0.20:
      bot.send_message(chat_id, "⚠️ Minimum withdrawal amount is $0.20!")
      return

    if amount > u_data["balance"]:
      bot.send_message(
          chat_id,
          f"⚠️ You do not have enough balance! Your balance is"
          f" ${u_data['balance']:.2f}",
      )
      return

    update_user(
        chat_id,
        withdraw_amount=amount,
        state="WAITING_WITHDRAW_DETAILS",
    )
    method = u_data.get("withdraw_method")
    bot.send_message(
        chat_id,
        f"📱 Please send your {method} account number/address for payment:",
        reply_markup=get_cancel_markup(),
    )

  elif state == "WAITING_WITHDRAW_DETAILS":
    method = u_data.get("withdraw_method")
    amount = u_data.get("withdraw_amount")
    update_user(chat_id, state=None)
    admin_msg = (
        f"💸 New Withdrawal Request!\n\n👤 User: @{user.username or 'None'}"
        f" ({chat_id})\n💵 Amount: ${amount:.2f}\n💳 Method:"
        f" {method}\n📋 Details: {text}"
    )
    approval_markup = types.InlineKeyboardMarkup(row_width=2)
    approval_markup.add(
        types.InlineKeyboardButton(
            "✅ Approve Payout", callback_data=f"wd_app_{chat_id}"
        ),
        types.InlineKeyboardButton(
            "❌ Reject Payout", callback_data=f"wd_rej_{chat_id}"
        ),
    )
    try:
      bot.send_message(ADMIN_CHAT_ID, admin_msg, reply_markup=approval_markup)
    except Exception:
      pass
    bot.send_message(
        chat_id,
        "✅ Withdrawal request submitted successfully! Admin will process it"
        " soon.",
        reply_markup=get_main_menu(),
    )


def send_admin_submission(admin_msg, chat_id):
  approval_markup = types.InlineKeyboardMarkup(row_width=2)
  approval_markup.add(
      types.InlineKeyboardButton("✅ Approve", callback_data=f"app_{chat_id}"),
      types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_{chat_id}"),
  )
  try:
    bot.send_message(ADMIN_CHAT_ID, admin_msg, reply_markup=approval_markup)
  except Exception:
    pass
  bot.send_message(
      chat_id,
      "✅ Task Submitted Successfully! Admin will review within 30 minutes.",
      reply_markup=get_main_menu(),
  )


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
  chat_id = call.message.chat.id
  data = call.data
  u_data = get_user(chat_id)

  if data == "check_subscription":
    if check_subscription(chat_id):
      try:
        bot.delete_message(chat_id, call.message.message_id)
      except Exception:
        pass
      bot.send_message(
          chat_id,
          "✅ Thank you for joining! You can now use the bot.",
          reply_markup=get_main_menu(),
      )
    else:
      bot.answer_callback_query(
          call.id,
          "⚠️ You haven't joined the channel yet! Please join first.",
          show_alert=True,
      )
    return

  if not check_subscription(chat_id):
    bot.answer_callback_query(
        call.id,
        "⚠️ Please join the update channel first to continue!",
        show_alert=True,
    )
    return

  if data.startswith("app_"):
    target_user = int(data.split("_")[1])
    bot.answer_callback_query(call.id, "Task Approved Successfully!")
    target_u_data = get_user(target_user)
    reward = target_u_data.get("pending_reward", INSTAGRAM_2FA_REWARD)

    new_balance = target_u_data["balance"] + reward
    new_success = target_u_data["total_success"] + 1
    new_pending = (
        target_u_data["review_pending"] - 1
        if target_u_data["review_pending"] > 0
        else 0
    )

    update_user(
        target_user,
        balance=new_balance,
        total_success=new_success,
        review_pending=new_pending,
        pending_reward=0.0,
    )

    try:
      bot.send_message(
          target_user,
          f"🎉 Your task has been approved! Reward of ${reward:.3f} added to your"
          " balance.",
      )
      bot.edit_message_text(
          call.message.text + "\n\n✅ STATUS: APPROVED BY ADMIN",
          chat_id,
          call.message.message_id,
      )
    except Exception:
      pass
    return

  elif data.startswith("rej_"):
    target_user = int(data.split("_")[1])
    bot.answer_callback_query(call.id, "Task Rejected!")
    target_u_data = get_user(target_user)

    new_rejected = target_u_data["admin_rejected"] + 1
    new_pending = (
        target_u_data["review_pending"] - 1
        if target_u_data["review_pending"] > 0
        else 0
    )

    update_user(
        target_user,
        admin_rejected=new_rejected,
        review_pending=new_pending,
        pending_reward=0.0,
    )

    try:
      bot.send_message(
          target_user, "❌ Your submitted task was rejected by the admin."
      )
      bot.edit_message_text(
          call.message.text + "\n\n❌ STATUS: REJECTED BY ADMIN",
          chat_id,
          call.message.message_id,
      )
    except Exception:
      pass
    return

  elif data.startswith("wd_app_"):
    target_user = int(data.split("_")[2])
    bot.answer_callback_query(call.id, "Payout Approved!")
    try:
      bot.send_message(
          target_user,
          "🎉 Your withdrawal request has been approved and paid by admin!",
      )
      bot.edit_message_text(
          call.message.text + "\n\n✅ STATUS: PAYOUT APPROVED",
          chat_id,
          call.message.message_id,
      )
    except Exception:
      pass
    return

  elif data.startswith("wd_rej_"):
    target_user = int(data.split("_")[2])
    bot.answer_callback_query(call.id, "Payout Rejected!")
    try:
      bot.send_message(
          target_user, "❌ Your withdrawal request was rejected by admin."
      )
      bot.edit_message_text(
          call.message.text + "\n\n✅ STATUS: PAYOUT REJECTED",
          chat_id,
          call.message.message_id,
      )
    except Exception:
      pass
    return

  elif data == "task_facebook":
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(
            f"🔥 Facebook Hotmail (${FB_HOTMAIL_REWARD}) [ON]",
            callback_data="fb_task_hotmail_info",
        ),
        types.InlineKeyboardButton(
            f"🍪 Fb Cookies (${FB_COOKIES_REWARD}) [ON]",
            callback_data="fb_task_cookies_info",
        ),
        types.InlineKeyboardButton(
            f"📄 Hotmail 10 Page (${HOTMAIL_10_PAGE_REWARD}) [ON]",
            callback_data="fb_task_hotmail_10_page_info",
        ),
        types.InlineKeyboardButton("🔙 Back", callback_data="back_to_main"),
    )
    bot.edit_message_text(
        "📂 Choose Facebook Task Type:",
        chat_id,
        call.message.message_id,
        reply_markup=markup,
    )
    return

  elif data == "task_instagram":
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(
            f"📸 Instagram 2FA (${INSTAGRAM_2FA_REWARD}) [ON]",
            callback_data="ig_task_2fa_start",
        ),
        types.InlineKeyboardButton("🔙 Back", callback_data="back_to_main"),
    )
    bot.edit_message_text(
        "📂 Choose Instagram Task Type:",
        chat_id,
        call.message.message_id,
        reply_markup=markup,
    )
    return

  elif data == "task_off_alert":
    bot.answer_callback_query(
        call.id, "⚠️ This task is currently turned off by admin!", show_alert=True
    )
    return

  elif data == "back_to_main":
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(
            "📘 1. Facebook Tasks", callback_data="task_facebook"
        ),
        types.InlineKeyboardButton(
            "📷 2. Instagram Tasks", callback_data="task_instagram"
        ),
        types.InlineKeyboardButton(
            "📧 3. Gmail Task (Coming Soon)", callback_data="task_off_alert"
        ),
    )
    bot.edit_message_text(
        "📌 Please select a category to start working:",
        chat_id,
        call.message.message_id,
        reply_markup=markup,
    )
    return

  elif data == "ig_task_2fa_start":
    update_user(chat_id, state="WAITING_IG_USERNAME")
    bot.send_message(
        chat_id,
        "📸 Please send your Instagram Username to generate 2FA session:",
        reply_markup=get_cancel_markup(),
    )
    return

  elif data in ["wd_bkash", "wd_binance", "wd_bep20"]:
    method = data.replace("wd_", "").upper()
    update_user(
        chat_id, withdraw_method=method, state="WAITING_WITHDRAW_AMOUNT"
    )
    bot.send_message(
        chat_id,
        f"✅ You selected {method}.\n💵 Please enter the amount you want to"
        f" withdraw (Balance: ${u_data['balance']:.2f}):",
        reply_markup=get_cancel_markup(),
    )
    return


if __name__ == "__main__":
  print(
      "Early Life Bot is running with Auto 2FA Generator & Google Sheets"
      " sync..."
  )
  try:
    bot.remove_webhook()
  except Exception:
    pass
  bot.infinity_polling(skip_pending=True)
