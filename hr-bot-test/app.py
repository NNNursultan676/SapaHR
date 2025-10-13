from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import config
from database import get_session, User, Vacation, Request, News, Activity, Notification, Reminder, PurchaseExecutor, Broadcast, KnowledgeCategory, KnowledgeArticle, Poll
import json

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

def is_admin():
    return session.get('role') == 'admin'

def require_auth(f):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def require_admin(f):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Доступ запрещен. Требуются права администратора.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_type = request.form.get('login_type')
        
        if login_type == 'admin':
            email = request.form.get('email')
            password = request.form.get('password')
            
            if email == config.HOST_ADMIN_LOGIN and password == config.HOST_ADMIN_PASSWORD:
                session['user_id'] = 'admin'
                session['username'] = 'Администратор'
                session['role'] = 'admin'
                return redirect(url_for('dashboard'))
            flash('Неверные данные администратора', 'error')
        
        else:
            telegram_id = request.form.get('telegram_id')
            db_session = get_session()
            user = db_session.query(User).filter_by(telegram_id=telegram_id).first()
            
            if user:
                session['user_id'] = user.id
                session['username'] = f"{user.first_name} {user.last_name or ''}"
                session['role'] = user.role
                session['telegram_id'] = user.telegram_id
                db_session.close()
                return redirect(url_for('dashboard'))
            
            db_session.close()
            flash('Пользователь не найден. Сначала напишите боту.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@require_auth
def dashboard():
    db_session = get_session()
    
    if is_admin():
        stats = {
            'total_users': db_session.query(User).count(),
            'pending_requests': db_session.query(Request).filter_by(status='pending').count(),
            'active_vacations': db_session.query(Vacation).filter_by(status='approved').count(),
            'total_news': db_session.query(News).count(),
            'total_broadcasts': db_session.query(Broadcast).count(),
            'total_activities': db_session.query(Activity).count()
        }
    else:
        user_id = session.get('user_id')
        stats = {
            'my_requests': db_session.query(Request).filter_by(user_id=user_id).count(),
            'my_vacations': db_session.query(Vacation).filter_by(user_id=user_id).count(),
            'my_activities': db_session.query(Activity).filter_by(user_id=user_id).count(),
            'total_news': db_session.query(News).count(),
            'my_points': db_session.query(User).filter_by(id=user_id).first().points if user_id else 0
        }
    
    db_session.close()
    
    return render_template('dashboard.html', stats=stats, is_admin=is_admin())

@app.route('/company')
@require_auth
def company():
    return render_template('company.html', companies=config.COMPANIES)

@app.route('/employees')
@require_auth
def employees():
    db_session = get_session()
    users = db_session.query(User).all()
    db_session.close()
    return render_template('employees.html', employees=users, is_admin=is_admin())

@app.route('/my-status')
@require_auth
def my_status():
    if is_admin():
        flash('Эта страница только для пользователей', 'error')
        return redirect(url_for('dashboard'))
    
    db_session = get_session()
    user = db_session.query(User).filter_by(id=session.get('user_id')).first()
    my_requests = db_session.query(Request).filter_by(user_id=user.id).order_by(Request.created_at.desc()).limit(5).all()
    my_vacations = db_session.query(Vacation).filter_by(user_id=user.id).order_by(Vacation.created_at.desc()).limit(5).all()
    my_activities = db_session.query(Activity).filter_by(user_id=user.id).order_by(Activity.created_at.desc()).limit(5).all()
    db_session.close()
    
    return render_template('my_status.html', user=user, requests=my_requests, vacations=my_vacations, activities=my_activities)

@app.route('/profile')
@require_auth
def profile():
    telegram_id = session.get('telegram_id')
    if not telegram_id:
        flash('Профиль доступен только для пользователей', 'error')
        return redirect(url_for('dashboard'))
    
    db_session = get_session()
    user = db_session.query(User).filter_by(telegram_id=telegram_id).first()
    db_session.close()
    
    return render_template('profile.html', user=user)

@app.route('/profile/update', methods=['POST'])
@require_auth
def update_profile():
    telegram_id = session.get('telegram_id')
    if not telegram_id:
        return jsonify({'success': False}), 401
    
    db_session = get_session()
    user = db_session.query(User).filter_by(telegram_id=telegram_id).first()
    
    if user:
        user.company = request.form.get('company')
        user.position = request.form.get('position')
        db_session.commit()
        flash('Профиль обновлен', 'success')
    
    db_session.close()
    return redirect(url_for('profile'))

@app.route('/executors')
@require_auth
def executors():
    db_session = get_session()
    executors = db_session.query(PurchaseExecutor).all()
    db_session.close()
    
    return render_template('executors.html', executors=executors, is_admin=is_admin())

@app.route('/executors/add', methods=['POST'])
@require_admin
def add_executor():
    db_session = get_session()
    executor = PurchaseExecutor(
        name=request.form.get('name'),
        company=request.form.get('company'),
        telegram_id=request.form.get('telegram_id'),
        email=request.form.get('email')
    )
    db_session.add(executor)
    db_session.commit()
    db_session.close()
    
    flash('Исполнитель успешно добавлен', 'success')
    return redirect(url_for('executors'))

@app.route('/executors/delete/<int:id>')
@require_admin
def delete_executor(id):
    db_session = get_session()
    executor = db_session.query(PurchaseExecutor).get(id)
    if executor:
        db_session.delete(executor)
        db_session.commit()
        flash('Исполнитель удален', 'success')
    db_session.close()
    return redirect(url_for('executors'))

@app.route('/broadcast')
@require_auth
def broadcast():
    db_session = get_session()
    broadcasts = db_session.query(Broadcast).order_by(Broadcast.created_at.desc()).all()
    db_session.close()
    
    return render_template('broadcast.html', broadcasts=broadcasts, is_admin=is_admin())

@app.route('/broadcast/send', methods=['POST'])
@require_admin
def send_broadcast():
    db_session = get_session()
    broadcast = Broadcast(
        title=request.form.get('title'),
        message=request.form.get('message'),
        sent_to='all'
    )
    db_session.add(broadcast)
    db_session.commit()
    db_session.close()
    
    flash('Рассылка отправлена', 'success')
    return redirect(url_for('broadcast'))

@app.route('/notifications')
@require_auth
def notifications():
    db_session = get_session()
    
    if is_admin():
        notifs = db_session.query(Notification).order_by(Notification.created_at.desc()).limit(50).all()
    else:
        telegram_id = session.get('telegram_id')
        notifs = db_session.query(Notification).filter_by(user_telegram_id=telegram_id).order_by(Notification.created_at.desc()).all()
    
    db_session.close()
    
    return render_template('notifications.html', notifications=notifs, is_admin=is_admin())

@app.route('/notifications/add', methods=['POST'])
@require_admin
def add_notification():
    db_session = get_session()
    
    target = request.form.get('target')
    if target == 'all':
        users = db_session.query(User).all()
        for user in users:
            notif = Notification(
                user_telegram_id=user.telegram_id,
                title=request.form.get('title'),
                message=request.form.get('message')
            )
            db_session.add(notif)
    else:
        notif = Notification(
            user_telegram_id=request.form.get('telegram_id'),
            title=request.form.get('title'),
            message=request.form.get('message')
        )
        db_session.add(notif)
    
    db_session.commit()
    db_session.close()
    
    flash('Уведомление создано', 'success')
    return redirect(url_for('notifications'))

@app.route('/reminders')
@require_auth
def reminders():
    db_session = get_session()
    
    if is_admin():
        rems = db_session.query(Reminder).order_by(Reminder.reminder_date).all()
    else:
        telegram_id = session.get('telegram_id')
        rems = db_session.query(Reminder).filter_by(user_telegram_id=telegram_id).order_by(Reminder.reminder_date).all()
    
    db_session.close()
    
    return render_template('reminders.html', reminders=rems, is_admin=is_admin())

@app.route('/reminders/add', methods=['POST'])
@require_auth
def add_reminder():
    db_session = get_session()
    
    telegram_id = session.get('telegram_id') if not is_admin() else request.form.get('telegram_id')
    
    reminder = Reminder(
        user_telegram_id=telegram_id,
        title=request.form.get('title'),
        message=request.form.get('message'),
        reminder_date=datetime.strptime(request.form.get('reminder_date'), '%Y-%m-%dT%H:%M')
    )
    db_session.add(reminder)
    db_session.commit()
    db_session.close()
    
    flash('Напоминание создано', 'success')
    return redirect(url_for('reminders'))

@app.route('/activities')
@require_auth
def activities():
    db_session = get_session()
    
    if is_admin():
        acts = db_session.query(Activity).order_by(Activity.created_at.desc()).all()
    else:
        user_id = session.get('user_id')
        acts = db_session.query(Activity).filter_by(user_id=user_id).order_by(Activity.created_at.desc()).all()
    
    db_session.close()
    
    return render_template('activities.html', activities=acts, is_admin=is_admin())

@app.route('/activities/add', methods=['POST'])
@require_admin
def add_activity():
    db_session = get_session()
    
    user_id = request.form.get('user_id')
    points = int(request.form.get('points', 0))
    
    activity = Activity(
        user_id=user_id,
        activity_type=request.form.get('activity_type'),
        description=request.form.get('description'),
        points=points
    )
    db_session.add(activity)
    
    user = db_session.query(User).get(user_id)
    if user:
        user.points += points
    
    db_session.commit()
    db_session.close()
    
    flash('Активность добавлена', 'success')
    return redirect(url_for('activities'))

@app.route('/news')
@require_auth
def news():
    db_session = get_session()
    news_list = db_session.query(News).order_by(News.created_at.desc()).all()
    db_session.close()
    
    return render_template('news.html', news=news_list, is_admin=is_admin())

@app.route('/news/add', methods=['POST'])
@require_admin
def add_news():
    db_session = get_session()
    news_item = News(
        title=request.form.get('title'),
        content=request.form.get('content'),
        author=session.get('username', 'Администратор')
    )
    db_session.add(news_item)
    db_session.commit()
    db_session.close()
    
    flash('Новость добавлена', 'success')
    return redirect(url_for('news'))

@app.route('/news/delete/<int:id>')
@require_admin
def delete_news(id):
    db_session = get_session()
    news_item = db_session.query(News).get(id)
    if news_item:
        db_session.delete(news_item)
        db_session.commit()
        flash('Новость удалена', 'success')
    db_session.close()
    return redirect(url_for('news'))

@app.route('/requests')
@require_auth
def requests_page():
    db_session = get_session()
    
    if is_admin():
        reqs = db_session.query(Request).order_by(Request.created_at.desc()).all()
    else:
        user_id = session.get('user_id')
        reqs = db_session.query(Request).filter_by(user_id=user_id).order_by(Request.created_at.desc()).all()
    
    db_session.close()
    
    return render_template('requests.html', requests=reqs, is_admin=is_admin())

@app.route('/requests/add', methods=['POST'])
@require_auth
def add_request():
    if is_admin():
        flash('Админ не может создавать заявки', 'error')
        return redirect(url_for('requests_page'))
    
    db_session = get_session()
    req = Request(
        user_id=session.get('user_id'),
        request_type=request.form.get('request_type'),
        title=request.form.get('title'),
        description=request.form.get('description')
    )
    db_session.add(req)
    db_session.commit()
    db_session.close()
    
    flash('Заявка создана', 'success')
    return redirect(url_for('requests_page'))

@app.route('/requests/update/<int:id>', methods=['POST'])
@require_admin
def update_request(id):
    db_session = get_session()
    req = db_session.query(Request).get(id)
    
    if req:
        req.status = request.form.get('status')
        req.admin_comment = request.form.get('admin_comment')
        req.updated_at = datetime.utcnow()
        db_session.commit()
        flash('Заявка обновлена', 'success')
    
    db_session.close()
    return redirect(url_for('requests_page'))

@app.route('/gamification')
@require_auth
def gamification():
    db_session = get_session()
    users = db_session.query(User).order_by(User.points.desc()).limit(10).all()
    db_session.close()
    
    return render_template('gamification.html', users=users, is_admin=is_admin())

@app.route('/mascot')
@require_auth
def mascot():
    return render_template('mascot.html')

@app.route('/vacations')
@require_auth
def vacations():
    db_session = get_session()
    
    if is_admin():
        vacs = db_session.query(Vacation).order_by(Vacation.created_at.desc()).all()
    else:
        user_id = session.get('user_id')
        vacs = db_session.query(Vacation).filter_by(user_id=user_id).order_by(Vacation.created_at.desc()).all()
    
    db_session.close()
    
    return render_template('vacations.html', vacations=vacs, is_admin=is_admin())

@app.route('/vacations/add', methods=['POST'])
@require_auth
def add_vacation():
    if is_admin():
        flash('Админ не может создавать отпуска', 'error')
        return redirect(url_for('vacations'))
    
    db_session = get_session()
    
    start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
    end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
    days_count = (end_date - start_date).days + 1
    
    vacation = Vacation(
        user_id=session.get('user_id'),
        start_date=start_date,
        end_date=end_date,
        days_count=days_count,
        reason=request.form.get('reason')
    )
    db_session.add(vacation)
    db_session.commit()
    db_session.close()
    
    flash('Заявка на отпуск создана', 'success')
    return redirect(url_for('vacations'))

@app.route('/vacations/update/<int:id>', methods=['POST'])
@require_admin
def update_vacation(id):
    db_session = get_session()
    vacation = db_session.query(Vacation).get(id)
    
    if vacation:
        vacation.status = request.form.get('status')
        vacation.admin_comment = request.form.get('admin_comment')
        db_session.commit()
        flash('Отпуск обновлен', 'success')
    
    db_session.close()
    return redirect(url_for('vacations'))

@app.route('/polls')
@require_auth
def polls():
    db_session = get_session()
    polls_list = db_session.query(Poll).order_by(Poll.created_at.desc()).all()
    db_session.close()
    return render_template('polls.html', polls=polls_list, is_admin=is_admin())

@app.route('/polls/create', methods=['POST'])
@require_admin
def create_poll():
    db_session = get_session()
    options = request.form.get('options').split('\n')
    options = [opt.strip() for opt in options if opt.strip()]
    
    poll = Poll(
        question=request.form.get('question'),
        options=json.dumps(options)
    )
    db_session.add(poll)
    db_session.commit()
    db_session.close()
    
    flash('Опрос создан', 'success')
    return redirect(url_for('polls'))

@app.route('/status-info')
@require_auth
def status_info():
    return render_template('status_info.html')

@app.route('/knowledge')
@require_auth
def knowledge():
    db_session = get_session()
    categories = db_session.query(KnowledgeCategory).all()
    recent_articles = db_session.query(KnowledgeArticle).order_by(KnowledgeArticle.created_at.desc()).limit(5).all()
    db_session.close()
    return render_template('knowledge.html', categories=categories, recent_articles=recent_articles, is_admin=is_admin())

@app.route('/knowledge/category/<int:category_id>')
@require_auth
def knowledge_category(category_id):
    db_session = get_session()
    category = db_session.query(KnowledgeCategory).get(category_id)
    articles = db_session.query(KnowledgeArticle).filter_by(category_id=category_id).order_by(KnowledgeArticle.created_at.desc()).all()
    db_session.close()
    return render_template('knowledge_category.html', category=category, articles=articles, is_admin=is_admin())

@app.route('/knowledge/article/<int:article_id>')
@require_auth
def knowledge_article(article_id):
    db_session = get_session()
    article = db_session.query(KnowledgeArticle).get(article_id)
    if article:
        article.views += 1
        db_session.commit()
    db_session.close()
    return render_template('knowledge_article.html', article=article, is_admin=is_admin())

@app.route('/knowledge/category/add', methods=['POST'])
@require_admin
def add_knowledge_category():
    db_session = get_session()
    category = KnowledgeCategory(
        name=request.form.get('name'),
        description=request.form.get('description'),
        icon=request.form.get('icon', '📚')
    )
    db_session.add(category)
    db_session.commit()
    db_session.close()
    
    flash('Категория добавлена', 'success')
    return redirect(url_for('knowledge'))

@app.route('/knowledge/article/add', methods=['POST'])
@require_admin
def add_knowledge_article():
    db_session = get_session()
    article = KnowledgeArticle(
        category_id=request.form.get('category_id'),
        title=request.form.get('title'),
        content=request.form.get('content'),
        author=session.get('username', 'Администратор')
    )
    db_session.add(article)
    db_session.commit()
    db_session.close()
    
    flash('Статья добавлена', 'success')
    return redirect(url_for('knowledge'))

@app.route('/search')
@require_auth
def search():
    query = request.args.get('q', '')
    results = {'employees': [], 'news': [], 'articles': [], 'requests': [], 'vacations': []}
    
    if query:
        db_session = get_session()
        
        users = db_session.query(User).filter(
            (User.first_name.ilike(f'%{query}%')) |
            (User.last_name.ilike(f'%{query}%')) |
            (User.company.ilike(f'%{query}%')) |
            (User.position.ilike(f'%{query}%'))
        ).limit(5).all()
        results['employees'] = users
        
        news_items = db_session.query(News).filter(
            (News.title.ilike(f'%{query}%')) |
            (News.content.ilike(f'%{query}%'))
        ).limit(5).all()
        results['news'] = news_items
        
        articles = db_session.query(KnowledgeArticle).filter(
            (KnowledgeArticle.title.ilike(f'%{query}%')) |
            (KnowledgeArticle.content.ilike(f'%{query}%'))
        ).limit(5).all()
        results['articles'] = articles
        
        if is_admin():
            reqs = db_session.query(Request).filter(
                (Request.title.ilike(f'%{query}%')) |
                (Request.description.ilike(f'%{query}%'))
            ).limit(5).all()
            results['requests'] = reqs
            
            vacs = db_session.query(Vacation).filter(
                Vacation.reason.ilike(f'%{query}%')
            ).limit(5).all()
            results['vacations'] = vacs
        
        db_session.close()
    
    return render_template('search.html', query=query, results=results, is_admin=is_admin())

def run_app():
    app.run(host=config.SERVER_HOST, port=config.SERVER_PORT, debug=False)
