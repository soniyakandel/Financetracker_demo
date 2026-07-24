import secrets
from datetime import timedelta

from flask import current_app

from app.extensions import db
from app.models.base import utcnow


class UserSession(db.Model):
    __tablename__ = "user_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    session_token = db.Column(db.String(64), unique=True, nullable=False, index=True)

    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    last_seen_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)
    revoked_reason = db.Column(db.String(50), nullable=True)

    user = db.relationship(
        "User",
        backref=db.backref("sessions", lazy="dynamic", cascade="all, delete-orphan"),
    )

    @classmethod
    def start(cls, user, ip_address, user_agent):
        hours = current_app.config["SESSION_ABSOLUTE_HOURS"]
        record = cls(
            user_id=user.id,
            session_token=secrets.token_hex(32),
            ip_address=ip_address,
            user_agent=(user_agent or "")[:255],
            expires_at=utcnow() + timedelta(hours=hours),
        )
        db.session.add(record)
        return record

    @property
    def is_idle_expired(self):
        minutes = current_app.config["SESSION_IDLE_MINUTES"]
        return utcnow() > self.last_seen_at + timedelta(minutes=minutes)

    @property
    def is_absolute_expired(self):
        return utcnow() > self.expires_at

    @property
    def is_valid(self):
        return (
            self.is_active
            and not self.is_idle_expired
            and not self.is_absolute_expired
        )

    def touch(self):
        self.last_seen_at = utcnow()

    def revoke(self, reason="logout"):
        self.is_active = False
        self.revoked_at = utcnow()
        self.revoked_reason = reason

    @property
    def device_label(self):
        agent = self.user_agent or ""
        browser = "Unknown browser"
        for name in ("Edg", "Chrome", "Firefox", "Safari"):
            if name in agent:
                browser = "Edge" if name == "Edg" else name
                break
        platform = "Unknown device"
        for token, label in (
            ("Windows", "Windows"),
            ("Mac", "macOS"),
            ("Android", "Android"),
            ("iPhone", "iPhone"),
            ("iPad", "iPad"),
            ("Linux", "Linux"),
        ):
            if token in agent:
                platform = label
                break
        return f"{browser} on {platform}"

    def __repr__(self):
        return f"<UserSession user={self.user_id} active={self.is_active}>"
