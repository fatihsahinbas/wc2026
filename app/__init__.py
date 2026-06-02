from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect
import os

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "1019add9c072a2951927d8cb5ab15a68370a94c34740e28e")

    db_url = os.getenv("DATABASE_URL", "sqlite:///wc2026.db")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["WTF_CSRF_ENABLED"] = True
    app.config["ADMIN_USERNAME"] = os.getenv("ADMIN_USERNAME", "admin")

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Bu sayfayı görmek için giriş yapmalısınız."
    login_manager.login_message_category = "warning"

    from .blueprints.auth import auth_bp
    from .blueprints.groups import groups_bp
    from .blueprints.matches import matches_bp
    from .blueprints.admin import admin_bp
    from .blueprints.api import api_bp
    from .blueprints.fixtures import fixtures_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(matches_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    app.register_blueprint(fixtures_bp)

    with app.app_context():
        db.create_all()
        try:
            db.session.execute(db.text(
                "ALTER TABLE matches ADD COLUMN api_match_id VARCHAR(32) UNIQUE"
            ))
            db.session.commit()
        except Exception:
            db.session.rollback()
        _seed_admin(app)

    return app


def _seed_admin(app):
    from .models import User

    admin_username = app.config["ADMIN_USERNAME"]
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

    existing = User.query.filter_by(username=admin_username).first()
    if not existing:
        admin = User(
            username=admin_username,
            email="admin@worldcup2026.local",
            is_admin=True,
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        print(f"[SEED] Admin kullanıcısı oluşturuldu: {admin_username}")