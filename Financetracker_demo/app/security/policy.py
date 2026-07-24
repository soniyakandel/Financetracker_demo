import re

from wtforms.validators import ValidationError

MIN_LENGTH = 8
MAX_LENGTH = 128

COMMON_PASSWORDS = {
    "password", "password1", "password123", "12345678", "123456789",
    "qwerty123", "letmein1", "welcome1", "admin123", "iloveyou",
    "abc12345", "changeme", "football1", "monkey123", "1q2w3e4r",
}

RULES = [
    f"At least {MIN_LENGTH} characters long",
    "At least one uppercase letter (A-Z)",
    "At least one lowercase letter (a-z)",
    "At least one number (0-9)",
    "At least one symbol (!@#$...)",
]


def check_password_strength(password):
    problems = []
    password = password or ""

    if len(password) < MIN_LENGTH:
        problems.append(f"Password must be at least {MIN_LENGTH} characters long.")
    if len(password) > MAX_LENGTH:
        problems.append(f"Password must be under {MAX_LENGTH} characters.")
    if not re.search(r"[A-Z]", password):
        problems.append("Password must contain an uppercase letter.")
    if not re.search(r"[a-z]", password):
        problems.append("Password must contain a lowercase letter.")
    if not re.search(r"[0-9]", password):
        problems.append("Password must contain a number.")
    if not re.search(r"[^A-Za-z0-9]", password):
        problems.append("Password must contain a symbol.")
    if password.lower() in COMMON_PASSWORDS:
        problems.append("That password is too common. Please pick another one.")

    return problems


def strength_score(password):
    password = password or ""
    score = 0
    if len(password) >= MIN_LENGTH:
        score += 1
    if len(password) >= 12:
        score += 1
    if re.search(r"[A-Z]", password) and re.search(r"[a-z]", password):
        score += 1
    if re.search(r"[0-9]", password) and re.search(r"[^A-Za-z0-9]", password):
        score += 1
    return score


class StrongPassword:

    def __call__(self, form, field):
        problems = check_password_strength(field.data)
        if problems:
            raise ValidationError(problems[0])
