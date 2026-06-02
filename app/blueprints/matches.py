from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from ..models import Match, Prediction
from ..forms import PredictionForm
from .. import db

matches_bp = Blueprint("matches", __name__, url_prefix="/matches")


@matches_bp.route("/")
@login_required
def index():
    matches = Match.query.order_by(Match.start_time).all()
    # Kullanıcının mevcut tahminlerini dict olarak hazırla
    user_preds = {
        p.match_id: p
        for p in current_user.predictions.all()
    }
    return render_template(
        "matches/index.html",
        matches=matches,
        user_preds=user_preds,
        now=datetime.now(timezone.utc),
        title="Maçlar",
    )


@matches_bp.route("/<int:match_id>")
@login_required
def detail(match_id):
    match = db.get_or_404(Match, match_id)
    user_pred = current_user.predictions.filter_by(match_id=match_id).first()
    form = PredictionForm(match_id=match_id)
    all_preds = match.predictions.all() if current_user.is_admin else []
    return render_template(
        "matches/detail.html",
        match=match,
        user_pred=user_pred,
        form=form,
        all_preds=all_preds,
        now=datetime.now(timezone.utc),
        title=f"{match.home_team} vs {match.away_team}",
    )


@matches_bp.route("/<int:match_id>/predict", methods=["POST"])
@login_required
def predict(match_id):
    match = db.get_or_404(Match, match_id)

    # Maç başlamış mı?
    now = datetime.now(timezone.utc)
    match_start = match.start_time.replace(tzinfo=timezone.utc)
    if now >= match_start:
        flash("Bu maç için tahmin süresi doldu.", "danger")
        return redirect(url_for("matches.detail", match_id=match_id))

    if match.is_finished:
        flash("Maç tamamlandı, tahmin yapılamaz.", "danger")
        return redirect(url_for("matches.detail", match_id=match_id))

    form = PredictionForm()
    if form.validate_on_submit():
        valid_outcomes = {"home", "draw", "away"}
        if form.predicted_outcome.data not in valid_outcomes:
            abort(400)

        pred = current_user.predictions.filter_by(match_id=match_id).first()
        if pred:
            pred.predicted_outcome = form.predicted_outcome.data
            flash("Tahmininiz güncellendi.", "success")
        else:
            pred = Prediction(
                user_id=current_user.id,
                match_id=match_id,
                predicted_outcome=form.predicted_outcome.data,
            )
            db.session.add(pred)
            flash("Tahmininiz kaydedildi! 🎯", "success")

        db.session.commit()

    return redirect(url_for("matches.index"))
