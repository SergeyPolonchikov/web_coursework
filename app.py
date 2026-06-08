from flask import Flask, render_template, redirect, url_for, request, flash, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

from models import db, User, Course, Task, Submission, Notification
from forms import LoginForm, RegisterForm

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите в систему'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()
    
    if not User.query.filter_by(username='teacher').first():
        teacher = User(
            username='teacher',
            email='teacher@example.com',
            password_hash=generate_password_hash('teacher123'),
            role='teacher',
            group='Преподавательская'
        )
        db.session.add(teacher)
        db.session.commit()
    
    if not User.query.filter_by(username='student').first():
        student = User(
            username='student',
            email='student@example.com',
            password_hash=generate_password_hash('student123'),
            role='student',
            group='ИС-21'
        )
        db.session.add(student)
        db.session.commit()
    
    if not Course.query.first():
        teacher = User.query.filter_by(username='teacher').first()
        if teacher:
            course = Course(
                title='Веб-разработка',
                description='Flask, HTML, CSS, Jinja2',
                teacher_id=teacher.id
            )
            db.session.add(course)
            db.session.commit()

@app.context_processor
def utility_processor():
    return {'now': datetime.utcnow()}

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user)
            flash('Вы успешно вошли в систему!', 'success')
            return redirect(url_for('dashboard'))
        flash('Неверное имя пользователя или пароль', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Имя пользователя уже существует', 'danger')
        elif User.query.filter_by(email=form.email.data).first():
            flash('Email уже зарегистрирован', 'danger')
        else:
            user = User(
                username=form.username.data,
                email=form.email.data,
                password_hash=generate_password_hash(form.password.data),
                role=form.role.data,
                group='Новая группа'
            )
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('Регистрация успешно завершена!', 'success')
            return redirect(url_for('dashboard'))
    
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'teacher':
        tasks = Task.query.join(Course).filter(Course.teacher_id == current_user.id).all()
    else:
        tasks = Task.query.filter_by(is_published=True).all()
    return render_template('dashboard.html', tasks=tasks)

@app.route('/profile')
@login_required
def profile():
    if current_user.role == 'student':
        submissions = Submission.query.filter_by(student_id=current_user.id).all()
        completed_tasks = len([s for s in submissions if s.grade is not None])
        avg_grade = sum([s.grade for s in submissions if s.grade]) / len(submissions) if submissions else 0
        submitted_task_ids = [s.task_id for s in submissions]
        active_tasks = Task.query.filter(Task.id.notin_(submitted_task_ids), Task.is_published == True, Task.deadline > datetime.utcnow()).count()
        recent_tasks = Task.query.filter_by(is_published=True).order_by(Task.created_at.desc()).limit(3).all()
        courses = Course.query.all()
        stats = {
            'completed': completed_tasks,
            'avg_grade': round(avg_grade),
            'active': active_tasks,
            'courses': len(courses)
        }
    else:
        stats = {
            'courses': Course.query.filter_by(teacher_id=current_user.id).count(),
            'tasks': Task.query.join(Course).filter(Course.teacher_id == current_user.id).count(),
            'students': User.query.filter_by(role='student').count(),
            'submissions': Submission.query.count()
        }
        recent_tasks = Task.query.join(Course).filter(Course.teacher_id == current_user.id).order_by(Task.created_at.desc()).limit(3).all()
        courses = Course.query.filter_by(teacher_id=current_user.id).all()
    
    return render_template('profile.html', stats=stats, recent_tasks=recent_tasks, courses=courses)

# ============ РЕДАКТИРОВАНИЕ ПРОФИЛЯ ============
@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.username = request.form.get('username')
        current_user.email = request.form.get('email')
        current_user.group = request.form.get('group')
        current_user.about = request.form.get('about')
        
        new_password = request.form.get('new_password')
        if new_password:
            current_user.password_hash = generate_password_hash(new_password)
        
        db.session.commit()
        flash('Профиль обновлен!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('edit_profile.html')

# ============ КУРСЫ ============
@app.route('/courses')
@login_required
def courses():
    if current_user.role == 'teacher':
        user_courses = Course.query.filter_by(teacher_id=current_user.id).all()
    else:
        user_courses = Course.query.all()
    return render_template('courses.html', courses=user_courses)

@app.route('/course/<int:course_id>')
@login_required
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    
    if current_user.role == 'teacher' and course.teacher_id != current_user.id:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('courses'))
    
    tasks = Task.query.filter_by(course_id=course_id)
    if current_user.role == 'student':
        tasks = tasks.filter_by(is_published=True)
    tasks = tasks.all()
    
    return render_template('course_detail.html', course=course, tasks=tasks)

@app.route('/create_course', methods=['GET', 'POST'])
@login_required
def create_course():
    if current_user.role != 'teacher':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        if title:
            course = Course(title=title, description=description, teacher_id=current_user.id)
            db.session.add(course)
            db.session.commit()
            flash('Курс успешно создан!', 'success')
            return redirect(url_for('courses'))
    return render_template('create_course.html')

# ============ ЗАДАНИЯ ============
@app.route('/create_task', methods=['GET', 'POST'])
@login_required
def create_task():
    if current_user.role != 'teacher':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('dashboard'))
    
    courses = Course.query.filter_by(teacher_id=current_user.id).all()
    if request.method == 'POST':
        course_id = request.form.get('course_id')
        course = Course.query.get(course_id)
        if course and course.teacher_id == current_user.id:
            task = Task(
                title=request.form.get('title'),
                description=request.form.get('description'),
                task_type=request.form.get('task_type'),
                max_score=int(request.form.get('max_score', 100)),
                deadline=datetime.strptime(request.form.get('deadline'), '%Y-%m-%dT%H:%M'),
                course_id=int(course_id),
                allow_resubmit=request.form.get('allow_resubmit') == 'on',
                is_published=request.form.get('is_published') == 'on'
            )
            db.session.add(task)
            db.session.commit()
            flash('Задание успешно создано!', 'success')
            return redirect(url_for('dashboard'))
    return render_template('create_task.html', courses=courses)

