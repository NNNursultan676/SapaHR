import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import TelegramError
import config
from database import get_session, User

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_group_membership(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=config.GROUP_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except TelegramError as e:
        logger.error(f"Error checking group membership: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    is_member = await check_group_membership(context, user.id)
    is_admin = str(user.id) == config.HOST_ADMIN_TELEGRAM_ID
    
    if not is_member and not is_admin:
        await update.message.reply_text(
            "❌ Извините, у вас нет доступа. Вас нет в нашей группе.\n"
            "❌ Кешіріңіз, сізге қол жетімділік жоқ. Сіз біздің топта емессіз."
        )
        return
    
    
    session = get_session()
    db_user = session.query(User).filter_by(telegram_id=str(user.id)).first()
    
    if not db_user:
        db_user = User(
            telegram_id=str(user.id),
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        session.add(db_user)
        session.commit()
    
    session.close()
    
    keyboard = [
        [InlineKeyboardButton("👥 О компании", callback_data='about_company'),
         InlineKeyboardButton("📊 Личные данные", callback_data='personal_data')],
        [InlineKeyboardButton("👨‍💼 Сотрудники", callback_data='employees'),
         InlineKeyboardButton("📝 Мой статус", callback_data='my_status')],
        [InlineKeyboardButton("💼 Вакансии", callback_data='vacations'),
         InlineKeyboardButton("🎯 Подать заявку", callback_data='submit_request')],
        [InlineKeyboardButton("📹 Предложить видео", callback_data='suggest_video'),
         InlineKeyboardButton("❓ Опросы", callback_data='polls')],
        [InlineKeyboardButton("✍️ Написать всем", callback_data='write_all'),
         InlineKeyboardButton("ℹ️ Информация о статусах", callback_data='status_info')],
        [InlineKeyboardButton("🌐 Открыть веб-приложение", web_app={'url': f'http://10.128.0.79:5000'})]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 Здравствуйте, {user.first_name}!\n\n"
        f"Добро пожаловать в SapaHR - систему управления персоналом.\n\n"
        f"Выберите действие из меню ниже:",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data
    
    if data == 'about_company':
        await query.message.reply_text(
            "🏢 О компании SAPA\n\n"
            "SAPA Technologies - ведущая технологическая компания в Казахстане.\n\n"
            f"Наши компании:\n" + "\n".join([f"• {comp}" for comp in config.COMPANIES])
        )
    
    elif data == 'personal_data':
        session = get_session()
        db_user = session.query(User).filter_by(telegram_id=str(user.id)).first()
        session.close()
        
        await query.message.reply_text(
            f"👤 Ваши данные:\n\n"
            f"Имя: {db_user.first_name or 'Не указано'} {db_user.last_name or ''}\n"
            f"Username: @{db_user.username or 'Не указан'}\n"
            f"Компания: {db_user.company or 'Не указана'}\n"
            f"Должность: {db_user.position or 'Не указана'}\n"
            f"Баллы: {db_user.points} 🏆"
        )
    
    elif data == 'employees':
        await query.message.reply_text("👨‍💼 Список сотрудников доступен в веб-приложении")
    
    elif data == 'my_status':
        await query.message.reply_text("📊 Информация о вашем статусе доступна в веб-приложении")
    
    elif data == 'vacations':
        await query.message.reply_text("🏖 Управление отпусками доступно в веб-приложении")
    
    elif data == 'submit_request':
        await query.message.reply_text("📝 Подача заявок доступна в веб-приложении")
    
    elif data == 'suggest_video':
        await query.message.reply_text("📹 Предложения видео принимаются в веб-приложении")
    
    elif data == 'polls':
        await query.message.reply_text("❓ Опросы доступны в веб-приложении")
    
    elif data == 'write_all':
        await query.message.reply_text("✉️ Рассылки доступны в веб-приложении для администраторов")
    
    elif data == 'status_info':
        await query.message.reply_text(
            "ℹ️ Информация о статусах:\n\n"
            "🟢 Активный - работает в офисе\n"
            "🟡 Удаленно - работает из дома\n"
            "🔴 Отпуск - в отпуске\n"
            "⚫ Больничный - на больничном"
        )

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("Bot started")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
