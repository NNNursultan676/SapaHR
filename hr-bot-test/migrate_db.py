
#!/usr/bin/env python3
"""
Скрипт миграции базы данных
"""

import logging
from sqlalchemy import text, inspect
from database import get_session, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def column_exists(table_name, column_name):
    """Проверка существования колонки в таблице"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def migrate_database():
    """Применить миграции к базе данных"""
    session = get_session()
    
    try:
        logger.info("Начало миграции базы данных...")
        
        # Миграции для таблицы users
        users_migrations = {
            'telegram_id': "ALTER TABLE users ADD COLUMN telegram_id VARCHAR UNIQUE",
            'username': "ALTER TABLE users ADD COLUMN username VARCHAR",
            'email': "ALTER TABLE users ADD COLUMN email VARCHAR UNIQUE",
            'password': "ALTER TABLE users ADD COLUMN password VARCHAR",
            'level': "ALTER TABLE users ADD COLUMN level INTEGER DEFAULT 1",
            'onboarding_progress': "ALTER TABLE users ADD COLUMN onboarding_progress INTEGER DEFAULT 0",
            'hire_date': "ALTER TABLE users ADD COLUMN hire_date TIMESTAMP",
            'termination_date': "ALTER TABLE users ADD COLUMN termination_date TIMESTAMP",
            'termination_reason': "ALTER TABLE users ADD COLUMN termination_reason VARCHAR(255)"
        }
        
        for column_name, migration_sql in users_migrations.items():
            if not column_exists('users', column_name):
                try:
                    session.execute(text(migration_sql))
                    logger.info(f"✅ Добавлена колонка users.{column_name}")
                except Exception as e:
                    logger.error(f"❌ Ошибка при добавлении users.{column_name}: {e}")
            else:
                logger.info(f"ℹ️ Колонка users.{column_name} уже существует")
        
        # Миграции для таблицы admins
        admins_migrations = {
            'telegram_id': "ALTER TABLE admins ADD COLUMN telegram_id VARCHAR UNIQUE"
        }
        
        for column_name, migration_sql in admins_migrations.items():
            if not column_exists('admins', column_name):
                try:
                    session.execute(text(migration_sql))
                    logger.info(f"✅ Добавлена колонка admins.{column_name}")
                except Exception as e:
                    logger.error(f"❌ Ошибка при добавлении admins.{column_name}: {e}")
            else:
                logger.info(f"ℹ️ Колонка admins.{column_name} уже существует")
        
        # Делаем nullable для существующих колонок admins
        try:
            session.execute(text("ALTER TABLE admins ALTER COLUMN email DROP NOT NULL"))
            logger.info("✅ admins.email теперь nullable")
        except Exception as e:
            logger.info(f"ℹ️ admins.email уже nullable или ошибка: {e}")
        
        try:
            session.execute(text("ALTER TABLE admins ALTER COLUMN login DROP NOT NULL"))
            logger.info("✅ admins.login теперь nullable")
        except Exception as e:
            logger.info(f"ℹ️ admins.login уже nullable или ошибка: {e}")
        
        try:
            session.execute(text("ALTER TABLE admins ALTER COLUMN password DROP NOT NULL"))
            logger.info("✅ admins.password теперь nullable")
        except Exception as e:
            logger.info(f"ℹ️ admins.password уже nullable или ошибка: {e}")
        
        session.commit()
        session.close()
        
        # Форсируем закрытие всех соединений
        from database import engine
        engine.dispose()
        
        logger.info("✅ Миграция базы данных завершена успешно!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка миграции: {e}")
        session.rollback()
        session.close()
        raise

if __name__ == "__main__":
    migrate_database()
