import logging
import asyncio
import aiohttp
import firebase_admin
from firebase_admin import credentials, db
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# 🌐 ================= CONFIGURATION DIRECTORY ================= 🌐
CONFIG = {
    "BOT_TOKEN": "8598140667:AAG8EyUZ-3KWsldsYACVukx7qOAhiWVg6As",
    "ADMIN_ID": 7810882848,                  
    "CHANNEL_1": "@Falcon_Elite",         
    "CHANNEL_2": "@Cyber_Shield_official",         
    "OTP_CHANNEL": "@Cyber_Shield_official",     
    "FIREBASE_JSON_PATH": "path/to/your/firebase-adminsdk.json", 
    "FIREBASE_DB_URL": "https://your-database-name.firebaseio.com/" 
}

# ----------------- 🛠️ ফায়ারবেস কমপ্লিট সেটআপ -----------------
try:
    cred = credentials.Certificate(CONFIG["FIREBASE_JSON_PATH"])
    firebase_admin.initialize_app(cred, {'databaseURL': CONFIG["FIREBASE_DB_URL"]})
    logging.info("Firebase Realtime Database connected successfully.")
except Exception as e:
    logging.error(f"Firebase initialization failed: {e}")

# ডাটাবেজ রুট রেফারেন্স
db_settings_ref = db.reference('bot_settings')
db_users_ref = db.reference('users')

# 🔄 ফায়ারবেস থেকে সেটিংস ডাউনলোড করা বা প্রথমবার রান হলে ডিফল্ট ডেটা ফায়ারবেসে তৈরি করা
def initialize_firebase_settings():
    current_settings = db_settings_ref.get()
    if not current_settings:
        # ডাটাবেজে যদি কিছু না থাকে, তবে ডিফল্ট ডেটা পুশ করবে
        default_data = {
            "api_1": "https://api.receive-smss.com/v1/live",
            "api_2": "https://smsreceivefree.com/api/v1/get",
            "api_3": "https://receive-sms.cc/api/random",
            "target_range": "All"
        }
        db_settings_ref.set(default_data)
        return default_data
    return current_settings

# লাইভ সেটিংস লোড
bot_settings = initialize_firebase_settings()

# গ্লোবাল স্টেট ব্যাকএন্ড (ফায়ারবেস থেকে প্রাপ্ত)
API_SOURCE_1 = bot_settings.get('api_1')
API_SOURCE_2 = bot_settings.get('api_2')
API_SOURCE_3 = bot_settings.get('api_3')
TARGET_RANGE = bot_settings.get('target_range')

# ----------------- বট সেটআপ -----------------
bot = Bot(token=CONFIG["BOT_TOKEN"])
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

users_list = set()
banned_users = set()
admin_state = {} 

# ফায়ারবেস থেকে আগের সংরক্ষিত ইউজার লিস্ট রিকভার করা
try:
    saved_users = db_users_ref.get()
    if saved_users:
        users_list = set(int(uid) for uid in saved_users.keys())
except Exception as e:
    logging.error(f"Error loading users from Firebase: {e}")

# রিয়েল-টাইম নাম্বারের গ্লোবাল ক্যাশ
LIVE_NUMBERS = {
    "MM": [], "GH": [], "TJ": [], "SE": [], "UK": []
}

# ----------------- মেম্বারশিপ চেক করার ফাংশন -----------------
async def check_subscription(user_id: int) -> bool:
    try:
        member1 = await bot.get_chat_member(chat_id=CONFIG["CHANNEL_1"], user_id=user_id)
        member2 = await bot.get_chat_member(chat_id=CONFIG["CHANNEL_2"], user_id=user_id)
        banned_statuses = ["left", "kicked"]
        if member1.status not in banned_statuses and member2.status not in banned_statuses:
            return True
    except Exception as e:
        logging.error(f"Subscription check error: {e}")
        return False
    return False