@app.route('/task/<int:task_id>')
@login_required
def task_detail(task_id):
    task = Task.query.get_or_404(task_id)
    submission = None
    
    # Проверяем, отправлял ли студент уже это задание
    if current_user.role == 'student':
        submission = Submission.query.filter_by(task_id=task_id, student_id=current_user.id).first()
    
    return render_template('task_detail.html', task=task, submission=submission)


@app.route('/submissions')
@login_required
def submissions():
    return render_template('submissions.html')

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    if current_user.role != 'teacher':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('dashboard'))
    
    task = Task.query.get_or_404(task_id)
    course = Course.query.get(task.course_id)
    
    if course.teacher_id != current_user.id:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        task.title = request.form.get('title')
        task.description = request.form.get('description')
        task.task_type = request.form.get('task_type')
        task.max_score = int(request.form.get('max_score', 100))
        task.deadline = datetime.strptime(request.form.get('deadline'), '%Y-%m-%dT%H:%M')
        task.allow_resubmit = request.form.get('allow_resubmit') == 'on'
        task.is_published = request.form.get('is_published') == 'on'
        db.session.commit()
        flash('Задание обновлено!', 'success')
        return redirect(url_for('dashboard'))  # <-- ПЕРЕНАПРАВЛЕНИЕ НА DASHBOARD
    
    courses = Course.query.filter_by(teacher_id=current_user.id).all()
    return render_template('edit_task.html', task=task, courses=courses)

