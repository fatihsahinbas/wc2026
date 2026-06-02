"""
Seed Script — WC2026
Çalıştırma: python seed.py
10 kullanıcı, 1 grup, 8 maç oluşturur.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

# Proje kökünü path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("SECRET_KEY", "seed-secret")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "X1ece979!1")

from app import create_app, db
from app.models import User, Group, Match, Prediction, group_members

app = create_app()

USERS = [
    ("emre",   "emre@worldcup.com",   "emre1234!!"),
    ("erdem",    "fatma@worldcup.com",    "erdem1234!"),
    ("ahmet",    "ahmet@worldcup.com",    "ahmet1234!"),
    ("erdinc",     "erdinc@worldcup.com",     "erdinc1234!"),
    ("fatih",  "fatih@worldcup.com",  "fatih1234!"),
    ("fuat",   "fuat@worldcup.com",   "fuat1234!"),
    ("mustafa",  "mustafa@worldcup.com",  "mustafa1234!"),
    ("alper",   "alper@worldcup.com",   "alper1234!"),
    ("yildirim",      "yildirim@worldcup.com", "yildirim1234!"),
]

MATCHES = [
    ("Türkiye",  "Brezilya",   "Group Stage", "MetLife Stadium, New York",       3),
    ("Almanya",  "Fransa",     "Group Stage", "SoFi Stadium, Los Angeles",       4),
    ("Arjantin", "İngiltere",  "Group Stage", "AT&T Stadium, Dallas",            5),
    ("İspanya",  "Portekiz",   "Group Stage", "Hard Rock Stadium, Miami",        6),
    ("Japonya",  "Hollanda",   "Group Stage", "Levi's Stadium, San Francisco",   7),
    ("Meksika",  "Uruguay",    "Group Stage", "Estadio Azteca, Mexico City",     8),
    ("Türkiye",  "Arjantin",   "Round of 16", "MetLife Stadium, New York",       30),
    ("Almanya",  "İspanya",    "Quarter-final","SoFi Stadium, Los Angeles",      37),
]

OUTCOMES = ["home", "draw", "away", "home", "away", "draw", "home", "draw"]


def seed():
    with app.app_context():
        print("🌱 Seed başlıyor...")

        # Admin zaten create edildi, diğer kullanıcıları ekle
        created_users = []
        for username, email, password in USERS:
            u = User.query.filter_by(username=username).first()
            if not u:
                u = User(username=username, email=email)
                u.set_password(password)
                db.session.add(u)
                print(f"  ➕ Kullanıcı: {username}")
            created_users.append(u)
        db.session.commit()

        # Grup oluştur
        group = Group.query.filter_by(name="WC2026 Ana Liga").first()
        if not group:
            admin = User.query.filter_by(username="admin").first()
            group = Group(
                name="WorldCup 2026 Ana Liga",
                description="10 kişilik ana tahmin grubu",
                invite_code="WORLDCUP2026MAIN",
                owner_id=admin.id,
            )
            group.members.append(admin)
            for u in created_users:
                group.members.append(u)
            db.session.add(group)
            db.session.commit()
            print(f"  ➕ Grup: {group.name} (davet kodu: {group.invite_code})")

        # Maçları oluştur
        now = datetime.now(timezone.utc)
        created_matches = []
        for i, (home, away, stage, venue, days_offset) in enumerate(MATCHES):
            m = Match.query.filter_by(home_team=home, away_team=away).first()
            if not m:
                m = Match(
                    home_team=home,
                    away_team=away,
                    stage=stage,
                    venue=venue,
                    start_time=now + timedelta(days=days_offset),
                )
                db.session.add(m)
                print(f"  ➕ Maç: {home} vs {away}")
            created_matches.append(m)
        db.session.commit()

        # Kullanıcılara tahminler ekle (ilk 5 maç için)
        for user in created_users[:8]:
            for i, match in enumerate(created_matches[:5]):
                existing = Prediction.query.filter_by(
                    user_id=user.id, match_id=match.id
                ).first()
                if not existing:
                    outcome = OUTCOMES[i % len(OUTCOMES)]
                    pred = Prediction(
                        user_id=user.id,
                        match_id=match.id,
                        predicted_outcome=outcome,
                    )
                    db.session.add(pred)
        db.session.commit()

        # İlk 2 maçı bitmiş olarak işaretle ve puan hesapla
        from app.scoring import recalculate_match_predictions
        match_results = [
            (created_matches[0], 2, 1),  # Türkiye 2-1 Brezilya (home kazanır)
            (created_matches[1], 1, 1),  # Almanya 1-1 Fransa (draw)
        ]
        for match, hs, as_ in match_results:
            if not match.is_finished:
                match.home_score = hs
                match.away_score = as_
                match.is_finished = True
                db.session.commit()
                result = recalculate_match_predictions(match)
                print(f"  ✅ {match.home_team} {hs}-{as_} {match.away_team} → {result['correct']} doğru tahmin puanlandı")

        print("\n✅ Seed tamamlandı!")
        print(f"   Admin giriş: admin / Admin2026!")
        print(f"   Test kullanıcı: mehmet / Test1234!")
        print(f"   Grup davet kodu: WC2026MAIN")


if __name__ == "__main__":
    seed()
