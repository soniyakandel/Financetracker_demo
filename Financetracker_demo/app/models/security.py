import hashlib
import secrets
from datetime import timedelta

from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.base import utcnow


class LoginAttempt(db.Model):

    __tablename__ = "login_attempts"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    ip_address = db.Column(db.String(45))
    success = db.Column(db.Boolean, default=False, nullable=False)
    attempted_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    @classmethod
    def record(cls, email, ip_address, success):
        db.session.add(
            cls(email=(email or "").lower(), ip_address=ip_address, success=success)
        )

    @classmethod
    def recent_failures(cls, email, minutes):
        since = utcnow() - timedelta(minutes=minutes)
        return cls.query.filter(
            cls.email == (email or "").lower(),
            cls.success.is_(False),
            cls.attempted_at >= since,
        ).count()


class OtpCode(db.Model):

    __tablename__ = "otp_codes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    code_hash = db.Column(db.String(255), nullable=False)
    purpose = db.Column(db.String(30), default="login", nullable=False)

    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    attempts = db.Column(db.Integer, default=0, nullable=False)

    user = db.relationship("User", backref=db.backref("otp_codes", lazy="dynamic"))

    @classmethod
    def issue(cls, user, purpose="login"):
        minutes = current_app.config["OTP_VALID_MINUTES"]
        plain = f"{secrets.randbelow(1_000_000):06d}"
        record = cls(
            user_id=user.id,
            code_hash=generate_password_hash(plain),
            purpose=purpose,
            expires_at=utcnow() + timedelta(minutes=minutes),
        )
        db.session.add(record)
        return record, plain

    @property
    def is_expired(self):
        return utcnow() > self.expires_at

    @property
    def is_usable(self):
        max_attempts = current_app.config["OTP_MAX_ATTEMPTS"]
        return not self.used and not self.is_expired and self.attempts < max_attempts

    def verify(self, plain_code):
        usable = self.is_usable
        self.attempts += 1
        if not usable:
            return False
        if check_password_hash(self.code_hash, (plain_code or "").strip()):
            self.used = True
            return True
        return False

    @classmethod
    def invalidate_all_for(cls, user):
        return cls.query.filter_by(user_id=user.id, used=False).update({"used": True})


class PasswordResetToken(db.Model):

    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)

    requested_ip = db.Column(db.String(45))

    user = db.relationship(
        "User",
        backref=db.backref(
            "reset_tokens", lazy="dynamic", cascade="all, delete-orphan"
        ),
    )

    @staticmethod
    def digest(plain_token):
        return hashlib.sha256((plain_token or "").encode("utf-8")).hexdigest()

    @classmethod
    def issue(cls, user, ip_address=None):
        minutes = current_app.config["PASSWORD_RESET_VALID_MINUTES"]
        plain = secrets.token_urlsafe(32)
        record = cls(
            user_id=user.id,
            token_hash=cls.digest(plain),
            expires_at=utcnow() + timedelta(minutes=minutes),
            requested_ip=ip_address,
        )
        db.session.add(record)
        return record, plain

    @classmethod
    def lookup(cls, plain_token):
        if not plain_token:
            return None
        record = cls.query.filter_by(token_hash=cls.digest(plain_token)).first()
        if record is None or not record.is_usable:
            return None
        return record

    @classmethod
    def invalidate_all_for(cls, user):
        return cls.query.filter_by(user_id=user.id, used=False).update(
            {"used": True, "used_at": utcnow()}
        )

    @property
    def is_expired(self):
        return utcnow() > self.expires_at

    @property
    def is_usable(self):
        return not self.used and not self.is_expired

    def consume(self):
        self.used = True
        self.used_at = utcnow()
