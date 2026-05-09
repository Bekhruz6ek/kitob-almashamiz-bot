import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters, ContextTypes
)

# ===================== SOZLAMALAR =====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))           # Telegram ID ingiz
KANAL_ID = os.getenv("KANAL_ID", "@Kitob_almashamiz_kanal")  # Kanal username

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===================== MA'LUMOTLAR =====================
# { user_id: [ {id, nomi, holati, narxi, boglanish, rasm, manzil, status}, ... ] }
elon_db = {}
# { user_id: [ "kitob nomi", ... ] }
istak_db = {}
elon_counter = [0]  # global ID uchun

# ===================== CONVERSATION STATES =====================
(NOMI, HOLATI, NARXI, BOGLANISH, RASM, MANZIL) = range(6)
ISTAK_NOMI = 10
QIDIR_NOMI = 20

# ===================== YORDAMCHI FUNKSIYALAR =====================
def yangi_id():
    elon_counter[0] += 1
    return elon_counter[0]

def holat_emoji(holat: str) -> str:
    holat = holat.lower()
    if "yangi" in holat:       return "🆕"
    if "yaxshi" in holat:      return "✅"
    if "o'rta" in holat or "orta" in holat: return "📖"
    if "eski" in holat:        return "📦"
    return "📚"

def elon_text(e: dict) -> str:
    emoji = holat_emoji(e["holati"])
    tur = e.get("tur", "Sotiladi")
    return (
        f"📚 *{e['nomi']}*\n"
        f"{emoji} Holati: {e['holati']}\n"
        f"💰 Narxi: {e['narxi']}\n"
        f"🔄 Tur: {tur}\n"
        f"📍 Manzil: {e['manzil']}\n"
        f"📞 Bog'lanish: {e['boglanish']}\n"
        f"🆔 E'lon #{e['id']}"
    )

async def wishlist_bildirishnoma(app, nomi: str, yangi_elon: dict):
    """Mos kitob e'lon qilinganda istak egasiga xabar yuborish"""
    for uid, istaklist in istak_db.items():
        for istak in istaklist:
            if istak.lower() in nomi.lower() or nomi.lower() in istak.lower():
                try:
                    await app.bot.send_message(
                        chat_id=uid,
                        text=(
                            f"🔔 *Siz qidirgan kitob topildi!*\n\n"
                            f"Siz '{istak}' kitobini izlagan edingiz.\n\n"
                            f"{elon_text(yangi_elon)}"
                        ),
                        parse_mode="Markdown"
                    )
                except Exception as ex:
                    logger.warning(f"Wishlist xabar yuborilmadi: {ex}")

# ===================== /start =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 *Kitob Almashamiz botiga xush kelibsiz!*\n\n"
        "📚 Bu yerda kitob *sotishingiz*, *sotib olishingiz*, "
        "*bepul berishingiz*, *almashtirishingiz* yoki *almashib o'qishingiz* mumkin!\n\n"
        "📌 *Buyruqlar:*\n"
        "➕ /elon — Kitob e'lon qilish\n"
        "🔍 /qidir — Kitob qidirish\n"
        "📖 /mening_kitoblarim — Mening e'lonlarim\n"
        "🗑 /ochirish — E'lonni o'chirish\n"
        "💛 /istaklar_qoshish — Istak ro'yxatiga qo'shish\n"
        "📋 /mening_istaklarim — Istak ro'yxatim\n"
        "ℹ️ /yordam — Yordam\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ===================== /yordam =====================
async def yordam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📘 *Yordam*\n\n"
        "🔹 /elon — Yangi kitob e'lon qoʻshish\n"
        "🔹 /qidir — Kitob nomi bo'yicha qidirish\n"
        "🔹 /mening_kitoblarim — O'zingizning e'lonlaringiz\n"
        "🔹 /ochirish — E'lonni o'chirish (ID kerak)\n"
        "🔹 /istaklar_qoshish — Kerakli kitob nomini ro'yxatga qo'shish\n"
        "🔹 /mening_istaklarim — O'z istak ro'yxatingiz\n\n"
        "❓ Savollar bo'lsa admin bilan bog'laning."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ===================== /elon — ConversationHandler =====================
