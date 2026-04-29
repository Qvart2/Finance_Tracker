"""
Финансовый трекер на Flask
Учебный проект, неделя 5-6: Авторизация пользователей
"""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from flask import Flask, render_template, redirect, url_for, request, jsonify
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
from sqlalchemy import func
from wtforms import (
    StringField,
    PasswordField,
    SubmitField,
    FloatField,
    TextAreaField,
    DateField,
    SelectField,
)
from wtforms.validators import (
    DataRequired,
    Length,
    EqualTo,
    ValidationError,
    NumberRange,
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///finance.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Пожалуйста, войдите для доступа к странице."


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

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
    """Форма добавления/редактирования транзакции"""

    class Meta:
        csrf = False

    amount = FloatField(
        "Сумма",
        validators=[
            DataRequired(message="Введите сумму"),
            NumberRange(min=0.01, message="Сумма должна быть положительной"),
        ],
    )
    date = DateField(
        "Дата",
        validators=[DataRequired(message="Выберите дату")],
        format="%Y-%m-%d",
    )
    description = TextAreaField("Описание")
    category_id = SelectField("Категория", coerce=int)
    type = SelectField(
        "Тип",
        choices=[("expense", "Расход"), ("income", "Доход")],
        default="expense",
    )
    submit = SubmitField("Сохранить")


class CategoryForm(FlaskForm):
    """Форма добавления/редактирования категории"""

    class Meta:
        csrf = False

    name = StringField(
        "Название",
        validators=[
            DataRequired(message="Введите название категории"),
            Length(max=100, message="Название не должно превышать 100 символов"),
        ],
    )
    type = SelectField(
        "Тип",
        choices=[("expense", "Расход"), ("income", "Доход")],
        default="expense",
    )
    color = StringField("Цвет", default="#667eea")
    submit = SubmitField("Сохранить")


class BudgetForm(FlaskForm):
    """Форма добавления/редактирования бюджета"""

    class Meta:
        csrf = False

    category_id = SelectField(
        "Категория",
        coerce=int,
        validators=[DataRequired(message="Выберите категорию")],
    )
    limit = FloatField(
        "Лимит",
        validators=[
            DataRequired(message="Введите лимит бюджета"),
            NumberRange(min=0.01, message="Лимит должен быть положительным"),
        ],
    )
    month = SelectField(
        "Месяц",
        choices=[
            (1, "Январь"),
            (2, "Февраль"),
            (3, "Март"),
            (4, "Апрель"),
            (5, "Май"),
            (6, "Июнь"),
            (7, "Июль"),
            (8, "Август"),
            (9, "Сентябрь"),
            (10, "Октябрь"),
            (11, "Ноябрь"),
            (12, "Декабрь"),
        ],
        coerce=int,
        validators=[DataRequired(message="Выберите месяц")],
        default=datetime.now().month,
    )
    year = SelectField(
        "Год",
        coerce=int,
        validators=[DataRequired(message="Выберите год")],
        default=datetime.now().year,
    )
    submit = SubmitField("Сохранить")


class Category(db.Model):
    """Категория транзакций"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' или 'expense'
    color = db.Column(db.String(7), default="#000000")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", backref=db.backref("categories", lazy=True))
    transactions = db.relationship("Transaction", backref="category", lazy=True)


class Transaction(db.Model):
    """Транзакция"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=True)
    type = db.Column(db.String(10), nullable=False, default="expense")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user = db.relationship("User", backref=db.backref("transactions", lazy=True))


class Budget(db.Model):
    """Бюджет для категории на месяц"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    limit = db.Column(db.Float, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    user = db.relationship("User", backref=db.backref("budgets", lazy=True))


def create_default_categories(user_id):
    """Создание базовых категорий для нового пользователя"""
    default_categories = [
        # Категории расходов
        {"name": "Продукты", "type": "expense", "color": "#28a745"},
        {"name": "Транспорт", "type": "expense", "color": "#17a2b8"},
        {"name": "Жильё", "type": "expense", "color": "#6c757d"},
        {"name": "Коммунальные услуги", "type": "expense", "color": "#ffc107"},
        {"name": "Развлечения", "type": "expense", "color": "#dc3545"},
        {"name": "Одежда", "type": "expense", "color": "#e83e8c"},
        {"name": "Здоровье", "type": "expense", "color": "#20c997"},
        {"name": "Образование", "type": "expense", "color": "#6610f2"},
        {"name": "Связь", "type": "expense", "color": "#fd7e14"},
        {"name": "Прочее", "type": "expense", "color": "#6c757d"},
        # Категории доходов
        {"name": "Зарплата", "type": "income", "color": "#28a745"},
        {"name": "Фриланс", "type": "income", "color": "#17a2b8"},
        {"name": "Инвестиции", "type": "income", "color": "#6610f2"},
        {"name": "Подарки", "type": "income", "color": "#e83e8c"},
        {"name": "Прочее", "type": "income", "color": "#6c757d"},
    ]

    for cat in default_categories:
        category = Category(
            user_id=user_id, name=cat["name"], type=cat["type"], color=cat["color"]
        )
        db.session.add(category)

    db.session.commit()


# ==================== МАРШРУТЫ АВТОРИЗАЦИИ ====================


@app.route("/register", methods=["GET", "POST"])
def register():
    """Регистрация нового пользователя"""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    form = RegistrationForm()

    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            form.username.data = data.get("username", "")
            form.password.data = data.get("password", "")
            form.confirm_password.data = data.get("confirm_password", "")

            if form.validate():
                user = User(username=form.username.data)
                user.set_password(form.password.data)
                db.session.add(user)
                db.session.commit()
                create_default_categories(user.id)
                return json_success(
                    "Регистрация успешна! Теперь вы можете войти.", url_for("login")
                )
            else:
                errors = {field: list(form[field].errors) for field in form.errors}
                return json_error("Ошибка валидации", errors)
        else:
            if form.validate_on_submit():
                user = User(username=form.username.data)
                user.set_password(form.password.data)
                db.session.add(user)
                db.session.commit()
                create_default_categories(user.id)
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
                    if next_page and not next_page.startswith("/"):
                        next_page = None
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
                    if next_page and not next_page.startswith("/"):
                        next_page = None
                    return (
                        redirect(next_page)
                        if next_page
                        else redirect(url_for("dashboard"))
                    )
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
    page = request.args.get("page", 1, type=int)
    per_page = 10

    total_income = (
        db.session.query(func.sum(Transaction.amount))
        .filter_by(user_id=current_user.id, type="income")
        .scalar()
        or 0.0
    )

    total_expense = (
        db.session.query(func.sum(Transaction.amount))
        .filter_by(user_id=current_user.id, type="expense")
        .scalar()
        or 0.0
    )

    balance = total_income - total_expense

    pagination = (
        Transaction.query.filter_by(user_id=current_user.id)
        .order_by(Transaction.date.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return render_template(
        "dashboard.html",
        transactions=pagination.items,
        pagination=pagination,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
    )


# ==================== МАРШРУТЫ ТРАНЗАКЦИЙ ====================


@app.route("/transaction/add", methods=["GET", "POST"])
@login_required
def add_transaction():
    """Добавление транзакции"""
    form = TransactionForm()

    categories = Category.query.filter_by(user_id=current_user.id).all()
    form.category_id.choices = [(0, "Без категории")] + [
        (c.id, c.name) for c in categories
    ]

    if request.method == "GET":
        form.date.data = datetime.today().date()

    if request.method == "POST":
        if request.is_json:
            data = request.get_json()

            amount_val = data.get("amount")
            form.amount.data = float(amount_val) if amount_val else None
            date_val = data.get("date")
            form.date.data = (
                datetime.strptime(date_val, "%Y-%m-%d").date() if date_val else None
            )
            form.description.data = data.get("description", "") or ""
            cat_id_val = data.get("category_id")
            form.category_id.data = (
                int(cat_id_val) if cat_id_val and str(cat_id_val) != "0" else 0
            )
            form.type.data = data.get("type", "expense")

            if form.validate():
                transaction = Transaction(
                    user_id=current_user.id,
                    amount=float(form.amount.data),
                    date=form.date.data,
                    description=form.description.data,
                    category_id=(
                        form.category_id.data if form.category_id.data != 0 else None
                    ),
                    type=form.type.data,
                )
                db.session.add(transaction)
                db.session.commit()
                return json_success("Транзакция добавлена!", url_for("dashboard"))
            else:
                errors = {
                    field.name: list(field.errors) for field in form if field.errors
                }
                return json_error("Ошибка валидации", errors)
        else:
            if form.validate_on_submit():
                transaction = Transaction(
                    user_id=current_user.id,
                    amount=float(form.amount.data),
                    date=form.date.data,
                    description=form.description.data,
                    category_id=(
                        form.category_id.data if form.category_id.data != 0 else None
                    ),
                    type=form.type.data,
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
        id=transaction_id, user_id=current_user.id
    ).first_or_404()

    form = TransactionForm()

    categories = Category.query.filter_by(user_id=current_user.id).all()
    form.category_id.choices = [(0, "Без категории")] + [
        (c.id, c.name) for c in categories
    ]

    if request.method == "GET":
        form.amount.data = transaction.amount
        form.date.data = transaction.date
        form.description.data = transaction.description
        form.category_id.data = transaction.category_id or 0
        form.type.data = transaction.type

    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            amount_val = data.get("amount")
            form.amount.data = float(amount_val) if amount_val else None
            form.date.data = (
                datetime.strptime(data.get("date"), "%Y-%m-%d").date()
                if data.get("date")
                else None
            )
            form.description.data = data.get("description", "")
            form.category_id.data = (
                int(data.get("category_id", 0)) if data.get("category_id") else 0
            )
            form.type.data = data.get("type", "expense")

            if form.validate():
                transaction.amount = float(form.amount.data)
                transaction.date = form.date.data
                transaction.description = form.description.data
                transaction.category_id = (
                    form.category_id.data if form.category_id.data != 0 else None
                )
                transaction.type = form.type.data
                db.session.commit()
                return json_success("Транзакция обновлена!", url_for("dashboard"))
            else:
                errors = {
                    field.name: list(field.errors) for field in form if field.errors
                }
                return json_error("Ошибка валидации", errors)
        else:
            if form.validate_on_submit():
                transaction.amount = float(form.amount.data)
                transaction.date = form.date.data
                transaction.description = form.description.data
                transaction.category_id = (
                    form.category_id.data if form.category_id.data != 0 else None
                )
                transaction.type = form.type.data
                db.session.commit()
                return redirect(url_for("dashboard"))

    return render_template(
        "transaction_form.html",
        form=form,
        action="Редактировать",
        transaction=transaction,
    )


@app.route("/transaction/delete/<int:transaction_id>", methods=["POST"])
@login_required
def delete_transaction(transaction_id):
    """Удаление транзакции"""
    transaction = Transaction.query.filter_by(
        id=transaction_id, user_id=current_user.id
    ).first_or_404()

    db.session.delete(transaction)
    db.session.commit()

    if request.is_json:
        return json_success("Транзакция удалена!")

    return redirect(url_for("dashboard"))


# ==================== МАРШРУТЫ КАТЕГОРИЙ ====================


@app.route("/categories")
@login_required
def categories():
    """Управление категориями"""
    categories_list = Category.query.filter_by(user_id=current_user.id).all()
    return render_template("categories.html", categories=categories_list)


@app.route("/category/add", methods=["GET", "POST"])
@login_required
def add_category():
    """Добавление категории"""
    form = CategoryForm()

    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            form.name.data = data.get("name", "")
            form.type.data = data.get("type", "expense")
            form.color.data = data.get("color", "#667eea")

            if form.validate():
                category = Category(
                    user_id=current_user.id,
                    name=form.name.data,
                    type=form.type.data,
                    color=form.color.data,
                )
                db.session.add(category)
                db.session.commit()
                return json_success("Категория добавлена!", url_for("categories"))
            else:
                errors = {
                    field.name: list(field.errors) for field in form if field.errors
                }
                return json_error("Ошибка валидации", errors)
        else:
            if form.validate_on_submit():
                category = Category(
                    user_id=current_user.id,
                    name=form.name.data,
                    type=form.type.data,
                    color=form.color.data,
                )
                db.session.add(category)
                db.session.commit()
                return redirect(url_for("categories"))

    return render_template("category_form.html", form=form, action="Добавить")


@app.route("/category/edit/<int:category_id>", methods=["GET", "POST"])
@login_required
def edit_category(category_id):
    """Редактирование категории"""
    category = Category.query.filter_by(
        id=category_id, user_id=current_user.id
    ).first_or_404()

    form = CategoryForm()

    if request.method == "GET":
        form.name.data = category.name
        form.type.data = category.type
        form.color.data = category.color

    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            form.name.data = data.get("name", "")
            form.type.data = data.get("type", "expense")
            form.color.data = data.get("color", "#667eea")

            if form.validate():
                category.name = form.name.data
                category.type = form.type.data
                category.color = form.color.data
                db.session.commit()
                return json_success("Категория обновлена!", url_for("categories"))
            else:
                errors = {
                    field.name: list(field.errors) for field in form if field.errors
                }
                return json_error("Ошибка валидации", errors)
        else:
            if form.validate_on_submit():
                category.name = form.name.data
                category.type = form.type.data
                category.color = form.color.data
                db.session.commit()
                return redirect(url_for("categories"))

    return render_template(
        "category_form.html", form=form, action="Редактировать", category=category
    )


@app.route("/category/delete/<int:category_id>", methods=["POST"])
@login_required
def delete_category(category_id):
    """Удаление категории"""
    category = Category.query.filter_by(
        id=category_id, user_id=current_user.id
    ).first_or_404()

    Transaction.query.filter_by(category_id=category_id).update({"category_id": None})

    Budget.query.filter_by(category_id=category_id).delete()

    db.session.delete(category)
    db.session.commit()

    if request.is_json:
        return json_success("Категория удалена!")

    return redirect(url_for("categories"))


# ==================== МАРШРУТЫ БЮДЖЕТОВ ====================


@app.route("/budgets")
@login_required
def budgets():
    """Управление бюджетами"""
    budgets_list = (
        Budget.query.filter_by(user_id=current_user.id)
        .order_by(Budget.year.desc(), Budget.month.desc())
        .all()
    )
    return render_template("budgets.html", budgets=budgets_list)


@app.route("/budget/add", methods=["GET", "POST"])
@login_required
def add_budget():
    """Добавление бюджета"""
    form = BudgetForm()

    categories = Category.query.filter_by(user_id=current_user.id, type="expense").all()
    form.category_id.choices = [(c.id, c.name) for c in categories]

    current_year = datetime.now().year
    form.year.choices = [(y, str(y)) for y in range(current_year - 1, current_year + 2)]
    form.year.data = current_year

    if request.method == "POST":
        if request.is_json:
            categories = Category.query.filter_by(
                user_id=current_user.id, type="expense"
            ).all()
            form.category_id.choices = [(c.id, c.name) for c in categories]

            current_year = datetime.now().year
            form.year.choices = [
                (y, str(y)) for y in range(current_year - 1, current_year + 2)
            ]

            data = request.get_json()
            form.category_id.data = (
                int(data.get("category_id")) if data.get("category_id") else None
            )
            form.limit.data = float(data.get("limit")) if data.get("limit") else None
            form.month.data = int(data.get("month")) if data.get("month") else None
            form.year.data = int(data.get("year")) if data.get("year") else current_year

            if form.validate():
                existing = Budget.query.filter_by(
                    user_id=current_user.id,
                    category_id=form.category_id.data,
                    month=form.month.data,
                    year=form.year.data,
                ).first()

                if existing:
                    return json_error(
                        "Бюджет для этой категории на указанный месяц уже существует."
                    )

                budget = Budget(
                    user_id=current_user.id,
                    category_id=form.category_id.data,
                    limit=form.limit.data,
                    month=form.month.data,
                    year=form.year.data,
                )
                db.session.add(budget)
                db.session.commit()
                return json_success("Бюджет добавлен!", url_for("budgets"))
            else:
                errors = {
                    field.name: list(field.errors) for field in form if field.errors
                }
                return json_error("Ошибка валидации", errors)
        else:
            if form.validate_on_submit():
                budget = Budget(
                    user_id=current_user.id,
                    category_id=form.category_id.data,
                    limit=form.limit.data,
                    month=form.month.data,
                    year=form.year.data,
                )
                db.session.add(budget)
                db.session.commit()
                return redirect(url_for("budgets"))

    return render_template("budget_form.html", form=form, action="Добавить")


@app.route("/budget/delete/<int:budget_id>", methods=["POST"])
@login_required
def delete_budget(budget_id):
    """Удаление бюджета"""
    budget = Budget.query.filter_by(
        id=budget_id, user_id=current_user.id
    ).first_or_404()

    db.session.delete(budget)
    db.session.commit()

    if request.is_json:
        return json_success("Бюджет удален!")

    return redirect(url_for("budgets"))


@app.route("/categories/by-type/<category_type>")
@login_required
def get_categories_by_type(category_type):
    """Получение категорий по типу (для AJAX)"""
    categories = Category.query.filter_by(user_id=current_user.id, type=category_type).all()
    return jsonify([{"id": c.id, "name": c.name} for c in categories])


@app.route("/")
def home():
    """Домашняя страница"""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(_):
    return render_template("500.html"), 500


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
