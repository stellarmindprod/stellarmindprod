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
    ATTENDANCE_TABLES, SUPABASE_ANON_KEY, COURSE_TABLE
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
    """
    Determines the batch table (b1-b4) based on roll number.
    This logic now maps semester 1/2 -> b1, 3/4 -> b2, 5/6 -> b3, 7/8 -> b4.
    We need a way to get semester from roll_no, or we must change this.

    Let's use the old logic from your JS:
    b25... -> b1 (1st Year)
    b24... -> b2 (2nd Year)
    b23... -> b3 (3rd Year)
    b22... -> b4 (4th Year)
    """
    if not roll_no or len(roll_no) < 2:
        return None
    
    roll_lower = roll_no.lower()
    
    if roll_lower.startswith('b25'): # 1st Year
        return 'b1'
    if roll_lower.startswith('b24'): # 2nd Year
        return 'b2'
    if roll_lower.startswith('b23'): # 3rd Year
        return 'b3'
    if roll_lower.startswith('b22'): # 4th Year
        return 'b4'
        
    print(f"Warning: Could not determine batch table for roll_no: {roll_no}")
    # Fallback for other formats, maybe just check first two chars?
    if roll_lower.startswith('b1'): return 'b1'
    if roll_lower.startswith('b2'): return 'b2'
    if roll_lower.startswith('b3'): return 'b3'
    if roll_lower.startswith('b4'): return 'b4'

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

# --- START OF NEW HELPER FUNCTION ---
def fetch_all_teachers():
    """Fetches all teachers (username and name) from the database."""
    try:
        teacher_url = get_supabase_rest_url(TEACHER_TABLE)
        # Select username and teacher_name, order by name
        teacher_params = {'select': 'username,teacher_name', 'order': 'teacher_name.asc'}
        response_teachers = requests.get(teacher_url, headers=SUPABASE_HEADERS, params=teacher_params, timeout=10)
        response_teachers.raise_for_status()
        return response_teachers.json() # Returns a list of teacher objects
    except Exception as e:
        print(f"Error fetching teachers: {e}")
        flash("Could not load teacher list for dropdowns.", "warning")
        return [] # Return empty list on error
