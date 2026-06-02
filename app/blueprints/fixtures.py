import os
import requests
from datetime import datetime, timezone
from flask import Blueprint, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from ..models import Match
from .. import db

fixtures_bp = Blueprint("fixtures", __name__, url_prefix="/admin/fixtures")

WC_COMPETITION_ID = "WC"
API_BASE = "https://api.football-data.org/v4"


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Admin yetkisi gerekli.", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def _get_headers():
    return {"X-Auth-Token": os.getenv("FOOTBALL_DATA_API_KEY", "")}


def _parse_datetime(dt_str):
    try:
        return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return datetime.utcnow()


def _map_stage(stage_str):
    mapping = {
        "GROUP_STAGE": "Group Stage",
        "LAST_32": "Round of 32",
        "LAST_16": "Round of 16",
        "QUARTER_FINALS": "Quarter-final",
        "SEMI_FINALS": "Semi-final",
        "THIRD_PLACE": "Third Place",
        "FINAL": "Final",
    }
    return mapping.get(stage_str, stage_str.replace("_", " ").title())


@fixtures_bp.route("/sync")
@login_required
@admin_required
def sync():
    api_key = os.getenv("FOOTBALL_DATA_API_KEY", "")
    if not api_key:
        flash("FOOTBALL_DATA_API_KEY environment variable eksik!", "danger")
        return redirect(url_for("admin.matches"))

    try:
        resp = requests.get(
            f"{API_BASE}/competitions/{WC_COMPETITION_ID}/matches",
            headers=_get_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        flash(f"API bağlantı hatası: {e}", "danger")
        return redirect(url_for("admin.matches"))

    matches_data = data.get("matches", [])
    if not matches_data:
        flash("API'den maç verisi gelmedi.", "warning")
        return redirect(url_for("admin.matches"))

    added = 0
    updated = 0
    scored = 0

    for m in matches_data:
        home = m.get("homeTeam", {}).get("name") or "TBD"
        away = m.get("awayTeam", {}).get("name") or "TBD"
        stage = _map_stage(m.get("stage", "GROUP_STAGE"))
        venue_info = m.get("venue") or ""
        start_time = _parse_datetime(m.get("utcDate", ""))
        api_id = str(m.get("id", ""))

        score = m.get("score", {})
        full_time = score.get("fullTime", {})
        home_score = full_time.get("home")
        away_score = full_time.get("away")
        status = m.get("status", "")
        is_finished = status in ("FINISHED", "AWARDED")

        existing = Match.query.filter_by(api_match_id=api_id).first()

        if existing:
            if is_finished and home_score is not None and not existing.is_finished:
                existing.home_score = home_score
                existing.away_score = away_score
                existing.is_finished = True
                from ..scoring import recalculate_match_predictions
                recalculate_match_predictions(existing)
                scored += 1
            updated += 1
        else:
            new_match = Match(
                home_team=home,
                away_team=away,
                stage=stage,
                venue=venue_info,
                start_time=start_time,
                api_match_id=api_id,
                home_score=home_score if is_finished else None,
                away_score=away_score if is_finished else None,
                is_finished=is_finished,
            )
            db.session.add(new_match)
            added += 1

    db.session.commit()

    flash(
        f"Tamamlandı: {added} yeni maç eklendi, "
        f"{updated} güncellendi, {scored} maç puanlandı.",
        "success",
    )
    return redirect(url_for("admin.matches"))