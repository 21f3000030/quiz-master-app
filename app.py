from datetime import datetime, timedelta
from flask import Flask, flash, json, render_template, request, redirect, session, url_for
from flask_login import current_user
from sqlalchemy import func
from config import config
from models import Chapter, Quiz, Quizresponse, Subject, db, User , Admin, Question 

app = Flask(__name__)
app.config.from_object(config)
# Automatic Database create 
db.init_app(app)

with app.app_context():
    db.create_all()

    # Add admin user to the Admin table
    if not Admin.query.first():  # Check if admin already exists
        admin = Admin(username='admin', password='adminpass', full_name='Admin User')
        db.session.add(admin)
        db.session.commit()

    print("database created")



    
#admin login
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        # Query the Admin table for credentials
        admin = Admin.query.filter_by(username=username, password=password).first()
        if admin:
            session["admin_full_name"] = admin.full_name  # Store admin's full name in session
            return redirect(url_for("admin_dashboard"))
        else:
            return "Invalid Admin Credentials", 401
    return render_template("admin_login.html")
from flask import redirect, url_for, session


#admin summary



@app.route('/admin_summary')
def admin_summary():
    # Basic Metrics
    total_attempts = db.session.query(func.count(Quizresponse.id)).scalar()
    overall_avg = db.session.query(func.avg(Quizresponse.total_scored)).scalar() or 0
    highest_score = db.session.query(func.max(Quizresponse.total_scored)).scalar() or 0
    
    # Time-based Performance
    daily_performance = db.session.query(
        func.date(Quizresponse.time_stamp_of_attempt).label('date'),
        func.avg(Quizresponse.total_scored).label('avg_score')
    ).group_by('date').order_by('date').all()
    
    # Corrected Subject Analysis
    subject_stats = db.session.query(
        Subject.name,
        func.avg(Quizresponse.total_scored).label('avg_score'),
        func.count(Quizresponse.id).label('attempts')
    ).join(Quizresponse.quiz)\
     .join(Quiz.chapter)\
     .join(Chapter.subject)\
     .group_by(Subject.name).all()
    
    return render_template('admin_summary.html',
        total_attempts=total_attempts,
        overall_avg=round(overall_avg, 2),
        highest_score=highest_score,
        daily_labels=[d[0] for d in daily_performance],  # Removed isoformat()
        daily_scores=[round(d[1], 2) for d in daily_performance],
        subject_names=[s[0] for s in subject_stats],
        subject_scores=[round(s[1], 2) for s in subject_stats]
    )

#admin dashboard
@app.route("/admin_dashboard")
def admin_dashboard():
    # Ensure the admin is logged in
    if "admin_full_name" not in session:
        return redirect(url_for("admin_login"))
    
    # Get the admin's full name from the session
    full_name = session["admin_full_name"]
    
    # Fetch all subjects to display on the dashboard
    subjects = Subject.query.all()

    # Get the search term from the query parameters
    search_term = request.args.get('search', '')

    if search_term:
        # Filter subjects based on the search term (case-insensitive search)
        subjects = Subject.query.filter(Subject.name.ilike(f"%{search_term}%")).all()
    else:
        # If no search term, retrieve all subjects
        subjects = Subject.query.all()

    
    # Render the dashboard with subjects and admin's full name
    return render_template("admin_dashboard.html", 
                           full_name=full_name, 
                           subjects=subjects)



#users

@app.route('/users')
def users():
    search_query = request.args.get('search', '').strip()

    # Fetch users with optional search filter
    if search_query:
        users = User.query.filter(
            (User.full_name.ilike(f"%{search_query}%")) | (User.email.ilike(f"%{search_query}%"))
        ).all()
    else:
        users = User.query.all()

    # Prepare data for the template
    user_data = []
    for user in users:
        # Get quiz responses for the user
        quiz_responses = Quizresponse.query.filter_by(user_id=user.id).all()

        # Number of quizzes attempted
        quizzes_attempted = len(quiz_responses)

        # Average performance
        total_score = sum(response.total_scored for response in quiz_responses)
        avg_performance = round(total_score / quizzes_attempted, 2) if quizzes_attempted > 0 else 0

        user_data.append({
            'full_name': user.full_name,
            'email': user.email,
            'quizzes_attempted': quizzes_attempted,
            'average_performance': avg_performance,
        })

    return render_template('users.html', users=user_data,enumerate=enumerate)


