from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, IntegerField, DateTimeField, BooleanField, FileField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password_confirm = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('student', 'Студент'), ('teacher', 'Преподаватель')], validators=[DataRequired()])

class TaskForm(FlaskForm):
    title = StringField('Название задания', validators=[DataRequired()])
    description = TextAreaField('Описание задания', validators=[DataRequired()])
    task_type = SelectField('Тип задания', choices=[
        ('Лабораторная работа', 'Лабораторная работа'),
        ('Практическая работа', 'Практическая работа'),
        ('Проект', 'Проект'),
        ('Тестирование', 'Тестирование')
    ])
    max_score = IntegerField('Максимальный балл', validators=[DataRequired()], default=100)
    deadline = DateTimeField('Срок сдачи', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    allow_resubmit = BooleanField('Разрешить повторную отправку работы', default=True)
    is_published = BooleanField('Отображать задание студентам сразу после публикации', default=True)

class SubmissionForm(FlaskForm):
    file = FileField('Файл работы', validators=[DataRequired()])