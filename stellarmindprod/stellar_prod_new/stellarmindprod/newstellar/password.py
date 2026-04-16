# hash_password.py
from werkzeug.security import generate_password_hash
import getpass # Use getpass to hide password input

def create_hash():
    """Generates a password hash using Werkzeug."""
    try:
        # Prompt for password securely (hides input)
        password = getpass.getpass("Enter the password to hash: ")
        confirm_password = getpass.getpass("Confirm the password: ")

        if not password:
            print("\nError: Password cannot be empty.")
            return

        if password != confirm_password:
            print("\nError: Passwords do not match.")
            return

        # Generate the hash using the recommended method
        # pbkdf2:sha256 is the default and is secure
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        print("\n--- Password Hash ---")
        print("Copy the entire line below and paste it into your Supabase password column:")
        print(hashed_password)
        print("---------------------\n")

    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    create_hash()