#logout
@app.route('/logout')
def logout():
    # Clear the session or any other authentication-related data
    session.clear()  # Clears all session data
    
    # Redirect the user to the login page after logging out
    return redirect(url_for('home'))





#summary
@app.route('/summary')
def summary():
    
    # Render the summary page and pass the summary data to the template
    return render_template('summary.html')




    return render_template(
        'quiz_result.html',
        quiz=quiz,
        total_score=total_score,
        total_questions=total_queAstions,
        attempted=attempted,
    )


#attempt_quiz
@app.route('/take_quiz/<int:quiz_id>')
def attempt_quiz(quiz_id):
    

    quiz = Quiz.query.get_or_404(quiz_id)  # Fetch the quiz using the provided ID
    questions = Question.query.filter_by(quiz_id=quiz_id).all()  # Fetch questions for the quiz

    # Parse the quiz date and time duration
    quiz_date = quiz.date_of_quiz  # Assuming quiz_date is in the format 'YYYY-MM-DD'
    time_duration_str = quiz.time_duration  # Assuming format "hh:mm"

    try:
        # Convert time_duration_str to timedelta
        hours, minutes = map(int, time_duration_str.split(':'))
        duration_timedelta = timedelta(hours=hours, minutes=minutes)
    except Exception as e:
        return f"Error parsing time_duration: {e}", 400

    # Assume the quiz starts at the beginning of the specified date (midnight)
    quiz_start_time = datetime.combine(quiz_date, datetime.min.time())
    quiz_end_time = quiz_start_time + duration_timedelta  # Calculate quiz end time

    # Get the current time
    current_time = datetime.now()

    # Log values for debugging
    print(f"Quiz Start Time: {quiz_start_time}")
    print(f"Quiz End Time: {quiz_end_time}")
    print(f"Current Time: {current_time}")

    # Calculate remaining time
    time_left = max(0, (quiz_end_time - current_time).total_seconds())  # Time left in seconds

    # Convert seconds to minutes for initial timer setup
    time_left_minutes = time_left // 60

    return render_template(
        'attempt_quiz.html',
        quiz=quiz,
        questions=questions,
        time_left=int(time_left_minutes)  # Pass remaining time in minutes to the template
    )
#submit quiz
@app.route('/submit_quiz/<int:quiz_id>', methods=['POST'])
def submit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    user_id = session.get('user_id')
    
    if not user_id:
        return redirect(url_for('login'))  

    total_scored = 0  
    user_responses = {}  

    for question in quiz.questions:
        selected_answer = request.form.get(f'question_{question.id}')
        user_responses[str(question.id)] = str(selected_answer)  # Ensure stored as string
        
        # Debugging prints
        print(f"Question ID: {question.id}")
        print(f"User Answer: '{selected_answer}' (Type: {type(selected_answer)})")
        print(f"Correct Answer: '{question.correct_option}' (Type: {type(question.correct_option)})")

        if str(selected_answer).strip() == str(question.correct_option).strip():
            total_scored += question.marks  

    # Save user response to database
    quiz_response = Quizresponse(
        quiz_id=quiz.id,
        user_id=user_id,
        total_scored=total_scored,
        user_responses=json.dumps(user_responses)  # Store as JSON string
    )
    
    db.session.add(quiz_response)
    db.session.commit()

    return redirect(url_for('quiz_result', quiz_response_id=quiz_response.id))


@app.route('/summary_statistics/<int:user_id>')
def user_summary_statistics(user_id):
    user = User.query.get_or_404(user_id)  # Ensure user exists

    # Fetch quiz attempts only for the logged-in user
    attempts = Quizresponse.query.filter_by(user_id=user_id).all()

    if not attempts:  # If the user has no quiz attempts, set default values
        return render_template('user_summary_statistics.html',
                               user=user,
                               average_score=0,
                               highest_score=0,
                               total_attempts=0,
                               scores=[],
                               dates=[],
                               good_scores=0,
                               average_scores=0,
                               poor_scores=0)

    # Compute statistics for users with attempts
    total_attempts = len(attempts)
    scores = [a.total_scored for a in attempts]
    dates = [a.time_stamp_of_attempt.strftime('%Y-%m-%d') for a in attempts]

    good_scores = len([s for s in scores if s >= 80])
    average_scores = len([s for s in scores if 50 <= s < 80])
    poor_scores = len([s for s in scores if s < 50])

    return render_template('user_summary_statistics.html',
                           user=user,
                           average_score=round(sum(scores) / len(scores), 2),
                           highest_score=max(scores),
                           total_attempts=total_attempts,
                           scores=scores,
                           dates=dates,
                           good_scores=good_scores,
                           average_scores=average_scores,
                           poor_scores=poor_scores)

