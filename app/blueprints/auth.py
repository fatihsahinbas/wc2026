from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from ..models import User
from ..forms import RegistrationForm, LoginForm
from .. import db

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
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
            next_page = request.args.get("next")
            flash(f"Hoş geldin, {user.username}! 🏆", "success")
            return redirect(next_page or url_for("matches.index"))
        flash("Kullanıcı adı veya parola hatalı.", "danger")

    return render_template("auth/login.html", form=form, title="Giriş Yap")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Çıkış yapıldı.", "info")
    return redirect(url_for("auth.login"))
