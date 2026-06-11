import logging
import os
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

# Функция для создания PDF с поддержкой русского языка
def create_base_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("DejaVu", "", "DejaVuSans.ttf")
    pdf.set_font("DejaVu", size=12)
    return pdf

# Стирание временного файла с диска
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
        "👋 **Привет! Я универсальный медиа-конвертер.**\n\n"
        "Просто отправь мне любой поддерживаемый файл или фото, "
        "и я предложу доступные варианты конвертации с помощью удобных кнопок!",
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
        
    user_files[message.from_user.id] = {"path": input_path, "type": "photo"}
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🖼️ Конвертировать в PDF", callback_data="photo_to_pdf"),
        InlineKeyboardButton("❌ Отмена", callback_data="cancel_action")
    )
    await message.reply("Изображение получено. Выберите действие:", reply_markup=keyboard)

# ===== ОБРАБОТКА ДОКУМЕНТОВ =====
@dp.message_handler(content_types=types.ContentType.DOCUMENT)
async def handle_document(message: types.Message):
    doc = message.document
    file_name = doc.file_name.lower()
    
    file_info = await bot.get_file(doc.file_id)
    downloaded = await bot.download_file(file_info.file_path)
    
    input_path = f"doc_{message.from_user.id}_{doc.file_id}_{doc.file_name}"
    with open(input_path, "wb") as f:
        f.write(downloaded.read())
        
    user_files[message.from_user.id] = {"path": input_path, "type": "doc", "orig_name": doc.file_name}
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    if file_name.endswith(".docx"):
        keyboard.add(
            InlineKeyboardButton("📄 DOCX ➡️ PDF (с картинками)", callback_data="docx_to_pdf"),
            InlineKeyboardButton("📝 DOCX ➡️ TXT (Только текст)", callback_data="docx_to_txt")
        )
    elif file_name.endswith(".pdf"):
        keyboard.add(
            InlineKeyboardButton("📝 PDF ➡️ TXT (Извлечь текст)", callback_data="pdf_to_txt"),
            InlineKeyboardButton("✍️ PDF ➡️ DOCX (В документ)", callback_data="pdf_to_docx")
        )
    elif file_name.endswith(".txt"):
        keyboard.add(
            InlineKeyboardButton("📄 TXT ➡️ PDF", callback_data="txt_to_pdf"),
            InlineKeyboardButton("✍️ TXT ➡️ DOCX", callback_data="txt_to_docx")
        )
    else:
        await message.reply("Извините, этот формат документов пока не поддерживается.")
        safe_remove(input_path)
        return

    keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_action"))
    await message.reply(f"Файл `{doc.file_name}` загружен. Что нужно сделать?", reply_markup=keyboard, parse_mode="Markdown")

# ===== ОБРАБОТЧИК КНОПОК (CALLBACK) =====
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
        await call.answer("Файл устарел или не найден. Отправьте его заново.", show_alert=True)
        await call.message.delete()
        return

    file_data = user_files[user_id]
    input_path = file_data["path"]
    
    await call.message.edit_text("⏳ Конвертирую файл, пожалуйста, подождите...")

    # Массив для хранения временных картинок, вытащенных из docx
    extracted_images = []

    try:
        # --- ФОТО В PDF ---
        if call.data == "photo_to_pdf":
            out_path = "converted_image.pdf"
            img = Image.open(input_path).convert("RGB")
            img.save(out_path, "PDF")
            
        # --- DOCX В PDF (С ПОДДЕРЖКОЙ КАРТИНОК И ТЕКСТА) ---
        elif call.data == "docx_to_pdf":
            out_path = "converted_docx.pdf"
            doc = Document(input_path)
            pdf = create_base_pdf()
            
            # Построчно перебираем структуру документа Word
            for paragraph in doc.paragraphs:
                # Проверяем наличие встроенных картинок внутри текущего абзаца
                inline_shapes = paragraph._element.xpath('.//w:drawing')
                if inline_shapes:
                    for shape in inline_shapes:
                        blips = shape.xpath('.//a:blip/@r:embed')
                        if blips:
                            rId = blips[0]
                            # Извлекаем файл картинки в байтах из архива docx
                            image_part = doc.part.related_parts[rId]
                            image_bytes = image_part._blob
                            
                            # Временно пишем картинку на диск
                            img_name = f"temp_extract_{user_id}_{len(extracted_images)}.png"
                            with open(img_name, "wb") as f_img:
                                f_img.write(image_bytes)
                            extracted_images.append(img_name)
                            
                            try:
                                with Image.open(img_name) as temp_pil:
                                    w, h = temp_pil.size
                                
                                # Рассчитываем ширину картинки под формат A4 (макс 180мм)
                                max_width = 180
                                ratio = max_width / float(w)
                                new_h = int(float(h) * ratio)
                                
                                # Проверяем, влезет ли картинка по высоте, если нет — переносим на новую страницу
                                if pdf.get_y() + new_h > 260:
                                    pdf.add_page()
                                    
                                pdf.image(img_name, w=max_width)
                                pdf.ln(5)
                            except Exception as img_err:
                                logging.error(f"Не удалось отрисовать картинку в PDF: {img_err}")

                # Если в абзаце присутствует текст, печатаем его вслед за картинкой
                if paragraph.text.strip():
                    if pdf.get_y() > 260:
                        pdf.add_page()
                    pdf.multi_cell(0, 10, paragraph.text)
                    pdf.ln(2)

            pdf.output(out_path)
            
        # --- DOCX В TXT ---
        elif call.data == "docx_to_txt":
            out_path = "converted_docx.txt"
            doc = Document(input_path)
            text = "\n".join([p.text for p in doc.paragraphs])
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)

        # --- TXT В PDF ---
        elif call.data == "txt_to_pdf":
            out_path = "converted_txt.pdf"
            with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            pdf = create_base_pdf()
            pdf.multi_cell(0, 10, text)
            pdf.output(out_path)

        # --- TXT В DOCX ---
        elif call.data == "txt_to_docx":
            out_path = "converted_txt.docx"
            with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            doc = Document()
            doc.add_paragraph(text)
            doc.save(out_path)

        # --- PDF В TXT ---
        elif call.data == "pdf_to_txt":
            out_path = "extracted_text.txt"
            reader = PdfReader(input_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text if text.strip() else "Не удалось извлечь печатный текст из PDF.")

        # --- PDF В DOCX ---
        elif call.data == "pdf_to_docx":
            out_path = "converted_pdf.docx"
            reader = PdfReader(input_path)
            doc = Document()
            for page in reader.pages:
                text = page.extract_text() or ""
                doc.add_paragraph(text)
            doc.save(out_path)

        # Отправка готового файла пользователю в чат
        with open(out_path, "rb") as f:
            await call.message.reply_document(f, caption="✨ Готово! Ваш файл успешно конвертирован.")
            
        await call.message.delete()
        safe_remove(out_path)

    except Exception as e:
        logging.error(f"Критическая ошибка конвертации: {e}")
        await call.message.edit_text("❌ Извините, произошла ошибка обработки структуры этого файла.")

    finally:
                # Полная чистка диска от всех типов временных файлов
        safe_remove(input_path)
        for img_path in extracted_images:
            safe_remove(img_path)
        if user_id in user_files:
            del user_files[user_id]

# ===== RUN =====
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
