from werkzeug.security import check_password_hash, generate_password_hash

HASH_METHOD = "pbkdf2:sha256:600000"


def hash_password(plain_password):
    return generate_password_hash(plain_password, method=HASH_METHOD)


def verify_password(password_hash, plain_password):
    if not password_hash or not plain_password:
        return False
    return check_password_hash(password_hash, plain_password)
