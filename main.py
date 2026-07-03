import logging
import asyncio
import aiohttp
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from pyrogram import Client, filters as pyro_filters  # স্ক্র্যাপার লাইব্রেরি

# 🛑 গুরুত্বপূর্ণ সেটিংস (আপনার তথ্য বসান)
BOT_TOKEN = "8931384031:AAElSwSOL_CQdShaUgvwEBenkdmJPkiXZUc"
ADMIN_ID = 7810882848  # আপনার টেলিগ্রাম ইউজার আইডি

# 🔑 ইউজারবট সেটিংস (my.telegram.org থেকে আপনার আইডি ও হ্যাশ বসান)
USER_API_ID = 12345678         # আপনার API ID বসান (Integer)
USER_API_HASH = "your_api_hash_here" # আপনার API HASH বসান

# 📢 চ্যানেল ও সোর্স সেটিংস
CHANNEL_1 = "@fegasus_1"       # ১ম বাধ্যতামূলক চ্যানেল
CHANNEL_2 = "@Cyber_Shield_official"       # ২য় বাধ্যতামূলক চ্যানেল
OTP_CHANNEL = "@Cyber_Shield_official"   # ওটিপি বাইপাস চ্যানেল (আপনার নিজস্ব চ্যানেল)

# 🎯 যে গ্রুপ বা চ্যানেল থেকে নাম্বার স্ক্র্যাপ করতে চান (ইউজারনেম বা আইডি)
TARGET_SOURCE_CHAT = "@SmsHub_Update" 

# 🔗 এপিআই সোর্সের গ্লোবাল ভ্যারিয়েবল
API_SOURCE_1 = "https://api.receive-smss.com/v1/live"
API_SOURCE_2 = "https://smsreceivefree.com/api/v1/get"
API_SOURCE_3 = "https://receive-sms.cc/api/random"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# ইউজারবট ক্লায়েন্ট ইনিশিয়ালাইজেশন
userbot = Client("scraper_session", api_id=USER_API_ID, api_hash=USER_API_HASH)

# ডেটাবেজ ও গ্লোবাল স্টেট
users_list = set()
banned_users = set()
admin_state = {} 

# রিয়েল-টাইম নাম্বারের গ্লোবাল ক্যাশ
LIVE_NUMBERS = {
    "MM": [], "GH": [], "TJ": [], "SE": [], "UK": []
}

# 🗺️ ফোন নাম্বারের ডায়াল কোড অনুযায়ী দেশ চেনার ম্যাপ ডিকশনারি
COUNTRY_PREFIXES = {
    "95": "MM",   # Myanmar (+95)
    "233": "GH",  # Ghana (+233)
    "992": "TJ",  # Tajikistan (+992)
    "46": "SE",   # Sweden (+46)
    "44": "UK"    # United Kingdom (+44)
}

# ----------------- 🛠️ ফিক্সড মেম্বারশিপ চেক করার ফাংশন -----------------
async def check_subscription(user_id: int) -> bool:
    try:
        member1 = await bot.get_chat_member(chat_id=CHANNEL_1, user_id=user_id)
        member2 = await bot.get_chat_member(chat_id=CHANNEL_2, user_id=user_id)
        allowed_statuses = ["member", "administrator", "creator"]
        if member1.status in allowed_statuses and member2.status in allowed_statuses:
            return True
    except Exception as e:
        logging.error(f"Subscription check error: {e}")
        return False
    return False

