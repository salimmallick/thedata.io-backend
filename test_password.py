from passlib.context import CryptContext

# Use the same password hashing context as in the API
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Test password
test_password = "test123"

# Generate a new hash
new_hash = pwd_context.hash(test_password)
print(f"Generated hash for '{test_password}': {new_hash}")

# Verify the password against the new hash
result = pwd_context.verify(test_password, new_hash)
print(f"\nVerification test with correct password: {'✅ Matches' if result else '❌ Does not match'}")

# Try wrong password
wrong_password = "wrong123"
result = pwd_context.verify(wrong_password, new_hash)
print(f"Verification test with wrong password: {'✅ Matches' if result else '❌ Does not match'}") 