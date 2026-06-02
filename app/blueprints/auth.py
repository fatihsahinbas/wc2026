from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from ..models import User
from ..forms import RegistrationForm, LoginForm
from .. import db
import os

from ..models import ActivityLog

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

def _registration_open():
    return os.getenv("REGISTRATION_OPEN", "false").lower() == "true"


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if not _registration_open():
        flash("Kayıt şu an kapalıdır.", "warning")
        return redirect(url_for("auth.login"))
    if current_user.is_authenticated:
        return redirect(url_for("matches.index"))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Kayıt başarılı! Giriş yapabilirsiniz.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form, title="Kayıt Ol")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("matches.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=True)
            log = ActivityLog(user_id=user.id, username=user.username,
                  action="Giriş yaptı",
                  ip_address=request.remote_addr)
            db.session.add(log)
            db.session.commit()
            next_page = request.args.get("next")
            flash(f"Hoş geldin, {user.username}! 🏆", "success")
            return redirect(next_page or url_for("matches.index"))
        flash("Kullanıcı adı veya parola hatalı.", "danger")

    return render_template("auth/login.html", form=form, title="Giriş Yap")


@auth_bp.route("/logout")
@login_required
def logout():
    log = ActivityLog(user_id=current_user.id, username=current_user.username,
                    action="Çıkış yaptı",
                    ip_address=request.remote_addr)
    db.session.add(log)
    db.session.commit()    
    logout_user()
    flash("Çıkış yapıldı.", "info")
    return redirect(url_for("auth.login"))

@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if not current_user.check_password(current_password):
            flash("Mevcut parolanız hatalı.", "danger")
        elif len(new_password) < 8:
            flash("Yeni parola en az 8 karakter olmalı.", "danger")
        elif new_password != confirm_password:
            flash("Yeni parolalar eşleşmiyor.", "danger")
        else:
            current_user.set_password(new_password)
            db.session.commit()
            flash("Parolanız başarıyla değiştirildi.", "success")
            return redirect(url_for("matches.index"))

    return render_template("auth/change_password.html", title="Parola Değiştir")