# ============================================================
# app.py — Complete Single File Application
# Smart Procrastination Detector — Phases 1 to 6
# ============================================================

from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user
from flask_login import login_required, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime, date, timedelta

# ============================================================
# APP SETUP
# ============================================================

app = Flask(__name__)
app.config['SECRET_KEY']                     = 'smartprocrastination2024'
app.config['SQLALCHEMY_DATABASE_URI']        = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db            = SQLAlchemy(app)
bcrypt        = Bcrypt(app)
login_manager = LoginManager(app)

login_manager.login_view             = 'login'
login_manager.login_message          = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'


# ============================================================
# DATABASE MODELS
# ============================================================

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(100), nullable=False)
    email    = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    tasks          = db.relationship('Task', backref='owner', lazy=True)
    focus_sessions = db.relationship('FocusSession', backref='user', lazy=True)


class Task(db.Model):
    __tablename__ = 'tasks'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    task_name   = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    deadline    = db.Column(db.Date, nullable=True)
    priority    = db.Column(db.String(20), default='Medium')
    status      = db.Column(db.String(20), default='Pending')
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    subtasks    = db.relationship('Subtask', backref='parent_task',
                                  lazy=True, cascade='all, delete-orphan')


class Subtask(db.Model):
    __tablename__ = 'subtasks'
    id           = db.Column(db.Integer, primary_key=True)
    task_id      = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    subtask_name = db.Column(db.String(200), nullable=False)
    status       = db.Column(db.String(20), default='Pending')


class FocusSession(db.Model):
    __tablename__ = 'focus_sessions'
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    duration     = db.Column(db.Integer, default=25)
    session_date = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================================
# USER LOADER
# ============================================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ============================================================
# CREATE TABLES
# ============================================================

with app.app_context():
    db.create_all()
    print("[DB] Tables ready.")


# ============================================================
# HELPERS
# ============================================================

def get_progress(task):
    if task.status == 'Completed':
        return 100
    total     = len(task.subtasks)
    completed = sum(1 for s in task.subtasks if s.status == 'Completed')
    if total == 0:
        return 0
    return int((completed / total) * 100)


def get_risk(task):
    if not task.deadline:
        return 'Low'
    today     = date.today()
    days_left = (task.deadline - today).days
    near      = days_left <= 3
    progress  = get_progress(task)
    if near and progress < 30:
        return 'High'
    elif near and progress < 60:
        return 'Medium'
    return 'Low'


# ============================================================
# HOME
# ============================================================

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('home.html')


# ============================================================
# REGISTER
# ============================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')
        if not name or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'warning')
            return redirect(url_for('login'))
        try:
            hashed   = bcrypt.generate_password_hash(password).decode('utf-8')
            new_user = User(name=name, email=email, password=hashed)
            db.session.add(new_user)
            db.session.commit()
            flash(f'Account created for {name}! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    return render_template('register.html')


# ============================================================
# LOGIN
# ============================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        print(f"[LOGIN] Attempting: {email}")
        user = User.query.filter_by(email=email).first()
        if user is None:
            flash('No account found with that email.', 'danger')
            return render_template('login.html')
        if bcrypt.check_password_hash(user.password, password):
            login_user(user, remember=True)
            flash(f'Welcome back, {user.name}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('dashboard'))
        else:
            flash('Wrong password.', 'danger')
    return render_template('login.html')


# ============================================================
# LOGOUT
# ============================================================

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))


# ============================================================
# DASHBOARD
# ============================================================

@app.route('/dashboard')
@login_required
def dashboard():
    all_tasks       = Task.query.filter_by(user_id=current_user.id).all()
    total_tasks     = len(all_tasks)
    completed_tasks = sum(1 for t in all_tasks if t.status == 'Completed')
    pending_tasks   = total_tasks - completed_tasks
    productivity_score = int((completed_tasks / total_tasks) * 100) \
                         if total_tasks > 0 else 0
    today      = date.today()
    week_later = today + timedelta(days=7)
    upcoming = []
    for task in all_tasks:
        if task.status == 'Completed':
            continue
        if task.deadline and task.deadline <= week_later:
            upcoming.append({
                'task'     : task,
                'days_left': (task.deadline - today).days,
                'progress' : get_progress(task),
                'risk'     : get_risk(task),
            })
    upcoming.sort(key=lambda x: x['days_left'])
    tasks_with_data = sorted([
        {'task': t, 'progress': get_progress(t), 'risk': get_risk(t)}
        for t in all_tasks
    ], key=lambda x: (
        x['task'].status == 'Completed',
        x['task'].deadline or date.max
    ))
    hour     = datetime.now().hour
    greeting = ('Good morning' if hour < 12
                else 'Good afternoon' if hour < 17
                else 'Good evening')
    today_str   = datetime.now().strftime('%A, %d %B %Y')
    focus_today = FocusSession.query.filter(
        FocusSession.user_id == current_user.id,
        FocusSession.session_date >= datetime.combine(
            today, datetime.min.time())
    ).count()
    return render_template('dashboard.html',
        user               = current_user,
        total_tasks        = total_tasks,
        completed_tasks    = completed_tasks,
        pending_tasks      = pending_tasks,
        productivity_score = productivity_score,
        upcoming           = upcoming,
        tasks_with_data    = tasks_with_data,
        greeting           = greeting,
        today_str          = today_str,
        focus_today        = focus_today,
    )


