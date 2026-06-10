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


    # ===== TEXT → PDF =====
    @dp.message_handler(commands=['text'])
    async def text_to_pdf(message: types.Message):
        text = message.get_args()

            if not text:
                    await message.reply("Используй: /text твой текст")
                            return

                                pdf = FPDF()
                                    pdf.add_page()
                                        pdf.set_font("Arial", size=12)
                                            pdf.multi_cell(0, 10, text)

                                                file_name = "text.pdf"
                                                    pdf.output(file_name)

                                                        await message.reply_document(open(file_name, "rb"))


                                                        # ===== DOCX → PDF =====
                                                        @dp.message_handler(content_types=types.ContentType.DOCUMENT)
                                                        async def docx_to_pdf(message: types.Message):
                                                            doc = message.document

                                                                if not doc.file_name.endswith(".docx"):
                                                                        await message.reply("Отправь .docx файл")
                                                                                return

                                                                                    file = await doc.download()
                                                                                        document = Document(file.name)

                                                                                            text = "\n".join([p.text for p in document.paragraphs])

                                                                                                pdf = FPDF()
                                                                                                    pdf.add_page()
                                                                                                        pdf.set_font("Arial", size=12)
                                                                                                            pdf.multi_cell(0, 10, text)

                                                                                                                file_name = "docx.pdf"
                                                                                                                    pdf.output(file_name)

                                                                                                                        await message.reply_document(open(file_name, "rb"))


                                                                                                                        # ===== IMAGE → PDF =====
                                                                                                                        @dp.message_handler(content_types=types.ContentType.PHOTO)
                                                                                                                        async def image_to_pdf(message: types.Message):
                                                                                                                            photo = message.photo[-1]
                                                                                                                                file = await photo.download()

                                                                                                                                    img = Image.open(file.name).convert("RGB")

                                                                                                                                        file_name = "image.pdf"
                                                                                                                                            img.save(file_name, "PDF")

                                                                                                                                                await message.reply_document(open(file_name, "rb"))


                                                                                                                                                # ===== START =====
                                                                                                                                                @dp.message_handler(commands=['start'])
                                                                                                                                                async def start(message: types.Message):
                                                                                                                                                    await message.reply(
                                                                                                                                                            "Привет! Я PDF конвертер.\n\n"
                                                                                                                                                                    "📄 /text текст → PDF\n"
                                                                                                                                                                            "📷 отправь фото → PDF\n"
                                                                                                                                                                                    "📄 отправь DOCX → PDF"
                                                                                                                                                                                        )


                                                                                                                                                                                        # ===== RUN =====
                                                                                                                                                                            if __name__ == "__main__":
                                                                                                                                                                                    import asyncio
                                                                                                                                                                                        from aiogram import executor

                                                                                                                                                                                            executor.start_polling(dp, skip_updates=True)