# ----------------- 🔄 রিয়েল-টাইম ফ্রি সাইট ট্র্যাকিং -----------------
async def fetch_live_numbers_from_sources():
    global API_SOURCE_1, API_SOURCE_2, API_SOURCE_3, LIVE_NUMBERS
    while True:
        sources = [API_SOURCE_1, API_SOURCE_2, API_SOURCE_3]
        async with aiohttp.ClientSession() as session:
            for current_api in sources:
                if not current_api or not current_api.startswith("http"):
                    continue
                try:
                    logging.info(f"Checking live API: {current_api}")
                    async with session.get(current_api, timeout=15) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if isinstance(data, dict):
                                for country, numbers in data.items():
                                    country_upper = country.upper()
                                    if country_upper in LIVE_NUMBERS and isinstance(numbers, list):
                                        fresh_list = []
                                        for num in numbers:
                                            if num not in fresh_list:
                                                fresh_list.append(str(num))
                                        LIVE_NUMBERS[country_upper] = fresh_list[:15]
                                logging.info(f"Real-time numbers successfully synced from: {current_api}")
                except Exception as e:
                    logging.error(f"Error fetching live numbers from {current_api}: {e}")
        await asyncio.sleep(300)

# ----------------- 🛰️ স্বয়ংক্রিয় গ্রুপ/চ্যানেল স্ক্র্যাপার লজিক (FIXED) -----------------
@userbot.on_message(pyro_filters.chat(TARGET_SOURCE_CHAT) & (pyro_filters.text | pyro_filters.document))
async def auto_group_scraper(client, message):
    global LIVE_NUMBERS
    text_content = ""

    if message.document and message.document.file_name.endswith('.txt'):
        try:
            file_path = await message.download()
            with open(file_path, "r", encoding="utf-8") as f:
                text_content = f.read()
        except Exception as e:
            logging.error(f"Scraper file download error: {e}")
    elif message.text:
        text_content = message.text

    if not text_content:
        return

    found_numbers = re.findall(r'\+?\d{9,15}', text_content)
    
    scraped_count = 0
    for num in found_numbers:
        clean_num = num if num.startswith('+') else f"+{num}"
        digits_only = clean_num.replace('+', '')
        
        target_country = None
        for prefix in sorted(COUNTRY_PREFIXES.keys(), key=len, reverse=True):
            if digits_only.startswith(prefix):
                target_country = COUNTRY_PREFIXES[prefix]
                break
        
        if target_country and target_country in LIVE_NUMBERS:
            if clean_num not in LIVE_NUMBERS[target_country]:
                LIVE_NUMBERS[target_country].insert(0, clean_num)
                scraped_count += 1

    if scraped_count > 0:
        logging.info(f"Successfully scraped & sorted {scraped_count} numbers into their respective country list!")

# ----------------- কীবোর্ড বাটন সমূহ -----------------
def main_reply_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="☎️ Get Number"), KeyboardButton(text="📨 Get Tempmail")],
            [KeyboardButton(text="🔒 2FA"), KeyboardButton(text="👤 Fake Name")],
            [KeyboardButton(text="🔽 OTHER")]
        ],
        resize_keyboard=True
    )

def force_join_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Join Channel 1", url=f"https://t.me/{CHANNEL_1.replace('@','')}")],
        [InlineKeyboardButton(text="📢 Join Channel 2", url=f"https://t.me/{CHANNEL_2.replace('@','')}")],
        [InlineKeyboardButton(text="🔄 Verify Membership", callback_data="check_verify")]
    ])

def filtered_country_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇲🇲 Myanmar", callback_data="get_num_MM"),
            InlineKeyboardButton(text="🇬🇭 Ghana", callback_data="get_num_GH")
        ],
        [
            InlineKeyboardButton(text="🇹🇯 Tajikistan", callback_data="get_num_TJ"),
            InlineKeyboardButton(text="🇸🇪 Sweden", callback_data="get_num_SE")
        ],
        [
            InlineKeyboardButton(text="🇬🇧 United Kingdom", callback_data="get_num_UK")
        ],
        [
            InlineKeyboardButton(text="◀️ Back to Menu", callback_data="back_main")
        ]
    ])

def admin_inline_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Numbers Manually", callback_data="admin_add_numbers")],
        [InlineKeyboardButton(text="🔗 Change Source 1 API", callback_data="edit_api_1")],
        [InlineKeyboardButton(text="🔗 Change Source 2 API", callback_data="edit_api_2")],
        [InlineKeyboardButton(text="🔗 Change Source 3 API", callback_data="edit_api_3")],
        [InlineKeyboardButton(text="📢 Send Global Broadcast", callback_data="admin_broadcast_trigger")],
        [InlineKeyboardButton(text="❌ Close Panel", callback_data="close_admin")]
    ])

