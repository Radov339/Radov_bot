import os
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# --- سيرفر ويب مصغر لإرضاء متطلبات منصة Render ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active and running 24/7!")
    def log_message(self, format, *args):
        pass

def run_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_http_server, daemon=True).start()
# ---------------------------------------------

API_ID = 30270110
API_HASH = "8916657625ad5550bea8382e44288159"
BOT_TOKEN = "8927929798:AAGWldvnByYZAZCNRuumLyHB5tp8zumVxH"

bot = Client("radov_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

SESSIONS_DIR = "./user_sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

login_steps = {}

def get_user_client(user_id: int) -> Client:
    session_path = os.path.join(SESSIONS_DIR, str(user_id))
    return Client(session_path, api_id=API_ID, api_hash=API_HASH)

@bot.on_message(filters.command("start") & filters.private)
async def start_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    session_file = os.path.join(SESSIONS_DIR, f"{user_id}.session")
    
    is_logged = "✅ متصل (حسابك مسجل)" if os.path.exists(session_file) else "❌ غير متصل (للروابط الخاصة فقط)"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 طريقة الاستخدام", callback_data="help")],
        [InlineKeyboardButton(f"🔑 حالة الحساب: {is_logged}", callback_data="toggle_login")]
    ])

    await message.reply_text(
        "👋 **أهلاً بك في بوت التحميل الذكي (Radov)!**\n\n"
        "• للروابط العادية: أرسل الرابط مباشرة وسأحمله لك.\n"
        "• للروابط الخاصة (المقيدة): اضغط على زر حالة الحساب لتسجيل الدخول برقمك.\n",
        reply_markup=keyboard
    )

@bot.on_callback_query()
async def callback_handler(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data
    session_file = os.path.join(SESSIONS_DIR, f"{user_id}.session")

    if data == "help":
        await callback_query.message.edit_text(
            "📖 **دليل الاستخدام:**\n\n"
            "1️⃣ **الروابط العامة:** أرسل رابط المنشور مباشرة وسأقوم بتحميله فوراً.\n"
            "2️⃣ **الروابط الخاصة (/c/):** تتطلب تسجيل الدخول برقم جوالك مرة واحدة لتتمكن من تحميل محتواها.\n\n"
            "اضغط على زر العودة للرجوع للقائمة الرئيسية.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]])
        )

    elif data == "main_menu":
        is_logged = "✅ متصل (حسابك مسجل)" if os.path.exists(session_file) else "❌ غير متصل"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 طريقة الاستخدام", callback_data="help")],
            [InlineKeyboardButton(f"🔑 حالة الحساب: {is_logged}", callback_data="toggle_login")]
        ])
        await callback_query.message.edit_text(
            "👋 **أهلاً بك مجدداً في القائمة الرئيسية:**",
            reply_markup=keyboard
        )

    elif data == "toggle_login":
        if os.path.exists(session_file):
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🚪 تسجيل الخروج وحذف الجلسة", callback_data="logout")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
            ])
            await callback_query.message.edit_text(
                "✅ **حسابك مسجل بالفعل ومربوط بالبوت.**\nيمكنك تحميل المحتوى المقيد مباشرة.",
                reply_markup=keyboard
            )
        else:
            login_steps[user_id] = {"step": "WAIT_PHONE"}
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="main_menu")]])
            await callback_query.message.edit_text(
                "📲 **تسجيل الدخول:**\n\n"
                "أرسل رقم هاتفك الآن في المحادثة مع رمز الدولة (مثال: `+966500000000`):",
                reply_markup=keyboard
            )

    elif data == "logout":
        if os.path.exists(session_file):
            os.remove(session_file)
        await callback_query.answer("تم تسجيل الخروج بنجاح!", show_alert=True)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 طريقة الاستخدام", callback_data="help")],
            [InlineKeyboardButton("🔑 حالة الحساب: ❌ غير متصل", callback_data="toggle_login")]
        ])
        await callback_query.message.edit_text("👋 **تم قطع الاتصال وحذف الجلسة بنجاح.**", reply_markup=keyboard)

