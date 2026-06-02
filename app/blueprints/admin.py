from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from ..models import Match, User, Group, Prediction,ActivityLog
from ..forms import MatchResultForm
from ..scoring import recalculate_match_predictions
from .. import db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ── Dashboard ─────────────────────────────────────────────────────────────────
@admin_bp.route("/")
@login_required
@admin_required
def dashboard():
    stats = {
        "users": User.query.count(),
        "groups": Group.query.count(),
        "matches": Match.query.count(),
        "predictions": Prediction.query.count(),
        "finished_matches": Match.query.filter_by(is_finished=True).count(),
    }
    upcoming = (
        Match.query.filter_by(is_finished=False)
        .order_by(Match.start_time)
        .limit(5)
        .all()
    )
    return render_template("admin/dashboard.html", stats=stats, upcoming=upcoming, title="Admin Panel")


# ── Maç Listesi ───────────────────────────────────────────────────────────────
@admin_bp.route("/matches")
@login_required
@admin_required
def matches():
    all_matches = Match.query.order_by(Match.start_time).all()
    return render_template("admin/matches.html", matches=all_matches, title="Maç Yönetimi")


# ── Maç Oluştur ───────────────────────────────────────────────────────────────
@admin_bp.route("/matches/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_match():
    if request.method == "POST":
        try:
            start_time = datetime.strptime(
                request.form["start_time"], "%Y-%m-%dT%H:%M"
            )
            match = Match(
                home_team=request.form["home_team"].strip(),
                away_team=request.form["away_team"].strip(),
                stage=request.form.get("stage", "Group Stage"),
                venue=request.form.get("venue", "").strip(),
                start_time=start_time,
            )
            db.session.add(match)
            db.session.commit()
            flash(f"Maç eklendi: {match.home_team} vs {match.away_team}", "success")
            return redirect(url_for("admin.matches"))
        except Exception as e:
            flash(f"Hata: {e}", "danger")

    return render_template("admin/create_match.html", title="Yeni Maç")


# ── Maç Sonucu Gir ────────────────────────────────────────────────────────────
@admin_bp.route("/matches/<int:match_id>/result", methods=["GET", "POST"])
@login_required
@admin_required
def match_result(match_id):
    match = db.get_or_404(Match, match_id)
    form = MatchResultForm(obj=match)

    if form.validate_on_submit():
        match.home_score = form.home_score.data
        match.away_score = form.away_score.data
        match.is_finished = True
        db.session.commit()

        # Puanları hemen hesapla
        result = recalculate_match_predictions(match)
        flash(
            f"Sonuç kaydedildi: {match.home_score}-{match.away_score}. "
            f"{result['processed']} tahmin güncellendi, "
            f"{result['correct']} doğru tahmin.",
            "success",
        )
        return redirect(url_for("admin.matches"))

    return render_template(
        "admin/match_result.html", match=match, form=form, title="Sonuç Gir"
    )


# ── Kullanıcı Listesi ─────────────────────────────────────────────────────────
@admin_bp.route("/users")
@login_required
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users, title="Kullanıcılar")

@admin_bp.route("/logs")
@login_required
@admin_required
def logs():
    page = request.args.get("page", 1, type=int)
    logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    return render_template("admin/logs.html", logs=logs, title="Aktivite Logları")