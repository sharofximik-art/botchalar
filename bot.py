import asyncio
import logging
import json
import random
import os
import re
import uuid
import logging
from aiogram import executor
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
import io
from PIL import Image

# --- ⚙️ BOTNI SOZLASH QISMI ---
TELEGRAM_TOKEN = "8204552206:AAH2Us7BdTC_imyJURR1VPzsHqTw8ZwvRtA"
GEMINI_API_KEY = "AIzaSyDvU5TbOmPw75SXtLPousoxs4HcsowqoTs"
CHANNEL_USERNAME = "KIMYO_OSON"  # @ belgisisiz yozing
ADMIN_ID = 632054105  # @userinfobot dan olingan shaxsiy ID raqamingiz
USERS_DB_FILE = "bot_users.txt"
TESTS_DB_FILE = "tests.json"
PRODUCTS_DB_FILE = "products.json"
REGISTERED_USERS_DB_FILE = "registered_users.json"
ACCESS_CODES_DB_FILE = "access_codes.json"
USER_ACCESS_DB_FILE = "user_test_access.json"

# --- Matnlar va Linklar ---
ABOUT_ME_TEXT = (
    "👋 Assalomu alaykum! Men Maxamadiyev Sharofiddinman.\n\n"
    "KIMYO REPETITORI | PROFESSIONAL TAYYORLOV\n"
    "Abituriyentmisiz? Maqsadingiz aniqmi? Unda vaqtni boy bermang!\n"
    "✅ 15 yillik tajriba\n"
    "✅ Kimyo fanlari bo'yicha falsafa doktori (PhD)\n"
    "✅ 1000 dan ortiq shogirdlarim — talabalar!\n"
    "Tibbiyot va boshqa nufuzli yo'nalishlarga kirish imtihonlariga mukammal tayyorlov!\n"
    "Darslar: Sirdaryo viloyati 📍 YANGIYER 📍 GULISTON\n"
    "🏃‍️ Qabul boshlandi! Joylar soni cheklangan!\n"
    "Batafsil ma'lumot uchun hoziroq yozing yoki qo'ng'iroq qiling!\n"
    "Telegram: @sharofximik\n"
    "☎ Telefon: +998915009464"
)
YOUTUBE_LINK = "https://www.youtube.com/@kimyooson7696/videos"
INSTAGRAM_LINK = "https://www.instagram.com/kimyo__oson?igsh=Mmk1dzhiOGxxcWhn"
PURCHASE_CONTACT = "@sharofximik"
PAID_TEST_INFO = f"Bu test pullik.\n\nTo'lov qilganingizdan so'ng sizga testga kirish uchun bir martalik maxsus parol beriladi. To'lov va parol olish uchun {PURCHASE_CONTACT} manziliga yozing."
ORDER_INFO_TEXT = f"Ushbu mahsulotga buyurtma berish uchun quyidagi tugmani bosing. Sizdan yetkazib berish uchun kerakli ma'lumotlar so'raladi.\n\nTo'lovni {PURCHASE_CONTACT} bilan kelishasiz."

# AI javoblari uchun imzo
AI_ANSWER_SIGNATURE = (
    "\n\n---\n"
    "🎓 Yordam kerakmi? Qo'shimcha savollar yoki individual darslar uchun:\n"
    f"Telegram: {PURCHASE_CONTACT}\n"
    "☎ Telefon: +998915009464"
)

# --- Tugmalar uchun matnlar ---
TEXT_AI_HELPER = "🤖 Masalangizni ishlab beraman"
TEXT_KNOWLEDGE_TEST = "🧠 Bilimni Sinash"
TEXT_SALES_SECTION = "📚 Sotuv Bo'limi"
TEXT_ABOUT_ME = "👤 Men Haqimda"
TEXT_SOCIALS = "🌐 Ijtimoiy Tarmoqlar"
TEXT_BACK_TO_MAIN = "⬅️ Asosiy Menyu"
TEXT_FREE_TESTS = "✅ Bepul Testlar"
TEXT_FREE_NATIONAL = "🎓 Bepul Milliy Sertifikat"
TEXT_PAID_TESTS = "💰 Pullik Testlar"
TEXT_PAID_NATIONAL = "🏆 Pullik Milliy Sertifikat"