#quiz result
import json  # Import JSON module

@app.route('/quiz_result/<int:quiz_response_id>')
def quiz_result(quiz_response_id):
    # Fetch the current quiz response, quiz, and user
    quiz_response = Quizresponse.query.get_or_404(quiz_response_id)
    quiz = Quiz.query.get_or_404(quiz_response.quiz_id)
    user = User.query.get_or_404(quiz_response.user_id)

    # Convert user_responses from JSON string to dictionary
    user_responses = json.loads(quiz_response.user_responses) if quiz_response.user_responses else {}

    # Fetch the user's previous quiz scores and quiz names
    previous_scores = Quizresponse.query.filter_by(user_id=user.id).all()

    # Fetch all quizzes at once to avoid multiple queries
    quiz_names_dict = {quiz.id: quiz.name for quiz in Quiz.query.all()}

    # Convert previous_scores to a JSON-serializable list of dictionaries
    previous_scores_data = [{
        'quiz_name': quiz_names_dict.get(score.quiz_id, 'Unknown Quiz'),
        'score': score.total_scored
    } for score in previous_scores]

    # Calculate summary statistics
    total_scores = [score.total_scored for score in previous_scores]
    average_score = sum(total_scores) / len(total_scores) if total_scores else 0
    highest_score = max(total_scores) if total_scores else 0
    total_attempts = len(previous_scores)

    return render_template(
        'quiz_result.html',
        quiz_response=quiz_response,
        quiz=quiz,
        user=user,
        user_responses=user_responses,  # Now it's a dictionary!
        previous_scores=previous_scores_data,
        average_score=average_score,
        highest_score=highest_score,
        total_attempts=total_attempts
    )

#quizes
@app.route('/quizzes/<int:chapter_id>', methods=['GET', 'POST'])
def quizzes(chapter_id):
    # Fetch the chapter details
    chapter = Chapter.query.get_or_404(chapter_id)
    
    if request.method == 'POST':
        # Get the form data
        quiz_name = request.form.get('name')
        date_of_quiz_str = request.form.get('date_of_quiz')
        time_duration = request.form.get('time_duration')
        total_marks = request.form.get('total_marks')
        
        # Validate form data
        if quiz_name and date_of_quiz_str and time_duration and total_marks:
            try:
                # Convert date_of_quiz_str (string) to a Python date object
                date_of_quiz = datetime.strptime(date_of_quiz_str, '%Y-%m-%d').date()
                
                # Create a new Quiz instance
                new_quiz = Quiz(
                    name=quiz_name,
                    date_of_quiz=date_of_quiz,
                    time_duration=time_duration,
                    total_marks=int(total_marks),
                    chapter_id=chapter_id
                )
                
                # Add and commit to the session
                db.session.add(new_quiz)
                db.session.commit()
                flash('Quiz added successfully!', 'success')
            
            except ValueError:
                flash('Invalid date format! Please use YYYY-MM-DD.', 'danger')
        else:
            flash('All fields are required!', 'danger')
    search_term = request.args.get('search', '')

    if search_term:
        # Filter quizzes based on the search term (case-insensitive search)
        quizzes = Quiz.query.filter(
            Quiz.chapter_id == chapter_id,
            Quiz.name.ilike(f"%{search_term}%")
        ).all()
    else:
        # If no search term, retrieve all quizzes for the chapter
        quizzes = Quiz.query.filter_by(chapter_id=chapter_id).all()

    

    return render_template('quizes.html', chapter=chapter, quizzes=quizzes)

# Edit Quiz


@app.route('/edit_quiz/<int:quiz_id>', methods=['GET', 'POST'])
def edit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        date_of_quiz_str = request.form['date_of_quiz']
        time_duration = request.form['time_duration']
        total_marks = request.form['total_marks']

        # Convert string date to Python date object
        date_of_quiz = datetime.strptime(date_of_quiz_str, '%Y-%m-%d').date()

        # Update quiz details
        quiz.name = name
        quiz.date_of_quiz = date_of_quiz
        quiz.time_duration = time_duration
        quiz.total_marks = total_marks
        db.session.commit()

        return redirect(url_for('quizzes', chapter_id=quiz.chapter_id))  # Redirect to quizzes page

    return render_template('edit_quiz.html', quiz=quiz)

