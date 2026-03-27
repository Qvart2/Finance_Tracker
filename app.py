"""
Финансовый трекер на Flask
Учебный проект, неделя 5-6: Авторизация пользователей
"""

from flask import Flask, render_template, redirect, url_for, request, jsonify
from wtforms import StringField, PasswordField, SubmitField, FloatField, TextAreaField, DateField, SelectField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date

app = Flask(__name__)
app.config["SECRET_KEY"] = "your-secret-key-change-in-production"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///finance.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Пожалуйста, войдите для доступа к странице."


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================


def json_success(message, redirect_url=None):
    """Возвращает JSON-ответ об успехе"""
    response = {"success": True, "message": message}
    if redirect_url:
        response["redirect"] = redirect_url
    return jsonify(response)


def json_error(message, errors=None):
    """Возвращает JSON-ответ об ошибке"""
    response = {"success": False, "message": message}
    if errors:
        response["errors"] = errors
    return jsonify(response), 400


# ==================== МОДЕЛИ ====================


class User(db.Model, UserMixin):
    """Пользователь"""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# ==================== ФОРМЫ ====================


class RegistrationForm(FlaskForm):
    """Форма регистрации"""

    username = StringField(
        "Имя пользователя",
        validators=[
            DataRequired(message="Введите имя пользователя"),
            Length(min=3, max=150, message="Имя должно быть от 3 до 150 символов"),
        ],
    )
    password = PasswordField(
        "Пароль",
        validators=[
            DataRequired(message="Введите пароль"),
            Length(min=6, message="Пароль должен быть не менее 6 символов"),
        ],
    )
    confirm_password = PasswordField(
        "Подтвердите пароль",
        validators=[
            DataRequired(message="Подтвердите пароль"),
            EqualTo("password", message="Пароли должны совпадать"),
        ],
    )
    submit = SubmitField("Зарегистрироваться")

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError("Это имя пользователя уже занято.")


class LoginForm(FlaskForm):
    """Форма входа"""

    username = StringField(
        "Имя пользователя",
        validators=[DataRequired(message="Введите имя пользователя")],
    )
    password = PasswordField(
        "Пароль", validators=[DataRequired(message="Введите пароль")]
    )
    submit = SubmitField("Войти")


class TransactionForm(FlaskForm):
    """Форма транзакции"""

    amount = FloatField(
        "Сумма",
        validators=[DataRequired(message="Введите сумму")],
    )
    date = DateField(
        "Дата",
        format="%Y-%m-%d",
        validators=[DataRequired(message="Выберите дату")],
    )
    description = TextAreaField("Описание")
    submit = SubmitField("Сохранить")


class Category(db.Model):
    """Категория транзакций"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' или 'expense'
    color = db.Column(db.String(7), default="#000000")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class Transaction(db.Model):
    """Транзакция"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Budget(db.Model):
    """Бюджет для категории на месяц"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    limit = db.Column(db.Float, nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1-12
    year = db.Column(db.Integer, nullable=False)


# ==================== МАРШРУТЫ АВТОРИЗАЦИИ ====================


@app.route("/register", methods=["GET", "POST"])
def register():
    """Регистрация нового пользователя"""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    form = RegistrationForm()
    
    if request.method == "POST":
        # Проверяем, AJAX это или обычный запрос
        if request.is_json:
            data = request.get_json()
            # Заполняем форму данными из JSON
            form.username.data = data.get("username", "")
            form.password.data = data.get("password", "")
            form.confirm_password.data = data.get("confirm_password", "")
            
            if form.validate():
                user = User(username=form.username.data)
                user.set_password(form.password.data)
                db.session.add(user)
                db.session.commit()
                return json_success("Регистрация успешна! Теперь вы можете войти.", url_for("login"))
            else:
                errors = {field: list(form[field].errors) for field in form.errors}
                return json_error("Ошибка валидации", errors)
        else:
            if form.validate_on_submit():
                user = User(username=form.username.data)
                user.set_password(form.password.data)
                db.session.add(user)
                db.session.commit()
                return redirect(url_for("login"))

    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Вход пользователя"""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    form = LoginForm()
    
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            form.username.data = data.get("username", "")
            form.password.data = data.get("password", "")
            
            if form.validate():
                user = User.query.filter_by(username=form.username.data).first()
                if user and user.check_password(form.password.data):
                    login_user(user)
                    next_page = data.get("next") or request.args.get("next")
                    redirect_url = next_page if next_page else url_for("dashboard")
                    return json_success("Вы успешно вошли!", redirect_url)
                else:
                    return json_error("Неверное имя пользователя или пароль.")
            else:
                errors = {field: list(form[field].errors) for field in form.errors}
                return json_error("Ошибка валидации", errors)
        else:
            if form.validate_on_submit():
                user = User.query.filter_by(username=form.username.data).first()
                if user and user.check_password(form.password.data):
                    login_user(user)
                    next_page = request.args.get("next")
                    return redirect(next_page) if next_page else redirect(url_for("dashboard"))
                else:
                    form.password.errors.append("Неверное имя пользователя или пароль.")

    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    """Выход из системы"""
    logout_user()
    return redirect(url_for("login"))


