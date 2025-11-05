# app.py
import json
import os
import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename
from functools import wraps

# --- APP CONFIGURATION ---
app = Flask(__name__)
# This secret key is essential for Flask sessions (user login) to work.
# In a real application, this should be a long, random string.
app.secret_key = 'a-very-secret-key-that-you-should-change'

# Configure a folder to store uploaded files (lectures, assignments, etc.)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Create the upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# --- DATABASE HELPER FUNCTIONS ---
# These are the same functions from your script.

def load_data(filename):
    """Loads data from a JSON file."""
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def save_data(filename, data):
    """Saves data to a JSON file."""
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        print(f"Error saving data: {e}")

def get_next_id(data_list, id_key):
    """Generates the next unique ID for a list of dictionaries."""
    if not data_list:
        return 1
    return max(item[id_key] for item in data_list) + 1

# --- LOGIN DECORATOR ---
# This is a helper to protect pages that require a user to be logged in.
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            flash("You need to be logged in to view this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- AUTHENTICATION ROUTES ---

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user_email' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        users = load_data('users.json')
        user = next((u for u in users if u['email'] == email and u['password'] == password), None)

        if user:
            session['user_id'] = user['user_id']
            session['user_email'] = user['email']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password.", "danger")
            
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        users = load_data('users.json')
        if any(u['email'] == email for u in users):
            flash("An account with this email already exists.", "danger")
            return redirect(url_for('signup'))

        new_user = {
            "user_id": get_next_id(users, 'user_id'),
            "name": name,
            "email": email,
            "password": password, # In a real app, hash passwords!
            "role": role,
            "join_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        users.append(new_user)
        save_data('users.json', users)
        
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for('login'))
        
    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))


# --- CORE APPLICATION ROUTES ---

@app.route('/dashboard')
@login_required
def dashboard():
    if session['user_role'] == 'Admin':
        users = load_data('users.json')
        students = [u for u in users if u['role'] == 'Student']
        return render_template('admin_dashboard.html', students=students)
    else: # Student
        lectures = load_data('lectures.json')
        notes = load_data('notes.json')
        assignments = load_data('assignments.json')
        return render_template('student_dashboard.html', lectures=lectures, notes=notes, assignments=assignments)


# --- ADMIN ROUTES ---

@app.route('/admin/lectures', methods=['GET', 'POST'])
@login_required
def manage_lectures():
    if session['user_role'] != 'Admin':
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        file = request.files['file']
        
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            lectures = load_data('lectures.json')
            new_lecture = {
                "lecture_id": get_next_id(lectures, 'lecture_id'),
                "title": title,
                "description": description,
                "file_path": filename,
                "uploaded_by": session['user_id'],
                "upload_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "accessed_by": []
            }
            lectures.append(new_lecture)
            save_data('lectures.json', lectures)
            flash("Lecture uploaded successfully.", "success")
            return redirect(url_for('manage_lectures'))

    lectures = load_data('lectures.json')
    return render_template('manage_lectures.html', lectures=lectures)

@app.route('/admin/assignments', methods=['GET', 'POST'])
@login_required
def manage_assignments():
    if session['user_role'] != 'Admin':
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        file = request.files['file']
        
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            assignments = load_data('assignments.json')
            new_assignment = {
                "assignment_id": get_next_id(assignments, 'assignment_id'),
                "title": title,
                "description": description,
                "file_path": filename,
                "uploaded_by": session['user_id'],
                "upload_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            assignments.append(new_assignment)
            save_data('assignments.json', assignments)
            flash("Assignment uploaded successfully.", "success")
            return redirect(url_for('manage_assignments'))

    assignments = load_data('assignments.json')
    submissions = load_data('submissions.json')
    users = load_data('users.json')
    
    # Add student names to submissions for easier display
    for sub in submissions:
        student = next((u for u in users if u['user_id'] == sub['submitted_by']), None)
        sub['student_name'] = student['name'] if student else 'Unknown'

    return render_template('manage_assignments.html', assignments=assignments, submissions=submissions)

@app.route('/admin/grade/<int:submission_id>', methods=['POST'])
@login_required
def grade_submission(submission_id):
    if session['user_role'] != 'Admin':
        return redirect(url_for('dashboard'))
    
    grade = request.form['grade']
    submissions = load_data('submissions.json')
    submission = next((s for s in submissions if s['submission_id'] == submission_id), None)
    
    if submission:
        submission['grade'] = grade
        save_data('submissions.json', submissions)
        flash("Submission graded.", "success")
    else:
        flash("Submission not found.", "danger")
        
    return redirect(url_for('manage_assignments'))


# --- STUDENT ROUTES ---

@app.route('/student/submit/<int:assignment_id>', methods=['POST'])
@login_required
def submit_assignment(assignment_id):
    if session['user_role'] != 'Student':
        return redirect(url_for('dashboard'))

    file = request.files['file']
    if file and file.filename != '':
        submissions = load_data('submissions.json')

        # Check if already submitted
        if any(s['assignment_id'] == assignment_id and s['submitted_by'] == session['user_id'] for s in submissions):
            flash("You have already submitted this assignment.", "warning")
            return redirect(url_for('dashboard'))
        
        filename = secure_filename(f"sub_{session['user_id']}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        new_submission = {
            "submission_id": get_next_id(submissions, 'submission_id'),
            "assignment_id": assignment_id,
            "submitted_by": session['user_id'],
            "file_path": filename,
            "submit_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "grade": "Not Graded"
        }
        submissions.append(new_submission)
        save_data('submissions.json', submissions)
        flash("Assignment submitted successfully!", "success")
    else:
        flash("You must select a file to submit.", "danger")

    return redirect(url_for('dashboard'))


# --- FILE SERVING ROUTE ---
# This route allows users to download the uploaded files.
@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# --- MAIN EXECUTION ---
if __name__ == '__main__':
    app.run(debug=True)