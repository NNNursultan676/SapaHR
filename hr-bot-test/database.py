
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import config
import logging

logger = logging.getLogger(__name__)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, nullable=True)
    username = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=True)
    password = Column(String, nullable=True)
    first_name = Column(String)
    last_name = Column(String)
    phone = Column(String)
    company = Column(String)
    position = Column(String)
    department = Column(String)
    avatar = Column(String)
    role = Column(String, default='employee')  # employee, hr, manager, admin
    points = Column(Integer, default=0)
    level = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    onboarding_completed = Column(Boolean, default=False)
    onboarding_progress = Column(Integer, default=0)
    hire_date = Column(DateTime)
    termination_date = Column(DateTime)
    termination_reason = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    vacations = relationship('Vacation', back_populates='user')
    requests = relationship('Request', back_populates='user')
    activities = relationship('Activity', back_populates='user')

class Vacation(Base):
    __tablename__ = 'vacations'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    days_count = Column(Integer)
    status = Column(String, default='pending')
    reason = Column(Text)
    admin_comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship('User', back_populates='vacations')

class Admin(Base):
    __tablename__ = 'admins'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, nullable=True)
    email = Column(String, unique=True, nullable=True)
    login = Column(String, unique=True, nullable=True)
    password = Column(String, nullable=True)
    level = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

# Инициализация движка базы данных
try:
    engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Error creating database engine: {e}")
    raise

def get_session():
    return SessionLocal()

