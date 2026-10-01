import datetime
import logging
import sqlite3
import telebot
from telebot import types

TOKEN = "8833506125:AAF09XldZ6p-niAMMZjspnAfnYK1u8r9nNs"
ADMIN_CHAT_ID = 8444176616
SUPPORT_USERNAME = "@supekrsupper"
REQUIRED_CHANNEL = "@honestcrazy11"
INSTAGRAM_2FA_REWARD = 0.034

bot = telebot.TeleBot(TOKEN)
logging.basicConfig(level=logging.INFO)


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
            state TEXT,
            pending_reward REAL DEFAULT 0.0,
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
            INSERT INTO users (chat_id, balance, total_submitted, total_success, review_pending, state, pending_reward)
            VALUES (?, 0.0, 0, 0, 0, NULL, 0.0)
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
      "state": row[5],
      "pending_reward": row[6],
      "withdraw_method": row[7],
      "withdraw_amount": row[8],
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
      types.KeyboardButton("🎧 Support"),
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
        "⚠️ Please join our update channel first to use Early Life Bot!",
        reply_markup=get_sub_markup(),
    )
    return

  bot.send_message(
      chat_id,
      f"👋 Welcome {message.from_user.first_name}!\nUse the menu below to"
      " start working.",
      reply_markup=get_main_menu(),
  )


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
        chat_id, "❌ Cancelled.", reply_markup=get_main_menu()
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
            f"📸 Instagram 2FA (${INSTAGRAM_2FA_REWARD})",
            callback_data="ig_task_start",
        )
    )
    bot.send_message(
        chat_id, "📌 Select task category:", reply_markup=markup
    )
    return

  elif text == "💰 Balance":
    bot.send_message(
        chat_id, f"💰 Your Balance: ${u_data['balance']:.3f}"
    )
    return

  elif text == "💸 Withdraw":
    if u_data["balance"] < 0.20:
      bot.send_message(
          chat_id, "⚠️ Minimum withdrawal balance is $0.20."
      )
    else:
      markup = types.InlineKeyboardMarkup(row_width=1)
      markup.add(
          types.InlineKeyboardButton("Bkash", callback_data="wd_bkash"),
          types.InlineKeyboardButton("Binance", callback_data="wd_binance"),
      )
      bot.send_message(
          chat_id, "💳 Choose withdrawal method:", reply_markup=markup
      )
    return

  elif text == "🎧 Support":
    bot.send_message(chat_id, f"🎧 Support: {SUPPORT_USERNAME}")
    return

  elif state == "WAITING_IG_USERNAME":
    update_user(
        chat_id,
        state=None,
        total_submitted=u_data["total_submitted"] + 1,
        review_pending=u_data["review_pending"] + 1,
        pending_reward=INSTAGRAM_2FA_REWARD,
    )

    admin_msg = (
        f"🚨 New Instagram Task (${INSTAGRAM_2FA_REWARD})\n\n👤 Worker:"
        f" @{user.username or 'None'} ({chat_id})\n📸 Username: {text}"
    )
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
        "✅ Task Submitted Successfully! Waiting for admin review.",
        reply_markup=get_main_menu(),
    )


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
  chat_id = call.message.chat.id
  data = call.data

  if data == "check_subscription":
    if check_subscription(chat_id):
      try:
        bot.delete_message(chat_id, call.message.message_id)
      except Exception:
        pass
      bot.send_message(
          chat_id, "✅ Verified! Welcome.", reply_markup=get_main_menu()
      )
    else:
      bot.answer_callback_query(
          call.id, "⚠️ Please join the channel first!", show_alert=True
      )
    return

  if data.startswith("app_"):
    target_user = int(data.split("_")[1])
    bot.answer_callback_query(call.id, "Approved!")
    target_u_data = get_user(target_user)
    reward = target_u_data.get("pending_reward", INSTAGRAM_2FA_REWARD)

    update_user(
        target_user,
        balance=target_u_data["balance"] + reward,
        total_success=target_u_data["total_success"] + 1,
        review_pending=max(0, target_u_data["review_pending"] - 1),
        pending_reward=0.0,
    )
    try:
      bot.send_message(
          target_user, f"🎉 Your task approved! +${reward:.3f} added."
      )
      bot.edit_message_text(
          call.message.text + "\n\n✅ APPROVED",
          chat_id,
          call.message.message_id,
      )
    except Exception:
      pass
    return

  elif data.startswith("rej_"):
    target_user = int(data.split("_")[1])
    bot.answer_callback_query(call.id, "Rejected!")
    target_u_data = get_user(target_user)

    update_user(
        target_user,
        review_pending=max(0, target_u_data["review_pending"] - 1),
        pending_reward=0.0,
    )
    try:
      bot.send_message(target_user, "❌ Your task was rejected.")
      bot.edit_message_text(
          call.message.text + "\n\n❌ REJECTED",
          chat_id,
          call.message.message_id,
      )
    except Exception:
      pass
    return

  elif data == "ig_task_start":
    update_user(chat_id, state="WAITING_IG_USERNAME")
    bot.send_message(
        chat_id,
        "📸 Please send your Instagram Username:",
        reply_markup=get_cancel_markup(),
    )
    return


if __name__ == "__main__":
  print("Bot is running...")
  bot.infinity_polling(skip_pending=True)
