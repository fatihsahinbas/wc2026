"""
WC2026 — Test Suite
Çalıştırma: pytest tests/ -v
"""
import pytest
import os
from datetime import datetime, timedelta, timezone

os.environ["SECRET_KEY"] = "test-secret"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "AdminTest123!"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"


@pytest.fixture
def app():
    from app import create_app, db as _db
    application = create_app()
    application.config["TESTING"] = True
    application.config["WTF_CSRF_ENABLED"] = False

    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    from app import db as _db
    return _db


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def regular_user(db):
    from app.models import User
    u = User(username="testuser", email="test@test.com")
    u.set_password("TestPass123!")
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def sample_match(db):
    from app.models import Match
    m = Match(
        home_team="Türkiye",
        away_team="Almanya",
        stage="Group Stage",
        start_time=datetime.now(timezone.utc) + timedelta(hours=2),
    )
    db.session.add(m)
    db.session.commit()
    return m


@pytest.fixture
def finished_match(db):
    from app.models import Match
    m = Match(
        home_team="Fransa",
        away_team="İspanya",
        stage="Group Stage",
        start_time=datetime.now(timezone.utc) - timedelta(hours=3),
        is_finished=True,
        home_score=2,
        away_score=1,
    )
    db.session.add(m)
    db.session.commit()
    return m


# ── Birim Testleri ────────────────────────────────────────────────────────────

class TestScoring:
    def test_correct_home_prediction_gives_3_points(self):
        from app.scoring import calculate_points
        assert calculate_points("home", "home") == 3

    def test_correct_draw_prediction_gives_3_points(self):
        from app.scoring import calculate_points
        assert calculate_points("draw", "draw") == 3

    def test_correct_away_prediction_gives_3_points(self):
        from app.scoring import calculate_points
        assert calculate_points("away", "away") == 3

    def test_wrong_prediction_gives_0_points(self):
        from app.scoring import calculate_points
        assert calculate_points("home", "away") == 0
        assert calculate_points("draw", "home") == 0
        assert calculate_points("away", "draw") == 0

    def test_recalculate_updates_all_predictions(self, app, db, regular_user, finished_match):
        from app.models import Prediction
        from app.scoring import recalculate_match_predictions

        # Doğru tahmin (home wins 2-1)
        pred1 = Prediction(
            user_id=regular_user.id,
            match_id=finished_match.id,
            predicted_outcome="home",
        )
        db.session.add(pred1)
        db.session.commit()

        result = recalculate_match_predictions(finished_match)
        assert result["processed"] == 1
        assert result["correct"] == 1
        assert pred1.points == 3

    def test_recalculate_wrong_prediction(self, app, db, regular_user, finished_match):
        from app.models import Prediction
        from app.scoring import recalculate_match_predictions

        pred = Prediction(
            user_id=regular_user.id,
            match_id=finished_match.id,
            predicted_outcome="away",  # Yanlış (home kazandı 2-1)
        )
        db.session.add(pred)
        db.session.commit()

        result = recalculate_match_predictions(finished_match)
        assert pred.points == 0
        assert result["correct"] == 0


class TestUserModel:
    def test_password_hashing(self, app, db, regular_user):
        assert regular_user.check_password("TestPass123!") is True
        assert regular_user.check_password("wrong") is False
        assert regular_user.password_hash != "TestPass123!"

    def test_match_outcome_property(self, app, db, finished_match):
        assert finished_match.result_outcome == "home"

    def test_draw_outcome_property(self, app, db):
        from app.models import Match
        m = Match(
            home_team="A", away_team="B",
            start_time=datetime.now(timezone.utc),
            is_finished=True, home_score=1, away_score=1
        )
        db.session.add(m)
        db.session.commit()
        assert m.result_outcome == "draw"


# ── Entegrasyon Testleri ──────────────────────────────────────────────────────

class TestAuthRoutes:
    def test_register_new_user(self, client):
        resp = client.post("/auth/register", data={
            "username": "yenikullanici",
            "email": "yeni@test.com",
            "password": "Sifre1234!",
            "confirm_password": "Sifre1234!",
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_login_valid_credentials(self, client, app, db, regular_user):
        resp = client.post("/auth/login", data={
            "username": "testuser",
            "password": "TestPass123!",
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_login_invalid_credentials(self, client):
        resp = client.post("/auth/login", data={
            "username": "nobody",
            "password": "wrong",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert "hatalı".encode() in resp.data or b"hatal" in resp.data

    def test_protected_route_redirects_anonymous(self, client):
        resp = client.get("/matches/")
        assert resp.status_code == 302
        assert "/auth/login" in resp.headers["Location"]


class TestMatchPrediction:
    def test_prediction_logic_direct(self, app, db, regular_user, sample_match):
        """Tahmin mantığını doğrudan model üzerinde test et."""
        from app.models import Prediction
        from datetime import datetime, timezone

        # Maç açık mı kontrol et
        assert sample_match.is_open_for_prediction is True

        pred = Prediction(
            user_id=regular_user.id,
            match_id=sample_match.id,
            predicted_outcome="home",
        )
        db.session.add(pred)
        db.session.commit()

        fetched = Prediction.query.filter_by(
            user_id=regular_user.id, match_id=sample_match.id
        ).first()
        assert fetched is not None
        assert fetched.predicted_outcome == "home"

    def test_prediction_blocked_on_finished_match_logic(self, app, db, finished_match):
        """Biten maçın is_open_for_prediction=False olduğunu doğrula."""
        assert finished_match.is_open_for_prediction is False

    def test_update_prediction(self, app, db, regular_user, sample_match):
        """Mevcut tahmini güncelleme mantığı."""
        from app.models import Prediction

        pred = Prediction(
            user_id=regular_user.id,
            match_id=sample_match.id,
            predicted_outcome="home",
        )
        db.session.add(pred)
        db.session.commit()

        pred.predicted_outcome = "draw"
        db.session.commit()

        updated = Prediction.query.filter_by(
            user_id=regular_user.id, match_id=sample_match.id
        ).first()
        assert updated.predicted_outcome == "draw"


class TestAdminRoutes:
    def _login_admin(self, client):
        client.post("/auth/login", data={
            "username": "admin",
            "password": "AdminTest123!",
        })

    def test_admin_dashboard_accessible(self, client, app):
        self._login_admin(client)
        resp = client.get("/admin/")
        assert resp.status_code == 200

    def test_non_admin_blocked(self, client, app, db, regular_user):
        client.post("/auth/login", data={
            "username": "testuser",
            "password": "TestPass123!",
        })
        resp = client.get("/admin/")
        assert resp.status_code == 403