# ============================================================
# TASKS — list
# ============================================================

@app.route('/tasks')
@login_required
def tasks():
    status_filter   = request.args.get('filter', 'all')
    priority_filter = request.args.get('priority', 'all')
    query = Task.query.filter_by(user_id=current_user.id)
    if status_filter == 'pending':
        query = query.filter_by(status='Pending')
    elif status_filter == 'completed':
        query = query.filter_by(status='Completed')
    if priority_filter in ['High', 'Medium', 'Low']:
        query = query.filter_by(priority=priority_filter)
    all_tasks  = query.order_by(Task.deadline.asc().nullslast()).all()
    tasks_data = [
        {'task': t, 'progress': get_progress(t), 'risk': get_risk(t)}
        for t in all_tasks
    ]
    total     = Task.query.filter_by(user_id=current_user.id).count()
    pending   = Task.query.filter_by(
                    user_id=current_user.id, status='Pending').count()
    completed = Task.query.filter_by(
                    user_id=current_user.id, status='Completed').count()
    return render_template('tasks.html',
        tasks_data      = tasks_data,
        status_filter   = status_filter,
        priority_filter = priority_filter,
        total           = total,
        pending         = pending,
        completed       = completed,
        today           = date.today(),
    )


# ============================================================
# TASKS — create
# ============================================================

