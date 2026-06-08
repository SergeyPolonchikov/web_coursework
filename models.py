from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')
    group = db.Column(db.String(50), nullable=True)
    about = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    teacher_courses = db.relationship('Course', back_populates='teacher', lazy=True)
    student_submissions = db.relationship('Submission', back_populates='student', lazy=True)


class Course(db.Model):
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    teacher = db.relationship('User', back_populates='teacher_courses')
    tasks = db.relationship('Task', back_populates='course', lazy=True, cascade='all, delete-orphan')


class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    task_type = db.Column(db.String(50), default='Лабораторная работа')
    max_score = db.Column(db.Integer, default=100)
    deadline = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    allow_resubmit = db.Column(db.Boolean, default=True)
    is_published = db.Column(db.Boolean, default=True)
    
    # Relationships
    course = db.relationship('Course', back_populates='tasks')
    submissions = db.relationship('Submission', back_populates='task', lazy=True, cascade='all, delete-orphan')


class Submission(db.Model):
    __tablename__ = 'submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    file_path = db.Column(db.String(500), nullable=True)  # Увеличил длину
    grade = db.Column(db.Integer, nullable=True)
    comment = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    task = db.relationship('Task', back_populates='submissions')
    student = db.relationship('User', back_populates='student_submissions')


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), nullable=True)
    message = db.Column(db.String(200), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='notifications', lazy=True)
    task = db.relationship('Task', backref='notifications', lazy=True)
    submission = db.relationship('Submission', backref='notifications', lazy=True)