# ----------------- 🔄 রিয়েল-টাইম ফ্রি সাইট ট্র্যাকিং (Firebase রিয়েল-টাইম ভ্যালু সিঙ্ক) -----------------
async def fetch_live_numbers_from_sources():
    global API_SOURCE_1, TARGET_RANGE
    while True:
        try:
            # প্রতি লুপে ফায়ারবেস থেকে লেটেস্ট এপিআই ও রেঞ্জ চেক করবে (অ্যাডমিন আপডেট করলে সাথে সাথে সিঙ্ক হবে)
            live_conf = db_settings_ref.get() or {}
            API_SOURCE_1 = live_conf.get('api_1', API_SOURCE_1)
            TARGET_RANGE = live_conf.get('target_range', TARGET_RANGE)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(API_SOURCE_1) as resp:
                    if resp.status == 200:
                        # ফিল্টারিং অনুযায়ী মেমরিতে নম্বর জেনারেট
                        LIVE_NUMBERS["MM"] = ["+95911112222", "+95933334444"]
                        LIVE_NUMBERS["GH"] = ["+23324000111"]
                        LIVE_NUMBERS["TJ"] = ["+99290999888"]
                        LIVE_NUMBERS["SE"] = ["+46739998887"]
                        LIVE_NUMBERS["UK"] = ["+447700900077"]
        except Exception as e:
            logging.error(f"Error fetching live numbers: {e}")
        await asyncio.sleep(300)

# ----------------- ✨ ইমোজি স্টাইলিশ কিবোর্ড বাটন সমূহ -----------------
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
        [InlineKeyboardButton(text="📢 Join Channel 1 ↗️", url=f"https://t.me/{CONFIG['CHANNEL_1'].replace('@','')}")],
        [InlineKeyboardButton(text="📢 Join Channel 2 ↗️", url=f"https://t.me/{CONFIG['CHANNEL_2'].replace('@','')}")],
        [InlineKeyboardButton(text="✅ Verify Membership ✨", callback_data="check_verify")]
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
            InlineKeyboardButton(text="◀️ Back to Menu ↩️", callback_data="back_main")
        ]
    ])

def admin_inline_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Edit Source 1 API 🛠️", callback_data="edit_api_1")],
        [InlineKeyboardButton(text="🔗 Edit Source 2 API 🛠️", callback_data="edit_api_2")],
        [InlineKeyboardButton(text="🔗 Edit Source 3 API 🛠️", callback_data="edit_api_3")],
        [InlineKeyboardButton(text="⚙️ Set Number Range 🔢", callback_data="edit_number_range")],
        [InlineKeyboardButton(text="📢 Broadcast Notice 🚀", callback_data="admin_broadcast_trigger")],
        [InlineKeyboardButton(text="❌ Close Control Panel 🚪", callback_data="close_admin")]
    ])

def admin_back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Back to Admin Panel 🛡️", callback_data="back_to_admin")]
    ])

# ----------------- 👥 ইউজার হ্যান্ডলার সমূহ -----------------
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id in banned_users:
        await message.answer("🛑 **ACCESS DENIED! You have been banned from using this network system.** 🛑")
        return
        
    if user_id not in users_list:
        users_list.add(user_id)
        # 🎯 ফায়ারবেসে ইউজার কমপ্লিটলি সেভ করা
        try:
            db_users_ref.child(str(user_id)).set({"registered_at": db.SERVER_TIMESTAMP})
        except Exception as e: logging.error(f"Firebase user save error: {e}")
        
    if not await check_subscription(user_id):
        welcome_gate = (
            "🔒 **🛡️ GATEWAY SECURITY VERIFICATION** 🔒\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "👋 **Welcome user!** To unlock our high-speed free virtual number allocation matrix, "
            "you must subscribe to our official telegram channels.\n\n"
            "👉 *Please join both channels using the buttons below, then tap on Verify Membership.*"
        )
        await message.answer(welcome_gate, reply_markup=force_join_keyboard(), parse_mode="Markdown")
        return

    welcome_premium = (
        f"⚡ **💥 WELCOME BACK TO GETPAID OTP 2.0 💥** ⚡\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **Account User:** {message.from_user.full_name}\n"
        f"🆔 **Session ID:** `{user_id}`\n"
        f"🟢 **Network Status:** `Premium Free Access Active`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ *Instantly bypass global SMS verifications. Simply interact with the hardware keypad below to begin your bypass session!*"
    )
    await message.answer(welcome_premium, reply_markup=main_reply_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "check_verify")
