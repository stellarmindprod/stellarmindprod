# stellarminprod/app.py

import requests
import json
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Import configuration variables
from config import (
    SUPABASE_URL, SUPABASE_HEADERS, STUDENT_TABLES, TEACHER_TABLE, ADMIN_TABLE,
    MARKS_TABLES, SECRET_KEY
    # Add other tables from config as needed, e.g., ATTENDANCE_TABLE
)

# Initialize Flask App
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

# --- Helper Functions ---

def get_supabase_rest_url(table_name):
    """Constructs the Supabase REST API URL for a table."""
    return f"{SUPABASE_URL}/rest/v1/{table_name}"

def determine_student_batch(roll_no):
    """Determines the batch table (b1-b4) based on roll number prefix or logic."""
    # Example Logic: This needs to be defined based on how roll numbers map to batches.
    # Placeholder: Assume first char determines batch (e.g., '1' -> b1, '2' -> b2)
    # Or based on year part if available in roll_no structure.
    # For now, we'll search all tables in the login function.
    # This function might be more useful during signup or data entry.
    year_prefix = roll_no[1] # Assuming roll no starts like 'b1...', 'b2...'
    if year_prefix == '1': return 'b1'
    if year_prefix == '2': return 'b2'
    if year_prefix == '3': return 'b3'
    if year_prefix == '4': return 'b4'
    return None # Or default to searching all

def get_marks_table_for_student(roll_no):
    """Determines the correct marks table (marks1-marks4) for a student."""
    # This logic depends on how students are mapped to marks tables (e.g., by year).
    # Assuming the same logic as determine_student_batch for simplicity.
    batch = determine_student_batch(roll_no)
    if batch == 'b1': return 'marks1'
    if batch == 'b2': return 'marks2'
    if batch == 'b3': return 'marks3'
    if batch == 'b4': return 'marks4'
    return None

# --- Authentication Decorators ---

def login_required(role=None):
    """Decorator to require login. Can optionally check for specific roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login_page'))
            if role:
                required_roles = role if isinstance(role, list) else [role]
                if session['user'].get('role') not in required_roles:
                    flash('You do not have permission to access this page.', 'danger')
                    return redirect(url_for('index')) # Redirect to a default page
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Authentication Logic ---

def fetch_and_verify_user(username, password):
    """Finds user across tables and verifies password."""
    username_lower = username.lower() # Use lowercase for lookup

    # 1. Try Student Tables
    for table_name in STUDENT_TABLES:
        url = get_supabase_rest_url(table_name)
        params = {'select': '*,student_password', 'roll_no': f'eq.{username_lower}'}
        try:
            response = requests.get(url, headers=SUPABASE_HEADERS, params=params)
            response.raise_for_status()
            data = response.json()
            if data and len(data) == 1:
                user_data = data[0]
                # !! CRITICAL SECURITY NOTE !!
                # The check below assumes PLAIN TEXT passwords in the database.
                # This is VERY INSECURE. In production, store hashed passwords
                # and use check_password_hash(user_data['student_password'], password).
                # Remove '.replace("$2b$", "$2a$")' if not using bcrypt compatibility fix.
                # if check_password_hash(user_data.get('student_password', '').replace("$2b$", "$2a$"), password):
                if user_data.get('student_password') == password: # Insecure plain text check
                    user_data.pop('student_password', None)
                    user_data['role'] = 'student'
                    user_data['batch'] = table_name # Store the batch table name
                    return user_data
        except requests.exceptions.RequestException as e:
            print(f"Error querying {table_name}: {e}")
        except json.JSONDecodeError:
            print(f"Failed to decode JSON from {table_name}")

    # 2. Try Teacher Table
    url = get_supabase_rest_url(TEACHER_TABLE)
    params = {'select': '*,teacher_password', 'username': f'eq.{username_lower}'}
    try:
        response = requests.get(url, headers=SUPABASE_HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        if data and len(data) == 1:
            user_data = data[0]
            # !! Use check_password_hash if passwords are hashed in DB !!
            # if check_password_hash(user_data.get('teacher_password', '').replace("$2b$", "$2a$"), password):
            if user_data.get('teacher_password') == password: # Insecure plain text check
                user_data.pop('teacher_password', None)
                user_data['role'] = 'teacher'
                return user_data
    except requests.exceptions.RequestException as e:
        print(f"Error querying {TEACHER_TABLE}: {e}")
    except json.JSONDecodeError:
        print(f"Failed to decode JSON from {TEACHER_TABLE}")

    # 3. Try Admin Table (Assuming 'admins' table and 'password' column)
    url = get_supabase_rest_url(ADMIN_TABLE)
    params = {'select': '*,password', 'username': f'eq.{username_lower}'}
    try:
        response = requests.get(url, headers=SUPABASE_HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        if data and len(data) == 1:
            user_data = data[0]
            # !! Use check_password_hash if passwords are hashed in DB !!
            # if check_password_hash(user_data.get('password', '').replace("$2b$", "$2a$"), password):
            if user_data.get('password') == password: # Insecure plain text check
                user_data.pop('password', None)
                user_data['role'] = 'admin'
                return user_data
    except requests.exceptions.RequestException as e:
        print(f"Error querying {ADMIN_TABLE}: {e}")
    except json.JSONDecodeError:
        print(f"Failed to decode JSON from {ADMIN_TABLE}")

    return None # No user found or password incorrect

# --- Flask Routes ---

@app.route("/")
def index():
    """Redirects to dashboard if logged in, otherwise to login."""
    if 'user' in session:
        user_role = session['user'].get('role')
        if user_role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user_role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        else: # student
            return redirect(url_for('student_dashboard'))
    return redirect(url_for('login_page'))

@app.route("/login", methods=["GET", "POST"])
def login_page():
    """Handles GET request for login page and POST for login attempt."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template("login.html")

        user_data = fetch_and_verify_user(username, password)

        if user_data:
            session['user'] = user_data # Store user data in session
            flash(f"Welcome back, {user_data.get('student_name') or user_data.get('teacher_name') or user_data.get('username')}!", "success")
            return redirect(url_for('index')) # Redirect to appropriate dashboard via index
        else:
            flash("Invalid credentials. Please try again.", "danger")
            return render_template("login.html"), 401 # Unauthorized

    # If GET request
    if 'user' in session:
        return redirect(url_for('index')) # Redirect logged-in users away from login page
    return render_template("login.html")

