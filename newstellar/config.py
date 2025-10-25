# stellarminprod/config.py

# --- Supabase Configuration ---
# Replace with your NEW Supabase project credentials.
# IMPORTANT: Use environment variables in production!
SUPABASE_URL = "https://xhemdlzqermutpdqetkz.supabase.co" # Your NEW project URL
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhoZW1kbHpxZXJtdXRwZHFldGt6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA2MTQ2NjAsImV4cCI6MjA3NjE5MDY2MH0.VBdCOBCHcSkfe88g-QKxUuh-Tn3x1AIwM2xJvHxstoY" # Your NEW project Anon Key
# It's generally better practice to use the SERVICE_ROLE_KEY for backend operations,
# but using ANON_KEY with appropriate RLS (Row Level Security) is also possible.
# Ensure your RLS policies allow the necessary backend operations.
SUPABASE_SERVICE_KEY = "YOUR_NEW_SUPABASE_SERVICE_ROLE_KEY" # Keep this secret!

# --- Database Table Names (Based on your provided SQL) ---
STUDENT_TABLES = ["b1", "b2", "b3", "b4"]
TEACHER_TABLE = "teachers"
ADMIN_TABLE = "admins" # Assumed table name for administrators
COURSE_TABLE = "courses"
GRADES_TABLE = "grades"
BACKLOG_TABLE = "backlogs"
MARKS_TABLES = ["marks1", "marks2", "marks3", "marks4"]
# Assumed table names based on old project files (add these to your DB)
ATTENDANCE_TABLE = "attendance"
EVENTS_TABLE = "events"
HOLIDAYS_TABLE = "holidays"

# --- Headers for Supabase REST API calls ---
# Using Anon key - ensure RLS is properly configured if using this.
SUPABASE_HEADERS = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation", # Optional: Returns the inserted/updated data
}

# Alternatively, using Service Key (bypasses RLS, use with caution)
# SUPABASE_SERVICE_HEADERS = {
#     "apikey": SUPABASE_SERVICE_KEY,
#     "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
#     "Content-Type": "application/json",
#     "Prefer": "return=representation",
# }

# --- Flask App Configuration ---
SECRET_KEY = "your_very_secret_flask_key_change_this" # Change this for production! Use a strong, random key.