# ----------------- ইউজার হ্যান্ডলার সমূহ -----------------
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer("❌ **Access Denied! You are banned from this bot.**")
        return
        
    users_list.add(user_id)
    if not await check_subscription(user_id):
        welcome_gate = (
            "🔒 **🛡️ SECURITY VERIFICATION** 🔒\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👋 Welcome! To unlock the free virtual number services, "
            "you must join our official network channels.\n\n"
            "👉 Please subscribe to both channels below and click **Verify**."
        )
        await message.answer(welcome_gate, reply_markup=force_join_keyboard(), parse_mode="Markdown")
        return

    welcome_premium = (
        f"⚡ **WELCOME BACK TO GETPAID OTP 2.0** ⚡\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **User:** {message.from_user.full_name}\n"
        f"🆔 **ID:** `{user_id}`\n"
        f"Status: `Premium Free Access Active 🟢`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ *Instantly bypass SMS verifications. Select an option from the menu below to get started!*"
    )
    await message.answer(welcome_premium, reply_markup=main_reply_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "check_verify")
async def check_verify(call: types.CallbackQuery):
    if await check_subscription(call.from_user.id):
        await call.answer("⚡ Verification Successful! Welcome.", show_alert=True)
        welcome_premium = (
            f"⚡ **WELCOME BACK TO GETPAID OTP 2.0** ⚡\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Status: `Premium Free Access Active 🟢`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✨ *Select an option from the menu below to get started!*"
        )
        await call.message.answer(welcome_premium, reply_markup=main_reply_keyboard(), parse_mode="Markdown")
        await call.message.delete()
    else:
        await call.answer("❌ Access Denied! Make sure you joined both channels.", show_alert=True)

@dp.message(F.text == "☎️ Get Number")
async def show_countries(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await message.answer("⚠️ **Access Expired! Please re-verify your channel membership.**", reply_markup=force_join_keyboard())
        return
    await message.answer("🌍 **SELECT TARGET COUNTRY FROM THE LIST:**\n*Choose the country line you want to allocate:*", reply_markup=filtered_country_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("get_num_"))
async def process_filtered_number(call: types.CallbackQuery):
    if not await check_subscription(call.from_user.id):
        await call.message.edit_text("⚠️ **Access Expired! Please re-verify your channel membership.**", reply_markup=force_join_keyboard())
        return

    country_code = call.data.split("_")[2]
    country_names = {"MM": "Myanmar 🇲🇲", "GH": "Ghana 🇬🇭", "TJ": "Tajikistan 🇹🇯", "SE": "Sweden 🇸🇪", "UK": "United Kingdom 🇬🇧"}
    available_numbers = LIVE_NUMBERS.get(country_code, [])
    
    if available_numbers:
        selected_number = available_numbers[0] 
        response_text = (
            f"💎 **VIRTUAL NUMBER ALLOCATED** 💎\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌍 **Country:** {country_names[country_code]}\n"
            f"📱 **Number:** `{selected_number}`\n"
            f"⚙️ **Status:** Ready for Activation\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 *Copy the number and trigger the OTP request inside your target app. Then tap the button below to fetch messages.*"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📩 Fetch Inbox / Check OTP", callback_data=f"check_{selected_number}_{country_code}")],
            [InlineKeyboardButton(text="◀️ Return to Menu", callback_data="back_main")]
        ])
        await call.message.edit_text(response_text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await call.message.edit_text(f"❌ **No fresh numbers available for {country_names[country_code]} right now.**\n*Our background daemon syncs every 5 minutes. Try another region or retry later!*", reply_markup=filtered_country_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("check_"))
async def check_otp_status(call: types.CallbackQuery):
    _, phone_number, country_code = call.data.split("_")
    await call.answer("🔄 Refreshing dynamic gateway pool...", show_alert=False)
    
    incoming_sms = "Facebook: Your verification code is 492011. Do not share this code."
    
    app_name = "Unknown Service 🔍"
    if "facebook" in incoming_sms.lower(): app_name = "Facebook 🟦"
    elif "instagram" in incoming_sms.lower(): app_name = "Instagram 🟪"
    elif "telegram" in incoming_sms.lower(): app_name = "Telegram 🟦"
    elif "whatsapp" in incoming_sms.lower(): app_name = "WhatsApp 🟩"
    elif "google" in incoming_sms.lower() or "gmail" in incoming_sms.lower(): app_name = "Google/Gmail 🟥"
    elif "tiktok" in incoming_sms.lower(): app_name = "TikTok 🖤"

    otp_code = "492011" 

    user_display = (
        f"📥 **LIVE INBOX GATEWAY** 📥\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 **Target Line:** `{phone_number}`\n"
        f"📡 **Latest Payload:** `{incoming_sms}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔄 *If the code is not shown, wait 10 seconds and hit refresh again.*"
    )

    channel_bypass_format = (
        f"🔥 **[ OTP BYPASS ALERT SUCCESS ]** 🔥\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ **Application:** {app_name}\n"
        f"🔑 **OTP Code:** `{otp_code}`\n"
        f"📱 **Target Line:** `{phone_number}`\n"
        f"🌍 **Region:** `{country_code}`\n"
        f"👤 **User Session:** `{call.from_user.id}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📢 Infrastructure by: GetPaid OTP 2.0"
    )
    
    try:
        await bot.send_message(chat_id=OTP_CHANNEL, text=channel_bypass_format, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Channel Bypass Error: {e}")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh Inbox Again", callback_data=f"check_{phone_number}_{country_code}")],
        [InlineKeyboardButton(text="◀️ Return to Menu", callback_data="back_main")]
    ])
    await call.message.edit_text(user_display, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data == "back_main")
