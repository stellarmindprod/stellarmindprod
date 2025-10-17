# Supabase Configuration
# IMPORTANT: These fields have been updated with your live Supabase credentials.
# It is highly recommended to use environment variables in a real production environment.
SUPABASE_URL = "https://xhemdlzqermutpdqetkz.supabase.co" # 💡 Find this in Supabase -> Settings -> API
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhoZW1kbHpxZXJtdXRwZHFldGt6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA2MTQ2NjAsImV4cCI6MjA3NjE5MDY2MH0.VBdCOBCHcSkfe88g-QKxUuh-Tn3x1AIwM2xJvHxstoY" # 💡 Find this in Supabase -> Settings -> API

# Database Table Names
# These lists define which tables the Flask app checks for user logins.
STUDENT_TABLES = ["b1", "b2", "b3", "b4"]
TEACHER_TABLE = "teachers"
# Assuming you have an 'admins' table for administrative users
ADMIN_TABLE = "admins"

# Headers for Supabase REST API calls
SUPABASE_HEADERS = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json"
}
