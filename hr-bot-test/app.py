from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import config
from database import get_session, User, Vacation, Request, News, Activity, Notification, Reminder, PurchaseExecutor, Broadcast, KnowledgeCategory, KnowledgeArticle, Poll, Onboarding
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
        user = db_session.query(User).filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = f"{user.first_name} {user.last_name or ''}"
            session['role'] = user.role
            session['email'] = user.email
            
            # Проверяем, завершен ли онбординг
            if not user.onboarding_completed:
                db_session.close()
                return redirect(url_for('onboarding'))
            
            db_session.close()
            flash('Добро пожаловать!', 'success')
            return redirect(url_for('dashboard'))

        db_session.close()
        flash('Неверный email или пароль', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

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

@app.route('/employees')
@require_auth
def employees():
    db_session = get_session()
    users = db_session.query(User).all()
    db_session.close()
    return render_template('employees.html', employees=users, is_admin=is_admin())

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

def run_app():
    app.run(host='0.0.0.0', port=5055, debug=False)