@app.route("/logout")
@login_required()
def logout():
    """Logs the user out by clearing the session."""
    session.pop('user', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login_page'))

# --- Dashboard Routes (Placeholders) ---

@app.route("/dashboard/student")
@login_required(role='student')
def student_dashboard():
    user = session['user']
    roll_no = user.get('roll_no')
    marks_table = get_marks_table_for_student(roll_no)

    marks_data = []
    semesters_data = {} # To hold SGPA/CGPA if available

    # Fetch Marks
    if marks_table:
        url = get_supabase_rest_url(marks_table)
        params = {'select': 'subject_code,mid1,mid2,endsem,final_grade,internal_marks', 'roll_no': f'eq.{roll_no}'}
        try:
            response = requests.get(url, headers=SUPABASE_HEADERS, params=params)
            response.raise_for_status()
            marks_data = response.json()
        except Exception as e:
            flash(f"Could not fetch marks: {e}", "warning")

    # Fetch Grades (SGPA/CGPA)
    try:
        url_grades = get_supabase_rest_url('grades') # Assuming 'grades' table name
        params_grades = {'select': '*', 'roll_no': f'eq.{roll_no}'}
        response_grades = requests.get(url_grades, headers=SUPABASE_HEADERS, params=params_grades)
        response_grades.raise_for_status()
        grades_result = response_grades.json()
        if grades_result and len(grades_result) == 1:
            raw_grades = grades_result[0]
            # Process grades for easier display
            for i in range(1, 9):
                sem_key = f'sem{i}'
                sgpa_key = f'sgpa_{sem_key}'
                credits_key = f'total_credits_{sem_key}'
                if raw_grades.get(sgpa_key) is not None or raw_grades.get(credits_key) is not None:
                    semesters_data[sem_key] = {
                        'sgpa': raw_grades.get(sgpa_key),
                        'credits': raw_grades.get(credits_key)
                    }
            semesters_data['cgpa'] = raw_grades.get('cgpa')

    except Exception as e:
        flash(f"Could not fetch grades data: {e}", "warning")


    return render_template("student_dashboard.html", user=user, marks=marks_data, grades=semesters_data)

@app.route("/dashboard/teacher")
@login_required(role='teacher')
def teacher_dashboard():
    user = session['user']
    # Add logic to fetch teacher-specific data (e.g., assigned courses)
    return render_template("teacher_dashboard.html", user=user)

@app.route("/dashboard/admin")
@login_required(role='admin')
def admin_dashboard():
    user = session['user']
    # Add logic to fetch admin-specific data or show admin controls
    return render_template("admin_dashboard.html", user=user)

# --- API Endpoints (Example for Student Marks) ---
# You might not need separate API endpoints if you render data directly in Flask templates,
# but they can be useful for dynamic updates or if you keep some JS-driven parts.

@app.route("/api/student/marks")
@login_required(role='student')
def api_get_student_marks():
    user = session['user']
    roll_no = user.get('roll_no')
    marks_table = get_marks_table_for_student(roll_no)

    if not marks_table:
        return jsonify({"error": "Could not determine marks table"}), 400

    url = get_supabase_rest_url(marks_table)
    # Select specific columns needed by the frontend
    params = {'select': 'subject_code,credits,mid1,mid2,endsem,final_grade,internal_marks', 'roll_no': f'eq.{roll_no}'}

    try:
        response = requests.get(url, headers=SUPABASE_HEADERS, params=params)
        response.raise_for_status()
        marks_data = response.json()
        return jsonify(marks_data), 200
    except requests.exceptions.RequestException as e:
        print(f"API Error fetching marks for {roll_no}: {e}")
        return jsonify({"error": f"Failed to fetch marks: {e}"}), 500
    except json.JSONDecodeError:
         print(f"API Error decoding marks JSON for {roll_no}")
         return jsonify({"error": "Failed to decode marks data"}), 500

# --- Error Handling ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


# --- Main Execution ---
if __name__ == "__main__":
    # In production, use a proper WSGI server like Gunicorn or Waitress
    # Example: gunicorn -w 4 app:app
    app.run(debug=True, port=5000) # debug=True is for development ONLY
