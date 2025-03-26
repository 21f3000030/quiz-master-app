
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()


class Admin(db.Model):
    _tablename_ = 'Admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    full_name = db.Column(db.String(150),nullable=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(50), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    qualification = db.Column(db.String(100))
    dob = db.Column(db.String(20))
    quizzes = db.relationship('Quiz', back_populates='user', cascade="all, delete-orphan")

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    chapters = db.relationship('Chapter', back_populates='subject', cascade="all, delete-orphan")



class Chapter(db.Model):
    __tablename__="chapter"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    subject = db.relationship('Subject', back_populates="chapters")
    quizzes = db.relationship('Quiz', back_populates="chapter", cascade="all, delete-orphan")

    
class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    date_of_quiz = db.Column(db.Date, nullable=False)
    time_duration = db.Column(db.String(5), nullable=False)  # Duration in "hh:mm" format
    total_marks = db.Column(db.Integer, nullable=False)  # Total Marks for the quiz
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  

    chapter = db.relationship('Chapter', back_populates="quizzes")
    questions = db.relationship('Question', back_populates="quiz", cascade="all, delete-orphan")
    user = db.relationship('User', back_populates='quizzes')

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_statement = db.Column(db.Text, nullable=False)
    option1 = db.Column(db.String(100))
    option2 = db.Column(db.String(100))
    option3 = db.Column(db.String(100))
    option4 = db.Column(db.String(100))
    correct_option = db.Column(db.String(255), nullable=False)
    marks = db.Column(db.Integer, nullable=False, default=1)  # Marks for each question
    quiz = db.relationship('Quiz', back_populates="questions")

    

class Quizresponse(db.Model):
    __tablename__ = 'quiz_responses'  # Table name
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)  # Foreign key to Quiz table
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Foreign key to User table
    time_stamp_of_attempt = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp when the quiz was submitted
    total_scored = db.Column(db.Integer, nullable=False)  # Total marks scored
    user_responses = db.Column(db.JSON, nullable=True)

    # Relationships
    quiz = db.relationship('Quiz', backref='quiz_responses', lazy=True)
    user = db.relationship('User', backref='quiz_responses', lazy=True)

    def __init__(self, quiz_id, user_id, total_scored, user_responses=None):
        self.quiz_id = quiz_id
        self.user_id = user_id
        self.total_scored = total_scored
        self.user_responses = user_responses
