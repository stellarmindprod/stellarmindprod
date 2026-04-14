# stellarminprod/config.py

# --- Supabase Configuration ---
# Replace with your NEW Supabase project credentials.
# IMPORTANT: Use environment variables in production!
SUPABASE_URL = "https://tydclxmzybbflmgxfpwh.supabase.co" # Your NEW project URL
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR5ZGNseG16eWJiZmxtZ3hmcHdoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU3MjA5MjUsImV4cCI6MjA5MTI5NjkyNX0.ZeEOawsnRhyERWjY9y8u05OvRHaoqqvR7Te0KilcVio" # Your NEW project Anon Key
# It's generally better practice to use the SERVICE_ROLE_KEY for backend operations,
# but using ANON_KEY with appropriate RLS (Row Level Security) is also possible.
# Ensure your RLS policies allow the necessary backend operations.
SUPABASE_SERVICE_KEY = "sb_secret_Ws613bJqEKwJWs_EO2vPmg_vlHTpEIQ" # Keep this secret!

# --- Database Table Names (Based on your provided SQL) ---
STUDENT_TABLES = ["b1", "b2", "b3", "b4"]
TEACHER_TABLE = "teachers"
ADMIN_TABLE = "admin" # Assumed table name for administrators
COURSE_TABLE = "courses"
GRADES_TABLE = "grades"
BACKLOG_TABLE = "backlogs"
MARKS_TABLES = ["marks1", "marks2", "marks3", "marks4"]
ATTENDANCE_TABLES = ["attendance1", "attendance2", "attendance3", "attendance4"] # For batch-specific attendance

# Assumed table names based on old project files (add these to your DB)
ATTENDANCE_TABLE = "attendance" # General/old table, keep for reference or other uses
EVENTS_TABLE = "events"
HOLIDAYS_TABLE = "holidays"
TIMETABLE_TABLE = "timetables"

# --- Notifications Tables ---
NOTIFICATIONS_TABLE = "notifications"
NOTIFICATION_READS_TABLE = "notification_reads"

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