# Delete Quiz
@app.route('/delete_quiz/<int:quiz_id>', methods=['POST'])
def delete_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    chapter_id = quiz.chapter_id  # Remember the chapter ID for redirection

    db.session.delete(quiz)  # Delete the quiz from the database
    db.session.commit()  # Commit the deletion to the database

    return redirect(url_for('quizzes', chapter_id=chapter_id))  # Redirect back to the chapter's quiz list




#view question
@app.route('/quiz/<int:quiz_id>/questions', methods=['GET'])
def view_questions(quiz_id):
    # Fetch the quiz and related chapter and subject
    quiz = Quiz.query.get_or_404(quiz_id)
    chapter = Chapter.query.get_or_404(quiz.chapter_id)
    subject = Subject.query.get_or_404(chapter.subject_id)

    # Fetch all questions under the specified quiz
    questions = Question.query.filter_by(quiz_id=quiz_id).all()

    # Render the questions page
    return render_template('questions.html',
        subject=subject,
        chapter=chapter,
        quiz=quiz,
        questions=questions
    )
#edit quesstion
@app.route('/edit_question/<int:question_id>', methods=['GET', 'POST'])
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)
    if request.method == 'POST':
        # Update the question
        question.question_statement = request.form['question_statement']
        question.option1 = request.form['option1']
        question.option2 = request.form['option2']
        question.option3 = request.form['option3']
        question.option4 = request.form['option4']
        question.correct_option = request.form['correct_option']
        question.marks = request.form['marks']
        db.session.commit()
        return redirect(url_for('manage_questions', quiz_id=question.quiz_id))
    
    return render_template('edit_question.html', question=question)


#delete question
@app.route('/delete_question/<int:question_id>', methods=['POST'])
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    quiz_id = question.quiz_id
    db.session.delete(question)
    db.session.commit()
    return redirect(url_for('manage_questions', quiz_id=quiz_id))


#manage question

@app.route('/quiz/<int:quiz_id>/questions', methods=['GET', 'POST'])
def manage_questions(quiz_id):
    # Fetch the quiz details
    quiz = Quiz.query.get_or_404(quiz_id)

    # Handle form submission
    if request.method == 'POST':
        # Get form data
        question_statement = request.form.get('question_statement')
        option1 = request.form.get('option1')
        option2 = request.form.get('option2')
        option3 = request.form.get('option3')
        option4 = request.form.get('option4')
        correct_option = request.form.get('correct_option')
        marks = request.form.get('marks')  # Fetch the marks field

        # Validate form data
        if all([question_statement, option1, option2, option3, option4, correct_option, marks]):
            try:
                # Create a new question object
                new_question = Question(
                    question_statement=question_statement,
                    option1=option1,
                    option2=option2,
                    option3=option3,
                    option4=option4,
                    correct_option=correct_option,
                    marks=int(marks),  # Store marks
                    quiz_id=quiz_id
                )
                # Add the question to the database
                db.session.add(new_question)
                db.session.commit()
                flash('Question added successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error adding question: {str(e)}', 'danger')
        else:
            flash('All fields are required!', 'danger')

    # Fetch existing questions for the quiz
    questions = Question.query.filter_by(quiz_id=quiz_id).all()

    # Render the questions page
    return render_template('questions.html', quiz=quiz, questions=questions)




#create chapter
@app.route('/existing_chapters/<int:subject_id>', methods=['GET', 'POST'])
def existing_chapters(subject_id):
    # Fetch the subject details
    subject = Subject.query.get(subject_id)
    if not subject:
        flash("Subject not found", "danger")
        return redirect(url_for('admin_dashboard'))

    # Fetch all chapters for the subject
    chapters = Chapter.query.filter_by(subject_id=subject_id).all()

    if request.method == 'POST':
        # Get the chapter details from the form
        chapter_name = request.form.get('name')
        chapter_description = request.form.get('description')

        # Save the new chapter to the database
        new_chapter = Chapter(name=chapter_name, description=chapter_description, subject_id=subject.id)
        db.session.add(new_chapter)
        db.session.commit()

        flash("Chapter added successfully!", "success")
        return redirect(url_for('existing_chapters', subject_id=subject.id))

    return render_template('existing_chapters.html', subject=subject, chapters=chapters)

