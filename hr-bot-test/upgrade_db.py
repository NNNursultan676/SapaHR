
from database import get_session, Base, engine
from sqlalchemy import text, inspect
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def column_exists(table_name, column_name):
    """Проверка существования колонки в таблице"""
    try:
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except:
        return False

def upgrade_database():
    """Обновление базы данных с новыми таблицами и полями"""
    
    logger.info("Начало обновления базы данных...")
    
    try:
        # Создаем все новые таблицы
        Base.metadata.create_all(engine)
        logger.info("✅ Таблицы созданы/обновлены")
        
        db_session = get_session()
        
        # Проверяем и добавляем новые поля в users
        users_upgrades = {
            'level': ("ALTER TABLE users ADD COLUMN level INTEGER DEFAULT 1", "level"),
            'onboarding_progress': ("ALTER TABLE users ADD COLUMN onboarding_progress INTEGER DEFAULT 0", "onboarding_progress"),
            'hire_date': ("ALTER TABLE users ADD COLUMN hire_date TIMESTAMP", "hire_date"),
            'termination_date': ("ALTER TABLE users ADD COLUMN termination_date TIMESTAMP", "termination_date"),
            'termination_reason': ("ALTER TABLE users ADD COLUMN termination_reason VARCHAR(255)", "termination_reason")
        }
        
        for field_name, (sql, column_name) in users_upgrades.items():
            if not column_exists('users', column_name):
                try:
                    db_session.execute(text(sql))
                    logger.info(f"✅ Добавлено поле {column_name} в users")
                except Exception as e:
                    logger.info(f"ℹ️ Поле {column_name} не добавлено: {e}")
            else:
                logger.info(f"ℹ️ Поле {column_name} уже существует в users")
        
        # Обновляем роль с 'user' на 'employee'
        try:
            db_session.execute(text("UPDATE users SET role = 'employee' WHERE role = 'user'"))
            logger.info("✅ Обновлены роли пользователей")
        except Exception as e:
            logger.info(f"ℹ️ Роли не обновлены: {e}")
        
        db_session.commit()
        db_session.close()
        
        # Форсируем закрытие всех соединений
        engine.dispose()
        
        logger.info("✅ База данных успешно обновлена!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении базы данных: {e}")
        db_session.rollback()
        db_session.close()
        raise

if __name__ == "__main__":
    upgrade_database()
