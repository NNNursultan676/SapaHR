from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import config
from database import get_session, User, Vacation, Request, News, Activity, Notification, Reminder, PurchaseExecutor, Broadcast, KnowledgeCategory, KnowledgeArticle, Poll, Onboarding, RequestTemplate, RequestFile
import json

app = Flask(__name__)
app.secret_key = config.SECRET_KEY



@app.template_filter('from_json')
def from_json_filter(value):
    if not value:
        return {}
    try:
        return json.loads(value)
    except:
        return {}

def is_admin():
    role = session.get('role')
    return role in ['developer', 'admin']

def is_developer():
    return session.get('role') == 'developer'

def get_role_level():
    role = session.get('role', 'employee')
    role_levels = {
        'developer': 5,
        'admin': 4,
        'moderator': 3,
        'manager': 2,
        'employee': 1
    }
    return role_levels.get(role, 1)

def require_auth(f):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def require_admin(f):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session or session.get('role') not in ['developer', 'admin']:
            flash('Доступ запрещен. Требуются права администратора.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def require_developer(f):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'developer':
            flash('Доступ запрещен. Требуются права разработчика.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')

        db_session = get_session()

        # Проверяем существование пользователя
        if db_session.query(User).filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'error')
            db_session.close()
            return redirect(url_for('register'))

        # Создаем нового пользователя
        hashed_password = generate_password_hash(password)
        new_user = User(
            email=email,
            password=hashed_password,
            first_name=first_name,
            last_name=last_name,
            phone=phone
        )
        db_session.add(new_user)
        db_session.commit()

        # Автоматический вход
        session['user_id'] = new_user.id
        session['username'] = f"{new_user.first_name} {new_user.last_name}"
        session['role'] = new_user.role
        session['email'] = new_user.email

        db_session.close()
        flash('Регистрация успешна!', 'success')
        return redirect(url_for('onboarding'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        db_session = get_session()
        try:
            user = db_session.query(User).filter_by(email=email).first()

            if user and user.password and check_password_hash(user.password, password):
                session['user_id'] = user.id
                session['username'] = f"{user.first_name} {user.last_name or ''}"
                session['role'] = user.role
                session['role_level'] = user.role_level or 1
                session['original_role'] = user.role  # Сохраняем оригинальную роль
                session['email'] = user.email
                
                # Проверяем, завершен ли онбординг
                if not user.onboarding_completed and user.role != 'developer':
                    db_session.close()
                    return redirect(url_for('onboarding'))
                
                db_session.close()
                flash('Добро пожаловать!', 'success')
                return redirect(url_for('dashboard'))

            flash('Неверный email или пароль', 'error')
        except Exception as e:
            flash(f'Ошибка при входе: {str(e)}', 'error')
        finally:
            db_session.close()

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/switch-role/<role>')
@require_auth
def switch_role(role):
    """Переключение роли (только для разработчика)"""
    if session.get('original_role') != 'developer':
        flash('У вас нет прав для переключения ролей', 'error')
        return redirect(url_for('dashboard'))
    
    valid_roles = ['developer', 'admin', 'moderator', 'manager', 'employee']
    if role not in valid_roles:
        flash('Недопустимая роль', 'error')
        return redirect(url_for('dashboard'))
    
    role_levels = {
        'developer': 5,
        'admin': 4,
        'moderator': 3,
        'manager': 2,
        'employee': 1
    }
    
    session['role'] = role
    session['role_level'] = role_levels[role]
    flash(f'Роль переключена на: {role}', 'success')
    return redirect(url_for('dashboard'))

@app.route('/manage-roles')
@require_auth
def manage_roles():
    """Управление ролями пользователей"""
    current_role = session.get('role')
    current_level = get_role_level()
    
    # Проверка прав доступа: только разработчик, админ и модератор
    if current_role not in ['developer', 'admin', 'moderator']:
        flash('У вас нет прав для управления ролями', 'error')
        return redirect(url_for('dashboard'))
    
    db_session = get_session()
    
    # Фильтруем пользователей в зависимости от роли текущего пользователя
    if current_role == 'developer':
        # Разработчик видит всех
        users = db_session.query(User).all()
    elif current_role == 'admin':
        # Админ видит только пользователей ниже себя
        users = db_session.query(User).filter(User.role_level < 4).all()
    elif current_role == 'moderator':
        # Модератор видит только руководителей и пользователей
        users = db_session.query(User).filter(User.role_level < 3).all()
    else:
        users = []
    
    db_session.close()
    return render_template('manage_roles.html', users=users, current_role=current_role)

@app.route('/assign-role/<int:user_id>', methods=['POST'])
@require_auth
def assign_role(user_id):
    """Назначение роли пользователю с учетом иерархии"""
    role = request.form.get('role')
    current_user_role = session.get('role')
    current_user_level = get_role_level()
    
    role_levels = {
        'developer': 5,
        'admin': 4,
        'moderator': 3,
        'manager': 2,
        'employee': 1
    }
    
    # Проверка допустимости роли
    if role not in role_levels:
        flash('Недопустимая роль', 'error')
        return redirect(url_for('manage_roles'))
    
    target_role_level = role_levels[role]
    
    # Проверка прав доступа по иерархии
    if current_user_role == 'developer':
        # Разработчик может назначать любую роль
        pass
    elif current_user_role == 'admin':
        # Админ может назначать только роли ниже себя (модератор, руководитель, пользователь)
        if target_role_level >= 4:  # developer или admin
            flash('Вы не можете назначать роль разработчика или администратора', 'error')
            return redirect(url_for('manage_roles'))
    elif current_user_role == 'moderator':
        # Модератор может назначать только руководителя и пользователя
        if target_role_level >= 3:  # developer, admin или moderator
            flash('Вы можете назначать только роли руководителя и пользователя', 'error')
            return redirect(url_for('manage_roles'))
    else:
        # Руководитель и пользователь не могут назначать роли
        flash('У вас нет прав для назначения ролей', 'error')
        return redirect(url_for('manage_roles'))
    
    db_session = get_session()
    user = db_session.query(User).get(user_id)
    
    if user:
        # Проверяем, не пытается ли пользователь изменить роль того, кто выше или равен ему
        if user.role_level >= current_user_level and current_user_role != 'developer':
            flash('Вы не можете изменять роль пользователя вашего уровня или выше', 'error')
            db_session.close()
            return redirect(url_for('manage_roles'))
        
        user.role = role
        user.role_level = role_levels[role]
        db_session.commit()
        flash(f'Роль пользователя {user.first_name} изменена на {role}', 'success')
    
    db_session.close()
    return redirect(url_for('manage_roles'))

@app.route('/onboarding')
@require_auth
def onboarding():
    if is_admin():
        return redirect(url_for('dashboard'))

    db_session = get_session()
    user = db_session.query(User).filter_by(id=session.get('user_id')).first()

    if user.onboarding_completed:
        return redirect(url_for('dashboard'))

    onboarding_tasks = db_session.query(Onboarding).filter_by(user_id=user.id).all()
    db_session.close()

    return render_template('onboarding.html', user=user, tasks=onboarding_tasks)

@app.route('/complete-onboarding', methods=['POST'])
@require_auth
def complete_onboarding():
    db_session = get_session()
    user = db_session.query(User).filter_by(id=session.get('user_id')).first()
    user.onboarding_completed = True
    db_session.commit()
    db_session.close()

    flash('Добро пожаловать! Онбординг завершен.', 'success')
    return redirect(url_for('dashboard'))

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
        }
        active_polls = db_session.query(Poll).filter_by(is_active=True).limit(1).first()
        recent_news = db_session.query(News).order_by(News.created_at.desc()).limit(3).all()
    else:
        user_id = session.get('user_id')
        user = db_session.query(User).filter_by(id=user_id).first()
        stats = {
            'my_requests': db_session.query(Request).filter_by(user_id=user_id).count(),
            'my_vacations': db_session.query(Vacation).filter_by(user_id=user_id).count(),
            'my_points': user.points if user else 0
        }
        active_polls = db_session.query(Poll).filter_by(is_active=True).limit(1).first()
        recent_news = db_session.query(News).order_by(News.created_at.desc()).limit(3).all()
        onboarding_tasks = db_session.query(Onboarding).filter_by(user_id=user_id, status='pending').all()
        stats['onboarding_tasks'] = onboarding_tasks

    db_session.close()

    return render_template('dashboard.html', stats=stats, is_admin=is_admin(), 
                         active_poll=active_polls, recent_news=recent_news)

@app.route('/polls')
@require_auth
def polls():
    db_session = get_session()
    
    if is_admin():
        polls_list = db_session.query(Poll).order_by(Poll.created_at.desc()).all()
        active_polls = [p for p in polls_list if p.is_active]
    else:
        polls_list = []
        active_polls = db_session.query(Poll).filter_by(is_active=True).order_by(Poll.created_at.desc()).all()
    
    db_session.close()
    
    return render_template('polls.html', polls=polls_list, active_polls=active_polls, is_admin=is_admin())

@app.route('/polls/create', methods=['POST'])
@require_admin
def create_poll():
    question = request.form.get('question')
    options = request.form.get('options')
    
    db_session = get_session()
    
    # Деактивируем все предыдущие опросы
    db_session.query(Poll).update({'is_active': False})
    
    # Создаем новый опрос
    new_poll = Poll(
        question=question,
        options=options.replace('\r\n', ',').replace('\n', ','),
        is_active=True
    )
    db_session.add(new_poll)
    db_session.commit()
    db_session.close()
    
    flash('Опрос создан и опубликован!', 'success')
    return redirect(url_for('polls'))

@app.route('/polls/activate/<int:poll_id>', methods=['POST'])
@require_admin
def activate_poll(poll_id):
    db_session = get_session()
    
    # Деактивируем все опросы
    db_session.query(Poll).update({'is_active': False})
    
    # Активируем выбранный
    poll = db_session.query(Poll).get(poll_id)
    if poll:
        poll.is_active = True
        db_session.commit()
        flash('Опрос активирован!', 'success')
    
    db_session.close()
    return redirect(url_for('polls'))

@app.route('/polls/deactivate/<int:poll_id>', methods=['POST'])
@require_admin
def deactivate_poll(poll_id):
    db_session = get_session()
    
    poll = db_session.query(Poll).get(poll_id)
    if poll:
        poll.is_active = False
        db_session.commit()
        flash('Опрос деактивирован!', 'success')
    
    db_session.close()
    return redirect(url_for('polls'))

@app.route('/polls/delete/<int:poll_id>', methods=['POST'])
@require_admin
def delete_poll(poll_id):
    db_session = get_session()
    
    poll = db_session.query(Poll).get(poll_id)
    if poll:
        db_session.delete(poll)
        db_session.commit()
        flash('Опрос удален!', 'success')
    
    db_session.close()
    return redirect(url_for('polls'))

@app.route('/poll/vote/<int:poll_id>', methods=['POST'])
@require_auth
def vote_poll(poll_id):
    option = request.form.get('option')

    db_session = get_session()
    poll = db_session.query(Poll).get(poll_id)

    if poll:
        votes = json.loads(poll.votes) if poll.votes else {}
        votes[option] = votes.get(option, 0) + 1
        poll.votes = json.dumps(votes)
        poll.total_votes += 1
        db_session.commit()

    db_session.close()
    flash('Спасибо за ваш голос!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/profile')
@require_auth
def profile():
    email = session.get('email')
    if not email or is_admin():
        flash('Профиль доступен только для пользователей', 'error')
        return redirect(url_for('dashboard'))

    db_session = get_session()
    user = db_session.query(User).filter_by(email=email).first()
    db_session.close()

    return render_template('profile.html', user=user)

@app.route('/profile/update', methods=['POST'])
@require_auth
def update_profile():
    email = session.get('email')
    if not email:
        return jsonify({'success': False}), 401

    db_session = get_session()
    user = db_session.query(User).filter_by(email=email).first()

    if user:
        user.company = request.form.get('company')
        user.position = request.form.get('position')
        user.department = request.form.get('department')
        user.phone = request.form.get('phone')
        db_session.commit()
        flash('Профиль обновлен', 'success')

    db_session.close()
    return redirect(url_for('profile'))

@app.route('/company')
@require_auth
def company():
    return render_template('company.html', companies=config.COMPANIES)

@app.route('/search')
@require_auth
def search():
    query = request.args.get('q', '')
    db_session = get_session()
    
    # Поиск по новостям, сотрудникам, заявкам
    news_results = db_session.query(News).filter(
        News.title.ilike(f'%{query}%')
    ).limit(5).all()
    
    employees_results = db_session.query(User).filter(
        User.first_name.ilike(f'%{query}%') | User.last_name.ilike(f'%{query}%')
    ).limit(5).all()
    
    requests_results = db_session.query(Request).filter(
        Request.title.ilike(f'%{query}%')
    ).limit(5).all()
    
    results = {
        'news': news_results,
        'employees': employees_results,
        'requests': requests_results
    }
    
    db_session.close()
    return render_template('search.html', query=query, results=results)

@app.route('/knowledge')
@require_auth
def knowledge():
    db_session = get_session()
    
    # Загружаем категории с предзагрузкой статей
    from sqlalchemy.orm import joinedload
    categories = db_session.query(KnowledgeCategory).options(joinedload(KnowledgeCategory.articles)).all()
    recent_articles = db_session.query(KnowledgeArticle).order_by(KnowledgeArticle.created_at.desc()).limit(5).all()
    
    # Создаем копии данных для использования после закрытия сессии
    categories_data = []
    for cat in categories:
        categories_data.append({
            'id': cat.id,
            'name': cat.name,
            'description': cat.description,
            'icon': cat.icon,
            'articles_count': len(cat.articles)
        })
    
    recent_articles_data = []
    for article in recent_articles:
        recent_articles_data.append({
            'id': article.id,
            'title': article.title,
            'category_id': article.category_id,
            'views': article.views,
            'created_at': article.created_at.strftime('%d.%m.%Y') if article.created_at else ''
        })
    
    db_session.close()
    return render_template('knowledge.html', categories=categories_data, recent_articles=recent_articles_data, is_admin=is_admin())

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
    flash('Категория создана!', 'success')
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
    flash('Статья создана!', 'success')
    return redirect(url_for('knowledge'))

@app.route('/knowledge/article/edit/<int:article_id>', methods=['POST'])
@require_admin
def edit_knowledge_article(article_id):
    db_session = get_session()
    article = db_session.query(KnowledgeArticle).get(article_id)
    if article:
        article.title = request.form.get('title')
        article.content = request.form.get('content')
        article.updated_at = datetime.utcnow()
        db_session.commit()
        flash('Статья обновлена!', 'success')
    db_session.close()
    return redirect(url_for('knowledge_article', article_id=article_id))

@app.route('/knowledge/article/delete/<int:article_id>', methods=['POST'])
@require_admin
def delete_knowledge_article(article_id):
    db_session = get_session()
    article = db_session.query(KnowledgeArticle).get(article_id)
    category_id = article.category_id if article else None
    if article:
        db_session.delete(article)
        db_session.commit()
        flash('Статья удалена!', 'success')
    db_session.close()
    return redirect(url_for('knowledge_category', category_id=category_id) if category_id else url_for('knowledge'))

@app.route('/knowledge/category/<int:category_id>')
@require_auth
def knowledge_category(category_id):
    db_session = get_session()
    category = db_session.query(KnowledgeCategory).get(category_id)
    articles = db_session.query(KnowledgeArticle).filter_by(category_id=category_id).all()
    db_session.close()
    return render_template('knowledge_category.html', category=category, articles=articles, is_admin=is_admin())

@app.route('/knowledge/article/<int:article_id>')
@require_auth
def knowledge_article(article_id):
    db_session = get_session()
    article = db_session.query(KnowledgeArticle).get(article_id)
    
    if not article:
        db_session.close()
        flash('Статья не найдена', 'error')
        return redirect(url_for('knowledge'))
    
    # Увеличиваем просмотры
    article.views += 1
    db_session.commit()
    
    # Создаем словарь с данными перед закрытием сессии
    article_data = {
        'id': article.id,
        'title': article.title,
        'content': article.content,
        'author': article.author,
        'views': article.views,
        'created_at': article.created_at,
        'updated_at': article.updated_at,
        'category_id': article.category_id
    }
    
    db_session.close()
    return render_template('knowledge_article.html', article=article_data, is_admin=is_admin())

@app.route('/gamification')
@require_auth
def gamification():
    db_session = get_session()
    users = db_session.query(User).order_by(User.points.desc()).limit(10).all()
    db_session.close()
    return render_template('gamification.html', users=users)

@app.route('/mascot')
@require_auth
def mascot():
    return render_template('mascot.html')

@app.route('/status_info')
@require_auth
def status_info():
    return render_template('status_info.html')

@app.route('/executors')
@require_admin
def executors():
    db_session = get_session()
    executors = db_session.query(PurchaseExecutor).all()
    db_session.close()
    return render_template('executors.html', executors=executors)

@app.route('/broadcast')
@require_admin
def broadcast():
    db_session = get_session()
    broadcasts = db_session.query(Broadcast).order_by(Broadcast.created_at.desc()).all()
    db_session.close()
    return render_template('broadcast.html', broadcasts=broadcasts)

@app.route('/notifications')
@require_auth
def notifications():
    db_session = get_session()
    
    if is_admin():
        # Админы видят все уведомления
        notifications = db_session.query(Notification).order_by(Notification.created_at.desc()).all()
    else:
        # Обычные пользователи видят только свои уведомления
        user_id = session.get('user_id')
        notifications = db_session.query(Notification).filter_by(user_id=user_id).order_by(Notification.created_at.desc()).all()
    
    db_session.close()
    return render_template('notifications.html', notifications=notifications, is_admin=is_admin())

@app.route('/reminders')
@require_admin
def reminders():
    db_session = get_session()
    reminders = db_session.query(Reminder).order_by(Reminder.reminder_date.desc()).all()
    db_session.close()
    return render_template('reminders.html', reminders=reminders)

@app.route('/activities')
@require_admin
def activities():
    db_session = get_session()
    activities = db_session.query(Activity).order_by(Activity.created_at.desc()).all()
    db_session.close()
    return render_template('activities.html', activities=activities)

@app.route('/employees')
@require_auth
def employees():
    db_session = get_session()
    users = db_session.query(User).all()
    db_session.close()
    return render_template('employees.html', employees=users, is_admin=is_admin())

@app.route('/my_status')
@require_auth
def my_status():
    if is_admin():
        flash('Эта страница доступна только для пользователей', 'error')
        return redirect(url_for('dashboard'))

    db_session = get_session()
    user_id = session.get('user_id')
    user = db_session.query(User).filter_by(id=user_id).first()
    
    my_vacations = db_session.query(Vacation).filter_by(user_id=user_id).order_by(Vacation.created_at.desc()).all()
    my_requests = db_session.query(Request).filter_by(user_id=user_id).order_by(Request.created_at.desc()).all()
    my_activities = db_session.query(Activity).filter_by(user_id=user_id).order_by(Activity.created_at.desc()).limit(10).all()
    
    db_session.close()
    
    return render_template('my_status.html', 
                         user=user,
                         vacations=my_vacations,
                         requests=my_requests,
                         activities=my_activities)

@app.route('/news')
@require_auth
def news():
    db_session = get_session()
    news_list = db_session.query(News).order_by(News.created_at.desc()).all()
    db_session.close()

    return render_template('news.html', news=news_list, is_admin=is_admin())

@app.route('/news/view/<int:id>')
@require_auth
def view_news(id):
    db_session = get_session()
    news_item = db_session.query(News).get(id)
    if news_item:
        news_item.views += 1
        db_session.commit()
    db_session.close()

    return render_template('news_detail.html', news=news_item, is_admin=is_admin())

@app.route('/news/add', methods=['POST'])
@require_admin
def add_news():
    db_session = get_session()
    news_item = News(
        title=request.form.get('title'),
        content=request.form.get('content'),
        category=request.form.get('category', 'general'),
        image_url=request.form.get('image_url'),
        author=session.get('username', 'Администратор')
    )
    db_session.add(news_item)
    db_session.commit()
    db_session.close()

    flash('Новость добавлена', 'success')
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

@app.route('/hr-analytics')
@require_admin
def hr_analytics():
    db_session = get_session()
    
    from database import Candidate, EmployeeMetrics
    
    stats = {
        'new_candidates': db_session.query(Candidate).filter_by(status='new').count(),
        'interview_candidates': db_session.query(Candidate).filter_by(status='interview').count(),
        'assessment_candidates': db_session.query(Candidate).filter_by(status='assessment').count(),
        'offer_candidates': db_session.query(Candidate).filter_by(status='offer').count(),
    }
    
    total = stats['new_candidates'] or 1
    stats['interview_percent'] = round((stats['interview_candidates'] / total) * 100, 1)
    stats['assessment_percent'] = round((stats['assessment_candidates'] / total) * 100, 1)
    stats['offer_percent'] = round((stats['offer_candidates'] / total) * 100, 1)
    
    rejection_reasons = [
        {'name': 'Нами проваален', 'count': 48, 'percent': 28},
        {'name': 'Несоответствующая квалификация', 'count': 13, 'percent': 10},
    ]
    
    turnover = {
        'rate': 8.4,
        'avg_tenure': 15.51
    }
    
    performance_metrics = []
    
    db_session.close()
    
    return render_template('hr_analytics.html', 
                         stats=stats, 
                         rejection_reasons=rejection_reasons,
                         turnover=turnover,
                         performance_metrics=performance_metrics)

@app.route('/lms')
@require_auth
def lms():
    """Информационная страница об обучении"""
    return render_template('lms.html')

@app.route('/requests-catalog')
@require_auth
def requests_catalog():
    db_session = get_session()
    
    user_id = session.get('user_id')
    user = db_session.query(User).filter_by(id=user_id).first()
    user_company = user.company if user else None
    
    # Получаем шаблоны заявок для компании пользователя
    if is_admin():
        # Админ видит все шаблоны
        templates = db_session.query(RequestTemplate).all()
        all_files = db_session.query(RequestFile).all()
    else:
        # Обычные пользователи и модераторы видят только шаблоны своей компании
        templates = db_session.query(RequestTemplate).filter_by(company=user_company).all()
        all_files = db_session.query(RequestFile).filter_by(company=user_company).all()
    
    my_requests = db_session.query(Request).filter_by(user_id=user_id).all()
    total_requests = db_session.query(Request).count()
    
    # Группируем файлы по шаблонам
    files_by_template = {}
    for file in all_files:
        template_key = file.template_id if file.template_id else 'general'
        if template_key not in files_by_template:
            files_by_template[template_key] = []
        files_by_template[template_key].append(file)
    
    db_session.close()
    
    return render_template('requests_catalog.html',
                         templates=templates,
                         files_by_template=files_by_template,
                         my_requests=my_requests,
                         total_requests=total_requests,
                         companies=config.COMPANIES,
                         user_company=user_company,
                         is_admin=is_admin()) 


@app.route('/template/add', methods=['POST'])
@require_auth
def add_template():
    """Добавление нового шаблона заявки"""
    current_role = session.get('role')
    
    if current_role not in ['developer', 'admin', 'moderator']:
        flash('У вас нет прав для добавления шаблонов', 'error')
        return redirect(url_for('requests_catalog'))
    
    db_session = get_session()
    user_id = session.get('user_id')
    user = db_session.query(User).filter_by(id=user_id).first()
    
    title = request.form.get('title')
    description = request.form.get('description')
    company = request.form.get('company')
    icon = request.form.get('icon', '📝')
    color = request.form.get('color', '#E8F5E9')
    
    # Модератор может добавлять только для своей компании
    if current_role == 'moderator' and company != user.company:
        flash('Вы можете добавлять шаблоны только для своей компании', 'error')
        db_session.close()
        return redirect(url_for('requests_catalog'))
    
    template = RequestTemplate(
        title=title,
        description=description,
        company=company,
        icon=icon,
        color=color,
        created_by=user_id
    )
    db_session.add(template)
    db_session.commit()
    db_session.close()
    
    flash('Шаблон успешно добавлен!', 'success')
    return redirect(url_for('requests_catalog'))

@app.route('/template/delete/<int:template_id>', methods=['POST'])
@require_auth
def delete_template(template_id):
    """Удаление шаблона заявки"""
    current_role = session.get('role')
    
    if current_role not in ['developer', 'admin', 'moderator']:
        flash('У вас нет прав для удаления шаблонов', 'error')
        return redirect(url_for('requests_catalog'))
    
    db_session = get_session()
    template = db_session.query(RequestTemplate).get(template_id)
    
    if template:
        # Модератор может удалять только шаблоны своей компании
        if current_role == 'moderator':
            user = db_session.query(User).filter_by(id=session.get('user_id')).first()
            if template.company != user.company:
                flash('Вы можете удалять только шаблоны своей компании', 'error')
                db_session.close()
                return redirect(url_for('requests_catalog'))
        
        # Удаляем связанные файлы
        files = db_session.query(RequestFile).filter_by(template_id=template_id).all()
        for file in files:
            db_session.delete(file)
        
        db_session.delete(template)
        db_session.commit()
        flash('Шаблон удален!', 'success')
    
    db_session.close()
    return redirect(url_for('requests_catalog'))

@app.route('/file/add', methods=['POST'])
@require_auth
def add_file_link():
    """Добавление ссылки на файл к шаблону"""
    current_role = session.get('role')
    
    if current_role not in ['developer', 'admin', 'moderator']:
        flash('У вас нет прав для добавления файлов', 'error')
        return redirect(url_for('requests_catalog'))
    
    try:
        template_id = request.form.get('template_id')
        file_name = request.form.get('file_name')
        file_url = request.form.get('file_url')
        file_type = request.form.get('file_type', 'pdf')
        company = request.form.get('company')
        
        if not file_name or not file_url:
            flash('Заполните название и ссылку на файл', 'error')
            return redirect(url_for('requests_catalog'))
        
        db_session = get_session()
        user = db_session.query(User).filter_by(id=session.get('user_id')).first()
        
        # Модератор может добавлять только для своей компании
        if current_role == 'moderator' and company != user.company:
            flash('Вы можете добавлять файлы только для своей компании', 'error')
            db_session.close()
            return redirect(url_for('requests_catalog'))
        
        request_file = RequestFile(
            template_id=int(template_id) if template_id and template_id != '' else None,
            filename=file_name,
            original_name=file_name,
            file_url=file_url,
            file_type=file_type,
            company=company,
            uploaded_by=session.get('user_id')
        )
        db_session.add(request_file)
        db_session.commit()
        db_session.close()
        
        flash('Ссылка на файл успешно добавлена!', 'success')
    except Exception as e:
        flash(f'Ошибка при добавлении файла: {str(e)}', 'error')
    
    return redirect(url_for('requests_catalog'))

@app.route('/file/delete/<int:file_id>', methods=['POST'])
@require_auth
def delete_file(file_id):
    """Удаление ссылки на файл"""
    current_role = session.get('role')
    
    if current_role not in ['developer', 'admin', 'moderator']:
        flash('У вас нет прав для удаления файлов', 'error')
        return redirect(url_for('requests_catalog'))
    
    db_session = get_session()
    file = db_session.query(RequestFile).get(file_id)
    
    if file:
        # Модератор может удалять только файлы своей компании
        if current_role == 'moderator':
            user = db_session.query(User).filter_by(id=session.get('user_id')).first()
            if file.company != user.company:
                flash('Вы можете удалять только файлы своей компании', 'error')
                db_session.close()
                return redirect(url_for('requests_catalog'))
        
        db_session.delete(file)
        db_session.commit()
        flash('Файл удален!', 'success')
    
    db_session.close()
    return redirect(url_for('requests_catalog'))

@app.route('/file/open/<int:file_id>')
@require_auth
def open_file(file_id):
    """Открыть файл по ссылке"""
    db_session = get_session()
    file = db_session.query(RequestFile).get(file_id)
    
    if not file:
        flash('Файл не найден', 'error')
        db_session.close()
        return redirect(url_for('requests_catalog'))
    
    # Проверяем доступ к файлу (только для своей компании)
    user = db_session.query(User).filter_by(id=session.get('user_id')).first()
    if not is_admin() and file.company != user.company:
        flash('У вас нет доступа к этому файлу', 'error')
        db_session.close()
        return redirect(url_for('requests_catalog'))
    
    db_session.close()
    return redirect(file.file_url)

def run_app():
    app.run(host='0.0.0.0', port=5055, debug=False)