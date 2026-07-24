from app.extensions import db
from app.models.base import utcnow

DEFAULT_CATEGORIES = [
    ("Food", "🍔", "#ef4444"),
    ("Transport", "🚌", "#f97316"),
    ("Shopping", "🛍️", "#eab308"),
    ("Entertainment", "🎬", "#22c55e"),
    ("Bills & Utilities", "💡", "#14b8a6"),
    ("Health & Medical", "🏥", "#3b82f6"),
    ("Education", "📚", "#6366f1"),
    ("Rent", "🏠", "#a855f7"),
    ("Travel", "✈️", "#ec4899"),
    ("Others", "📌", "#64748b"),
]


class Category(db.Model):

    __tablename__ = "categories"
    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_category_user_name"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    name = db.Column(db.String(50), nullable=False)
    icon = db.Column(db.String(10), default="📌")
    colour = db.Column(db.String(7), default="#64748b")

    is_default = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship(
        "User",
        backref=db.backref("categories", lazy="dynamic", cascade="all, delete-orphan"),
    )

    @classmethod
    def create_defaults_for(cls, user):
        for name, icon, colour in DEFAULT_CATEGORIES:
            db.session.add(
                cls(
                    user_id=user.id,
                    name=name,
                    icon=icon,
                    colour=colour,
                    is_default=True,
                )
            )

    def __repr__(self):
        return f"<Category {self.name}>"
