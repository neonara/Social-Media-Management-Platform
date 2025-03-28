import string
import random
from typing import Optional

def generate_strong_password(length: int = 12) -> str:
    """
    Generate a strong password with at least one of each:
    - Uppercase letter
    - Lowercase letter
    - Number
    - Special character
    
    Args:
        length (int): Length of password (minimum 12)
    
    Returns:
        str: Generated password
    """
    if length < 12:
        length = 12

    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    symbols = "!@#$%^&*()_+-=[]{}|"

    # Ensure at least one of each type
    password = [
        random.choice(lowercase),
        random.choice(uppercase),
        random.choice(digits),
        random.choice(symbols)
    ]

    # Fill the rest randomly
    remaining_length = length - len(password)
    all_characters = lowercase + uppercase + digits + symbols
    password.extend(random.choice(all_characters) for _ in range(remaining_length))

    # Shuffle the password
    random.shuffle(password)
    return ''.join(password)

def validate_password_strength(password: str) -> Optional[str]:
    """
    Validate password strength requirements.
    
    Args:
        password (str): Password to validate
    
    Returns:
        Optional[str]: Error message if password is invalid, None if valid
    """
    if len(password) < 12:
        return "Password must be at least 12 characters long"
    
    if not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return "Password must contain at least one number"
    
    if not any(c in string.punctuation for c in password):
        return "Password must contain at least one special character"
    
    return None