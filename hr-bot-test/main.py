import os
import sys
import logging
import signal # Keep signal import as it might be used by Flask or other libraries
import time # Keep time import as it might be used by Flask or other libraries
from datetime import datetime, timezone # Keep datetime import as it might be used by Flask or other libraries

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def start_web_app(): # This function is no longer directly called by main, but might be imported elsewhere. Keeping it for now.
    """Запуск веб-приложения"""
    logger.info("🌐 Starting web application...")

    try:
        # Инициализация базы данных
        from database import init_db, test_database_connection, get_session, Admin
        import config
        logger.info("Initializing database...")

        if test_database_connection():
            logger.info("Database connection successful")
            init_db()
            logger.info("Database initialized")

            # Создание главного администратора
            try:
                session = get_session()
                main_admin_telegram_id = config.HOST_ADMIN_TELEGRAM_ID

                if not session.query(Admin).filter(Admin.telegram_id == main_admin_telegram_id).first():
                    from datetime import datetime, timezone
                    new_admin = Admin(
                        telegram_id=main_admin_telegram_id,
                        login=config.HOST_ADMIN_LOGIN,
                        password=config.HOST_ADMIN_PASSWORD,
                        level=3,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    session.add(new_admin)
                    session.commit()
                    logger.info(f"✅ Главный администратор создан (Telegram ID: {main_admin_telegram_id})")
                else:
                    logger.info(f"ℹ️ Главный администратор уже существует (Telegram ID: {main_admin_telegram_id})")

                session.close()
            except Exception as e:
                logger.error(f"Ошибка при создании администратора: {e}")
        else:
            logger.error("Database connection failed")
            return

        # Импортируем Flask приложение
        from app import app

        # Запускаем приложение
        logger.info("Starting Flask application on 0.0.0.0:5055")
        app.run(
            host='0.0.0.0',
            port=5055,
            debug=False
        )

    except Exception as e:
        logger.error(f"Web app startup failed: {e}")

def start_bot(): # This function is removed in the new main logic.
    """Запуск Telegram бота"""
    logger.info("🤖 Starting Telegram bot...")
    from bot import run_bot
    run_bot()

def signal_handler(sig, frame):
    """Обработчик сигнала завершения"""
    logger.info("\n⚠️ Stopping services...")
    sys.exit(0)

def main():
    """Главная функция запуска приложения"""

    # Переходим в директорию проекта
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    logger.info("🚀 Starting SapaHR Web Application...")
    logger.info("=" * 50)

    try:
        # Инициализация базы данных
        from database import init_db, test_database_connection

        logger.info("Initializing database...")

        if test_database_connection():
            logger.info("Database connection successful")
            init_db()
            logger.info("Database initialized")
        else:
            logger.error("Database connection failed")
            return

        # Импортируем Flask приложение
        from app import app

        # Запускаем приложение
        logger.info("Starting Flask application on 0.0.0.0:5055")
        logger.info("✅ Web app: http://0.0.0.0:5055")

        app.run(
            host='0.0.0.0',
            port=5055,
            debug=False
        )

    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()