# --- END OF NEW HELPER FUNCTION ---

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
                    user_data['roll_no'] = user_data.get('roll_no', username_lower) # Ensure roll_no is set
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
                user_data['username'] = user_data.get('username', username_lower) # Ensure username is set
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
b24_timetable = { # This is 'b2'
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
            
            # --- START OF MODIFICATION ---
            # Check the user's role and redirect accordingly
            if user_data.get('role') == 'admin':
                return redirect(url_for('admin_dashboard')) # Redirect admins to admin dashboard
            else:
                return redirect(url_for('index')) # Redirect all other users to main dashboard
            # --- END OF MODIFICATION ---

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
            flash("Invalid Roll Number format or year. Must start with b22, b23, b24, or b25.", "danger")
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
    """
    Renders the teacher attendance marking page.
    Fetches courses assigned to the logged-in teacher.
    """
    user = session.get('user')
    # Use 'username' from session, as 'teacher_name' might be the full name
    teacher_username = user.get('username') 

    if not teacher_username:
        flash("Could not identify teacher username. Please log in again.", "danger")
        return redirect(url_for('login_page'))

    all_assigned_courses = []
    try:
        # Fetch courses assigned to this teacher from the 'courses' table
        url = get_supabase_rest_url(COURSE_TABLE)
        # Assumes 'assisting_teacher' column stores the teacher's 'username'
        # MODIFIED: Added 'credits' to the select query
        params = {'select': 'course_code,course_name,semester,credits', 'assisting_teacher': f'eq.{teacher_username}'}
        response = requests.get(url, headers=SUPABASE_HEADERS, params=params, timeout=10)
        response.raise_for_status() # Raise an exception for bad status codes
        all_assigned_courses = response.json()
        
        if not all_assigned_courses:
             flash(f"You are not currently assigned to any courses. (Checked 'assisting_teacher' column for username: '{teacher_username}').", "warning")
             # Still render the page, JS will show "No subjects"
             
    except requests.exceptions.RequestException as e:
        print(f"Error fetching courses for teacher {teacher_username}: {e}")
        flash("Error loading your assigned courses.", "danger")
        # Render the page anyway, JS will handle empty list
    except ValueError as e:
        # This catches get_supabase_rest_url error if COURSE_TABLE is not allowed
        print(f"Configuration error: {e}")
        flash("Server configuration error trying to access courses.", "danger")
        return redirect(url_for('index'))

    # Render the actual template, passing in all the data the JS needs
    return render_template(
        "teacher_attendance.html",
        user=user,
        supabase_url=SUPABASE_URL,
        supabase_key=SUPABASE_ANON_KEY,
        # Pass the lists as JSON strings for the template to safely embed
        all_assigned_courses_json=json.dumps(all_assigned_courses),
        attendance_tables_json=json.dumps(ATTENDANCE_TABLES) 
    )

@app.route("/teacher/marks")
@login_required(role='teacher')
def enter_marks_page():
    """
    Renders the teacher marks entry page.
    Fetches courses assigned to the logged-in teacher.
    """
    user = session.get('user')
    teacher_username = user.get('username') 

    if not teacher_username:
        flash("Could not identify teacher username. Please log in again.", "danger")
        return redirect(url_for('login_page'))

    all_assigned_courses = []
    try:
        # Fetch courses assigned to this teacher from the 'courses' table
        url = get_supabase_rest_url(COURSE_TABLE)
        # MODIFICATION: Added 'credits' to the select query
        params = {'select': 'course_code,course_name,semester,credits', 'assisting_teacher': f'eq.{teacher_username}'}
        response = requests.get(url, headers=SUPABASE_HEADERS, params=params, timeout=10)
        response.raise_for_status()
        all_assigned_courses = response.json()
        
        if not all_assigned_courses:
             flash(f"You are not currently assigned to any courses. (Checked 'assisting_teacher' column for username: '{teacher_username}').", "warning")
             
    except requests.exceptions.RequestException as e:
        print(f"Error fetching courses for teacher {teacher_username}: {e}")
        flash("Error loading your assigned courses.", "danger")
    except ValueError as e:
        print(f"Configuration error: {e}")
        flash("Server configuration error trying to access courses.", "danger")
        return redirect(url_for('index'))

    # Render the new marks template
    return render_template(
        "teacher_marks.html", # <-- New Template
        user=user,
        supabase_url=SUPABASE_URL,
        supabase_key=SUPABASE_ANON_KEY,
        # Pass the lists as JSON strings for the template to safely embed
        all_assigned_courses_json=json.dumps(all_assigned_courses),
        marks_tables_json=json.dumps(MARKS_TABLES) # <-- Pass MARKS_TABLES
    )

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

@app.route("/admin/dashboard")
@login_required(role='admin')
def admin_dashboard():
    """Renders the admin-specific dashboard."""
    user = session.get('user')
    return render_template("admin_dashboard.html", user=user)


# --- Placeholder Routes for Teacher/Admin Actions (Kept) ---
# ... (your other admin routes like /admin/attendance follow)

@app.route("/admin/users")
@login_required(role='admin')
def manage_users_page():
     flash("User management not yet implemented.", "info")
     return redirect(url_for('index'))

# --- START: COURSE MANAGEMENT ROUTES ---

@app.route("/admin/courses")
@login_required(role='admin')
def manage_courses_page():
    """Renders the course management page with a list of courses."""
    courses = []
    all_teachers = fetch_all_teachers()
    
    # --- NEW: Search Logic ---
    search_params = {
        'select': '*',
        'order': 'semester.asc,course_name.asc'
    }
    # Get search terms from query string (e.g., /admin/courses?search_name=Intro)
    search_code = request.args.get('search_code', '').strip()
    search_name = request.args.get('search_name', '').strip()
    search_teacher = request.args.get('search_teacher', '').strip()
    search_semester = request.args.get('search_semester', '').strip()

    # Add filters to params if they exist
    # 'ilike' is case-insensitive 'like' (partial match)
    if search_code:
        search_params['course_code'] = f'ilike.%{search_code}%'
    if search_name:
        search_params['course_name'] = f'ilike.%{search_name}%'
    if search_teacher:
        search_params['assisting_teacher'] = f'ilike.%{search_teacher}%'
    if search_semester:
        search_params['semester'] = f'eq.{search_semester}' # 'eq' is exact match

    try:
        url = get_supabase_rest_url(COURSE_TABLE)
        
        # Use the built 'search_params' dictionary
        response = requests.get(url, headers=SUPABASE_HEADERS, params=search_params, timeout=10)
        response.raise_for_status() 
        
        courses = response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching courses: {e}")
        flash("Could not load courses from the database.", "danger")
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for('admin_dashboard'))
        
    # Pass 'request.args' to the template to pre-fill search fields
    return render_template("manage_courses.html", courses=courses, search_params=request.args,all_teachers=all_teachers)


