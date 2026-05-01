import sqlite3
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = ""

# 👑 твой Telegram ID
ADMIN_ID = 


# =========================
# 🗄️ DATABASE
# =========================

def init_db():
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        phone TEXT,
        date TEXT,
        time TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(date, time)
    )
    """)

    conn.commit()
    conn.close()


def save_booking(user_id, username, phone, date, time):
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()

    try:
        cursor.execute("""
        INSERT INTO bookings (user_id, username, phone, date, time)
        VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, phone, date, time))

        conn.commit()
        return True

    except sqlite3.IntegrityError:
        return False

    finally:
        conn.close()


def get_booked_times(date):
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()

    cursor.execute("SELECT time FROM bookings WHERE date = ?", (date,))
    rows = cursor.fetchall()

    conn.close()
    return [r[0] for r in rows]


def get_all_bookings():
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT date, time, phone, username
    FROM bookings
    ORDER BY date, time
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows


def delete_booking(date, time):
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM bookings
    WHERE date = ? AND time = ?
    """, (date, time))

    conn.commit()
    conn.close()


# =========================
# 📅 DATES
# =========================

def get_dates_keyboard():
    buttons = []
    today = datetime.now()

    for i in range(1, 6):
        day = today + timedelta(days=i)
        date_str = day.strftime("%Y-%m-%d")

        buttons.append([
            InlineKeyboardButton(
                date_str,
                callback_data=f"date|{date_str}"
            )
        ])

    return InlineKeyboardMarkup(buttons)


# =========================
# ⏰ TIMES
# =========================

def get_time_keyboard(date):
    all_times = ["10:00", "12:00", "14:00", "16:00", "18:00"]
    booked = get_booked_times(date)

    buttons = []

    for t in all_times:
        if t not in booked:
            buttons.append([
                InlineKeyboardButton(
                    t,
                    callback_data=f"time|{date}|{t}"
                )
            ])

    if not buttons:
        buttons = [[InlineKeyboardButton("Нет слотов", callback_data="none")]]

    return InlineKeyboardMarkup(buttons)


# =========================
# 📞 PHONE
# =========================

def phone_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Отправить номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


# =========================
# 🤖 START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "👋 Запись на массаж\n\n📞 Отправьте номер телефона:",
        reply_markup=phone_keyboard()
    )


# =========================
# 📞 PHONE HANDLER
# =========================

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact

    if not contact:
        return

    context.user_data["phone"] = contact.phone_number

    await update.message.reply_text(
        "📅 Выберите дату:",
        reply_markup=get_dates_keyboard()
    )


# =========================
# 📊 CALLBACKS
# =========================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    # ---------------- DATE ----------------
    if data.startswith("date|"):
        _, date = data.split("|", 1)
        context.user_data["date"] = date

        await query.message.edit_text(
            f"📅 {date}\nВыберите время:",
            reply_markup=get_time_keyboard(date)
        )

    # ---------------- TIME ----------------
    elif data.startswith("time|"):
        _, date, time = data.split("|")

        user_id = query.from_user.id
        username = query.from_user.username or "no_username"
        phone = context.user_data.get("phone")

        if not phone:
            await query.message.edit_text("❌ Сначала отправьте телефон")
            return

        success = save_booking(user_id, username, phone, date, time)

        if success:
            await query.message.edit_text(
                f"✅ Запись подтверждена!\n\n📅 {date}\n⏰ {time}\n📞 {phone}"
            )
        else:
            await query.message.edit_text(
                "❌ Уже занято",
                reply_markup=get_time_keyboard(date)
            )

    # ---------------- DELETE (ADMIN) ----------------
    elif data.startswith("del|"):
        _, date, time = data.split("|")

        if query.from_user.id != ADMIN_ID:
            await query.answer("Нет доступа", show_alert=True)
            return

        delete_booking(date, time)

        await query.message.edit_text(
            f"🗑 Удалено\n📅 {date}\n⏰ {time}"
        )


# =========================
# 👑 ADMIN BOOKINGS
# =========================

async def bookings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа")
        return

    data = get_all_bookings()

    if not data:
        await update.message.reply_text("📭 Нет записей")
        return

    for date, time, phone, username in data:
        text = (
            f"📅 {date} ⏰ {time}\n"
            f"📞 {phone}\n"
            f"👤 {username}"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Удалить", callback_data=f"del|{date}|{time}")]
        ])

        await update.message.reply_text(text, reply_markup=keyboard)


# =========================
# 🚀 START BOT
# =========================

def main():
    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bookings", bookings_cmd))

    app.add_handler(MessageHandler(filters.CONTACT, get_phone))
    app.add_handler(CallbackQueryHandler(callback_handler))

    print("Bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()
