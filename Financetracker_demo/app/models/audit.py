from app.extensions import db
from app.models.base import utcnow

EVENT_REGISTER = "register"
EVENT_LOGIN_SUCCESS = "login_success"
EVENT_LOGIN_FAILED = "login_failed"
EVENT_LOGIN_LOCKED = "login_locked"
EVENT_OTP_ISSUED = "otp_issued"
EVENT_OTP_FAILED = "otp_failed"
EVENT_OTP_VERIFIED = "otp_verified"
EVENT_LOGOUT = "logout"
EVENT_PASSWORD_CHANGED = "password_changed"
EVENT_PROFILE_UPDATED = "profile_updated"
EVENT_SESSION_REVOKED = "session_revoked"
EVENT_SESSION_EXPIRED = "session_expired"
EVENT_ACCESS_DENIED = "access_denied"

EVENT_LABELS = {
    EVENT_REGISTER: "Account created",
    EVENT_LOGIN_SUCCESS: "Signed in",
    EVENT_LOGIN_FAILED: "Failed sign-in attempt",
    EVENT_LOGIN_LOCKED: "Account locked",
    EVENT_OTP_ISSUED: "Verification code sent",
    EVENT_OTP_FAILED: "Wrong verification code",
    EVENT_OTP_VERIFIED: "Verification code accepted",
    EVENT_LOGOUT: "Signed out",
    EVENT_PASSWORD_CHANGED: "Password changed",
    EVENT_PROFILE_UPDATED: "Profile updated",
    EVENT_SESSION_REVOKED: "Session revoked",
    EVENT_SESSION_EXPIRED: "Session expired",
    EVENT_ACCESS_DENIED: "Access denied",
}


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)

    event = db.Column(db.String(40), nullable=False, index=True)
    detail = db.Column(db.String(255))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)

    user = db.relationship(
        "User",
        backref=db.backref("audit_logs", lazy="dynamic", cascade="all, delete-orphan"),
    )

    @property
    def label(self):
        return EVENT_LABELS.get(self.event, self.event)

    @property
    def is_warning(self):
        return self.event in (
            EVENT_LOGIN_FAILED,
            EVENT_LOGIN_LOCKED,
            EVENT_OTP_FAILED,
            EVENT_ACCESS_DENIED,
        )

    def __repr__(self):
        return f"<AuditLog {self.event} user={self.user_id}>"