@app.route('/tasks/create', methods=['GET', 'POST'])
@login_required
def create_task():
    if request.method == 'POST':
        task_name   = request.form.get('task_name', '').strip()
        description = request.form.get('description', '').strip()
        deadline    = request.form.get('deadline', '')
        priority    = request.form.get('priority', 'Medium')
        if not task_name:
            flash('Task name is required.', 'danger')
            return redirect('/tasks/create')
        deadline_date = None
        if deadline:
            try:
                deadline_date = datetime.strptime(deadline, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date.', 'danger')
                return redirect('/tasks/create')
        try:
            new_task = Task(
                user_id     = current_user.id,
                task_name   = task_name,
                description = description,
                deadline    = deadline_date,
                priority    = priority,
                status      = 'Pending',
            )
            db.session.add(new_task)
            db.session.commit()
            flash(f'Task "{task_name}" created!', 'success')
            return redirect('/tasks')
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    return render_template('create_task.html', today=date.today())


# ============================================================
# TASKS — edit
# ============================================================

@app.route('/tasks/edit/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('Permission denied.', 'danger')
        return redirect('/tasks')
    if request.method == 'POST':
        task_name   = request.form.get('task_name', '').strip()
        description = request.form.get('description', '').strip()
        deadline    = request.form.get('deadline', '')
        priority    = request.form.get('priority', 'Medium')
        if not task_name:
            flash('Task name is required.', 'danger')
            return redirect(f'/tasks/edit/{task_id}')
        deadline_date = None
        if deadline:
            try:
                deadline_date = datetime.strptime(deadline, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date.', 'danger')
                return redirect(f'/tasks/edit/{task_id}')
        try:
            task.task_name   = task_name
            task.description = description
            task.deadline    = deadline_date
            task.priority    = priority
            db.session.commit()
            flash('Task updated!', 'success')
            return redirect('/tasks')
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    return render_template('edit_task.html', task=task)


# ============================================================
# TASKS — delete
# ============================================================

@app.route('/tasks/delete/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('Permission denied.', 'danger')
        return redirect('/tasks')
    try:
        name = task.task_name
        db.session.delete(task)
        db.session.commit()
        flash(f'Task "{name}" deleted.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    return redirect('/tasks')


# ============================================================
# TASKS — toggle
# ============================================================

@app.route('/tasks/toggle/<int:task_id>', methods=['POST'])
@login_required
def toggle_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('Permission denied.', 'danger')
        return redirect('/tasks')
    try:
        if task.status == 'Pending':
            task.status = 'Completed'
            flash(f'"{task.task_name}" marked complete!', 'success')
        else:
            task.status = 'Pending'
            flash(f'"{task.task_name}" marked pending.', 'info')
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    return redirect('/tasks')


# ============================================================
# TASK DETAIL
# ============================================================

@app.route('/tasks/<int:task_id>')
@login_required
def task_detail(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('Permission denied.', 'danger')
        return redirect('/tasks')
    progress  = get_progress(task)
    risk      = get_risk(task)
    today     = date.today()
    days_left = (task.deadline - today).days if task.deadline else None
    return render_template('task_detail.html',
        task      = task,
        progress  = progress,
        risk      = risk,
        days_left = days_left,
        today     = today,
    )


# ============================================================
# SUBTASKS — add
# ============================================================

@app.route('/tasks/<int:task_id>/subtasks/add', methods=['POST'])
@login_required
def add_subtask(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('Permission denied.', 'danger')
        return redirect('/tasks')
    subtask_name = request.form.get('subtask_name', '').strip()
    if not subtask_name:
        flash('Subtask name cannot be empty.', 'danger')
        return redirect(f'/tasks/{task_id}')
    try:
        db.session.add(Subtask(
            task_id      = task_id,
            subtask_name = subtask_name,
            status       = 'Pending',
        ))
        db.session.commit()
        flash('Subtask added!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    return redirect(f'/tasks/{task_id}')


# ============================================================
# SUBTASKS — toggle
# ============================================================

@app.route('/tasks/<int:task_id>/subtasks/toggle/<int:subtask_id>',
           methods=['POST'])
@login_required
def toggle_subtask(task_id, subtask_id):
    task    = Task.query.get_or_404(task_id)
    subtask = Subtask.query.get_or_404(subtask_id)
    if task.user_id != current_user.id or subtask.task_id != task_id:
        flash('Permission denied.', 'danger')
        return redirect('/tasks')
    try:
        subtask.status = 'Completed' if subtask.status == 'Pending' \
                         else 'Pending'
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    return redirect(f'/tasks/{task_id}')


# ============================================================
# SUBTASKS — edit
# ============================================================

@app.route('/tasks/<int:task_id>/subtasks/edit/<int:subtask_id>',
           methods=['POST'])
@login_required
def edit_subtask(task_id, subtask_id):
    task    = Task.query.get_or_404(task_id)
    subtask = Subtask.query.get_or_404(subtask_id)
    if task.user_id != current_user.id or subtask.task_id != task_id:
        flash('Permission denied.', 'danger')
        return redirect('/tasks')
    new_name = request.form.get('subtask_name', '').strip()
    if not new_name:
        flash('Subtask name cannot be empty.', 'danger')
        return redirect(f'/tasks/{task_id}')
    try:
        subtask.subtask_name = new_name
        db.session.commit()
        flash('Subtask updated!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    return redirect(f'/tasks/{task_id}')


# ============================================================
# SUBTASKS — delete
# ============================================================

@app.route('/tasks/<int:task_id>/subtasks/delete/<int:subtask_id>',
           methods=['POST'])
@login_required
def delete_subtask(task_id, subtask_id):
    task    = Task.query.get_or_404(task_id)
    subtask = Subtask.query.get_or_404(subtask_id)
    if task.user_id != current_user.id or subtask.task_id != task_id:
        flash('Permission denied.', 'danger')
        return redirect('/tasks')
    try:
        db.session.delete(subtask)
        db.session.commit()
        flash('Subtask deleted.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    return redirect(f'/tasks/{task_id}')


# ============================================================
# ANALYTICS — Phase 6
# ============================================================

@app.route('/analytics')
@login_required
def analytics():
    all_tasks = Task.query.filter_by(user_id=current_user.id).all()

    total_tasks     = len(all_tasks)
    completed_tasks = sum(1 for t in all_tasks if t.status == 'Completed')
    pending_tasks   = total_tasks - completed_tasks
    productivity_score = int((completed_tasks / total_tasks) * 100) \
                         if total_tasks > 0 else 0

    # Priority breakdown
    high_tasks   = sum(1 for t in all_tasks if t.priority == 'High')
    medium_tasks = sum(1 for t in all_tasks if t.priority == 'Medium')
    low_tasks    = sum(1 for t in all_tasks if t.priority == 'Low')

    # Risk breakdown
    high_risk   = sum(1 for t in all_tasks if get_risk(t) == 'High')
    medium_risk = sum(1 for t in all_tasks if get_risk(t) == 'Medium')
    low_risk    = sum(1 for t in all_tasks if get_risk(t) == 'Low')

    # Overdue tasks
    today         = date.today()
    overdue_tasks = sum(
        1 for t in all_tasks
        if t.deadline and t.deadline < today and t.status == 'Pending'
    )

    # Subtask stats
    all_subtasks       = []
    for t in all_tasks:
        all_subtasks.extend(t.subtasks)
    total_subtasks     = len(all_subtasks)
    completed_subtasks = sum(1 for s in all_subtasks if s.status == 'Completed')

    # Focus session stats
    all_sessions   = FocusSession.query.filter_by(
                         user_id=current_user.id).all()
    total_sessions = len(all_sessions)
    total_minutes  = sum(s.duration for s in all_sessions)

    # Focus sessions this week
    week_ago          = datetime.combine(today - timedelta(days=7),
                                         datetime.min.time())
    sessions_this_week = FocusSession.query.filter(
        FocusSession.user_id == current_user.id,
        FocusSession.session_date >= week_ago
    ).count()

    # Tasks with progress for table
    tasks_with_data = []
    for task in all_tasks:
        tasks_with_data.append({
            'task'    : task,
            'progress': get_progress(task),
            'risk'    : get_risk(task),
        })
    tasks_with_data.sort(
        key=lambda x: x['progress'], reverse=True
    )

    # Weekly completion data (last 7 days)
    weekly_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = sum(
            1 for t in all_tasks
            if t.status == 'Completed'
            and t.created_at
            and t.created_at.date() == day
        )
        weekly_data.append({
            'day'  : day.strftime('%a'),
            'date' : day.strftime('%d %b'),
            'count': count,
        })

    return render_template('analytics.html',
        total_tasks        = total_tasks,
        completed_tasks    = completed_tasks,
        pending_tasks      = pending_tasks,
        productivity_score = productivity_score,
        high_tasks         = high_tasks,
        medium_tasks       = medium_tasks,
        low_tasks          = low_tasks,
        high_risk          = high_risk,
        medium_risk        = medium_risk,
        low_risk           = low_risk,
        overdue_tasks      = overdue_tasks,
        total_subtasks     = total_subtasks,
        completed_subtasks = completed_subtasks,
        total_sessions     = total_sessions,
        total_minutes      = total_minutes,
        sessions_this_week = sessions_this_week,
        tasks_with_data    = tasks_with_data,
        weekly_data        = weekly_data,
        today              = today,
    )


# ============================================================
# FOCUS TIMER
# ============================================================

@app.route('/focus-timer')
@login_required
def focus_timer():
    return render_template('focus_timer.html')


@app.route('/focus-timer/save', methods=['POST'])
@login_required
def save_focus_session():
    try:
        duration = int(request.form.get('duration', 25))
        session  = FocusSession(
            user_id      = current_user.id,
            duration     = duration,
            session_date = datetime.utcnow(),
        )
        db.session.add(session)
        db.session.commit()
        flash(f'Focus session of {duration} minutes saved!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving session: {str(e)}', 'danger')
    return redirect('/focus-timer')


# ============================================================
# PROFILE
# ============================================================

@app.route('/profile')
@login_required
def profile():
    all_tasks      = Task.query.filter_by(user_id=current_user.id).all()
    total_tasks    = len(all_tasks)
    completed      = sum(1 for t in all_tasks if t.status == 'Completed')
    total_sessions = FocusSession.query.filter_by(
                         user_id=current_user.id).count()
    total_minutes  = sum(
        s.duration for s in
        FocusSession.query.filter_by(user_id=current_user.id).all()
    )
    score = int((completed / total_tasks) * 100) if total_tasks > 0 else 0
    return render_template('profile.html',
        total_tasks    = total_tasks,
        completed      = completed,
        total_sessions = total_sessions,
        total_minutes  = total_minutes,
        score          = score,
    )


# ============================================================
# RUN
# ============================================================
print("REACHED END OF FILE")
if __name__ == '__main__':
    print("[APP] Running at http://127.0.0.1:5000")
    app.run(debug=True)
# if __name__ == "_main_":
#     app.run(debug=True)p