# --- FSM Holatlari ---
class Registration(StatesGroup): getting_name = State()
class TakeTest(StatesGroup): waiting_for_answers = State(); entering_code = State()
class AddPDFTest(StatesGroup): getting_title = State(); getting_pdf = State(); getting_key = State(); get_type = State()
class OrderProduct(StatesGroup): getting_region = State(); getting_city = State(); getting_name = State(); getting_phone = State()

# --- Kodning qolgan qismi ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# --- Ma'lumotlar bazasi bilan ishlash funksiyalari ---
def load_json_data(filename, default_type=list):
    if not os.path.exists(filename) or os.path.getsize(filename) == 0: return default_type()
    try:
        with open(filename, "r", encoding='utf-8') as file: return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError): return default_type()
def save_json_data(data, filename):
    with open(filename, "w", encoding='utf-8') as file: json.dump(data, file, indent=4, ensure_ascii=False)
def get_users_from_db():
    if not os.path.exists(USERS_DB_FILE): return set()
    with open(USERS_DB_FILE, "r") as file: return set(int(line.strip()) for line in file)
def add_user_to_db(user_id: int):
    users = get_users_from_db()
    if user_id not in users:
        with open(USERS_DB_FILE, "a") as file: file.write(str(user_id) + "\n")

# --- MENYULARNI YARATISH ---
main_menu_keyboard = ReplyKeyboardBuilder().row(
    KeyboardButton(text=TEXT_AI_HELPER)
).row(
    KeyboardButton(text=TEXT_KNOWLEDGE_TEST), KeyboardButton(text=TEXT_SALES_SECTION)
).row(
    KeyboardButton(text=TEXT_ABOUT_ME), KeyboardButton(text=TEXT_SOCIALS)
).as_markup(resize_keyboard=True)

knowledge_test_keyboard = ReplyKeyboardBuilder().row(
    KeyboardButton(text=TEXT_FREE_TESTS), KeyboardButton(text=TEXT_FREE_NATIONAL)
).row(
    KeyboardButton(text=TEXT_PAID_TESTS), KeyboardButton(text=TEXT_PAID_NATIONAL)
).row(KeyboardButton(text=TEXT_BACK_TO_MAIN)).as_markup(resize_keyboard=True)

def get_sales_section_keyboard():
    products = load_json_data(PRODUCTS_DB_FILE)
    builder = ReplyKeyboardBuilder()
    buttons = [KeyboardButton(text=product['button_text']) for product in products]
    builder.row(*buttons, width=2)
    builder.row(KeyboardButton(text=TEXT_BACK_TO_MAIN))
    return builder.as_markup(resize_keyboard=True)

socials_keyboard = InlineKeyboardBuilder().row(
    InlineKeyboardButton(text="🎥 YouTube", url=YOUTUBE_LINK)
).row(
    InlineKeyboardButton(text="📸 Instagram", url=INSTAGRAM_LINK)
).as_markup()

# --- ASOSIY HANDLERLAR ---
async def check_subscription(user_id: int):
    try:
        member = await bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        logging.info(f"User {user_id} status in @{CHANNEL_USERNAME}: {member.status}")
        return member.status in ['member', 'administrator', 'creator']
    except TelegramBadRequest as e:
        logging.error(f"TelegramBadRequest when checking user {user_id}: {e}")
        return False
    except Exception as e:
        logging.error(f"UNKNOWN error when checking user {user_id}: {e}")
        return False

