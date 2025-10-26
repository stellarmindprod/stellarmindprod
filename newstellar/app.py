# stellarminprod/app.py

import requests
import json
import datetime # Import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Import configuration variables
from config import (
    SUPABASE_URL, SUPABASE_HEADERS, STUDENT_TABLES, TEACHER_TABLE, ADMIN_TABLE,
    MARKS_TABLES, SECRET_KEY, GRADES_TABLE, EVENTS_TABLE, HOLIDAYS_TABLE,
    ATTENDANCE_TABLES, SUPABASE_ANON_KEY, COURSE_TABLE # Added COURSE_TABLE
)

# Initialize Flask App
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

# --- Helper Functions ---

def get_supabase_rest_url(table_name):
    """Constructs the Supabase REST API URL for a table."""
    # Basic validation to prevent unintended table access
    allowed_tables = STUDENT_TABLES + MARKS_TABLES + ATTENDANCE_TABLES + [
        TEACHER_TABLE, ADMIN_TABLE, GRADES_TABLE, EVENTS_TABLE, HOLIDAYS_TABLE,
        COURSE_TABLE # Added COURSE_TABLE
    ] # Add other valid tables
    if table_name not in allowed_tables:
         raise ValueError(f"Access to table '{table_name}' is not permitted.")
    return f"{SUPABASE_URL}/rest/v1/{table_name}"

def determine_student_batch(roll_no):
    """Determines the batch table (b1-b4) based on roll number prefix."""
    if not roll_no or len(roll_no) < 2:
        return None
    
    # Updated logic to be more robust, e.g., 'b24...' -> 'b4'
    # This assumes 'b' followed by year digit
    year_prefix_char = roll_no.lower()[1] 
    
    # Assuming 'b21...' is 'b1', 'b22...' is 'b2', 'b23...' is 'b3', 'b24...' is 'b4'
    # This logic seems brittle. Let's try a different assumption based on the user's JS:
    # The JS logic checks for 'b2400' specifically.
    
    # Let's use the logic from the old file: 'b24...' maps to b24 schedule.
    # And your tables are b1, b2, b3, b4.
    # We'll assume for now b1 = 1st year, b2 = 2nd year, etc.
    # And b24... is 2nd year ('b2')
    # A more robust mapping is needed, but for now:
    
    if roll_no.lower().startswith('b24'): # 2nd Year
        return 'b2'
    if roll_no.lower().startswith('b23'): # 3rd Year
        return 'b3'
    if roll_no.lower().startswith('b22'): # 4th Year
        return 'b4'
    if roll_no.lower().startswith('b25'): # 1st Year
        return 'b1'
        
    print(f"Warning: Could not determine batch for roll_no: {roll_no}")
    return None # Return None if no match

def get_marks_table_for_student(roll_no):
    """Determines the correct marks table (marks1-marks4) for a student."""
    batch = determine_student_batch(roll_no)
    if batch == 'b1': return 'marks1'
    if batch == 'b2': return 'marks2'
    if batch == 'b3': return 'marks3'
    if batch == 'b4': return 'marks4'
    return None

def determine_attendance_table(batch_table):
    """Determines the correct attendance table (attendance1-4) from a student batch table (b1-4)."""
    if batch_table == 'b1': return 'attendance1'
    if batch_table == 'b2': return 'attendance2'
    if batch_table == 'b3': return 'attendance3'
    if batch_table == 'b4': return 'attendance4'
    return None

# --- Context Processor ---
@app.context_processor
def inject_now():
    return {'now': datetime.datetime.utcnow()}

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
                user_role = session['user'].get('role')
                if user_role not in required_roles:
                    flash(f'Access denied. Required role: {", ".join(required_roles)}.', 'danger')
                    return redirect(url_for('index')) # Redirect to main dashboard

            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Authentication Logic ---

