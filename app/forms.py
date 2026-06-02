from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField,
    TextAreaField, SelectField, HiddenField, IntegerField
)
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo,
    ValidationError, NumberRange, Optional
)
from .models import User, Group


class RegistrationForm(FlaskForm):
    username = StringField(
        "Kullanıcı Adı",
        validators=[DataRequired(), Length(min=3, max=64)],
    )
    email = StringField("E-posta", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField(
        "Parola",
        validators=[DataRequired(), Length(min=8, message="En az 8 karakter olmalı.")],
    )
    confirm_password = PasswordField(
        "Parolayı Onayla",
        validators=[DataRequired(), EqualTo("password", message="Parolalar eşleşmiyor.")],
    )
    submit = SubmitField("Kayıt Ol")

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError("Bu kullanıcı adı zaten alınmış.")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError("Bu e-posta zaten kayıtlı.")


class LoginForm(FlaskForm):
    username = StringField("Kullanıcı Adı", validators=[DataRequired()])
    password = PasswordField("Parola", validators=[DataRequired()])
    submit = SubmitField("Giriş Yap")


class GroupCreateForm(FlaskForm):
    name = StringField("Grup Adı", validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField("Açıklama", validators=[Optional(), Length(max=300)])
    submit = SubmitField("Grubu Oluştur")

    def validate_name(self, field):
        if Group.query.filter_by(name=field.data).first():
            raise ValidationError("Bu grup adı zaten kullanılıyor.")


class JoinGroupForm(FlaskForm):
    invite_code = StringField(
        "Davet Kodu",
        validators=[DataRequired(), Length(min=6, max=16)],
    )
    submit = SubmitField("Gruba Katıl")


class PredictionForm(FlaskForm):
    match_id = HiddenField(validators=[DataRequired()])
    predicted_outcome = SelectField(
        "Tahmininiz",
        choices=[
            ("home", "Ev Sahibi Kazanır"),
            ("draw", "Beraberlik"),
            ("away", "Deplasman Kazanır"),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField("Tahmini Kaydet")


class MatchResultForm(FlaskForm):
    home_score = IntegerField(
        "Ev Sahibi Gol",
        validators=[DataRequired(), NumberRange(min=0, max=30)],
    )
    away_score = IntegerField(
        "Deplasman Gol",
        validators=[DataRequired(), NumberRange(min=0, max=30)],
    )
    submit = SubmitField("Sonucu Kaydet ve Puanları Hesapla")
