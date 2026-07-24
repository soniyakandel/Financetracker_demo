from datetime import timedelta

from flask import current_app
from flask_login import UserMixin

from app.extensions import db, login_manager
from app.models.base import utcnow
from app.security.passwords import hash_password, verify_password


class User(UserMixin, db.Model):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    is_active_account = db.Column(db.Boolean, default=True, nullable=False)
    is_locked = db.Column(db.Boolean, default=False, nullable=False)
    failed_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    password_changed_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def set_password(self, plain_password):
        self.password_hash = hash_password(plain_password)
        self.password_changed_at = utcnow()

    def check_password(self, plain_password):
        return verify_password(self.password_hash, plain_password)

    def lock(self):
        minutes = current_app.config["LOCKOUT_MINUTES"]
        self.is_locked = True
        self.locked_until = utcnow() + timedelta(minutes=minutes)

    def unlock(self):
        self.is_locked = False
        self.locked_until = None
        self.failed_attempts = 0

    @property
    def is_currently_locked(self):
        if not self.is_locked:
            return False
        if self.locked_until and utcnow() >= self.locked_until:
            return False
        return True

    @property
    def is_active(self):
        return self.is_active_account and not self.is_currently_locked

    def __repr__(self):
        return f"<User {self.email}>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