def fetch_and_verify_user(username, password):
    """Finds user across tables and verifies password."""
    username_lower = username.lower() 

    # 1. Try Student Tables
    # Determine batch from username (roll_no)
    batch_table = determine_student_batch(username_lower)
    if batch_table:
        try:
            url = get_supabase_rest_url(batch_table)
            params = {'select': '*,student_password', 'roll_no': f'eq.{username_lower}'}
            response = requests.get(url, headers=SUPABASE_HEADERS, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data and len(data) == 1:
                user_data = data[0]
                if check_password_hash(user_data.get('student_password', ''), password):
                    user_data.pop('student_password', None) 
                    user_data['role'] = 'student'
                    user_data['batch'] = batch_table 
                    return user_data
        except Exception as e:
            print(f"Error querying {batch_table}: {e}")

    # 2. Try Teacher Table
    try:
        url = get_supabase_rest_url(TEACHER_TABLE)
        params = {'select': '*,teacher_password', 'username': f'eq.{username_lower}'}
        response = requests.get(url, headers=SUPABASE_HEADERS, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data and len(data) == 1:
            user_data = data[0]
            if check_password_hash(user_data.get('teacher_password', ''), password):
                user_data.pop('teacher_password', None)
                user_data['role'] = 'teacher'
                return user_data
    except Exception as e:
        print(f"Error querying {TEACHER_TABLE}: {e}")

    # 3. Try Admin Table
    try:
        url = get_supabase_rest_url(ADMIN_TABLE)
        params = {'select': '*,password', 'username': f'eq.{username_lower}'}
        response = requests.get(url, headers=SUPABASE_HEADERS, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data and len(data) == 1:
            user_data = data[0]
            if check_password_hash(user_data.get('password', ''), password):
                user_data.pop('password', None)
                user_data['role'] = 'admin'
                return user_data
    except Exception as e:
        print(f"Error querying {ADMIN_TABLE}: {e}")

    return None # No user found or password incorrect

# --- Flask Routes ---

# Hardcoded Timetable (as from your JS)
# This should ideally be moved to the database
b24_timetable = {
    "MON": [
        "09:30 - 10:30 → Digital Logic Design (ECE Faculty) Shed III",
        "10:30 - 11:30 → Computational Mathematics (RS) Shed III",
        "11:30 - 12:30 → Data Structure and Algorithms (LA) Shed III",
        "12:30 - 14:00 → BREAK",
        "14:00 - 16:00 → DLD Lab 'Aw' (ECE Faculty)",
        "16:00 - 18:00 → DSA Lab (LA/AKT/BBS) CL-4",
    ],
    "TUE": [
        "09:30 - 10:30 → Computer Networks (ALM) Shed III",
        "10:30 - 11:30 → Data Structure and Algorithms (LA) Shed III",
        "11:30 - 13:30 → DSA Lab (LA/AKT/BBS) CL-4",
        "13:30 - 15:00 → BREAK",
        "15:00 - 16:00 → Digital Logic Design (ECE Faculty) Shed III",
        "16:00 - 18:00 → DLD Lab 'Ax' (ECE Faculty)",
    ],
    "WED": [
        "09:30 - 10:30 → Computer Networks (ALM) Shed III",
        "10:30 - 11:30 → Foundation to Machine Learning (BBS) Shed III",
        "11:30 - 12:30 → Computational Mathematics (RS) Shed III",
        "12:30 - 14:00 → Break",
        "14:00 - 15:00 → Object Oriented System Design(PKK) Shed III",
        "15:00 - 16:00 → Digital Logic Design (ECE Faculty) Shed III",
        "16:00 - 18:00 → DLD Lab 'Ay' (ECE Faculty)",
    ],
    "THU": [
        "08:30 - 09:30 → Professional Practice (BBS) Shed III",
        "09:30 - 10:30 → Computational Mathematics (RS) Shed III",
        "10:30 - 11:30 → Computer Networks (ALM) Shed III",
        "11:30 - 13:30 → Computer Networks Lab (ALM) CL-4",
        "13:30 - 15:00 → BREAK",
        "15:00 - 16:00 → Object Oriented System Design (PKK) Shed III",
        "16:00 - 18:00 → DLD Lab 'Az' (ECE Faculty)",
    ],
    "FRI": [
        "08:30 - 09:30 → Professional Practice (BBS) Shed III",
        "09:30 - 10:30 → Computer Networks (ALM) Shed III",
        "10:30 - 12:30 → Foundation to Machine Learning (BBS) Shed III",
        "12:30 - 14:00 → BREAK",
        "14:00 - 15:00 → Object Oriented System Design (PKK) Shed III",
        "15:00 - 16:00 → Data Structure and Algorithms (LA) Shed III",
        "16:00 - 18:00 → OOSD Lab (PKK) CL-3",
    ],
}
# Add other timetables if necessary
timetables = {
    'b2': b24_timetable # Assuming b24 roll_no maps to 'b2' table
    # 'b1': b25_timetable, 
    # 'b3': b23_timetable,
    # 'b4': b22_timetable,
}


@app.route("/")
@login_required() # User must be logged in to see the dashboard
def index():
    """Renders the main combined dashboard."""
    user = session['user']
    events_data = []
    holidays_data = []
    daily_schedule = []
    today_is_holiday = False
    
    # Get today's date info (assuming server is in same timezone as users or UTC)
    # Using UTC for consistency
    today = datetime.datetime.utcnow() 
    today_str = today.strftime('%a').upper() # MON, TUE...
    today_date_str = today.strftime('%Y-%m-%d') # 2025-10-25

    # Fetch Events
    try:
        url_events = get_supabase_rest_url(EVENTS_TABLE)
        params_events = {'select': '*', 'date': f'gte.{today_date_str}', 'order': 'date.asc'}
        response_events = requests.get(url_events, headers=SUPABASE_HEADERS, params=params_events, timeout=5)
        if response_events.ok:
            events_data = response_events.json()
    except Exception as e:
        print(f"Error fetching events: {e}")
        flash("Could not load upcoming events.", "warning")

    # Fetch Holidays
    try:
        url_holidays = get_supabase_rest_url(HOLIDAYS_TABLE)
        params_holidays = {'select': '*', 'date': f'gte.{today_date_str}', 'order': 'date.asc'}
        response_holidays = requests.get(url_holidays, headers=SUPABASE_HEADERS, params=params_holidays, timeout=5)
        if response_holidays.ok:
            holidays_data = response_holidays.json()
            # Check if today is a holiday
            for holiday in holidays_data:
                if holiday.get('date') == today_date_str:
                    today_is_holiday = True
                    break
    except Exception as e:
        print(f"Error fetching holidays: {e}")
        flash("Could not load upcoming holidays.", "warning")

    # Get Student Schedule (if user is student)
    if user.get('role') == 'student':
        if today_str in ["SAT", "SUN"]:
            today_is_holiday = True
        
        if not today_is_holiday:
            student_batch = user.get('batch') # e.g., 'b2'
            if student_batch and student_batch in timetables:
                daily_schedule = timetables[student_batch].get(today_str, [])
            else:
                # No schedule found for this batch
                daily_schedule = [] # Template will handle this
    
    return render_template(
        "dashboard.html", 
        user=user, 
        events=events_data, 
        holidays=holidays_data, 
        daily_schedule=daily_schedule, 
        today_is_holiday=today_is_holiday
    )


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
            display_name = (user_data.get('student_name') or
                            user_data.get('teacher_name') or
                            user_data.get('username', 'User'))
            flash(f"Welcome back, {display_name}!", "success")
            return redirect(url_for('index')) # Redirect to the NEW dashboard
        else:
            flash("Invalid credentials. Please try again.", "danger")
            return render_template("login.html"), 401

    # If GET request
    if 'user' in session:
        return redirect(url_for('index')) # Redirect logged-in users to new dashboard
    return render_template("login.html")

@app.route("/logout")
@login_required()
def logout():
    """Logs the user out by clearing the session."""
    session.pop('user', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login_page'))

# --- Route for Student Signup Page ---
@app.route("/signup", methods=["GET", "POST"])
def signup_page():
    if request.method == "POST":
        roll_no = request.form.get("roll_no", "").strip().lower()
        student_name = request.form.get("student_name", "").strip()
        student_email = request.form.get("student_email", "").strip().lower()
        password = request.form.get("student_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not all([roll_no, student_name, student_email, password, confirm_password]):
            flash("All fields are required.", "danger")
            return render_template("signup.html")
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("signup.html")
        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
            return render_template("signup.html")

        batch_table = determine_student_batch(roll_no)
        if not batch_table:
            flash("Invalid Roll Number format or year.", "danger")
            return render_template("signup.html")

        # Check if user already exists
        try:
            url_check = get_supabase_rest_url(batch_table)
            params_check_roll = {'select': 'roll_no', 'roll_no': f'eq.{roll_no}'}
            params_check_email = {'select': 'student_email', 'student_email': f'eq.{student_email}'}

            response_roll = requests.get(url_check, headers=SUPABASE_HEADERS, params=params_check_roll, timeout=5)
            response_email = requests.get(url_check, headers=SUPABASE_HEADERS, params=params_check_email, timeout=5)

            if response_roll.ok and response_roll.json():
                 flash(f"Roll number '{roll_no}' is already registered.", "danger")
                 return render_template("signup.html")
            if response_email.ok and response_email.json():
                 flash(f"Email '{student_email}' is already registered.", "danger")
                 return render_template("signup.html")

        except requests.exceptions.RequestException as e:
            print(f"Error checking existing user: {e}")
            flash("Could not verify user existence. Please try again.", "warning")
            return render_template("signup.html")
        except ValueError as e:
            flash(str(e), "danger")
            return render_template("signup.html")

        hashed_password = generate_password_hash(password)

        new_student_data = {
            "roll_no": roll_no,
            "student_name": student_name,
            "student_email": student_email,
            "student_password": hashed_password, # Store the HASH
        }

        # Insert into Supabase
        try:
            url_insert = get_supabase_rest_url(batch_table)
            response_insert = requests.post(url_insert, headers=SUPABASE_HEADERS, json=new_student_data, timeout=10)
            response_insert.raise_for_status()

            if response_insert.status_code == 201:
                flash("Account created successfully! Please log in.", "success")
                return redirect(url_for('login_page'))
            else:
                error_details = response_insert.json().get('message', 'Unknown error')
                flash(f"Signup failed: {error_details}", "danger")
                print(f"Supabase signup error response: {response_insert.text}")
                return render_template("signup.html")

        except requests.exceptions.RequestException as e:
            print(f"Error inserting user: {e}")
            flash("Signup failed due to a network or server error. Please try again.", "danger")
            return render_template("signup.html")
        except ValueError as e:
            flash(str(e), "danger")
            return render_template("signup.html")
        except Exception as e:
            print(f"Unexpected error during signup: {e}")
            flash("An unexpected error occurred during signup.", "danger")
            return render_template("signup.html")

    return render_template("signup.html")

# --- Route for Teacher Signup Page ---
@app.route("/teacher-signup", methods=["GET", "POST"])
def teacher_signup_page():
    if request.method == "POST":
        # --- Teacher Signup Logic (Placeholder) ---
        # Implement logic similar to student signup:
        # 1. Get form data (teacher_name, username, email, password, confirm_password, department?)
        # 2. Validate input.
        # 3. Check if teacher username/email already exists in TEACHER_TABLE.
        # 4. Hash the password.
        # 5. Insert the new teacher record into TEACHER_TABLE.
        # 6. Redirect to login with success/error message.
        flash("Teacher signup not yet implemented.", "info")
        return redirect(url_for('login_page')) # Redirect for now

    return render_template("teacher_signup.html") 

# --- Route for Forgot Password Page ---
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password_page():
    if request.method == "POST":
        username_or_email = request.form.get("username_or_email", "").strip()
        flash("Password reset functionality is not yet fully implemented.", "info")
        return redirect(url_for('login_page'))

    return render_template("forgot_password.html")


# --- NEW Student-facing Placeholder Routes ---
@app.route("/student/attendance")
@login_required(role='student')
def student_attendance_page():
     user = session.get('user')
     if not user or user.get('role') != 'student':
         flash("You must be logged in as a student to view this page.", "danger")
         return redirect(url_for('login_page'))

     batch_table = user.get('batch') # e.g., 'b2'
     attendance_table = determine_attendance_table(batch_table)

     if not attendance_table:
         flash("Could not determine attendance records for your batch.", "warning")
         return redirect(url_for('index'))

     return render_template(
         "attendance.html", 
         user=user, 
         attendance_table=attendance_table,
         supabase_url=SUPABASE_URL,
         supabase_key=SUPABASE_ANON_KEY
     )

@app.route("/student/marks")
@login_required(role='student')
def student_marks_page():
    user = session.get('user')
    if not user or user.get('role') != 'student':
        flash("You must be logged in as a student to view this page.", "danger")
        return redirect(url_for('login_page'))
    
    roll_no = user.get('roll_no')
    if not roll_no:
        flash("Could not identify student roll number.", "danger")
        return redirect(url_for('index'))

    # Use the existing helper function to get the correct marks table
    marks_table = get_marks_table_for_student(roll_no) 

    if not marks_table:
        flash("Could not determine marks records for your batch.", "warning")
        return redirect(url_for('index'))

    return render_template(
        "marks.html", # Render the new marks.html template
        user=user, 
        marks_table=marks_table, # Pass the correct marks table name
        supabase_url=SUPABASE_URL,
        supabase_key=SUPABASE_ANON_KEY
    )


# --- Placeholder Routes for Teacher/Admin Actions (Kept) ---

@app.route("/teacher/attendance")
@login_required(role='teacher')
def mark_attendance_page():
     flash("Attendance marking not yet implemented.", "info")
     return redirect(url_for('index'))

@app.route("/teacher/marks")
@login_required(role='teacher')
def enter_marks_page():
     flash("Marks entry not yet implemented.", "info")
     return redirect(url_for('index'))

@app.route("/teacher/students")
@login_required(role='teacher')
def view_student_profiles_page():
     flash("Student profile view not yet implemented.", "info")
     return redirect(url_for('index'))

@app.route("/admin/attendance")
@login_required(role='admin')
def admin_mark_attendance_page():
     flash("Admin attendance management not yet implemented.", "info")
     return redirect(url_for('index'))

@app.route("/admin/marks")
@login_required(role='admin')
def admin_enter_marks_page():
     flash("Admin marks management not yet implemented.", "info")
     return redirect(url_for('index'))

@app.route("/admin/users")
@login_required(role='admin')
def manage_users_page():
     flash("User management not yet implemented.", "info")
     return redirect(url_for('index'))

@app.route("/admin/courses")
@login_required(role='admin')
def manage_courses_page():
     flash("Course management not yet implemented.", "info")
     return redirect(url_for('index'))

@app.route("/admin/events")
@login_required(role='admin')
def manage_events_page():
     flash("Event management not yet implemented.", "info")
     return redirect(url_for('index'))


# --- Error Handling ---
@app.errorhandler(404)
def page_not_found(e):
    print(f"404 Error: {e}")
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    print(f"Internal Server Error: {e}")
    return render_template('500.html'), 500

# --- Main Execution ---
if __name__ == "__main__":
    app.run(debug=True, port=5000)
