from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from . import db, login_manager

# ── Association table: user <-> group ────────────────────────────────────────
group_members = db.Table(
    "group_members",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("group_id", db.Integer, db.ForeignKey("groups.id"), primary_key=True),
    db.Column("joined_at", db.DateTime, default=lambda: datetime.now(timezone.utc)),
)


# ── User ─────────────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    predictions = db.relationship("Prediction", back_populates="user", lazy="dynamic")
    groups = db.relationship(
        "Group", secondary=group_members, back_populates="members", lazy="dynamic"
    )
    owned_groups = db.relationship("Group", back_populates="owner", lazy="dynamic",
                                   foreign_keys="Group.owner_id")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def total_points(self, group_id: int | None = None) -> int:
        q = self.predictions.filter(Prediction.points.isnot(None))
        if group_id:
            q = q.join(Match).filter(Match.id.isnot(None))
        return sum(p.points for p in q.all())

    def __repr__(self):
        return f"<User {self.username}>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ── Group ─────────────────────────────────────────────────────────────────────
class Group(db.Model):
    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(300))
    invite_code = db.Column(db.String(16), unique=True, nullable=False, index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    owner = db.relationship("User", back_populates="owned_groups",
                            foreign_keys=[owner_id])
    members = db.relationship(
        "User", secondary=group_members, back_populates="groups", lazy="dynamic"
    )

    def member_count(self) -> int:
        return self.members.count()

    def leaderboard(self) -> list[dict]:
        """Gruba üye kullanıcıları toplam puana göre sıralı döndür."""
        results = []
        for user in self.members.all():
            pts = sum(
                p.points for p in user.predictions.filter(Prediction.points.isnot(None)).all()
            )
            results.append({"user": user, "points": pts})
        return sorted(results, key=lambda x: x["points"], reverse=True)

    def __repr__(self):
        return f"<Group {self.name}>"


# ── Match ─────────────────────────────────────────────────────────────────────
class Match(db.Model):
    __tablename__ = "matches"

    id = db.Column(db.Integer, primary_key=True)
    home_team = db.Column(db.String(60), nullable=False)
    away_team = db.Column(db.String(60), nullable=False)
    stage = db.Column(db.String(40), nullable=False, default="Group Stage")
    venue = db.Column(db.String(100))
    start_time = db.Column(db.DateTime, nullable=False)

    # Sonuç alanları (admin girer)
    home_score = db.Column(db.Integer)
    away_score = db.Column(db.Integer)
    is_finished = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    predictions = db.relationship("Prediction", back_populates="match", lazy="dynamic")

    @property
    def result_outcome(self) -> str | None:
        """'home' | 'draw' | 'away' | None"""
        if self.home_score is None or self.away_score is None:
            return None
        if self.home_score > self.away_score:
            return "home"
        if self.home_score < self.away_score:
            return "away"
        return "draw"

    @property
    def is_open_for_prediction(self) -> bool:
        return not self.is_finished and datetime.now(timezone.utc) < self.start_time.replace(
            tzinfo=timezone.utc
        )

    def __repr__(self):
        return f"<Match {self.home_team} vs {self.away_team}>"


# ── Prediction ────────────────────────────────────────────────────────────────
class Prediction(db.Model):
    __tablename__ = "predictions"
    __table_args__ = (
        db.UniqueConstraint("user_id", "match_id", name="uq_user_match"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=False)

    # Kullanıcının tahmin ettiği sonuç
    predicted_outcome = db.Column(db.String(10), nullable=False)  # 'home'|'draw'|'away'

    points = db.Column(db.Integer)  # None = henüz hesaplanmadı
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = db.relationship("User", back_populates="predictions")
    match = db.relationship("Match", back_populates="predictions")

    def __repr__(self):
        return f"<Prediction user={self.user_id} match={self.match_id} {self.predicted_outcome}>"
