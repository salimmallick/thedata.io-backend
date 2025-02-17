from passlib.context import CryptContext

# Use the same password hashing context as in the API
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Generate hash for the password "admin"
password = "admin"
hashed_password = pwd_context.hash(password)
print(f"Password hash for '{password}': {hashed_password}") 