@app.route('/submit_task/<int:task_id>', methods=['POST'])
@login_required
def submit_task(task_id):
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('dashboard'))
    
    task = Task.query.get_or_404(task_id)
    
    if 'file' not in request.files:
        flash('Файл не выбран', 'danger')
        return redirect(url_for('task_detail', task_id=task_id))
    
    file = request.files['file']
    if file.filename == '':
        flash('Файл не выбран', 'danger')
        return redirect(url_for('task_detail', task_id=task_id))
    
    if file:
        # Создаем папку uploads если её нет
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        
        # Сохраняем файл
        filename = secure_filename(f"{current_user.id}_{task_id}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Проверяем, есть ли уже отправка
        submission = Submission.query.filter_by(task_id=task_id, student_id=current_user.id).first()
        
        if submission:
            # Обновляем существующую
            submission.file_path = filepath
            submission.submitted_at = datetime.utcnow()
            submission.grade = None
            submission.comment = None
            flash('Работа обновлена!', 'success')
        else:
            # Создаем новую
            submission = Submission(
                task_id=task_id,
                student_id=current_user.id,
                file_path=filepath,
                submitted_at=datetime.utcnow()
            )
            db.session.add(submission)
            flash('Работа успешно отправлена!', 'success')
        
        db.session.commit()
        
        # Отладка - проверяем сохранилось ли
        print(f"=== SUBMISSION SAVED ===")
        print(f"Task ID: {task_id}")
        print(f"Student ID: {current_user.id}")
        print(f"File path: {filepath}")
        
        # Проверяем в базе
        check_sub = Submission.query.filter_by(task_id=task_id, student_id=current_user.id).first()
        if check_sub:
            print(f"Submission found in DB: ID={check_sub.id}, file_path={check_sub.file_path}")
        else:
            print("ERROR: Submission NOT found in database!")
    
    return redirect(url_for('task_detail', task_id=task_id))

@app.route('/statistics')
@login_required
def statistics():
    if current_user.role == 'teacher':
        # Статистика для преподавателя - результаты студентов по курсам
        courses = Course.query.filter_by(teacher_id=current_user.id).all()
        
        all_courses_stats = []
        
        for course in courses:
            # Получаем все задания курса
            tasks = Task.query.filter_by(course_id=course.id).all()
            tasks_count = len(tasks)
            
            # Получаем всех студентов, которые отправляли работы на этот курс
            students_with_submissions = db.session.query(User, Submission).join(
                Submission, Submission.student_id == User.id
            ).join(
                Task, Task.id == Submission.task_id
            ).filter(
                Task.course_id == course.id
            ).distinct(User.id).all()
            
            # Собираем уникальных студентов
            students_data = []
            student_ids = set()
            
            for student, _ in students_with_submissions:
                if student.id not in student_ids:
                    student_ids.add(student.id)
                    
                    # Получаем все работы студента по этому курсу
                    student_submissions = Submission.query.join(Task).filter(
                        Task.course_id == course.id,
                        Submission.student_id == student.id
                    ).all()
                    
                    # Подсчитываем статистику по студенту
                    submitted_count = len(student_submissions)
                    graded_count = len([s for s in student_submissions if s.grade is not None])
                    not_graded_count = submitted_count - graded_count
                    
                    avg_grade = 0
                    if graded_count > 0:
                        grades = [s.grade for s in student_submissions if s.grade]
                        avg_grade = sum(grades) / len(grades)
                    
                    # Задания, которые студент не сдал
                    submitted_task_ids = [s.task_id for s in student_submissions]
                    not_submitted = [t for t in tasks if t.id not in submitted_task_ids]
                    
                    # Прогресс студента по курсу
                    if tasks_count > 0:
                        progress = (submitted_count / tasks_count) * 100
                    else:
                        progress = 0
                    
                    students_data.append({
                        'student': student,
                        'submitted_count': submitted_count,
                        'graded_count': graded_count,
                        'not_graded_count': not_graded_count,
                        'avg_grade': round(avg_grade, 1),
                        'not_submitted_tasks': not_submitted,
                        'progress': round(progress, 1)
                    })
            
            # Общая статистика по курсу
            total_submissions = Submission.query.join(Task).filter(Task.course_id == course.id).count()
            total_students = len(students_data)
            
            # Средний балл по курсу
            all_grades = []
            for student in students_data:
                if student['avg_grade'] > 0:
                    all_grades.append(student['avg_grade'])
            course_avg_grade = sum(all_grades) / len(all_grades) if all_grades else 0
            
            all_courses_stats.append({
                'course': course,
                'tasks_count': tasks_count,
                'total_submissions': total_submissions,
                'total_students': total_students,
                'avg_grade': round(course_avg_grade, 1),
                'students': students_data
            })
        
        return render_template('statistics_teacher.html', courses_stats=all_courses_stats)
    
    else:
        # Статистика для студента (оставляем как было)
        submissions = Submission.query.filter_by(student_id=current_user.id).all()
        courses = Course.query.all()
        
        course_stats = []
        for course in courses:
            tasks_in_course = Task.query.filter_by(course_id=course.id, is_published=True).all()
            submitted_tasks = Submission.query.join(Task).filter(
                Task.course_id == course.id,
                Submission.student_id == current_user.id
            ).all()
            
            completed = len([s for s in submitted_tasks if s.grade is not None])
            pending = len([s for s in submitted_tasks if s.grade is None])
            total = len(tasks_in_course)
            
            avg_grade = 0
            if completed > 0:
                grades = [s.grade for s in submitted_tasks if s.grade]
                if grades:
                    avg_grade = sum(grades) / len(grades)
            
            progress = 0
            if total > 0:
                progress = (completed / total) * 100
            
            course_stats.append({
                'course': course,
                'total_tasks': total,
                'submitted': len(submitted_tasks),
                'completed': completed,
                'pending': pending,
                'avg_grade': round(avg_grade, 1),
                'progress': round(progress, 1)
            })
        
        total_tasks = Task.query.filter_by(is_published=True).count()
        completed_tasks = len([s for s in submissions if s.grade is not None])
        pending_tasks = len([s for s in submissions if s.grade is None])
        not_started = total_tasks - len(submissions)
        
        avg_grade = 0
        if completed_tasks > 0:
            grades = [s.grade for s in submissions if s.grade]
            if grades:
                avg_grade = sum(grades) / completed_tasks
        
        now = datetime.utcnow()
        upcoming_tasks = Task.query.filter(Task.is_published == True, Task.deadline > now).count()
        overdue_tasks = Task.query.filter(Task.is_published == True, Task.deadline < now).count()
        
        completed_percentage = 0
        if total_tasks > 0:
            completed_percentage = (completed_tasks / total_tasks) * 100
        
        pending_percentage = 0
        if total_tasks > 0:
            pending_percentage = (pending_tasks / total_tasks) * 100
        
        stats = {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': pending_tasks,
            'not_started': not_started,
            'avg_grade': round(avg_grade, 1),
            'upcoming_tasks': upcoming_tasks,
            'overdue_tasks': overdue_tasks,
            'completed_percentage': round(completed_percentage, 1),
            'pending_percentage': round(pending_percentage, 1),
            'course_stats': course_stats
        }
        return render_template('statistics.html', stats=stats)
    
@app.route('/create_task_with_course/<int:course_id>', methods=['GET', 'POST'])
@login_required
def create_task_with_course(course_id):
    if current_user.role != 'teacher':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('dashboard'))
    
    course = Course.query.get_or_404(course_id)
    
    # Проверяем, что курс принадлежит текущему преподавателю
    if course.teacher_id != current_user.id:
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        task = Task(
            title=request.form.get('title'),
            description=request.form.get('description'),
            task_type=request.form.get('task_type'),
            max_score=int(request.form.get('max_score', 100)),
            deadline=datetime.strptime(request.form.get('deadline'), '%Y-%m-%dT%H:%M'),
            course_id=course_id,
            allow_resubmit=request.form.get('allow_resubmit') == 'on',
            is_published=request.form.get('is_published') == 'on'
        )
        db.session.add(task)
        db.session.commit()
        flash('Задание успешно создано!', 'success')
        return redirect(url_for('course_detail', course_id=course_id))
    
    return render_template('create_task_with_course.html', course=course)

if __name__ == '__main__':
    app.run(debug=True)