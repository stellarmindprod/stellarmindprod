import json
import requests
from flask import Flask, request, jsonify, render_template, redirect, url_for
from config import SUPABASE_URL, SUPABASE_HEADERS, STUDENT_TABLES, TEACHER_TABLE, ADMIN_TABLE

# Initialize Flask App
app = Flask(__name__)

# --- Helper Function for Supabase Query ---
def fetch_user_from_table(table_name, username, password):
    """Queries a specific Supabase table for a user match."""
    # Ensure the table name is safe before using it in the URL
    if table_name not in STUDENT_TABLES + [TEACHER_TABLE, ADMIN_TABLE]:
        return None

    # Construct the base URL for the table
    url = f"{SUPABASE_URL}/rest/v1/{table_name}"
    
    # We query for the user by roll_no/username.
    # We MUST perform the password check server-side for security.
    # The columns for roll number/username and password vary by table type.
    
    select_columns = "*"
    if table_name in STUDENT_TABLES:
        username_column = "roll_no"
        password_column = "student_password"
    elif table_name == TEACHER_TABLE:
        username_column = "username"
        password_column = "teacher_password"
    elif table_name == ADMIN_TABLE:
        username_column = "username"
        password_column = "password"
    else:
        return None

    # Supabase filter parameters (check username)
    params = {
        'select': select_columns,
        username_column: f'eq.{username.lower()}' # Ensure case insensitivity by converting username to lower
    }

    try:
        response = requests.get(url, headers=SUPABASE_HEADERS, params=params)
        response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        # Check if exactly one record was found and if the password matches
        if data and len(data) == 1:
            user_data = data[0]
            
            # **IMPORTANT SECURITY NOTE**: In a real app, passwords must be securely HASHED (e.g., using bcrypt)
            # and never stored in plain text. This simple check is for demonstration based on the provided schema.
            # If the Supabase tables store plain text (as implied by the old JS logic), this check works:
            if user_data.get(password_column) == password:
                # Remove the sensitive password before returning the data
                user_data.pop(password_column, None) 
                return user_data

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Supabase or processing request for table {table_name}: {e}")
        # Log the error but continue to next table check
        pass
    except json.JSONDecodeError:
        print(f"Failed to decode JSON response from Supabase for table {table_name}")
        pass

    return None

# --- Flask Routes ---

@app.route("/")
@app.route("/login")
def login_page():
    """Renders the login HTML page."""
    return render_template("login.html")

@app.route("/api/login", methods=["POST"])
def api_login():
    """Handles the secure server-side authentication."""
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required"}), 400

    # 1. Try Student Tables (b1, b2, b3, b4)
    for table_name in STUDENT_TABLES:
        user_data = fetch_user_from_table(table_name, username, password)
        if user_data:
            # Add role and class/batch information before returning
            user_data['role'] = 'student'
            user_data['batch'] = table_name
            return jsonify({"success": True, "user": user_data}), 200

    # 2. Try Teacher Table
    teacher_data = fetch_user_from_table(TEACHER_TABLE, username, password)
    if teacher_data:
        teacher_data['role'] = 'teacher'
        return jsonify({"success": True, "user": teacher_data}), 200
    
    # 3. Try Admin Table
    admin_data = fetch_user_from_table(ADMIN_TABLE, username, password)
    if admin_data:
        admin_data['role'] = 'admin'
        return jsonify({"success": True, "user": admin_data}), 200


    # If no match found after all checks
    return jsonify({"success": False, "message": "Invalid credentials"}), 401


if __name__ == "__main__":
    # In a production environment, use a WSGI server like Gunicorn
    app.run(debug=True, port=5000)