@dp.message(CommandStart())
async def send_welcome(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    add_user_to_db(user_id)
    user_name = message.from_user.first_name
    welcome_photo = FSInputFile("images/welcome.jpg")

    is_subscribed = await check_subscription(user_id)
    if is_subscribed:
        await message.answer_photo(photo=welcome_photo, caption=f"Assalomu alaykum, {user_name}!\n\nAsosiy menyudan kerakli bo'limni tanlang:", reply_markup=main_menu_inline())
    else:
        await bot.send_message(message.chat.id, f"Assalomu alaykum, {user_name}!\n\nBotdan to'liq foydalanish uchun, iltimos, avval kanalimizga a'zo bo'ling: @{CHANNEL_USERNAME}\n\nA'zo bo'lgach, /start buyrug'ini qayta bosing.", parse_mode=None)

@dp.message(F.text == TEXT_BACK_TO_MAIN)
async def handle_back_to_main(message: types.Message, state: FSMContext): await send_welcome(message, state)

# --- MENYU BO'LIMLARI UCHUN HANDLERLAR ---
@dp.message(F.text == TEXT_KNOWLEDGE_TEST)
async def handle_knowledge_section(message: types.Message):
    await message.answer("🧠 **Bilimni Sinash** bo'limiga xush kelibsiz!\n\nQuyidagi bo'limchalardan birini tanlang:", reply_markup=knowledge_test_keyboard)

@dp.message(F.text == TEXT_SALES_SECTION)
async def handle_sales_section(message: types.Message):
    await message.answer("📚 **Sotuv Bo'limi**\n\nQuyidagi mahsulotlarimiz bilan tanishishingiz mumkin:", reply_markup=get_sales_section_keyboard())

@dp.message(F.text == TEXT_ABOUT_ME)
async def handle_about_me(message: types.Message):
    photo = FSInputFile("images/about_me.jpg")
    await message.answer_photo(photo, caption=ABOUT_ME_TEXT)

@dp.message(F.text == TEXT_SOCIALS)
async def handle_socials(message: types.Message):
    photo = FSInputFile("images/socials.jpg")
    await message.answer_photo(photo, caption="Ijtimoiy tarmoqlarimizga obuna bo'ling:", reply_markup=socials_keyboard)

@dp.message(F.text == TEXT_AI_HELPER)
async def handle_ai_helper_info(message: types.Message):
    photo = FSInputFile("images/ai_helper.jpg")
    await message.answer_photo(photo, caption="🤖 **AI Yordamchi** bo'limidasiz.\n\nMenga masalani matn yoki rasm shaklida yuboring, men yechishga harakat qilaman.")

# --- SOTUV BO'LIMI (DINAMIK MAHSULOTLAR) ---
products_list = [p['button_text'] for p in load_json_data(PRODUCTS_DB_FILE)]
@dp.message(F.text.in_(products_list))
async def handle_dynamic_product(message: types.Message, state: FSMContext):
    products = load_json_data(PRODUCTS_DB_FILE)
    selected_product = next((p for p in products if p['button_text'] == message.text), None)
    if not selected_product: return
    await state.update_data(product_name=selected_product['button_text'])
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🛒 Buyurtma Berish", callback_data=f"order_product_{selected_product['id']}"))
    for i, sample in enumerate(selected_product.get('samples', [])):
        builder.row(InlineKeyboardButton(text=f"📄 {sample['title']}", callback_data=f"get_sample_{selected_product['id']}_{i}"))
    image_path = selected_product.get('image', 'images/guides.jpg')
    await message.answer_photo(photo=FSInputFile(image_path), caption=f"Siz **{selected_product['button_text']}** mahsulotini tanladingiz.\n\nNamuna ko'rish yoki buyurtma berish uchun quyidagi tugmalardan foydalaning.", reply_markup=builder.as_markup())

# ... (Qolgan barcha funksiyalar [buyurtma, testlar, admin va h.k.] o'zgarishsiz qoladi)
@dp.callback_query(F.data.startswith("get_sample_"))
async def send_product_sample(callback: types.CallbackQuery):
    try:
        _, product_id, sample_index_str = callback.data.split("_")
        sample_index = int(sample_index_str)
        products = load_json_data(PRODUCTS_DB_FILE)
        product = next((p for p in products if p['id'] == product_id), None)
        if product and len(product['samples']) > sample_index:
            sample = product['samples'][sample_index]
            file_path = os.path.join("samples", sample['file_name'])
            if os.path.exists(file_path):
                await callback.message.answer_document(FSInputFile(file_path), caption=f"**{sample['title']}**")
            else:
                await callback.message.answer("Kechirasiz, namuna fayli topilmadi.")
        else:
            await callback.message.answer("Xatolik: Namuna ma'lumotlari topilmadi.")
    except Exception as e:
        logging.error(f"Namuna yuborishda xato: {e}")
        await callback.message.answer("Kechirasiz, namuna faylni yuborishda xatolik yuz berdi.")
    await callback.answer()

@dp.callback_query(F.data.startswith("order_product_"))
async def order_product_start(callback: types.CallbackQuery, state: FSMContext):
    product_id = callback.data.split("_")[2]
    products = load_json_data(PRODUCTS_DB_FILE)
    product = next((p for p in products if p['id'] == product_id), None)
    if product:
        await state.update_data(product_name=product['button_text'])
    await state.set_state(OrderProduct.getting_region)
    await callback.message.answer("Buyurtmani rasmiylashtirish uchun, iltimos, viloyatingizni kiriting:")
    await callback.answer()

@dp.message(OrderProduct.getting_region)
async def order_product_region(message: types.Message, state: FSMContext):
    await state.update_data(region=message.text)
    await state.set_state(OrderProduct.getting_city)
    await message.answer("Tuman yoki shahringizni kiriting:")

@dp.message(OrderProduct.getting_city)
async def order_product_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await state.set_state(OrderProduct.getting_name)
    await message.answer("Ism va familiyangizni to'liq kiriting:")

@dp.message(OrderProduct.getting_name)
async def order_product_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await state.set_state(OrderProduct.getting_phone)
    await message.answer("Telefon raqamingizni kiriting (masalan, +998901234567):")

@dp.message(OrderProduct.getting_phone)
async def order_product_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    order_data = await state.get_data()
    registered_users = load_json_data(REGISTERED_USERS_DB_FILE, default_type=dict)
    user_registered_name = registered_users.get(str(message.from_user.id), "Noma'lum (ro'yxatdan o'tmagan)")
    admin_message = f"🔔 **Yangi Buyurtma!**\n\n👤 **Foydalanuvchi:** {user_registered_name} (@{message.from_user.username})\n📦 **Mahsulot:** {order_data.get('product_name')}\n\n**Yetkazib berish ma'lumotlari:**\n- **Viloyat:** {order_data.get('region')}\n- **Tuman/Shahar:** {order_data.get('city')}\n- **Ism Familiya:** {order_data.get('full_name')}\n- **Telefon:** {order_data.get('phone')}"
    try:
        await bot.send_message(ADMIN_ID, admin_message)
    except Exception as e:
        logging.error(f"Adminga buyurtma yuborishda xato: {e}")
    await message.answer("✅ Rahmat! Buyurtmangiz qabul qilindi. Tez orada siz bilan bog'lanamiz.", reply_markup=main_menu_inline())
    await state.clear()

@dp.message(F.text.in_([TEXT_FREE_TESTS, TEXT_FREE_NATIONAL, TEXT_PAID_TESTS, TEXT_PAID_NATIONAL]))
async def show_tests_by_type(message: types.Message, state: FSMContext):
    type_map = {TEXT_FREE_TESTS: "free", TEXT_FREE_NATIONAL: "free_national", TEXT_PAID_TESTS: "paid", TEXT_PAID_NATIONAL: "paid_national"}
    test_type = type_map[message.text]
    users = load_json_data(REGISTERED_USERS_DB_FILE, default_type=dict)
    if str(message.from_user.id) not in users:
        await state.set_state(Registration.getting_name)
        await message.answer("Test ishlashdan oldin ro'yxatdan o'tishingiz kerak.\n\nIltimos, ism-familiyangizni kiriting:")
        return
    all_tests = load_json_data(TESTS_DB_FILE)
    tests_of_type = [test for test in all_tests if test.get("type") == test_type]
    if not tests_of_type:
        await message.answer("Hozircha bu bo'limda testlar mavjud emas.")
        return
    test_list_builder = InlineKeyboardBuilder()
    for test in tests_of_type:
        test_list_builder.row(InlineKeyboardButton(text=test['title'], callback_data=f"select_test_{test['id']}"))
    await message.answer(f"Marhamat, **{message.text}** ro'yxatidan test tanlang:", reply_markup=test_list_builder.as_markup())

@dp.message(Registration.getting_name)
async def process_registration_name(message: types.Message, state: FSMContext):
    users = load_json_data(REGISTERED_USERS_DB_FILE, default_type=dict)
    users[str(message.from_user.id)] = message.text
    save_json_data(users, REGISTERED_USERS_DB_FILE)
    await message.answer("✅ Rahmat, siz muvaffaqiyatli ro'yxatdan o'tdingiz!\n\nEndi testni tanlashingiz mumkin.", reply_markup=main_menu_inline())
    await state.clear()
    # Registratsiyadan so'ng to'g'ri test bo'limiga qaytarish uchun
    # Bu qismni hozircha sodda qoldiramiz, foydalanuvchi tugmani qayta bosadi.

@dp.message(Command("getcode"))
async def generate_code_start(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    tests = load_json_data(TESTS_DB_FILE)
    paid_tests = [test for test in tests if test.get("is_paid", False)]
    if not paid_tests:
        await message.answer("Hali hech qanday pullik test qo'shilmagan.")
        return
    builder = InlineKeyboardBuilder()
    for test in paid_tests:
        builder.row(InlineKeyboardButton(text=test['title'], callback_data=f"gencode_{test['id']}"))
    await message.answer("Qaysi pullik test uchun parol yaratmoqchisiz?", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("gencode_"))
async def generate_code_finish(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    test_id = callback.data.split("_")[1]
    codes = load_json_data(ACCESS_CODES_DB_FILE, default_type=dict)
    new_code = str(uuid.uuid4()).split('-')[0].upper()
    if test_id not in codes: codes[test_id] = []
    codes[test_id].append({"code": new_code, "used_by": None})
    save_json_data(codes, ACCESS_CODES_DB_FILE)
    await callback.message.edit_text(f"✅ Test uchun yangi parol yaratildi:\n\n`{new_code}`\n\nBu parolni to'lov qilgan foydalanuvchiga yuboring. Parol bir marta ishlatiladi.", parse_mode="Markdown")
    await callback.answer()

@dp.message(Command("addtestpdf"))
async def add_pdf_test_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.set_state(AddPDFTest.getting_title)
    await message.answer("Yangi PDF test qo'shish boshlandi.\n\nIltimos, test uchun sarlavha (nom) yuboring:")

@dp.message(AddPDFTest.getting_title)
async def add_pdf_test_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AddPDFTest.getting_pdf)
    await message.answer("Sarlavha qabul qilindi.\n\nEndi test savollari joylashgan PDF faylni yuboring.")

@dp.message(AddPDFTest.getting_pdf, F.document)
async def add_pdf_test_pdf(message: types.Message, state: FSMContext):
    if not message.document.mime_type == 'application/pdf':
        await message.answer("Xatolik: Iltimos, faqat PDF formatidagi fayl yuboring."); return
    if not os.path.exists("tests_pdf"): os.makedirs("tests_pdf")
    file_id = message.document.file_id
    file_info = await bot.get_file(file_id)
    file_path = file_info.file_path
    file_name = f"{uuid.uuid4()}.pdf"
    destination = os.path.join("tests_pdf", file_name)
    await bot.download_file(file_path, destination)
    await state.update_data(pdf_path=destination)
    await state.set_state(AddPDFTest.getting_key)
    await message.answer("PDF fayl qabul qilindi.\n\nEndi bu testning kalitlarini `1a2b3c...` ko'rinishida yuboring.")

@dp.message(AddPDFTest.getting_key)
async def add_pdf_test_key(message: types.Message, state: FSMContext):
    await state.update_data(answer_key=message.text.lower().replace(" ", ""))
    await state.set_state(AddPDFTest.get_type)
    await message.answer("Kalitlar qabul qilindi.\n\nEndi test turini kiriting. Variantlar: `free`, `free_national`, `paid`, `paid_national`")

@dp.message(AddPDFTest.get_type)
async def add_pdf_test_type(message: types.Message, state: FSMContext):
    test_type = message.text.lower()
    if test_type not in ['free', 'free_national', 'paid', 'paid_national']:
        await message.answer("Xatolik! Faqat `free`, `free_national`, `paid` yoki `paid_national` turlaridan birini kiriting.")
        return
    await state.update_data(type=test_type, is_paid=(test_type in ['paid', 'paid_national']))
    test_data = await state.get_data()
    tests = load_json_data(TESTS_DB_FILE)
    new_test = {"id": str(uuid.uuid4()), "title": test_data.get("title"), "pdf_path": test_data.get("pdf_path"), "answer_key": test_data.get("answer_key"), "type": test_data.get("type"), "is_paid": test_data.get("is_paid")}
    tests.append(new_test)
    save_json_data(tests, TESTS_DB_FILE)
    await state.clear()
    await message.answer(f"✅ Muvaffaqiyatli! Yangi '{test_type}' turidagi test bazaga qo'shildi.")

@dp.callback_query(F.data.startswith("select_test_"))
async def select_test(callback: types.CallbackQuery, state: FSMContext):
    test_id = callback.data.split("_")[2]
    user_id = str(callback.from_user.id)
    tests = load_json_data(TESTS_DB_FILE)
    selected_test = next((test for test in tests if test['id'] == test_id), None)
    if not selected_test: await callback.answer("Xatolik: Test topilmadi.", show_alert=True); return
    if not selected_test.get("is_paid", False):
        await start_test_process(callback, state, test_id); return
    user_access = load_json_data(USER_ACCESS_DB_FILE, default_type=dict)
    if user_id in user_access and test_id in user_access[user_id]:
        await start_test_process(callback, state, test_id)
    else:
        await state.update_data(selected_test_id=test_id)
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🔑 Parolni kiritish", callback_data=f"enter_code_{test_id}"))
        await callback.message.answer(PAID_TEST_INFO, reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("enter_code_"))
async def enter_code_prompt(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(TakeTest.entering_code)
    await callback.message.answer("Iltimos, test uchun olgan maxsus parolingizni kiriting:")
    await callback.answer()

@dp.message(TakeTest.entering_code)
async def process_entered_code(message: types.Message, state: FSMContext):
    user_code = message.text.upper()
    user_id = str(message.from_user.id)
    user_data = await state.get_data()
    test_id = user_data.get("selected_test_id")
    if not test_id: await message.answer("Xatolik yuz berdi. /start bosing."); await state.clear(); return
    codes = load_json_data(ACCESS_CODES_DB_FILE, default_type=dict)
    is_code_valid = False
    if test_id in codes:
        for code_info in codes[test_id]:
            if code_info['code'] == user_code and code_info['used_by'] is None:
                code_info['used_by'] = user_id
                is_code_valid = True
                break
    if is_code_valid:
        save_json_data(codes, ACCESS_CODES_DB_FILE)
        user_access = load_json_data(USER_ACCESS_DB_FILE, default_type=dict)
        if user_id not in user_access: user_access[user_id] = []
        user_access[user_id].append(test_id)
        save_json_data(user_access, USER_ACCESS_DB_FILE)
        await message.answer("✅ Rahmat! Parol to'g'ri. Testga ruxsat ochildi.")
        await start_test_process(message, state, test_id)
    else:
        await message.answer("❌ Parol xato yoki avval ishlatilgan. Iltimos, qayta tekshiring yoki admin bilan bog'laning.")
        await state.clear()

async def start_test_process(update: types.Update, state: FSMContext, test_id: str):
    tests = load_json_data(TESTS_DB_FILE)
    selected_test = next((test for test in tests if test['id'] == test_id), None)
    if not selected_test: return
    await state.set_state(TakeTest.waiting_for_answers)
    await state.update_data(test_id=test_id)
    try:
        test_file = FSInputFile(selected_test['pdf_path'])
        if isinstance(update, types.CallbackQuery):
            await update.message.delete()
            chat_id = update.message.chat.id
        else: chat_id = update.chat.id
        await bot.send_document(chat_id=chat_id, document=test_file, caption=f"Siz **{selected_test['title']}** testini boshladingiz.\n\nTestni ishlab bo'lgach, javoblaringizni `1a2b3c...` ko'rinishida yuboring.")
    except Exception as e:
        if isinstance(update, types.CallbackQuery): await update.message.answer("Xatolik: Test faylini yuborib bo'lmadi.")
        else: await update.answer("Xatolik: Test faylini yuborib bo'lmadi.")
        logging.error(f"PDF yuborishda xato: {e}")
        await state.clear()

@dp.message(TakeTest.waiting_for_answers)
async def process_test_answers(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    test_id = user_data.get('test_id')
    tests = load_json_data(TESTS_DB_FILE)
    current_test = next((test for test in tests if test['id'] == test_id), None)
    if not current_test: await message.answer("Xatolik yuz berdi. Iltimos, /start bosing."); await state.clear(); return
    correct_key = current_test['answer_key']
    user_key_raw = message.text.lower().replace(" ", "")
    total_questions = len(re.findall(r'\d+', correct_key))
    correct_answers_count = 0
    results_text = f"**{current_test['title']}** testi natijalari:\n\n"
    correct_answers_map = dict(re.findall(r'(\d+)([a-z])', correct_key))
    user_answers_map = dict(re.findall(r'(\d+)([a-z])', user_key_raw))
    for i in range(1, total_questions + 1):
        q_num = str(i)
        correct_answer = correct_answers_map.get(q_num, '?')
        user_answer = user_answers_map.get(q_num, 'belgilanmagan')
        results_text += f"{q_num}. To'g'ri: **{correct_answer.upper()}** | Siz: "
        if user_answer == correct_answer:
            correct_answers_count += 1
            results_text += f"**{user_answer.upper()} ✅**\n"
        else:
            results_text += f"**{user_answer.upper()} ❌**\n"
    percentage = (correct_answers_count / total_questions) * 100 if total_questions > 0 else 0
    results_text += f"\nUmumiy natija: **{total_questions}** ta savoldan **{correct_answers_count}** tasi to'g'ri ({percentage:.1f}%)."
    await message.answer(results_text, parse_mode="Markdown", reply_markup=main_menu_inline())
    await state.clear()

@dp.message(Command("sendad"))
async def send_advertisement(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    if not message.reply_to_message: await message.answer("Iltimos, bu buyruqni reklama bo'ladigan xabarga 'reply' qilib yuboring."); return
    users = get_users_from_db()
    ad_message = message.reply_to_message
    await message.answer(f"Reklama yuborish boshlandi. Jami foydalanuvchilar soni: {len(users)}")
    success_count, fail_count = 0, 0
    for user_id in users:
        try:
            await bot.copy_message(chat_id=user_id, from_chat_id=message.chat.id, message_id=ad_message.message_id)
            success_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            fail_count += 1
            logging.error(f"ID {user_id} ga xabar yuborilmadi: {e}")
    await message.answer(f"Reklama yuborish yakunlandi.\n\n✅ Yuborildi: {success_count}\n❌ Yuborilmadi: {fail_count}")

# --- AI YORDAMCHI UCHUN YAKUNIY HANDLERLAR ---
@dp.message(F.photo)
async def handle_ai_photo(message: types.Message):
    if not await check_subscription(message.from_user.id): await message.answer(f"Botdan foydalanish uchun, iltimos, avval kanalimizga a'zo bo'ling: @{CHANNEL_USERNAME}"); return
    waiting_message = await message.answer("🖼️ Rasm tahlil qilinmoqda...")
    try:
        photo_bytes = io.BytesIO()
        await bot.download(message.photo[-1], destination=photo_bytes)
        img = Image.open(photo_bytes)
        caption_text = message.caption or ""
        prompt_parts = ["Rasmdagi masalani yoki savolni bosqichma-bosqich, tushunarli qilib yechib ber.", img]
        if caption_text: prompt_parts.insert(1, f"\nQo'shimcha ma'lumot: {caption_text}")
        response = await model.generate_content_async(prompt_parts)
        final_answer = response.text + AI_ANSWER_SIGNATURE  # IMZO QO'SHILDI
        await waiting_message.delete()
        await message.answer(final_answer)
    except Exception as e:
        logging.error(f"Gemini (photo) bilan ishlashda xatolik: {e}")
        await waiting_message.delete()
        await message.answer("Kechirasiz, rasmni tahlil qilishda xatolik yuz berdi.")

@dp.message()
async def handle_ai_text(message: types.Message):
    # Bu handler eng oxirida turishi kerak, chunki u barcha qolgan matnlarni ushlaydi
    if not await check_subscription(message.from_user.id): await message.answer(f"Botdan foydalanish uchun, iltimos, avval kanalimizga a'zo bo'ling: @{CHANNEL_USERNAME}"); return
    waiting_message = await message.answer("⏳ Matndan javob tayyorlanmoqda...")
    try:
        prompt = f"Sen o'quvchilarga yordam beradigan tajribali o'qituvchisan. Quyidagi masalani bosqichma-bosqich, tushunarli qilib yechib ber. Masala: '{message.text}'"
        response = await model.generate_content_async(prompt)
        final_answer = response.text + AI_ANSWER_SIGNATURE  # IMZO QO'SHILDI
        await waiting_message.delete()
        await message.answer(final_answer)
    except Exception as e:
        logging.error(f"Gemini (text) bilan ishlashda xatolik: {e}")
        await waiting_message.delete()
        await message.answer("Kechirasiz, javob olishda xatolik yubordi.")

async def main():
    for folder in ["images", "samples", "tests_pdf"]:
        if not os.path.exists(folder):
            os.makedirs(folder)
            logging.info(f"'{folder}' papkasi yaratildi.")
    logging.info("Bot ishga tushmoqda...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())


# === INLINE MAIN MENU PATCH (auto-injected) ===
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu_inline():
    kb = InlineKeyboardBuilder()
    kb.button(text=TEXT_AI_HELPER, callback_data="menu:ai")
    kb.button(text=TEXT_KNOWLEDGE_TEST, callback_data="menu:knowledge")
    kb.button(text=TEXT_SALES_SECTION, callback_data="menu:sales")
    kb.button(text=TEXT_ABOUT_ME, callback_data="menu:about")
    kb.button(text=TEXT_SOCIALS, callback_data="menu:socials")
    kb.adjust(1)
    return kb.as_markup()

@dp.callback_query(F.data == "menu:back")
async def _cb_back(cb: types.CallbackQuery, state: FSMContext):
    # Reuse your existing back-to-main handler
    await handle_back_to_main(cb.message, state)
    await cb.answer()

@dp.callback_query(F.data == "menu:ai")
async def _cb_ai(cb: types.CallbackQuery):
    await handle_ai_helper_info(cb.message)
    await cb.answer()

@dp.callback_query(F.data == "menu:knowledge")
async def _cb_knowledge(cb: types.CallbackQuery):
    await handle_knowledge_section(cb.message)
    await cb.answer()

@dp.callback_query(F.data == "menu:sales")
async def _cb_sales(cb: types.CallbackQuery):
    await handle_sales_section(cb.message)
    await cb.answer()

@dp.callback_query(F.data == "menu:about")
async def _cb_about(cb: types.CallbackQuery):
    await handle_about_me(cb.message)
    await cb.answer()

@dp.callback_query(F.data == "menu:socials")
async def _cb_socials(cb: types.CallbackQuery):
    await handle_socials(cb.message)
    await cb.answer()
# === END PATCH ===