@app.route('/admin/courses/add', methods=['POST'])
@login_required(role='admin')
def add_course():
    """Handles the form submission for adding a new course."""
    if request.method == 'POST':
        # Get data from form
        course_code = request.form.get('course_code', "").strip().upper()
        course_name = request.form.get('course_name', "").strip()
        assisting_teacher = request.form.get('assisting_teacher', "").strip()
        credits = request.form.get('credits')
        semester = request.form.get('semester')

        # Basic validation
        if not all([course_code, course_name, credits, semester]):
            flash('Course Code, Name, Credits, and Semester are required.', 'danger')
            return redirect(url_for('manage_courses_page'))

        new_course_data = {
            "course_code": course_code,
            "course_name": course_name,
            "assisting_teacher": assisting_teacher if assisting_teacher else None,
            "credits": int(credits),
            "semester": int(semester)
        }

        try:
            url = get_supabase_rest_url(COURSE_TABLE)
            headers = SUPABASE_HEADERS.copy()
            headers['Prefer'] = 'return=minimal'
            
            response = requests.post(url, headers=headers, json=new_course_data, timeout=10)
            response.raise_for_status()

            if response.status_code == 201:
                flash(f'Course "{course_name}" added successfully!', 'success')
            else:
                flash(f'Received unexpected status: {response.status_code}', 'warning')

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:
                flash(f'Error: Course code "{course_code}" already exists.', 'danger')
            else:
                error_details = e.response.json().get('message', 'Unknown error')
                flash(f'Error adding course: {error_details}', 'danger')
                print(f"Supabase add course error: {e.response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error inserting course: {e}")
            flash("Adding course failed due to a network or server error.", "danger")
        except ValueError as e:
            flash(str(e), "danger") 
        except Exception as e:
            print(f"Unexpected error adding course: {e}")
            flash("An unexpected error occurred.", "danger")

    return redirect(url_for('manage_courses_page'))


@app.route('/admin/courses/delete/<string:course_code>', methods=['POST'])
@login_required(role='admin')
def delete_course(course_code):
    """Handles the POST request to delete a course."""
    if request.method == 'POST':
        try:
            url = get_supabase_rest_url(COURSE_TABLE)
            params = {'course_code': f'eq.{course_code}'}
            
            headers = SUPABASE_HEADERS.copy()
            headers['Prefer'] = 'return=minimal'

            response = requests.delete(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            flash(f'Course "{course_code}" deleted successfully.', 'success')

        except requests.exceptions.RequestException as e:
            print(f"Error deleting course: {e}")
            flash("Deleting course failed due to a network or server error.", "danger")
        except ValueError as e:
            flash(str(e), "danger")
        except Exception as e:
            print(f"Unexpected error deleting course: {e}")
            flash("An unexpected error occurred.", "danger")

    return redirect(url_for('manage_courses_page'))


# --- NEW: EDIT AND UPDATE ROUTES ---

@app.route('/admin/courses/edit/<string:course_code>')
@login_required(role='admin')
def edit_course_page(course_code):
    """Shows the form to edit a specific course."""
    course = None
    all_teachers = fetch_all_teachers()
    try:
        url = get_supabase_rest_url(COURSE_TABLE)
        # Select the specific course by its code
        params = {'select': '*', 'course_code': f'eq.{course_code}'}
        
        response = requests.get(url, headers=SUPABASE_HEADERS, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data and len(data) == 1:
            course = data[0]
            return render_template("edit_course.html", course=course,all_teachers=all_teachers)
        else:
            flash(f"Course '{course_code}' not found.", 'danger')
            return redirect(url_for('manage_courses_page'))

    except requests.exceptions.RequestException as e:
        print(f"Error fetching course {course_code}: {e}")
        flash("Could not load course data for editing.", "danger")
        return redirect(url_for('manage_courses_page'))
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for('manage_courses_page'))


@app.route('/admin/courses/update', methods=['POST'])
@login_required(role='admin')
def update_course():
    """Handles the form submission for updating an existing course."""
    if request.method == 'POST':
        # Get data from form
        course_code = request.form.get('course_code') # From hidden input
        course_name = request.form.get('course_name', "").strip()
        assisting_teacher = request.form.get('assisting_teacher', "").strip()
        credits = request.form.get('credits')
        semester = request.form.get('semester')

        if not all([course_code, course_name, credits, semester]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('edit_course_page', course_code=course_code))

        # Data to update
        update_data = {
            "course_name": course_name,
            "assisting_teacher": assisting_teacher if assisting_teacher else None,
            "credits": int(credits),
            "semester": int(semester)
        }

        try:
            url = get_supabase_rest_url(COURSE_TABLE)
            # Use params to specify WHICH row to update
            params = {'course_code': f'eq.{course_code}'}
            
            headers = SUPABASE_HEADERS.copy()
            headers['Prefer'] = 'return=minimal'

            # Send a PATCH request with the update_data
            response = requests.patch(url, headers=headers, params=params, json=update_data, timeout=10)
            response.raise_for_status()

            flash(f'Course "{course_name}" updated successfully!', 'success')
            return redirect(url_for('manage_courses_page'))

        except requests.exceptions.RequestException as e:
            print(f"Error updating course: {e}")
            flash("Updating course failed due to a network or server error.", 'danger')
        except ValueError as e:
            flash(str(e), "danger")
        except Exception as e:
            print(f"Unexpected error updating course: {e}")
            flash("An unexpected error occurred.", 'danger')

        # If anything fails, redirect back to the edit page
        return redirect(url_for('edit_course_page', course_code=course_code))

    return redirect(url_for('manage_courses_page'))


# --- END: COURSE MANAGEMENT ROUTES ---

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