def check_and_add_columns():
    """Проверка и добавление недостающих колонок"""
    from sqlalchemy import inspect
    
    session = get_session()
    inspector = inspect(engine)
    
    try:
        # Проверяем колонки в таблице users
        if 'users' in inspector.get_table_names():
            existing_columns = [col['name'] for col in inspector.get_columns('users')]
            
            users_columns = {
                'telegram_id': "ALTER TABLE users ADD COLUMN telegram_id VARCHAR UNIQUE",
                'username': "ALTER TABLE users ADD COLUMN username VARCHAR",
                'email': "ALTER TABLE users ADD COLUMN email VARCHAR UNIQUE",
                'password': "ALTER TABLE users ADD COLUMN password VARCHAR",
                'first_name': "ALTER TABLE users ADD COLUMN first_name VARCHAR",
                'last_name': "ALTER TABLE users ADD COLUMN last_name VARCHAR",
                'phone': "ALTER TABLE users ADD COLUMN phone VARCHAR",
                'company': "ALTER TABLE users ADD COLUMN company VARCHAR",
                'position': "ALTER TABLE users ADD COLUMN position VARCHAR",
                'department': "ALTER TABLE users ADD COLUMN department VARCHAR",
                'avatar': "ALTER TABLE users ADD COLUMN avatar VARCHAR",
                'role': "ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'employee'",
                'points': "ALTER TABLE users ADD COLUMN points INTEGER DEFAULT 0",
                'level': "ALTER TABLE users ADD COLUMN level INTEGER DEFAULT 1",
                'is_active': "ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE",
                'onboarding_completed': "ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN DEFAULT FALSE",
                'onboarding_progress': "ALTER TABLE users ADD COLUMN onboarding_progress INTEGER DEFAULT 0",
                'hire_date': "ALTER TABLE users ADD COLUMN hire_date TIMESTAMP",
                'termination_date': "ALTER TABLE users ADD COLUMN termination_date TIMESTAMP",
                'termination_reason': "ALTER TABLE users ADD COLUMN termination_reason VARCHAR(255)",
                'created_at': "ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            }
            
            for col_name, sql in users_columns.items():
                if col_name not in existing_columns:
                    try:
                        session.execute(text(sql))
                        session.commit()
                        logger.info(f"✅ Добавлена колонка users.{col_name}")
                    except Exception as e:
                        logger.warning(f"Не удалось добавить users.{col_name}: {e}")
                        session.rollback()
        
        # Проверяем колонки в таблице news
        if 'news' in inspector.get_table_names():
            existing_columns = [col['name'] for col in inspector.get_columns('news')]
            
            news_columns = {
                'image_url': "ALTER TABLE news ADD COLUMN image_url VARCHAR(500)",
                'category': "ALTER TABLE news ADD COLUMN category VARCHAR(100)",
                'author': "ALTER TABLE news ADD COLUMN author VARCHAR(255)",
                'views': "ALTER TABLE news ADD COLUMN views INTEGER DEFAULT 0"
            }
            
            for col_name, sql in news_columns.items():
                if col_name not in existing_columns:
                    try:
                        session.execute(text(sql))
                        session.commit()
                        logger.info(f"✅ Добавлена колонка news.{col_name}")
                    except Exception as e:
                        logger.warning(f"Не удалось добавить news.{col_name}: {e}")
                        session.rollback()
        
        # Проверяем колонки в таблице admins
        if 'admins' in inspector.get_table_names():
            existing_columns = [col['name'] for col in inspector.get_columns('admins')]
            
            admins_columns = {
                'telegram_id': "ALTER TABLE admins ADD COLUMN telegram_id VARCHAR UNIQUE"
            }
            
            for col_name, sql in admins_columns.items():
                if col_name not in existing_columns:
                    try:
                        session.execute(text(sql))
                        session.commit()
                        logger.info(f"✅ Добавлена колонка admins.{col_name}")
                    except Exception as e:
                        logger.warning(f"Не удалось добавить admins.{col_name}: {e}")
                        session.rollback()
            
            # Делаем nullable для существующих колонок users
            try:
                session.execute(text("ALTER TABLE users ALTER COLUMN telegram_id DROP NOT NULL"))
                session.commit()
                logger.info("✅ users.telegram_id теперь nullable")
            except:
                pass
        
        # Проверяем колонки в таблице polls
        if 'polls' in inspector.get_table_names():
            existing_columns = [col['name'] for col in inspector.get_columns('polls')]
            
            polls_columns = {
                'is_active': "ALTER TABLE polls ADD COLUMN is_active BOOLEAN DEFAULT TRUE"
            }
            
            for col_name, sql in polls_columns.items():
                if col_name not in existing_columns:
                    try:
                        session.execute(text(sql))
                        session.commit()
                        logger.info(f"✅ Добавлена колонка polls.{col_name}")
                    except Exception as e:
                        logger.warning(f"Не удалось добавить polls.{col_name}: {e}")
                        session.rollback()
        
        # Проверяем колонки в таблице onboarding
        if 'onboarding' in inspector.get_table_names():
            existing_columns = [col['name'] for col in inspector.get_columns('onboarding')]
            
            if 'progress' not in existing_columns:
                try:
                    session.execute(text("ALTER TABLE onboarding ADD COLUMN progress INTEGER DEFAULT 0"))
                    session.commit()
                    logger.info("✅ Добавлена колонка onboarding.progress")
                except Exception as e:
                    logger.warning(f"Не удалось добавить onboarding.progress: {e}")
                    session.rollback()
            
            # Делаем nullable для существующих колонок admins
            try:
                session.execute(text("ALTER TABLE admins ALTER COLUMN email DROP NOT NULL"))
                session.commit()
                logger.info("✅ admins.email теперь nullable")
            except:
                pass
            
            try:
                session.execute(text("ALTER TABLE admins ALTER COLUMN login DROP NOT NULL"))
                session.commit()
                logger.info("✅ admins.login теперь nullable")
            except:
                pass
            
            try:
                session.execute(text("ALTER TABLE admins ALTER COLUMN password DROP NOT NULL"))
                session.commit()
                logger.info("✅ admins.password теперь nullable")
            except:
                pass
        
    except Exception as e:
        logger.error(f"Ошибка при проверке колонок: {e}")
        session.rollback()
    finally:
        session.close()

def init_knowledge_base():
    """Инициализация базы знаний"""
    session = get_session()
    
    try:
        if session.query(KnowledgeCategory).count() > 0:
            logger.info("База знаний уже инициализирована")
            session.close()
            return
        
        categories_data = [
            {
                'name': 'Отпуска',
                'icon': '🏖',
                'description': 'Процессы оформления и планирования отпусков',
                'articles': [
                    {
                        'title': 'Как оформить отпуск',
                        'content': '''<h2>Процедура оформления отпуска</h2>
<p>Для оформления отпуска необходимо:</p>
<ol>
<li>Заполнить заявку на отпуск минимум за 2 недели до начала</li>
<li>Указать даты начала и окончания отпуска</li>
<li>Указать причину (обязательный или дополнительный отпуск)</li>
<li>Дождаться одобрения от руководителя</li>
</ol>'''
                    },
                    {
                        'title': 'График отпусков',
                        'content': '''<h2>График отпусков на год</h2>
<p>График отпусков составляется ежегодно до 15 декабря предшествующего года.</p>'''
                    }
                ]
            },
            {
                'name': 'Заявки и запросы',
                'icon': '📝',
                'description': 'Процессы подачи и обработки различных заявок',
                'articles': [
                    {
                        'title': 'Типы заявок',
                        'content': '''<h2>Виды заявок в системе</h2>
<p>Технические, кадровые и административные заявки.</p>'''
                    }
                ]
            },
            {
                'name': 'FAQ - Частые вопросы',
                'icon': '❓',
                'description': 'Ответы на самые частые вопросы сотрудников',
                'articles': [
                    {
                        'title': 'Как получить справку с места работы?',
                        'content': '''<h2>Получение справки с места работы</h2>
<p>Подайте заявку через систему SapaHR.</p>'''
                    }
                ]
            }
        ]
        
        for cat_data in categories_data:
            articles = cat_data.pop('articles')
            category = KnowledgeCategory(**cat_data)
            session.add(category)
            session.flush()
            
            for article_data in articles:
                article = KnowledgeArticle(
                    category_id=category.id,
                    author='Администратор',
                    **article_data
                )
                session.add(article)
        
        session.commit()
        logger.info("База знаний успешно инициализирована!")
    except Exception as e:
        logger.error(f"Ошибка инициализации базы знаний: {e}")
        session.rollback()
    finally:
        session.close()

def init_db():
    try:
        Base.metadata.create_all(engine)
        logger.info("Database tables created successfully")
        
        # Автоматическая проверка и добавление недостающих колонок
        check_and_add_columns()
        logger.info("Database columns verified and updated")
        
        # Автоматическая инициализация базы знаний
        init_knowledge_base()
        
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

def test_database_connection():
    try:
        session = get_session()
        session.execute(text("SELECT 1"))
        session.close()
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

class Request(Base):
    __tablename__ = 'requests'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    request_type = Column(String)
    title = Column(String)
    description = Column(Text)
    status = Column(String, default='pending')
    admin_comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    user = relationship('User', back_populates='requests')

class News(Base):
    __tablename__ = 'news'
    
    id = Column(Integer, primary_key=True)
    title = Column(String)
    content = Column(Text)
    image_url = Column(String)
    category = Column(String)
    author = Column(String)
    views = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Activity(Base):
    __tablename__ = 'activities'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    activity_type = Column(String)
    description = Column(Text)
    points = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship('User', back_populates='activities')

class Notification(Base):
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    title = Column(String)
    message = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Reminder(Base):
    __tablename__ = 'reminders'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    title = Column(String)
    message = Column(Text)
    reminder_date = Column(DateTime)
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class PurchaseExecutor(Base):
    __tablename__ = 'purchase_executors'
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    company = Column(String)
    email = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Broadcast(Base):
    __tablename__ = 'broadcasts'
    
    id = Column(Integer, primary_key=True)
    title = Column(String)
    message = Column(Text)
    sent_to = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class KnowledgeCategory(Base):
    __tablename__ = 'knowledge_categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    icon = Column(String, default='📚')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    articles = relationship('KnowledgeArticle', back_populates='category')

class KnowledgeArticle(Base):
    __tablename__ = 'knowledge_articles'
    
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey('knowledge_categories.id'))
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    author = Column(String)
    views = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    category = relationship('KnowledgeCategory', back_populates='articles')