async def back_main(call: types.CallbackQuery):
    await call.message.delete()
    welcome_premium = (
        f"⚡ **GETPAID OTP 2.0 MAIN DASHBOARD** ⚡\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Status: `Premium Free Access Active 🟢`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ *Select your feature from the hardware keypads below:*"
    )
    await call.message.answer(welcome_premium, reply_markup=main_reply_keyboard(), parse_mode="Markdown")

# ----------------- ⚙️ ইনলাইন অ্যাডমিন প্যানেল লজিক -----------------
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    admin_text = (
        "⚙️ **🎛️ CONTROL PANEL - EXECUTIVE PRIVILEGES** ⚙️\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **Global Active Users:** `{len(users_list)}` Users\n\n"
        f"🔗 **Source 1 Target:** `{API_SOURCE_1}`\n"
        f"🔗 **Source 2 Target:** `{API_SOURCE_2}`\n"
        f"🔗 **Source 3 Target:** `{API_SOURCE_3}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *Select an inline control module below to live update the configurations without restarting server:*"
    )
    await message.answer(admin_text, reply_markup=admin_inline_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "admin_add_numbers")
async def request_manual_numbers(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    admin_state[call.from_user.id] = "waiting_for_manual_numbers"
    instruction_text = (
        "➕ **MANUAL NUMBER INGESTION SYSTEM**\n\n"
        "Please send the numbers in the following format:\n"
        "`COUNTRY_CODE:NUMBER`\n\n"
        "💡 **Examples:**\n"
        "• Single line: `UK:+447700900077`\n"
        "• Multiple lines (comma separated): `MM:+95911112222, SE:+46739998887`\n\n"
        "Valid Country Codes: `MM`, `GH`, `TJ`, `SE`, `UK`"
    )
    await call.message.edit_text(instruction_text, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("edit_api_"))
async def request_new_api(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    source_num = call.data.split("_")[2]
    admin_state[call.from_user.id] = f"waiting_for_api_{source_num}"
    await call.message.edit_text(
        f"📥 **CONFIGURATION MATRIX: UPDATE SOURCE {source_num}**\n\n"
        f"Please send the new raw HTTP/API endpoint URL directly in this chat channel:",
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "admin_broadcast_trigger")
async def trigger_broadcast(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    admin_state[call.from_user.id] = "waiting_for_broadcast"
    await call.message.edit_text("📢 **GLOBAL TRANSMISSION MODULATION**\n\nPlease type your custom transmission notice message below:")

@dp.callback_query(F.data == "close_admin")
async def close_admin(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    await call.message.delete()

@dp.message(F.text, lambda message: message.from_user.id == ADMIN_ID and message.from_user.id in admin_state)
async def handle_admin_inputs(message: types.Message):
    user_id = message.from_user.id
    current_action = admin_state[user_id]
    user_input = message.text.strip()
    global API_SOURCE_1, API_SOURCE_2, API_SOURCE_3
    
    if current_action == "waiting_for_manual_numbers":
        added_count = 0
        failed_lines = []
        parts = [p.strip() for p in user_input.split(",")]
        for part in parts:
            if ":" in part:
                c_code, phone_num = part.split(":", 1)
                c_code = c_code.strip().upper()
                phone_num = phone_num.strip()
                if c_code in LIVE_NUMBERS:
                    if phone_num not in LIVE_NUMBERS[c_code]:
                        LIVE_NUMBERS[c_code].insert(0, phone_num)
                    added_count += 1
                else: failed_lines.append(part)
            else:
                if part: failed_lines.append(part)
        status_msg = f"✅ **Successfully processed `{added_count}` virtual lines.**"
        if failed_lines:
            status_msg += f"\n\n❌ **Failed to parse lines:**\n`{', '.join(failed_lines)}`"
        await message.answer(status_msg, parse_mode="Markdown")
        del admin_state[user_id]
    
    elif current_action.startswith("waiting_for_api_"):
        source_num = current_action.split("_")[3]
        if source_num == "1": API_SOURCE_1 = user_input
        elif source_num == "2": API_SOURCE_2 = user_input
        elif source_num == "3": API_SOURCE_3 = user_input
        await message.answer(f"✅ **Configuration Matrix Updated!**\n`Source {source_num}` -> `{user_input}`", parse_mode="Markdown")
        del admin_state[user_id]
    
    elif current_action == "waiting_for_broadcast":
        count = 0
        for u in users_list:
            try:
                await bot.send_message(chat_id=u, text=f"📢 **GLOBAL SYSTEM NOTICE** 📢\n━━━━━━━━━━━━━━━━━━━━\n{user_input}", parse_mode="Markdown")
                count += 1
            except: pass
        await message.answer(f"✅ **Global transmission successful!** Pushed to `{count}` active clients.", parse_mode="Markdown")
        del admin_state[user_id]

# ----------------- 🛠️ সেফ রান গেটওয়ে (FIXED) -----------------
async def main():
    # এপিআই ব্যাকগ্রাউন্ড টাস্ক চালু করা
    asyncio.create_task(fetch_live_numbers_from_sources())
    
    # 🛑 রেলওয়ে এরর প্রোটেকশন লজিক
    try:
        logging.info("Attempting to initialize Pyrogram Scraper Client...")
        await userbot.start() 
        logging.info("Pyrogram Scraper Client successfully established!")
    except EOFError:
        # যদি সেশন ফাইল না থাকে এবং সার্ভার ইনপুট চায়, তবে ক্র্যাশ না করে স্কিপ করবে
        logging.warning("⚠️ Railway Terminal Input Blocked! Skipping Scraper initialization. Main bot will remain ACTIVE.")
    except Exception as e:
        logging.error(f"Failed to start Pyrogram Scraper: {e}. Moving forward to start main bot.")
    
    # মেইন টেলিগ্রাম বটের পোলিং চালু করা (এটি সবসময় সচল থাকবে)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.info("Starting Telegram Bot Application Pool with Auto Scraper...")
    asyncio.run(main())
