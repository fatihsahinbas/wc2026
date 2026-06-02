"""
REST API v1 — JSON Endpoint'leri
=================================
Tüm endpoint'ler JSON döner.
Kimlik doğrulama: session cookie (aynı oturum) veya ileride JWT eklenebilir.
"""
from datetime import datetime, timezone
from functools import wraps
from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user
from ..models import Match, Group, Prediction, User
from ..scoring import recalculate_match_predictions
from .. import db

api_bp = Blueprint("api", __name__)


def admin_required_api(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({"error": "Admin yetkisi gerekli."}), 403
        return f(*args, **kwargs)
    return decorated


# ── Maçlar ────────────────────────────────────────────────────────────────────
@api_bp.route("/matches", methods=["GET"])
@login_required
def api_matches():
    matches = Match.query.order_by(Match.start_time).all()
    return jsonify([
        {
            "id": m.id,
            "home_team": m.home_team,
            "away_team": m.away_team,
            "stage": m.stage,
            "venue": m.venue,
            "start_time": m.start_time.isoformat(),
            "is_finished": m.is_finished,
            "home_score": m.home_score,
            "away_score": m.away_score,
            "result_outcome": m.result_outcome,
        }
        for m in matches
    ])


# ── Tahmin ────────────────────────────────────────────────────────────────────
@api_bp.route("/matches/<int:match_id>/predict", methods=["POST"])
@login_required
def api_predict(match_id):
    match = db.get_or_404(Match, match_id)
    now = datetime.now(timezone.utc)
    if now >= match.start_time.replace(tzinfo=timezone.utc):
        return jsonify({"error": "Tahmin süresi doldu."}), 400
    if match.is_finished:
        return jsonify({"error": "Maç tamamlandı."}), 400

    data = request.get_json(silent=True) or {}
    outcome = data.get("predicted_outcome")
    if outcome not in ("home", "draw", "away"):
        return jsonify({"error": "Geçersiz outcome. 'home', 'draw', 'away' olmalı."}), 400

    pred = current_user.predictions.filter_by(match_id=match_id).first()
    if pred:
        pred.predicted_outcome = outcome
    else:
        pred = Prediction(user_id=current_user.id, match_id=match_id, predicted_outcome=outcome)
        db.session.add(pred)
    db.session.commit()

    return jsonify({
        "message": "Tahmin kaydedildi.",
        "match_id": match_id,
        "predicted_outcome": outcome,
    }), 200


# ── Admin: Maç Sonucu ─────────────────────────────────────────────────────────
@api_bp.route("/admin/matches/<int:match_id>/result", methods=["POST"])
@login_required
@admin_required_api
def api_match_result(match_id):
    match = db.get_or_404(Match, match_id)
    data = request.get_json(silent=True) or {}
    home_score = data.get("home_score")
    away_score = data.get("away_score")

    if home_score is None or away_score is None:
        return jsonify({"error": "home_score ve away_score gerekli."}), 400

    match.home_score = int(home_score)
    match.away_score = int(away_score)
    match.is_finished = True
    db.session.commit()

    result = recalculate_match_predictions(match)
    return jsonify({
        "message": "Sonuç kaydedildi ve puanlar hesaplandı.",
        **result,
    }), 200


# ── Grup Sıralaması ───────────────────────────────────────────────────────────
@api_bp.route("/groups/<int:group_id>/leaderboard", methods=["GET"])
@login_required
def api_leaderboard(group_id):
    group = db.get_or_404(Group, group_id)
    board = group.leaderboard()
    return jsonify({
        "group_id": group.id,
        "group_name": group.name,
        "leaderboard": [
            {
                "rank": i + 1,
                "username": entry["user"].username,
                "points": entry["points"],
            }
            for i, entry in enumerate(board)
        ],
    })


# ── Kullanıcı Profili ─────────────────────────────────────────────────────────
@api_bp.route("/me", methods=["GET"])
@login_required
def api_me():
    preds = current_user.predictions.all()
    return jsonify({
        "id": current_user.id,
        "username": current_user.username,
        "total_points": sum(p.points for p in preds if p.points is not None),
        "total_predictions": len(preds),
        "correct_predictions": sum(1 for p in preds if p.points == 3),
    })
