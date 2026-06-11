import logging
import os
import subprocess
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image

# ===== НАСТРОЙКА ТОКЕНА =====
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise Exception("BOT_TOKEN is not set in environment variables")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

user_files = {}

def safe_remove(filepath):
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception as e:
            logging.error(f"Ошибка удаления файла {filepath}: {e}")

# ===== МЕНЮ СТАРТА =====
@dp.message_handler(commands=['start', 'help'])
async def start_command(message: types.Message):
    await message.reply(
        "👋 **Привет! Я профессиональный конвертер.**\n\n"
        "Отправь мне документ Word (`.docx`), текстовый файл или фото, "
        "и я преобразую его в PDF **с идеальным сохранением всего форматирования!**",
        parse_mode="Markdown"
    )

# ===== ОБРАБОТКА ИЗОБРАЖЕНИЙ =====
@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message):
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    downloaded = await bot.download_file(file_info.file_path)
    
    input_path = f"img_{message.from_user.id}_{photo.file_id}.jpg"
    with open(input_path, "wb") as f:
        f.write(downloaded.read())
        
    user_files[message.from_user.id] = {"path": input_path}
    
    keyboard = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("🖼️ Конвертировать в PDF", callback_data="photo_to_pdf"),
        InlineKeyboardButton("❌ Отмена", callback_data="cancel_action")
    )
    await message.reply("Изображение получено. Выберите действие:", reply_markup=keyboard)

# ===== ОБРАБОТКА ДОКУМЕНТОВ =====
@dp.message_handler(content_types=types.ContentType.DOCUMENT)
async def handle_document(message: types.Message):
    doc = message.document
    file_name = doc.file_name.lower()
    
    if not (file_name.endswith(".docx") or file_name.endswith(".txt") or file_name.endswith(".doc")):
        await message.reply("Извините, поддерживаются только форматы .docx, .doc, .txt и изображения.")
        return

    file_info = await bot.get_file(doc.file_id)
    downloaded = await bot.download_file(file_info.file_path)
    
    input_path = f"doc_{message.from_user.id}_{doc.file_name}"
    with open(input_path, "wb") as f:
        f.write(downloaded.read())
        
    user_files[message.from_user.id] = {"path": input_path, "orig_name": doc.file_name}
    
    keyboard = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("📄 Конвертировать в PDF", callback_data="office_to_pdf"),
        InlineKeyboardButton("❌ Отмена", callback_data="cancel_action")
    )
    await message.reply(f"Файл `{doc.file_name}` успешно получен.", reply_markup=keyboard, parse_mode="Markdown")

# ===== ОБРАБОТЧИК КНОПОК =====
@dp.callback_query_handler(lambda call: True)
async def process_callback(call: types.CallbackQuery):
    user_id = call.from_user.id
    
    if call.data == "cancel_action":
        if user_id in user_files:
            safe_remove(user_files[user_id]["path"])
            del user_files[user_id]
        await call.message.edit_text("Действие отменено.")
        return

    if user_id not in user_files:
        await call.answer("Файл не найден. Отправьте его заново.", show_alert=True)
        await call.message.delete()
        return

    input_path = user_files[user_id]["path"]
    await call.message.edit_text("⏳ Идет идеальная конвертация через LibreOffice Core. Подождите...")

    try:
        if call.data == "photo_to_pdf":
            out_path = f"converted_{user_id}.pdf"
            img = Image.open(input_path).convert("RGB")
            img.save(out_path, "PDF")

            elif call.data == "office_to_pdf":
            # Фиксированное имя для выходного файла, чтобы ничего не терялось
            out_path = f"result_{user_id}.pdf"
            
            # Запускаем оригинальную утилиту LibreOffice
            cmd = [
                "libreoffice", "--headless", "--convert-to", "pdf", 
                input_path, "--outdir", "."
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            
            # Находим созданный LibreOffice файл и переименовываем его в наш out_path
            orig_base = os.path.splitext(os.path.basename(input_path))[0]
            generated_file = f"{orig_base}.pdf"
            
            if os.path.exists(generated_file):
                os.rename(generated_file, out_path)


        # Отправка готового файла
        if os.path.exists(out_path):
            with open(out_path, "rb") as f:
                await call.message.reply_document(f, caption="✨ Готово! Файл сохранен с исходным форматированием.")
            safe_remove(out_path)
            await call.message.delete()
        else:
            raise Exception("Файл PDF не был сгенерирован движком.")

    except Exception as e:
        logging.error(f"Ошибка офисной конвертации: {e}")
        await call.message.edit_text("❌ Ошибка генерации. Убедитесь, что структура документа корректна.")

    finally:
        safe_remove(input_path)
        if user_id in user_files:
            del user_files[user_id]

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
