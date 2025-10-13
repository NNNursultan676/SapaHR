from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import config

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, nullable=False)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    company = Column(String)
    position = Column(String)
    role = Column(String, default='user')
    points = Column(Integer, default=0)
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
    author = Column(String)
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
    user_telegram_id = Column(String)
    title = Column(String)
    message = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Reminder(Base):
    __tablename__ = 'reminders'
    
    id = Column(Integer, primary_key=True)
    user_telegram_id = Column(String)
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
    telegram_id = Column(String)
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
    created_at = Column(DateTime, default=datetime.utcnow)

engine = create_engine(config.DATABASE_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def get_session():
    return Session()