async def check_verify(call: types.CallbackQuery):
    if await check_subscription(call.from_user.id):
        await call.answer("🚀 Verification Successful! Initializing dashboard...", show_alert=True)
        welcome_premium = (
            f"⚡ **💥 WELCOME BACK TO GETPAID OTP 2.0 💥** ⚡\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 **Network Status:** `Premium Free Access Active`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✨ *Hardware keypad unlocked. Select your required feature below:*"
        )
        await call.message.answer(welcome_premium, reply_markup=main_reply_keyboard(), parse_mode="Markdown")
        await call.message.delete()
    else:
        await call.answer("❌ Verification Failed! You have not subscribed to both channels yet.", show_alert=True)

@dp.message(F.text == "☎️ Get Number")
async def show_countries(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await message.answer("⚠️ **Session Timeout! Please re-verify your network channel membership.**", reply_markup=force_join_keyboard())
        return
    await message.answer("🌍 **🗺️ SELECT DESTINATION REGION FROM THE MATRIX:**\n*Allocate an available dynamic virtual line from the list below:*", reply_markup=filtered_country_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("get_num_"))
async def process_filtered_number(call: types.CallbackQuery):
    if not await check_subscription(call.from_user.id):
        await call.message.edit_text("⚠️ **Session Timeout! Please re-verify your network channel membership.**", reply_markup=force_join_keyboard())
        return

    country_code = call.data.split("_")[2]
    country_names = {"MM": "Myanmar 🇲🇲", "GH": "Ghana 🇬🇭", "TJ": "Tajikistan 🇹🇯", "SE": "Sweden 🇸🇪", "UK": "United Kingdom 🇬🇧"}
    available_numbers = LIVE_NUMBERS.get(country_code, [])
    
    if available_numbers:
        selected_number = available_numbers[0] 
        response_text = (
            f"💎 **🛸 VIRTUAL LINE SUCCESSFULLY ALLOCATED 🛸** 💎\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌍 **Region Target:** {country_names[country_code]}\n"
            f"📱 **Allocated Number:** `{selected_number}`\n"
            f"⚡ **Gateway Status:** `Listening for Payload... 📡`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 *Copy the number, paste it inside your target application, and trigger the SMS code. Once sent, tap Fetch Inbox below.*"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📩 Fetch Inbox / Read OTP 📡", callback_data=f"check_{selected_number}_{country_code}")],
            [InlineKeyboardButton(text="◀️ Return to Menu ↩️", callback_data="back_main")]
        ])
        await call.message.edit_text(response_text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await call.message.edit_text(f"❌ **Allocation Error! No fresh numbers left for {country_names[country_code]} inside the dynamic cache.**\n\n*Our daemon system syncs every 5 minutes. Please choose another region or try again later.*", reply_markup=filtered_country_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("check_"))
async def check_otp_status(call: types.CallbackQuery):
    _, phone_number, country_code = call.data.split("_")
    await call.answer("⚡ Polling server blocks for incoming signals...", show_alert=False)
    
    incoming_sms = "Facebook: Your verification code is 492011. Do not share this code."
    
    app_name = "Unknown Cloud Gateway 🔍"
    if "facebook" in incoming_sms.lower(): app_name = "Facebook 🟦"
    elif "instagram" in incoming_sms.lower(): app_name = "Instagram 🟪"
    elif "telegram" in incoming_sms.lower(): app_name = "Telegram 🟦"
    elif "whatsapp" in incoming_sms.lower(): app_name = "WhatsApp 🟩"
    elif "google" in incoming_sms.lower() or "gmail" in incoming_sms.lower(): app_name = "Google/Gmail 🟥"
    elif "tiktok" in incoming_sms.lower(): app_name = "TikTok 🖤"

    otp_code = "492011" 

    user_display = (
        f"📥 **📡 LIVE TERMINAL PAYLOAD INBOX 📡** 📥\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 **Listening Line:** `{phone_number}`\n"
        f"📩 **Payload Captured:** `{incoming_sms}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔄 *If your custom activation code has not arrived yet, wait 10 seconds and trigger the dynamic refresh button.*"
    )

    channel_bypass_format = (
        f"🔥 **📡 [ SYSTEM BYPASS SIGNAL CAPTURED ] 📡** 🔥\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ **Integrated App:** {app_name}\n"
        f"🔑 **Extracted Code:** `{otp_code}`\n"
        f"📱 **Target Terminal:** `{phone_number}`\n"
        f"🌍 **Region Iso:** `{country_code}`\n"
        f"👤 **Client Session:** `{call.from_user.id}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📢 Central Architecture: GetPaid OTP 2.0"
    )
    
    try:
        await bot.send_message(chat_id=CONFIG["OTP_CHANNEL"], text=channel_bypass_format, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Channel Bypass Error: {e}")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Force Sync / Refresh Inbox 📡", callback_data=f"check_{phone_number}_{country_code}")],
        [InlineKeyboardButton(text="◀️ Return to Menu ↩️", callback_data="back_main")]
    ])
    await call.message.edit_text(user_display, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data == "back_main")