@bot.on_message(filters.text & filters.private)
async def handle_text(client: Client, message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    session_file = os.path.join(SESSIONS_DIR, f"{user_id}.session")

    if user_id in login_steps and login_steps[user_id].get("step") == "WAIT_PHONE":
        if text.startswith("+") and text[1:].isdigit():
            status_msg = await message.reply_text("⏳ جاري إرسال كود التحقق من تيليجرام...")
            user_client = get_user_client(user_id)
            try:
                await user_client.connect()
                sent_code = await user_client.send_code(text)
                login_steps[user_id] = {
                    "step": "WAIT_CODE",
                    "phone": text,
                    "phone_code_hash": sent_code.phone_code_hash,
                    "client": user_client
                }
                await status_msg.edit_text("📩 **وصلك كود من تيليجرام.**\n\nأرسل كود التحقق هنا الآن:")
            except Exception as e:
                await status_msg.edit_text(f"❌ تعذر إرسال الكود:\n`{str(e)}`\nتأكد من صحة الرقم ومفتاح الدولة.")
        else:
            await message.reply_text("❌ صيغة الرقم غير صحيحة. يجب أن يبدأ بـ + مع رمز الدولة (مثل `+966...`).")
        return

    if user_id in login_steps and login_steps[user_id].get("step") == "WAIT_CODE":
        phone_code = text.replace(" ", "")
        user_data = login_steps[user_id]
        user_client = user_data["client"]
        phone_number = user_data["phone"]

        status_msg = await message.reply_text("⏳ جاري التحقق من الكود...")
        try:
            await user_client.sign_in(phone_number, user_data["phone_code_hash"], phone_code)
            await status_msg.edit_text(
                "✅ **تم تسجيل الدخول بنجاح!**\n\n"
                "يمكنك الآن إرسال أي رابط مقيد وسأقوم بتحميله لك مباشرة.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]])
            )
            del login_steps[user_id]
        except Exception as e:
            await status_msg.edit_text(f"❌ الكود غير صحيح أو يتطلب كلمة مرور ثنائية (2FA):\n`{str(e)}`\nأعد إرسال الكود الصحيح:")
        return

    if "t.me/" in text:
        parts = text.split("/")
        
        if "/c/" in text:
            if not os.path.exists(session_file):
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔑 تسجيل الدخول الآن", callback_data="toggle_login")],
                    [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
                ])
                await message.reply_text(
                    "🔒 **هذا الرابط يتبع قناة أو مجموعة خاصة (مقيدة).**\n\n"
                    "تحتاج لتسجيل الدخول بحسابك أولاً لتتمكن من تحميله.",
                    reply_markup=keyboard
                )
                return

            status_msg = await message.reply_text("⏳ جاري جلب المحتوى الخاص...")
            user_client = get_user_client(user_id)
            try:
                await user_client.connect()
                msg_id = int(parts[-1])
                chat_id = int("-100" + parts[-2])

                target_msg = await user_client.get_messages(chat_id, msg_id)
                if not target_msg or not target_msg.media:
                    await status_msg.edit_text("❌ لم يتم العثور على وسائط في هذا الرابط!")
                    await user_client.disconnect()
                    return

                file_path = await user_client.download_media(target_msg)
                await user_client.disconnect()

                await status_msg.edit_text("📤 جاري رفع الملف لك...")
                await message.reply_document(document=file_path, caption="✅ **تم التحميل بنجاح!**")

                if os.path.exists(file_path):
                    os.remove(file_path)
                await status_msg.delete()

            except Exception as e:
                await status_msg.edit_text(f"❌ حدث خطأ:\n`{str(e)}`")
                if user_client.is_connected:
                    await user_client.disconnect()
        
        else:
            status_msg = await message.reply_text("⏳ جاري تحميل المحتوى العام...")
            try:
                chat_id = parts[-2]
                msg_id = int(parts[-1])
                
                target_msg = await bot.get_messages(chat_id, msg_id)
                if not target_msg or not target_msg.media:
                    await status_msg.edit_text("❌ لم يتم العثور على وسائط في هذا الرابط!")
                    return

                file_path = await bot.download_media(target_msg)
                await status_msg.edit_text("📤 جاري رفع الملف لك...")
                
                await message.reply_document(document=file_path, caption="✅ **تم التحميل بنجاح!**")
                
                if os.path.exists(file_path):
                    os.remove(file_path)
                await status_msg.delete()

            except Exception as e:
                await status_msg.edit_text(f"❌ حدث خطأ:\n`{str(e)}`")

async def main():
    await bot.start()
    print("🚀 البوت يعمل الآن بنجاح 24/7...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