class Poll(Base):
    __tablename__ = 'polls'
    
    id = Column(Integer, primary_key=True)
    question = Column(String, nullable=False)
    options = Column(Text, nullable=False)
    votes = Column(Text, default='{}')
    total_votes = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Onboarding(Base):
    __tablename__ = 'onboarding'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    title = Column(String)
    description = Column(Text)
    assignee = Column(String)
    status = Column(String, default='pending')
    progress = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Candidate(Base):
    __tablename__ = 'candidates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    position = Column(String)
    status = Column(String, default='new')  # new, interview, offer, hired, rejected
    source = Column(String)
    phone = Column(String)
    email = Column(String)
    resume_url = Column(String)
    interview_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class Course(Base):
    __tablename__ = 'courses'
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String)
    duration = Column(Integer)  # в часах
    points = Column(Integer, default=0)
    icon = Column(String, default='📚')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class CourseEnrollment(Base):
    __tablename__ = 'course_enrollments'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    course_id = Column(Integer, ForeignKey('courses.id'))
    progress = Column(Integer, default=0)
    status = Column(String, default='in_progress')  # in_progress, completed
    score = Column(Integer)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

class Quiz(Base):
    __tablename__ = 'quizzes'
    
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey('courses.id'))
    question = Column(String, nullable=False)
    options = Column(Text)  # JSON array
    correct_answer = Column(String)
    points = Column(Integer, default=10)
    created_at = Column(DateTime, default=datetime.utcnow)

class EmployeeMetrics(Base):
    __tablename__ = 'employee_metrics'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    metric_type = Column(String)  # performance, attendance, etc
    value = Column(Float)
    period = Column(String)  # месяц/год
    created_at = Column(DateTime, default=datetime.utcnow)

engine = create_engine(config.DATABASE_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def get_session():
    return Session()