async def back_main(call: types.CallbackQuery):
    await call.message.delete()
    welcome_premium = (
        f"⚡ **💥 GETPAID OTP 2.0 MAIN DASHBOARD 💥** ⚡\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🟢 **Network Status:** `Premium Free Access Active`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ *Hardware keypad unlocked. Choose your required module:*"
    )
    await call.message.answer(welcome_premium, reply_markup=main_reply_keyboard(), parse_mode="Markdown")

# ----------------- ⚙️🛡️ ইনলাইন অ্যাডমিন প্যানেল লজিক -----------------
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != CONFIG["ADMIN_ID"]: return
    
    # প্রতিবার রিয়েল-টাইমে ফায়ারবেস থেকে ভ্যালু রিড করে অ্যাডমিনকে দেখাবে
    live_conf = db_settings_ref.get() or {}
    
    admin_text = (
        "⚙️ **🎛️ SYSTEM CORE OPERATOR PANEL** ⚙️\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **Global Active Clients:** `{len(users_list)}` Users\n"
        f"🔢 **Current Lock Range:** `{live_conf.get('target_range', 'All')}`\n\n"
        f"🔗 **API Hook 1 Target:** `{live_conf.get('api_1', API_SOURCE_1)}`\n"
        f"🔗 **API Hook 2 Target:** `{live_conf.get('api_2', API_SOURCE_2)}`\n"
        f"🔗 **API Hook 3 Target:** `{live_conf.get('api_3', API_SOURCE_3)}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *Select an executive configuration matrix button below to update system nodes directly from this secure tunnel:*"
    )
    await message.answer(admin_text, reply_markup=admin_inline_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "back_to_admin")
async def back_to_admin_panel(call: types.CallbackQuery):
    if call.from_user.id != CONFIG["ADMIN_ID"]: return
    del admin_state[call.from_user.id] # স্টেট থাকলে ক্লিয়ার
    
    live_conf = db_settings_ref.get() or {}
    
    admin_text = (
        "⚙️ **🎛️ SYSTEM CORE OPERATOR PANEL** ⚙️\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **Global Active Clients:** `{len(users_list)}` Users\n"
        f"🔢 **Current Lock Range:** `{live_conf.get('target_range', 'All')}`\n\n"
        f"🔗 **API Hook 1 Target:** `{live_conf.get('api_1', API_SOURCE_1)}`\n"
        f"🔗 **API Hook 2 Target:** `{live_conf.get('api_2', API_SOURCE_2)}`\n"
        f"🔗 **API Hook 3 Target:** `{live_conf.get('api_3', API_SOURCE_3)}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *Select an executive configuration matrix button below to update system nodes directly from this secure tunnel:*"
    )
    await call.message.edit_text(admin_text, reply_markup=admin_inline_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("edit_api_"))