# ==================== ГЛАВНЫЕ МАРШРУТЫ ====================


@app.route("/dashboard")
@login_required
def dashboard():
    """Главная страница с транзакциями"""
    transactions = (
        Transaction.query.filter_by(user_id=current_user.id)
        .order_by(Transaction.date.desc())
        .all()
    )
    return render_template("dashboard.html", transactions=transactions)


@app.route("/transaction/add", methods=["GET", "POST"])
@login_required
def add_transaction():
    """Добавление транзакции"""
    form = TransactionForm()
    
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            try:
                amount = float(data.get("amount", 0))
                date_str = data.get("date", "")
                transaction_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
            except (ValueError, TypeError):
                return json_error("Неверный формат данных")
            
            if amount <= 0:
                return json_error("Сумма должна быть больше 0")
            
            transaction = Transaction(
                user_id=current_user.id,
                amount=amount,
                date=transaction_date,
                description=data.get("description", "")
            )
            db.session.add(transaction)
            db.session.commit()
            return json_success("Транзакция добавлена!", url_for("dashboard"))
        else:
            if form.validate_on_submit():
                transaction = Transaction(
                    user_id=current_user.id,
                    amount=form.amount.data,
                    date=form.date.data,
                    description=form.description.data
                )
                db.session.add(transaction)
                db.session.commit()
                return redirect(url_for("dashboard"))
    
    return render_template("transaction_form.html", form=form, action="Добавить")


@app.route("/transaction/edit/<int:transaction_id>", methods=["GET", "POST"])
@login_required
def edit_transaction(transaction_id):
    """Редактирование транзакции"""
    transaction = Transaction.query.filter_by(
        id=transaction_id, 
        user_id=current_user.id
    ).first_or_404()
    
    form = TransactionForm(obj=transaction)
    
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            try:
                amount = float(data.get("amount", 0))
                date_str = data.get("date", "")
                transaction_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
            except (ValueError, TypeError):
                return json_error("Неверный формат данных")
            
            if amount <= 0:
                return json_error("Сумма должна быть больше 0")
            
            transaction.amount = amount
            transaction.date = transaction_date
            transaction.description = data.get("description", "")
            db.session.commit()
            return json_success("Транзакция обновлена!", url_for("dashboard"))
        else:
            if form.validate_on_submit():
                transaction.amount = form.amount.data
                transaction.date = form.date.data
                transaction.description = form.description.data
                db.session.commit()
                return redirect(url_for("dashboard"))
    
    return render_template("transaction_form.html", form=form, action="Редактировать", transaction=transaction)


@app.route("/transaction/delete/<int:transaction_id>", methods=["POST"])
@login_required
def delete_transaction(transaction_id):
    """Удаление транзакции"""
    transaction = Transaction.query.filter_by(
        id=transaction_id, 
        user_id=current_user.id
    ).first_or_404()
    
    db.session.delete(transaction)
    db.session.commit()
    
    if request.is_json:
        return json_success("Транзакция удалена!")
    
    return redirect(url_for("dashboard"))


@app.route("/")
def home():
    """Домашняя страница"""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
