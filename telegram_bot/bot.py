# bot.py
import logging
import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from telegram import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ваши токены
BOT_TOKEN = "8249414346:AAH6bXmsfne9O-Cubu1a61vDp_tSNO0VSvc"
DG_TOKEN = "025397fd-2b9e-4524-9c2f-3c4644e3af1a"

# URL вашего веб-приложения
WEB_APP_URL = "https://alexeiyaganov.github.io/2gis_app/map.html"


async def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start"""
    user = update.effective_user

    # Создаем клавиатуру с кнопкой веб-приложения
    keyboard = [
        [KeyboardButton("🏠 Поиск жилья в Москве", web_app=WebAppInfo(url=WEB_APP_URL))],
        [KeyboardButton("📍 Поделиться локацией", request_location=True)],
        ["ℹ️ Помощь", "🏙️ Районы Москвы"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        "Я бот для поиска и рекомендаций жилья в Москве.\n\n"
        "🔹 <b>Поиск жилья</b> - умный подбор квартир по вашим критериям\n"
        "🔹 <b>Районы Москвы</b> - информация о разных округах\n"
        "🔹 <b>Рекомендации</b> - AI-подбор лучших вариантов\n\n"
        "Нажмите кнопку ниже, чтобы начать поиск:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def help_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды помощи"""
    help_text = """
🤖 <b>Бот для поиска жилья в Москве</b>

🏠 <b>Основные функции:</b>

• <b>Умный поиск жилья</b> - подбор квартир по текстовому запросу
• <b>Рейтинги районов</b> - оценка инфраструктуры, экологии, транспорта
• <b>AI-рекомендации</b> - интеллектуальный подбор лучших вариантов
• <b>Карта 2GIS</b> - просмотр на интерактивной карте

📝 <b>Примеры запросов:</b>
• "студия с евроремонтом до 100000"
• "двушка у метро в Северо-Западном округе"
• "трешка в новостройке с мебелью"

🏙️ <b>Доступные районы:</b>
• Северо-Западный округ
• ЦАО - Центральный округ
• ЗАО - Западный округ  

⚡ <b>Технологии:</b>
• 2GIS API для карт и информации о районах
• AI-алгоритмы для рекомендаций
• Реальные данные с ЦИАН
    """
    await update.message.reply_text(help_text, parse_mode='HTML')


async def handle_location(update: Update, context: CallbackContext) -> None:
    """Обработка отправленной локации"""
    location = update.message.location
    lat = location.latitude
    lng = location.longitude

    await update.message.reply_text(
        f"📍 <b>Ваша локация получена!</b>\n\n"
        f"Можете использовать ее для поиска жилья поблизости.\n\n"
        f"🌐 <b>Координаты:</b>\n"
        f"Широта: <code>{lat}</code>\n"
        f"Долгота: <code>{lng}</code>\n\n"
        f"🗺️ <a href='https://2gis.ru/geo/{lng},{lat}'>Открыть в 2GIS</a>\n"
        f"🏠 <a href='{WEB_APP_URL}?lat={lat}&lng={lng}'>Искать жилье рядом</a>",
        parse_mode='HTML',
        disable_web_page_preview=True
    )


async def handle_web_app_data(update: Update, context: CallbackContext) -> None:
    """Обработка данных из веб-приложения"""
    try:
        data = json.loads(update.message.web_app_data.data)
        action = data.get('action')

        if action == 'share_location':
            lat = data.get('lat')
            lng = data.get('lng')
            message = data.get('message', 'Моя локация')

            await update.message.reply_location(
                latitude=lat,
                longitude=lng,
                live_period=86400
            )

            await update.message.reply_text(
                f"📍 <b>{message}</b>\n\n"
                f"🗺️ <a href='https://2gis.ru/geo/{lng},{lat}'>Открыть в 2GIS</a>",
                parse_mode='HTML'
            )

        elif action == 'share_housing':
            offer = data.get('offer', {})
            message = data.get('message', 'Найдено жилье')

            await update.message.reply_text(
                f"🏠 <b>Найдено отличное жилье!</b>\n\n"
                f"{message}\n\n"
                f"📏 Площадь: {offer.get('area', 'N/A')} м²\n"
                f"🏢 Этаж: {offer.get('floor', 'N/A')}/{offer.get('total_floors', 'N/A')}\n"
                f"🚇 До метро: {offer.get('metro_time', 'N/A')} мин\n"
                f"⭐ Рейтинг: {offer.get('score', 'N/A')}\n\n"
                f"<a href='{WEB_APP_URL}'>Посмотреть на карте</a>",
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"Error processing web app data: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке данных")


async def handle_message(update: Update, context: CallbackContext) -> None:
    """Обработка текстовых сообщений"""
    text = update.message.text

    if text == "ℹ️ Помощь":
        await help_command(update, context)
    elif text == "🏙️ Районы Москвы":
        await send_districts_info(update, context)
    else:
        await update.message.reply_text(
            "Используйте кнопки ниже для поиска жилья 🏠",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("🏠 Поиск жилья в Москве", web_app=WebAppInfo(url=WEB_APP_URL))],
                [KeyboardButton("📍 Поделиться локацией", request_location=True)],
                ["🏙️ Районы Москвы", "ℹ️ Помощь"]
            ], resize_keyboard=True)
        )


async def send_districts_info(update: Update, context: CallbackContext) -> None:
    """Отправка информации о районах Москвы"""
    districts_info = """
🏙️ <b>Районы Москвы для поиска жилья</b>

<b>Северо-Западный округ</b>
• Экологически чистый район
• Развитая инфраструктура  
• Хорошая транспортная доступность
• Умеренные цены на жилье

<b>ЦАО - Центральный округ</b>
• Престижный центр города
• Отличная транспортная доступность  
• Высокие цены на жилье
• Много культурных объектов

<b>ЗАО - Западный округ</b>
• Хорошая экология
• Развитая инфраструктура
• Комфортные спальные районы
• Умеренные цены

<b>Выберите район в веб-приложении для подробной информации и поиска жилья!</b>
    """

    await update.message.reply_text(
        districts_info,
        parse_mode='HTML',
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("🏠 Поиск жилья в Москве", web_app=WebAppInfo(url=WEB_APP_URL))],
            ["ℹ️ Помощь"]
        ], resize_keyboard=True)
    )


def main() -> None:
    """Запуск бота"""
    # Создаем Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запускаем бота
    print("🤖 Бот запускается...")
    print(f"🔑 Токен бота: {BOT_TOKEN[:10]}...")
    print(f"🗺️ Токен 2GIS: {DG_TOKEN[:10]}...")
    print("🏠 Система рекомендаций жилья готова!")
    print("📊 Используются реальные данные из файла cian_north_west")
    print("⏳ Ожидаем сообщения...")

    application.run_polling()
    print("✅ Бот успешно запущен!")


if __name__ == "__main__":
    main()