async def elon_boshlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💰 Sotiladi", callback_data="tur_Sotiladi"),
         InlineKeyboardButton("🤝 Almashiladi", callback_data="tur_Almashiladi")],
        [InlineKeyboardButton("📖 Almashib o'qiladi", callback_data="tur_Almashib o'qiladi"),
         InlineKeyboardButton("🎁 Bepul beriladi", callback_data="tur_Bepul beriladi")],
    ]
    await update.message.reply_text(
        "📚 *Kitob turi:* Qanday e'lon bermoqchisiz?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return NOMI

async def elon_tur_tanlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tur = query.data.replace("tur_", "")
    context.user_data["tur"] = tur
    await query.edit_message_text(f"✅ Tur tanlandi: *{tur}*\n\n📖 Kitob nomini yozing:", parse_mode="Markdown")
    return NOMI

async def elon_nomi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nomi"] = update.message.text
    keyboard = [
        [InlineKeyboardButton("🆕 Yangi", callback_data="holat_Yangi"),
         InlineKeyboardButton("✅ Yaxshi", callback_data="holat_Yaxshi")],
        [InlineKeyboardButton("📖 O'rta", callback_data="holat_O'rta"),
         InlineKeyboardButton("📦 Eski", callback_data="holat_Eski")],
    ]
    await update.message.reply_text(
        "📊 Kitob holatini tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return HOLATI

async def elon_holati_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    holat = query.data.replace("holat_", "")
    context.user_data["holati"] = holat
    tur = context.user_data.get("tur", "Sotiladi")
    if tur == "Bepul beriladi":
        context.user_data["narxi"] = "Bepul 🎁"
        await query.edit_message_text("📞 Bog'lanish uchun kontakt (telefon yoki @username) yozing:")
        return BOGLANISH
    await query.edit_message_text("💰 Narxini yozing (masalan: 25000 so'm yoki 'Almashish'):")
    return NARXI

async def elon_narxi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["narxi"] = update.message.text
    await update.message.reply_text("📞 Bog'lanish uchun kontakt (telefon yoki @username) yozing:")
    return BOGLANISH

async def elon_boglanish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["boglanish"] = update.message.text
    await update.message.reply_text(
        "📸 Kitob rasmini yuboring.\n_(Rasm bo'lmasa /skip yozing)_",
        parse_mode="Markdown"
    )
    return RASM

async def elon_rasm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data["rasm"] = update.message.photo[-1].file_id
    else:
        context.user_data["rasm"] = None
    await update.message.reply_text("📍 Manzilingizni yozing (shahar/tuman):")
    return MANZIL

async def elon_rasm_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["rasm"] = None
    await update.message.reply_text("📍 Manzilingizni yozing (shahar/tuman):")
    return MANZIL

async def elon_manzil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["manzil"] = update.message.text
    uid = update.effective_user.id

    elon = {
        "id": yangi_id(),
        "nomi": context.user_data["nomi"],
        "holati": context.user_data["holati"],
        "narxi": context.user_data["narxi"],
        "boglanish": context.user_data["boglanish"],
        "rasm": context.user_data.get("rasm"),
        "manzil": context.user_data["manzil"],
        "tur": context.user_data.get("tur", "Sotiladi"),
        "status": "Faol",
        "user_id": uid,
    }

    if uid not in elon_db:
        elon_db[uid] = []
    elon_db[uid].append(elon)

    # Foydalanuvchiga tasdiqlash
    msg = f"✅ *E'lon muvaffaqiyatli qo'shildi!*\n\n{elon_text(elon)}"
    if elon["rasm"]:
        await update.message.reply_photo(elon["rasm"], caption=msg, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, parse_mode="Markdown")

    # Kanalga yuborish
    try:
        kanal_msg = f"📢 *Yangi e'lon!*\n\n{elon_text(elon)}\n\n📬 Botga murojaat: @Kitob_almashamizbot"
        if elon["rasm"]:
            await context.bot.send_photo(KANAL_ID, elon["rasm"], caption=kanal_msg, parse_mode="Markdown")
        else:
            await context.bot.send_message(KANAL_ID, kanal_msg, parse_mode="Markdown")
    except Exception as ex:
        logger.warning(f"Kanalga yuborishda xato: {ex}")

    # Wishlist bildirishnomasi
    await wishlist_bildirishnoma(context.application, elon["nomi"], elon)

    context.user_data.clear()
    return ConversationHandler.END

async def elon_bekor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ E'lon bekor qilindi.")
    return ConversationHandler.END

# ===================== /qidir =====================
async def qidir_boshlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Qidirmoqchi bo'lgan kitob nomini yozing:")
    return QIDIR_NOMI

async def qidir_nomi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    so_z = update.message.text.lower()
    natijalar = []
    for uid, elonlar in elon_db.items():
        for e in elonlar:
            if so_z in e["nomi"].lower() and e["status"] == "Faol":
                natijalar.append(e)

    if not natijalar:
        await update.message.reply_text(
            f"😕 *'{update.message.text}'* bo'yicha hech narsa topilmadi.\n\n"
            "💡 /istaklar_qoshish orqali bu kitobni istak ro'yxatiga qo'shishingiz mumkin!",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(f"✅ *{len(natijalar)} ta natija topildi:*", parse_mode="Markdown")
        for e in natijalar[:10]:
            msg = elon_text(e)
            if e["rasm"]:
                await update.message.reply_photo(e["rasm"], caption=msg, parse_mode="Markdown")
            else:
                await update.message.reply_text(msg, parse_mode="Markdown")

    return ConversationHandler.END

# ===================== /mening_kitoblarim =====================
async def mening_kitoblarim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    elonlar = elon_db.get(uid, [])

    if not elonlar:
        await update.message.reply_text("📭 Sizda hozircha e'lonlar yo'q.\n\n/elon buyrug'i bilan qo'shing!")
        return

    await update.message.reply_text(f"📚 Sizning e'lonlaringiz ({len(elonlar)} ta):")
    for e in elonlar:
        keyboard = []
        if e["status"] == "Faol":
            keyboard.append([InlineKeyboardButton("✅ Sotildi / Berildi", callback_data=f"sotildi_{e['id']}")])
        msg = elon_text(e) + f"\n📌 Status: *{e['status']}*"
        markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        if e["rasm"]:
            await update.message.reply_photo(e["rasm"], caption=msg, parse_mode="Markdown", reply_markup=markup)
        else:
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=markup)

async def sotildi_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    elon_id = int(query.data.replace("sotildi_", ""))

    for e in elon_db.get(uid, []):
        if e["id"] == elon_id:
            e["status"] = "Sotildi ✅"
            await query.edit_message_caption(
                caption=elon_text(e) + "\n📌 Status: *Sotildi ✅*",
                parse_mode="Markdown"
            ) if e["rasm"] else await query.edit_message_text(
                elon_text(e) + "\n📌 Status: *Sotildi ✅*",
                parse_mode="Markdown"
            )
            return

    await query.answer("E'lon topilmadi.")

# ===================== /ochirish =====================
async def ochirish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    elonlar = elon_db.get(uid, [])

    if not elonlar:
        await update.message.reply_text("📭 Sizda o'chiriladigan e'lon yo'q.")
        return

    keyboard = []
    for e in elonlar:
        keyboard.append([InlineKeyboardButton(
            f"🗑 #{e['id']} — {e['nomi'][:25]}",
            callback_data=f"ochir_{e['id']}"
        )])

    await update.message.reply_text(
        "🗑 *Qaysi e'lonni o'chirmoqchisiz?*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def ochirish_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    elon_id = int(query.data.replace("ochir_", ""))

    elonlar = elon_db.get(uid, [])
    yangi_list = [e for e in elonlar if e["id"] != elon_id]

    if len(yangi_list) < len(elonlar):
        elon_db[uid] = yangi_list
        await query.edit_message_text(f"✅ E'lon #{elon_id} o'chirildi.")
    else:
        await query.edit_message_text("❌ E'lon topilmadi.")

# ===================== /istaklar_qoshish =====================
async def istaklar_qoshish_boshlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💛 *Istak ro'yxatiga qo'shish*\n\nQaysi kitobni qidirmoqdasiz? Nomini yozing:",
        parse_mode="Markdown"
    )
    return ISTAK_NOMI

async def istak_nomi_qabul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    nomi = update.message.text.strip()

    if uid not in istak_db:
        istak_db[uid] = []

    if nomi in istak_db[uid]:
        await update.message.reply_text("ℹ️ Bu kitob allaqachon istak ro'yxatingizda bor.")
    else:
        istak_db[uid].append(nomi)
        await update.message.reply_text(
            f"✅ *'{nomi}'* istak ro'yxatingizga qo'shildi!\n\n"
            "Bu kitob e'lon qilinganda sizga xabar beramiz 🔔",
            parse_mode="Markdown"
        )
    return ConversationHandler.END

# ===================== /mening_istaklarim =====================
async def mening_istaklarim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    istaklist = istak_db.get(uid, [])

    if not istaklist:
        await update.message.reply_text(
            "📋 Istak ro'yxatingiz bo'm-bo'sh.\n\n"
            "💡 /istaklar_qoshish orqali kitob qo'shing!"
        )
        return

    text = "💛 *Sizning istak ro'yxatingiz:*\n\n"
    keyboard = []
    for i, istak in enumerate(istaklist, 1):
        text += f"{i}. 📖 {istak}\n"
        keyboard.append([InlineKeyboardButton(f"🗑 '{istak[:20]}' ni o'chirish", callback_data=f"istak_ochir_{i-1}")])

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def istak_ochir_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    idx = int(query.data.replace("istak_ochir_", ""))

    istaklist = istak_db.get(uid, [])
    if 0 <= idx < len(istaklist):
        nomdao = istaklist.pop(idx)
        await query.edit_message_text(f"✅ *'{nomdao}'* istak ro'yxatidan o'chirildi.", parse_mode="Markdown")
    else:
        await query.edit_message_text("❌ Topilmadi.")

# ===================== /barcha (ADMIN) =====================
async def barcha_elonlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Bu buyruq faqat admin uchun!")
        return

    jami = []
    for elonlar in elon_db.values():
        jami.extend(elonlar)

    if not jami:
        await update.message.reply_text("📭 Hozircha hech qanday e'lon yo'q.")
        return

    await update.message.reply_text(f"📊 *Jami e'lonlar: {len(jami)} ta*", parse_mode="Markdown")
    for e in jami[:20]:
        msg = elon_text(e) + f"\n📌 Status: *{e['status']}*\n👤 User ID: `{e['user_id']}`"
        try:
            if e["rasm"]:
                await update.message.reply_photo(e["rasm"], caption=msg, parse_mode="Markdown")
            else:
                await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(msg, parse_mode="Markdown")

# ===================== ASOSIY =====================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # E'lon conversation
    elon_conv = ConversationHandler(
        entry_points=[CommandHandler("elon", elon_boshlash)],
        states={
            NOMI: [
                CallbackQueryHandler(elon_tur_tanlash, pattern="^tur_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, elon_nomi),
            ],
            HOLATI: [
                CallbackQueryHandler(elon_holati_callback, pattern="^holat_"),
            ],
            NARXI: [MessageHandler(filters.TEXT & ~filters.COMMAND, elon_narxi)],
            BOGLANISH: [MessageHandler(filters.TEXT & ~filters.COMMAND, elon_boglanish)],
            RASM: [
                MessageHandler(filters.PHOTO, elon_rasm),
                CommandHandler("skip", elon_rasm_skip),
                MessageHandler(filters.TEXT & ~filters.COMMAND, elon_rasm_skip),
            ],
            MANZIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, elon_manzil)],
        },
        fallbacks=[CommandHandler("bekor", elon_bekor)],
        allow_reentry=True,
    )

    # Qidiruv conversation
    qidir_conv = ConversationHandler(
        entry_points=[CommandHandler("qidir", qidir_boshlash)],
        states={
            QIDIR_NOMI: [MessageHandler(filters.TEXT & ~filters.COMMAND, qidir_nomi)],
        },
        fallbacks=[CommandHandler("bekor", elon_bekor)],
    )

    # Istak conversation
    istak_conv = ConversationHandler(
        entry_points=[CommandHandler("istaklar_qoshish", istaklar_qoshish_boshlash)],
        states={
            ISTAK_NOMI: [MessageHandler(filters.TEXT & ~filters.COMMAND, istak_nomi_qabul)],
        },
        fallbacks=[CommandHandler("bekor", elon_bekor)],
    )

    app.add_handler(elon_conv)
    app.add_handler(qidir_conv)
    app.add_handler(istak_conv)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("yordam", yordam))
    app.add_handler(CommandHandler("mening_kitoblarim", mening_kitoblarim))
    app.add_handler(CommandHandler("ochirish", ochirish))
    app.add_handler(CommandHandler("mening_istaklarim", mening_istaklarim))
    app.add_handler(CommandHandler("barcha", barcha_elonlar))

    app.add_handler(CallbackQueryHandler(sotildi_callback, pattern="^sotildi_"))
    app.add_handler(CallbackQueryHandler(ochirish_callback, pattern="^ochir_"))
    app.add_handler(CallbackQueryHandler(istak_ochir_callback, pattern="^istak_ochir_"))
    app.add_handler(CallbackQueryHandler(elon_tur_tanlash, pattern="^tur_"))

    print("🤖 Kitob Almashamiz boti ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
