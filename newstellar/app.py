# stellarminprod/app.py

import requests
import json
import datetime # Import datetime
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Import configuration variables
from config import (
    SUPABASE_URL, SUPABASE_HEADERS, STUDENT_TABLES, TEACHER_TABLE, ADMIN_TABLE,
    MARKS_TABLES, SECRET_KEY, GRADES_TABLE, EVENTS_TABLE, HOLIDAYS_TABLE,
    ATTENDANCE_TABLES, SUPABASE_ANON_KEY, COURSE_TABLE,TIMETABLE_TABLE
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
        COURSE_TABLE, TIMETABLE_TABLE # Added COURSE_TABLE
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

# --- START NEW HELPER ---
def get_current_semester(student_batch, current_month):
    """Determines the student's current semester based on batch and month."""
    
    # Logic: b25 -> Year 1 (b1), b24 -> Year 2 (b2), etc.
    year_map = {
        'b1': 1,  # Corresponds to b25
        'b2': 2,  # Corresponds to b24
        'b3': 3,  # Corresponds to b23
        'b4': 4   # Corresponds to b22
    }
    student_year = year_map.get(student_batch)
    if not student_year:
        return None

    # Assuming July-December is ODD semester, Jan-June is EVEN semester
    # Adjust this logic if your academic calendar is different
    if 7 <= current_month <= 12: # July to Dec -> Odd Sem
        return student_year * 2 - 1 # Year 1 -> Sem 1, Year 2 -> Sem 3
    else: # Jan to June -> Even Sem
        return student_year * 2 # Year 1 -> Sem 2, Year 2 -> Sem 4
# --- END NEW HELPER ---

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

# --- Authentication Logic (MODIFIED) ---

def fetch_and_verify_user(username, password):
    """Finds user across tables and verifies password."""
    # Assume username could be roll_no (student), username (teacher/admin), or email (parent/student)
    username_lower = username.lower() 

    # 1. Try Student Tables (by roll_no)
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
                # Check password
                if check_password_hash(user_data.get('student_password', ''), password):
                    user_data.pop('student_password', None) # Remove hash from session data
                    user_data.pop('parent_password', None)
                    user_data['role'] = 'student'
                    user_data['batch'] = batch_table 
                    user_data['roll_no'] = user_data.get('roll_no', username_lower) # Ensure roll_no is set
                    return user_data
        except Exception as e:
            print(f"Error querying {batch_table} by roll_no: {e}")

    # 2. Try Teacher Table (by username)
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

    # 3. Try Admin Table (by username)
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

    # 4. --- NEW: Try Parent Login (by parent_email) ---
    # This will check b1, b2, b3, b4 for a matching parent_email
    for batch_table in STUDENT_TABLES:
        try:
            url = get_supabase_rest_url(batch_table)
            # Query by parent_email (which is what the parent enters as 'username')
            params = {'select': '*,parent_password,roll_no,student_name', 'parent_email': f'eq.{username_lower}'}
            response = requests.get(url, headers=SUPABASE_HEADERS, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data and len(data) == 1:
                parent_data = data[0]
                # Verify the parent_password
                # THIS ASSUMES parent_password IS HASHED in the database
                if check_password_hash(parent_data.get('parent_password', ''), password):
                    # Create a session object for the parent
                    user_data = {
                        'role': 'parent',
                        'parent_email': parent_data['parent_email'],
                        'student_roll_no': parent_data['roll_no'],
                        'student_name': parent_data['student_name'],
                        'batch': batch_table # Store which batch table the student is in
                    }
                    return user_data
        except Exception as e:
            print(f"Error querying {batch_table} for parent: {e}")
            
    # 5. --- NEW: Try Student Login by Email ---
    # This allows students to log in with email OR roll_no
    for batch_table in STUDENT_TABLES:
        try:
            url = get_supabase_rest_url(batch_table)
            params = {'select': '*,student_password,roll_no', 'student_email': f'eq.{username_lower}'}
            response = requests.get(url, headers=SUPABASE_HEADERS, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data and len(data) == 1:
                user_data = data[0]
                if check_password_hash(user_data.get('student_password', ''), password):
                    user_data.pop('student_password', None)
                    user_data.pop('parent_password', None)
                    user_data['role'] = 'student'
                    user_data['batch'] = batch_table
                    user_data['roll_no'] = user_data.get('roll_no')
                    return user_data
        except Exception as e:
            print(f"Error querying {batch_table} by student_email: {e}")


    return None # No user found or password incorrect

# --- Flask Routes ---

# Hardcoded Timetable (as from your JS)
# This should ideally be moved to the database


@app.route("/")
@login_required() # User must be logged in to see the dashboard
def index():
    """Renders the main combined dashboard."""
    user = session['user']
    
    # --- NEW: Redirect parents away from the main index ---
    if user.get('role') == 'parent':
        return redirect(url_for('parent_dashboard'))
    # --- End of New Redirect ---
    
    events_data = []
    holidays_data = []
    daily_schedule = []
    today_is_holiday = False
    
    # Get today's date info (assuming server is in same timezone as users or UTC)
    IST = ZoneInfo("Asia/Kolkata")
    today = datetime.datetime.now(IST) 
    today_str = today.strftime('%a').upper() # MON, TUE...
    today_date_str = today.strftime('%Y-%m-%d') # 2025-10-25
    current_month = today.month

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
        if today_str in ["SAT", "SUN"] and not today_is_holiday:
            # We'll let the DB query handle if there are Sat/Sun classes
            pass 

        if not today_is_holiday:
            student_batch = user.get('batch') # e.g., 'b2'
            # Use the new helper function
            current_semester = get_current_semester(student_batch, current_month)
            
            if current_semester:
                try:
                    url_tt = get_supabase_rest_url(TIMETABLE_TABLE)
                    # Use Supabase join to fetch course name/code from 'courses' table
                    params_tt = {
                        'select': 'start_time,end_time,venue,subject_code,courses(course_name,course_code)',
                        'semester': f'eq.{current_semester}',
                        'day_of_week': f'eq.{today_str}',
                        'order': 'start_time.asc'
                    }
                    response_tt = requests.get(url_tt, headers=SUPABASE_HEADERS, params=params_tt, timeout=5)
                    response_tt.raise_for_status()
                    
                    fetched_entries = response_tt.json()
                    
                    # Format the fetched data for the dashboard
                    for entry in fetched_entries:
                        course_details = "Free Period" # Default
                        if entry.get('courses'): # 'courses' will be non-null if subject_code matched
                            course_name = entry['courses']['course_name']
                            course_code = entry['courses']['course_code']
                            course_details = f"{course_name} ({course_code})"
                        elif entry.get('subject_code'): # Fallback if join fails but code exists
                             course_details = entry.get('subject_code')

                        venue = entry.get('venue') or 'N/A'
                        schedule_str = f"{entry['start_time']} - {entry['end_time']} → {course_details} ({venue})"
                        daily_schedule.append(schedule_str)
                
                except Exception as e:
                    print(f"Error fetching timetable from DB: {e}")
                    flash("Could not load today's schedule.", "warning")
            
            else:
                print(f"Could not determine current semester for batch {student_batch}")
    
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
        # Changed 'username' to 'email_or_username' for clarity
        email_or_username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip() 

        if not email_or_username or not password:
            flash("Username/Email and password are required.", "danger")
            return render_template("login.html")

        # Pass the email or username to the verification function
        user_data = fetch_and_verify_user(email_or_username, password)

        if user_data:
            session['user'] = user_data # Store user data in session
            
            # Determine display name
            display_name = "User"
            if user_data.get('role') == 'parent':
                display_name = f"Parent of {user_data.get('student_name', 'Student')}"
            else:
                display_name = (user_data.get('student_name') or
                                user_data.get('teacher_name') or
                                user_data.get('username', 'User'))

            flash(f"Welcome back, {display_name}!", "success")
            
            # --- START OF MODIFICATION ---
            # Check the user's role and redirect accordingly
            role = user_data.get('role')
            if role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif role == 'parent':
                return redirect(url_for('parent_dashboard')) # <-- NEW PARENT REDIRECT
            else:
                # This covers 'student' and 'teacher'
                return redirect(url_for('index'))
            # --- END OF MODIFICATION ---

        else:
            flash("Invalid credentials. Please try again.", "danger")
            return render_template("login.html"), 401

    # If GET request
    if 'user' in session:
        # --- MODIFICATION: Redirect logged-in parents to their dashboard ---
        if session['user'].get('role') == 'parent':
            return redirect(url_for('parent_dashboard'))
        return redirect(url_for('index')) # Redirect other logged-in users to main dashboard
    
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

        # --- NEW: Parent fields ---
        parent_email = request.form.get("parent_email", "").strip().lower()
        parent_password = request.form.get("parent_password", "").strip()
        
        # Basic validation
        if not all([roll_no, student_name, student_email, password, confirm_password, parent_email, parent_password]):
            flash("All fields (including parent details) are required.", "danger")
            return render_template("signup.html")
        if password != confirm_password:
            flash("Student passwords do not match.", "danger")
            return render_template("signup.html")
        if len(password) < 8:
            flash("Student password must be at least 8 characters long.", "danger")
            return render_template("signup.html")
        if len(parent_password) < 8:
            flash("Parent password must be at least 8 characters long.", "danger")
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
            params_check_parent_email = {'select': 'parent_email', 'parent_email': f'eq.{parent_email}'}


            response_roll = requests.get(url_check, headers=SUPABASE_HEADERS, params=params_check_roll, timeout=5)
            response_email = requests.get(url_check, headers=SUPABASE_HEADERS, params=params_check_email, timeout=5)
            response_parent_email = requests.get(url_check, headers=SUPABASE_HEADERS, params=params_check_parent_email, timeout=5)


            if response_roll.ok and response_roll.json():
                 flash(f"Roll number '{roll_no}' is already registered.", "danger")
                 return render_template("signup.html")
            if response_email.ok and response_email.json():
                 flash(f"Email '{student_email}' is already registered.", "danger")
                 return render_template("signup.html")
            if response_parent_email.ok and response_parent_email.json():
                 flash(f"Parent Email '{parent_email}' is already registered.", "danger")
                 return render_template("signup.html")

        except requests.exceptions.RequestException as e:
            print(f"Error checking existing user: {e}")
            flash("Could not verify user existence. Please try again.", "warning")
            return render_template("signup.html")
        except ValueError as e:
            flash(str(e), "danger")
            return render_template("signup.html")

        # Hash both passwords
        hashed_student_password = generate_password_hash(password)
        hashed_parent_password = generate_password_hash(parent_password)


        new_student_data = {
            "roll_no": roll_no,
            "student_name": student_name,
            "student_email": student_email,
            "student_password": hashed_student_password, # Store the HASH
            "parent_email": parent_email,
            "parent_password": hashed_parent_password # Store the HASH
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

# --- NEW PARENT DASHBOARD ROUTE ---
@app.route("/parent/dashboard")
@login_required(role='parent')
def parent_dashboard():
    """Renders the parent dashboard."""
    user = session.get('user') # This user is the parent
    
    student_roll_no = user.get('student_roll_no')
    student_name = user.get('student_name')
    batch_table = user.get('batch') # e.g., 'b1'

    if not all([student_roll_no, student_name, batch_table]):
        flash("Could not identify student information. Please log in again.", "danger")
        return redirect(url_for('login_page'))
        
    # Determine the correct tables for this student
    attendance_table = determine_attendance_table(batch_table)
    marks_table = get_marks_table_for_student(student_roll_no) # Use roll_no for this one

    if not attendance_table or not marks_table:
        flash("Could not find student records.", "warning")
        return redirect(url_for('index'))

    # Pass all necessary info to the template for JS fetching
    return render_template(
        "parent_dashboard.html",
        user=user, # Parent's session data
        student_roll_no=student_roll_no,
        student_name=student_name,
        attendance_table=attendance_table,
        marks_table=marks_table,
        supabase_url=SUPABASE_URL,
        supabase_key=SUPABASE_ANON_KEY
    )
# --- END OF NEW PARENT ROUTE ---


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

# --- START: TEACHER MANAGEMENT ROUTES (NEW & CORRECTED) ---
@app.route("/admin/teachers")
@login_required(role='admin')
def manage_teachers_page():
    """Renders the teacher management page with a list of teachers."""
    teachers = []
    
    search_params = {
        'select': 'teacher_id,username,teacher_name,department,teacher_email', # Exclude password
        'order': 'teacher_name.asc'
    }
    
    search_username = request.args.get('search_username', '').strip()
    search_name = request.args.get('search_name', '').strip()

    if search_username:
        search_params['username'] = f'ilike.%{search_username}%'
    if search_name:
        search_params['teacher_name'] = f'ilike.%{search_name}%'

    try:
        url = get_supabase_rest_url(TEACHER_TABLE)
        response = requests.get(url, headers=SUPABASE_HEADERS, params=search_params, timeout=10)
        response.raise_for_status() 
        teachers = response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching teachers: {e}")
        flash("Could not load teachers from the database.", "danger")
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for('admin_dashboard'))
        
    return render_template("manage_teacher.html", teachers=teachers, search_params=request.args)


@app.route('/admin/teachers/add', methods=['POST'])
@login_required(role='admin')
def add_teacher():
    """Handles the form submission for adding a new teacher."""
    if request.method == 'POST':
        username = request.form.get('username', "").strip()
        teacher_name = request.form.get('teacher_name', "").strip()
        department = request.form.get('department', "").strip()
        teacher_email = request.form.get('teacher_email', "").strip().lower()
        
        # Use a default password
        default_password = "password" 

        if not all([username, teacher_name, teacher_email]): 
            flash('Username, Name, and Email are required.', 'danger')
            return redirect(url_for('manage_teachers_page'))
        
        # Hash the default password
        hashed_password = generate_password_hash(default_password)

        new_teacher_data = {
            "username": username,
            "teacher_name": teacher_name,
            "department": department if department else None,
            "teacher_email": teacher_email,
            "teacher_password": hashed_password # Store the hash of the default password
        }

        try:
            url = get_supabase_rest_url(TEACHER_TABLE)
            headers = SUPABASE_HEADERS.copy()
            headers['Prefer'] = 'return=minimal'
            
            response = requests.post(url, headers=headers, json=new_teacher_data, timeout=10)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            # Check status code explicitly after raise_for_status might not be strictly needed,
            # but doesn't hurt for clarity. raise_for_status handles non-2xx codes.
            if response.status_code == 201:
                flash(f'Teacher "{teacher_name}" added successfully with a default password!', 'success')
            else:
                # This part might be less likely reached if raise_for_status is used effectively
                flash(f'Received unexpected status: {response.status_code}', 'warning')
                
        except requests.exceptions.HTTPError as e:
             # Handle specific errors like conflicts (409)
             if e.response.status_code == 409: 
                 error_details = e.response.json().get('message', '')
                 if 'username' in error_details:
                     flash(f'Error: Username "{username}" already exists.', 'danger')
                 elif 'teacher_email' in error_details:
                     flash(f'Error: Email "{teacher_email}" already exists.', 'danger')
                 else:
                     # Generic conflict message if details are unclear
                     flash(f'Error: Username or Email already exists.', 'danger')
             else:
                 # Handle other HTTP errors (like 400 Bad Request, 500 Server Error)
                 error_details = e.response.json().get('message', 'Unknown HTTP error')
                 flash(f'Error adding teacher: {error_details}', 'danger')
                 print(f"Supabase add teacher HTTP error: {e.response.text}")
        except requests.exceptions.RequestException as e:
            # Handle network errors (connection timeout, DNS issues etc.)
            print(f"Error inserting teacher (Network/Request): {e}")
            flash("Adding teacher failed due to a network or server connection error.", "danger")
        except ValueError as e:
            # Handle errors from get_supabase_rest_url (invalid table)
            flash(str(e), "danger") 
        except Exception as e:
            # Catch any other unexpected errors during the process
            print(f"Unexpected error adding teacher: {e}")
            flash("An unexpected error occurred while adding the teacher.", "danger")

    return redirect(url_for('manage_teachers_page'))


@app.route('/admin/teachers/delete/<int:teacher_id>', methods=['POST'])
@login_required(role='admin')
def delete_teacher(teacher_id):
    """Handles the POST request to delete a teacher."""
    if request.method == 'POST':
        try:
            url = get_supabase_rest_url(TEACHER_TABLE)
            params = {'teacher_id': f'eq.{teacher_id}'} # Use teacher_id
            
            headers = SUPABASE_HEADERS.copy()
            headers['Prefer'] = 'return=minimal'

            response = requests.delete(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            # Check if deletion actually happened (optional, Supabase might not return count)
            # You might need to adjust based on actual Supabase behavior or just assume success on 2xx
            flash(f'Teacher deleted successfully.', 'success')

        except requests.exceptions.HTTPError as e:
             # Handle cases where the teacher might not exist (404) or other errors
             error_details = e.response.json().get('message', 'Could not delete teacher')
             flash(f'Error deleting teacher: {error_details}', 'danger')
             print(f"Supabase delete teacher HTTP error: {e.response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error deleting teacher (Network/Request): {e}")
            flash("Deleting teacher failed due to a network or server error.", "danger")
        except ValueError as e:
            flash(str(e), "danger")
        except Exception as e:
            print(f"Unexpected error deleting teacher: {e}")
            flash("An unexpected error occurred while deleting the teacher.", "danger")

    return redirect(url_for('manage_teachers_page'))


@app.route('/admin/teachers/edit/<int:teacher_id>')
@login_required(role='admin')
def edit_teacher_page(teacher_id):
    """Shows the form to edit a specific teacher."""
    teacher = None
    try:
        url = get_supabase_rest_url(TEACHER_TABLE)
        # Select specific fields excluding password
        params = {'select': 'teacher_id,username,teacher_name,department,teacher_email', 'teacher_id': f'eq.{teacher_id}'}
        
        response = requests.get(url, headers=SUPABASE_HEADERS, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data and len(data) == 1:
            teacher = data[0]
            return render_template("edit_teacher.html", teacher=teacher)
        else:
            flash(f"Teacher with ID '{teacher_id}' not found.", 'danger')
            return redirect(url_for('manage_teachers_page'))

    except requests.exceptions.RequestException as e:
        print(f"Error fetching teacher {teacher_id}: {e}")
        flash("Could not load teacher data for editing.", "danger")
        return redirect(url_for('manage_teachers_page'))
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for('manage_teachers_page'))


@app.route('/admin/teachers/update', methods=['POST'])
@login_required(role='admin')
def update_teacher():
    """Handles the form submission for updating an existing teacher."""
    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id')
        teacher_name = request.form.get('teacher_name', "").strip()
        department = request.form.get('department', "").strip()
        teacher_email = request.form.get('teacher_email', "").strip().lower()
        # Password field removed from form data retrieval

        if not all([teacher_id, teacher_name, teacher_email]):
            flash('Name and Email are required.', 'danger')
            # Redirect back to the edit page for the specific teacher
            return redirect(url_for('edit_teacher_page', teacher_id=teacher_id))

        # Data to update, excluding password
        update_data = {
            "teacher_name": teacher_name,
            "department": department if department else None,
            "teacher_email": teacher_email
        }

        # Removed the logic block that checked for and hashed a new password

        try:
            url = get_supabase_rest_url(TEACHER_TABLE)
            params = {'teacher_id': f'eq.{teacher_id}'}
            headers = SUPABASE_HEADERS.copy()
            headers['Prefer'] = 'return=minimal'

            response = requests.patch(url, headers=headers, params=params, json=update_data, timeout=10)
            response.raise_for_status()

            flash(f'Teacher "{teacher_name}" updated successfully!', 'success')
            # Redirect to the main teacher list page after successful update
            return redirect(url_for('manage_teachers_page'))

        except requests.exceptions.HTTPError as e:
             if e.response.status_code == 409: # conflict checking for email uniqueness
                 flash(f'Error: Email "{teacher_email}" is already in use by another teacher.', 'danger')
             else:
                 error_details = e.response.json().get('message', 'Unknown error')
                 flash(f'Error updating teacher: {error_details}', 'danger')
                 print(f"Supabase update teacher HTTP error: {e.response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error updating teacher (Network/Request): {e}")
            flash("Updating teacher failed due to a network or server connection error.", 'danger')
        except ValueError as e: # Catches potential errors from get_supabase_rest_url
            flash(str(e), "danger")
        except Exception as e:
            print(f"Unexpected error updating teacher: {e}")
            flash("An unexpected error occurred while updating the teacher.", 'danger')

        # If any error occurs, redirect back to the edit page for the same teacher
        return redirect(url_for('edit_teacher_page', teacher_id=teacher_id))

    # If not POST, redirect to the main teacher list (though typically accessed via GET on edit_teacher_page)
    return redirect(url_for('manage_teachers_page'))
# --- END: TEACHER MANAGEMENT ROUTES ---


@app.route("/admin/timetable", methods=['GET'])
@login_required(role='admin')
def manage_timetable_page():
    """Renders the main timetable management page."""
    selected_semester = request.args.get('semester', type=int)
    all_courses = []
    timetable_entries = {} # Will be grouped by day

    try:
        # Fetch all courses to populate the "Add Entry" dropdown
        url_courses = get_supabase_rest_url(COURSE_TABLE)
        params_courses = {'select': 'course_code,course_name,semester', 'order': 'semester.asc,course_name.asc'}
        response_courses = requests.get(url_courses, headers=SUPABASE_HEADERS, params=params_courses, timeout=10)
        response_courses.raise_for_status()
        all_courses = response_courses.json()

        if selected_semester:
            # If a semester is selected, fetch its existing timetable
            url_tt = get_supabase_rest_url(TIMETABLE_TABLE)
            # Join with courses table to get subject names
            params_tt = {
                'select': 'id,day_of_week,start_time,end_time,subject_code,venue,courses(course_name)',
                'semester': f'eq.{selected_semester}',
                'order': 'day_of_week.asc,start_time.asc'
            }
            response_tt = requests.get(url_tt, headers=SUPABASE_HEADERS, params=params_tt, timeout=10)
            response_tt.raise_for_status()
            
            # Group the flat list of entries into a dictionary by day
            for entry in response_tt.json():
                day = entry['day_of_week']
                if day not in timetable_entries:
                    timetable_entries[day] = []
                timetable_entries[day].append(entry)

    except Exception as e:
        print(f"Error loading timetable page: {e}")
        flash(f"Error loading data: {e}", "danger")

    return render_template(
        "manage_timetable.html",
        selected_semester=selected_semester,
        all_courses=all_courses,
        timetable_entries=timetable_entries
    )


@app.route("/admin/timetable/add", methods=['POST'])
@login_required(role='admin')
def add_timetable_entry():
    """Handles adding a new timetable entry."""
    semester = request.form.get('semester') # Get semester for redirect
    try:
        day = request.form.get('day_of_week')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        subject_code = request.form.get('subject_code') or None # Use None if empty
        venue = request.form.get('venue') or None

        if not all([semester, day, start_time, end_time]):
            flash("Semester, Day, Start Time, and End Time are required.", "danger")
            return redirect(url_for('manage_timetable_page', semester=semester))

        new_entry = {
            "semester": int(semester),
            "day_of_week": day,
            "start_time": start_time,
            "end_time": end_time,
            "subject_code": subject_code,
            "venue": venue
        }
        
        url = get_supabase_rest_url(TIMETABLE_TABLE)
        headers = SUPABASE_HEADERS.copy()
        headers['Prefer'] = 'return=minimal' # We don't need the data back
        
        response = requests.post(url, headers=headers, json=new_entry, timeout=10)
        response.raise_for_status() # Will error on failure
        
        flash("Timetable entry added successfully!", "success")

    except Exception as e:
        print(f"Error adding timetable entry: {e}")
        flash(f"Error adding entry: {e}", "danger")
    
    return redirect(url_for('manage_timetable_page', semester=semester))


@app.route("/admin/timetable/delete/<int:entry_id>", methods=['POST'])
@login_required(role='admin')
def delete_timetable_entry(entry_id):
    """Handles deleting a timetable entry by its ID."""
    semester = request.form.get('semester') # Get semester from hidden form for redirect
    try:
        url = get_supabase_rest_url(TIMETABLE_TABLE)
        params = {'id': f'eq.{entry_id}'} # Delete where id matches
        headers = SUPABASE_HEADERS.copy()
        headers['Prefer'] = 'return=minimal'
        
        response = requests.delete(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        flash("Entry deleted successfully.", "success")
    
    except Exception as e:
        print(f"Error deleting entry: {e}")
        flash(f"Error deleting entry: {e}", "danger")

    return redirect(url_for('manage_timetable_page', semester=semester))

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
