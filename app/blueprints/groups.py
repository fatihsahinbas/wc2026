import secrets
from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from ..models import Group
from ..forms import GroupCreateForm, JoinGroupForm
from .. import db

groups_bp = Blueprint("groups", __name__, url_prefix="/groups")


@groups_bp.route("/")
@login_required
def index():
    my_groups = current_user.groups.all()
    all_groups = Group.query.order_by(Group.created_at.desc()).all()
    create_form = GroupCreateForm()
    join_form = JoinGroupForm()
    return render_template(
        "groups/index.html",
        my_groups=my_groups,
        all_groups=all_groups,
        create_form=create_form,
        join_form=join_form,
        title="Gruplar",
    )


@groups_bp.route("/create", methods=["POST"])
@login_required
def create():
    form = GroupCreateForm()
    if form.validate_on_submit():
        code = secrets.token_urlsafe(8)[:10].upper()
        group = Group(
            name=form.name.data,
            description=form.description.data,
            invite_code=code,
            owner_id=current_user.id,
        )
        group.members.append(current_user)
        db.session.add(group)
        db.session.commit()
        flash(f'"{group.name}" grubu oluşturuldu. Davet kodu: {code}', "success")
        return redirect(url_for("groups.detail", group_id=group.id))
    flash("Grup oluşturulamadı. Formu kontrol edin.", "danger")
    return redirect(url_for("groups.index"))


@groups_bp.route("/join", methods=["POST"])
@login_required
def join():
    form = JoinGroupForm()
    if form.validate_on_submit():
        group = Group.query.filter_by(invite_code=form.invite_code.data.upper()).first()
        if not group:
            flash("Geçersiz davet kodu.", "danger")
            return redirect(url_for("groups.index"))
        if current_user in group.members.all():
            flash("Zaten bu grubun üyesisiniz.", "info")
            return redirect(url_for("groups.detail", group_id=group.id))
        group.members.append(current_user)
        db.session.commit()
        flash(f'"{group.name}" grubuna katıldınız!', "success")
        return redirect(url_for("groups.detail", group_id=group.id))
    flash("Katılma işlemi başarısız.", "danger")
    return redirect(url_for("groups.index"))


@groups_bp.route("/<int:group_id>")
@login_required
def detail(group_id):
    group = db.get_or_404(Group, group_id)
    if current_user not in group.members.all() and not current_user.is_admin:
        abort(403)
    leaderboard = group.leaderboard()
    return render_template(
        "groups/detail.html",
        group=group,
        leaderboard=leaderboard,
        title=group.name,
    )


@groups_bp.route("/<int:group_id>/leaderboard")
@login_required
def leaderboard(group_id):
    group = db.get_or_404(Group, group_id)
    if current_user not in group.members.all() and not current_user.is_admin:
        abort(403)
    board = group.leaderboard()
    return render_template(
        "groups/leaderboard.html",
        group=group,
        leaderboard=board,
        title=f"{group.name} — Sıralama",
    )