# Edit Chapter
@app.route('/edit_chapter/<int:chapter_id>', methods=['GET', 'POST'])
def edit_chapter(chapter_id):
    chapter = Chapter.query.get(chapter_id)
    
    if request.method == 'POST':
        # Update the chapter with form data
        chapter.name = request.form['name']
        chapter.description = request.form['description']
        db.session.commit()  # Commit the changes to the database
        return redirect(url_for('existing_chapters', subject_id=chapter.subject_id))  # Redirect back to chapter list
        
    return render_template('edit_chapter.html', chapter=chapter)


# Delete Chapter
@app.route('/delete_chapter/<int:chapter_id>', methods=['POST'])
def delete_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    subject_id = chapter.subject_id  # Remember the subject ID for redirection

    db.session.delete(chapter)  # Delete the chapter from the database
    db.session.commit()  # Commit the deletion to the database
    return redirect(url_for('existing_chapters', subject_id=subject_id))  # Redirect back to the subject's chapter list

#view chapter
@app.route('/view_chapter/<int:chapter_id>', methods=['GET', 'POST'])
def view_chapter(chapter_id):
    # Fetch chapter details
    chapter = Chapter.query.get_or_404(chapter_id)
    
    # Fetch related quizzes
    quizzes = Quiz.query.filter_by(chapter_id=chapter_id).all()  # Assuming a Quiz model exists

    if request.method == 'POST':
        # Get the quiz details from the form
        quiz_name = request.form.get('name')
        quiz_description = request.form.get('description')

        # Save the new quiz to the database
        new_quiz = Quiz(name=quiz_name, description=quiz_description, chapter_id=chapter.id)
        db.session.add(new_quiz)
        db.session.commit()

        flash("Quiz added successfully!", "success")
        return redirect(url_for('view_chapter', chapter_id=chapter.id))

    # Render the quizes.html template with chapter and quizzes data
    return render_template('quizes.html', chapter=chapter, quizzes=quizzes)





#create a new subject
@app.route("/add-subject", methods=["GET", "POST"])
def add_subject():
    if request.method == "POST":
        name = request.form["name"]
        description = request.form.get("description", "")

        new_subject = Subject(name=name, description=description)
        db.session.add(new_subject)
        db.session.commit()

        return redirect(url_for("admin_dashboard"))
    return render_template("add_subject.html")


#edit subject
@app.route('/edit_subject/<int:subject_id>', methods=['GET', 'POST'])
def edit_subject(subject_id):
    subject = Subject.query.get(subject_id)
    if request.method == 'POST':
        # Process the form and update the subject
        subject.name = request.form['name']
        subject.description = request.form['description']
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_subject.html', subject=subject)

#delete subject
@app.route('/delete_subject/<int:subject_id>', methods=['POST'])
def delete_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    db.session.delete(subject)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))




#home page
@app.route("/")
def home():
    return render_template("home.html")


# User registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        
        
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        qualification = request.form.get('qualification')
        dob = request.form.get('dob')

        new_user = User(email=email, password=password, full_name=full_name, qualification=qualification, dob=dob)
        db.session.add(new_user)
        db.session.commit()
        print('Registration successful!')
        return redirect(url_for('login'))

    return render_template('register.html')

# User login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:  
            # Store user ID in the session
            session['user_id'] = user.id

            # Redirect to the user's specific dashboard
            return redirect(url_for("user_dashboard", user_id=user.id))
        else:
            flash("Invalid email or password!", "danger")
            return redirect(url_for('login'))

    return render_template("login.html")

#user dashboard
@app.route('/user/dashboard/<int:user_id>', methods=['GET'])
def user_dashboard(user_id):
    if 'user_id' not in session or session['user_id'] != user_id:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    user = User.query.get_or_404(user_id)
    subjects = Subject.query.all()

    # Get selected subject and chapter IDs from request
    selected_subject_id = request.args.get('subject_id', type=int)
    selected_chapter_id = request.args.get('chapter_id', type=int)

    chapters = []
    quizzes = []

    # Filter chapters based on selected subject
    if selected_subject_id:
        chapters = Chapter.query.filter_by(subject_id=selected_subject_id).all()

    # Filter quizzes based on selected subject and chapter
    if selected_subject_id and selected_chapter_id:
        quizzes = (
            Quiz.query
            .join(Chapter)
            .filter(Chapter.subject_id == selected_subject_id, Quiz.chapter_id == selected_chapter_id)
            .all()
        )

    return render_template(
        'user_dashboard.html',
        user=user,
        subjects=subjects,
        chapters=chapters,
        quizzes=quizzes,
        selected_subject_id=selected_subject_id,
        selected_chapter_id=selected_chapter_id
    )





if __name__ == "__main__":
    app.run(debug=True)