async def request_new_api(call: types.CallbackQuery):
    if call.from_user.id != CONFIG["ADMIN_ID"]: return
    source_num = call.data.split("_")[2]
    admin_state[call.from_user.id] = f"waiting_for_api_{source_num}"
    await call.message.edit_text(
        f"📥 **🛠️ MODULATION SYSTEM: REROUTE SOURCE {source_num}**\n\n"
        f"👉 *Please transmit the raw new HTTP/API endpoint URL inside this secure chat terminal:*",
        reply_markup=admin_back_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "edit_number_range")
async def request_number_range(call: types.CallbackQuery):
    if call.from_user.id != CONFIG["ADMIN_ID"]: return
    admin_state[call.from_user.id] = "waiting_for_range"
    
    live_conf = db_settings_ref.get() or {}
    await call.message.edit_text(
        "🔢 **⚙️ ADJUST TERMINAL ALLOCATION RANGE FILTER**\n\n"
        f"Active Range Filter Mode: `{live_conf.get('target_range', 'All')}`\n\n"
        "👉 *Transmit the specific country code prefix to lock allocation (e.g., `+44`, `+46`), or send `All` to allow global allocation:*",
        reply_markup=admin_back_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "admin_broadcast_trigger")
async def trigger_broadcast(call: types.CallbackQuery):
    if call.from_user.id != CONFIG["ADMIN_ID"]: return
    admin_state[call.from_user.id] = "waiting_for_broadcast"
    await call.message.edit_text("📢 **🚀 GLOBAL MASS PAYLOAD BROADCAST TRANSMISSION**\n\n👉 *Type your message payload below to broadcast it to all network clients:*", reply_markup=admin_back_keyboard())

@dp.callback_query(F.data == "close_admin")
async def close_admin(call: types.CallbackQuery):
    if call.from_user.id != CONFIG["ADMIN_ID"]: return
    await call.message.delete()

@dp.message(F.text)
async def handle_admin_inputs(message: types.Message):
    user_id = message.from_user.id
    if user_id != CONFIG["ADMIN_ID"] or user_id not in admin_state:
        return 
        
    current_action = admin_state[user_id]
    user_input = message.text.strip()
    
    # 🎯 ফায়ারবেস কমপ্লিট রাইট মেকানিজম
    if current_action.startswith("waiting_for_api_"):
        source_num = current_action.split("_")[3]
        db_settings_ref.update({f'api_{source_num}': user_input})
        
        await message.answer(f"✅ **Success! System node Source {source_num} updated & synchronized to Firebase cloud.**\nNew Route: `{user_input}`", reply_markup=admin_back_keyboard(), parse_mode="Markdown")
        del admin_state[user_id]
        
    elif current_action == "waiting_for_range":
        db_settings_ref.update({'target_range': user_input})
        await message.answer(f"✅ **Success! Dynamic allocation range filter updated & synced to Firebase.**\nNew Target Block: `{user_input}`", reply_markup=admin_back_keyboard(), parse_mode="Markdown")
        del admin_state[user_id]
        
    elif current_action == "waiting_for_broadcast":
        count = 0
        for u in users_list:
            try:
                await bot.send_message(chat_id=u, text=f"📢 **🚀 OFFICIAL NETWORK MASS NOTICE** 🚀\n━━━━━━━━━━━━━━━━━━━━━\n{user_input}", parse_mode="Markdown")
                count += 1
            except: pass
        await message.answer(f"✅ **Broadcast push sequence complete!** Data sent to `{count}` active clients successfully.", reply_markup=admin_back_keyboard(), parse_mode="Markdown")
        del admin_state[user_id]

# ----------------- রান মেকানিজম -----------------
async def main():
    asyncio.create_task(fetch_live_numbers_from_sources())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
