import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from docx import Document
from PIL import Image
from fpdf import FPDF

# ===== TOKEN (Railway Variables) =====
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN is not set in environment variables")

# ===== BOT =====
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)

# Функция для создания PDF с поддержкой русского языка
def create_base_pdf():
    pdf = FPDF()
    pdf.add_page()
    # Регистрируем шрифт DejaVuSans, который корректно отображает кириллицу
    # Файл DejaVuSans.ttf должен лежать в корне вашего репозитория на GitHub
    pdf.add_font("DejaVu", "", "DejaVuSans.ttf")
    pdf.set_font("DejaVu", size=12)
    return pdf

# ===== TEXT -> PDF =====
@dp.message_handler(commands=['text'])
async def text_to_pdf(message: types.Message):
    text = message.get_args()
    
    if not text:
        await message.reply("Используй: /text твой текст")
        return

    pdf = create_base_pdf()
    pdf.multi_cell(0, 10, text)
    
    file_name = "text.pdf"
    pdf.output(file_name)
    
    with open(file_name, "rb") as pdf_file:
        await message.reply_document(pdf_file)

# ===== DOCX -> PDF =====
@dp.message_handler(content_types=types.ContentType.DOCUMENT)
async def docx_to_pdf(message: types.Message):
    doc = message.document
    
    if not doc.file_name.endswith(".docx"):
        await message.reply("Отправь .docx файл")
        return

    # Скачивание файла во временную папку
    file_info = await bot.get_file(doc.file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    
    temp_docx = "temp.docx"
    with open(temp_docx, "wb") as f:
        f.write(downloaded_file.read())
        
    document = Document(temp_docx)
    text = "\n".join([p.text for p in document.paragraphs])
    
    pdf = create_base_pdf()
    pdf.multi_cell(0, 10, text)
    
    file_name = "docx.pdf"
    pdf.output(file_name)
    
    with open(file_name, "rb") as pdf_file:
        await message.reply_document(pdf_file)
        
    # Чистка временных файлов
    if os.path.exists(temp_docx):
        os.remove(temp_docx)

# ===== IMAGE -> PDF =====
@dp.message_handler(content_types=types.ContentType.PHOTO)
async def image_to_pdf(message: types.Message):
    photo = message.photo[-1]
    
    file_info = await bot.get_file(photo.file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    
    temp_img = "temp_image.jpg"
    with open(temp_img, "wb") as f:
        f.write(downloaded_file.read())
        
    img = Image.open(temp_img).convert("RGB")
    
    file_name = "image.pdf"
    img.save(file_name, "PDF")
    
    with open(file_name, "rb") as pdf_file:
        await message.reply_document(pdf_file)
        
    # Чистка временных файлов
    if os.path.exists(temp_img):
        os.remove(temp_img)

# ===== START =====
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply(
        "Привет! Я PDF конвертер.\n\n"
        "📄 /text текст -> PDF\n"
        "📸 отправь фото -> PDF\n"
        "📝 отправь DOCX -> PDF"
    )

# ===== RUN =====
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
