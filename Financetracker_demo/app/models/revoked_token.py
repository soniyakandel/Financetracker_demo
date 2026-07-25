from datetime import datetime, timezone

from app.extensions import db
from app.models.base import utcnow


class RevokedToken(db.Model):
    __tablename__ = "revoked_tokens"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(32), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    @classmethod
    def revoke(cls, payload):
        if cls.query.filter_by(jti=payload["jti"]).first():
            return
        db.session.add(
            cls(
                jti=payload["jti"],
                user_id=int(payload["sub"]),
                expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc).replace(tzinfo=None),
            )
        )

    @classmethod
    def is_revoked(cls, jti):
        return cls.query.filter_by(jti=jti).first() is not None

    @classmethod
    def purge_expired(cls):
        cls.query.filter(cls.expires_at < utcnow()).delete()
