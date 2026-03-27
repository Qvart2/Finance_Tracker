"""
Финансовый трекер на Flask
Учебный проект, неделя 8: Доработка
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
    category_id = SelectField(
        "Категория",
        coerce=int,
    )
    description = TextAreaField("Описание")
    submit = SubmitField("Сохранить")


class CategoryForm(FlaskForm):
    """Форма категории"""

    name = StringField(
        "Название",
        validators=[DataRequired(message="Введите название категории")],
    )
    type = SelectField(
        "Тип",
        choices=[("expense", "Расход"), ("income", "Доход")],
        validators=[DataRequired(message="Выберите тип категории")],
    )
    color = StringField("Цвет (HEX)", default="#667eea")
    submit = SubmitField("Сохранить")


class BudgetForm(FlaskForm):
    """Форма бюджета"""

    category_id = SelectField(
        "Категория",
        coerce=int,
        validators=[DataRequired(message="Выберите категорию")],
    )
    limit = FloatField(
        "Лимит",
        validators=[DataRequired(message="Введите лимит бюджета")],
    )
    month = SelectField(
        "Месяц",
        coerce=int,
        choices=[
            (1, "Январь"), (2, "Февраль"), (3, "Март"), (4, "Апрель"),
            (5, "Май"), (6, "Июнь"), (7, "Июль"), (8, "Август"),
            (9, "Сентябрь"), (10, "Октябрь"), (11, "Ноябрь"), (12, "Декабрь"),
        ],
    )
    year = SelectField(
        "Год",
        coerce=int,
        validators=[DataRequired(message="Выберите год")],
    )
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
    
    # Связь с категорией
    category = db.relationship("Category", backref="transactions", lazy=True)


class Budget(db.Model):
    """Бюджет для категории на месяц"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    limit = db.Column(db.Float, nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1-12
    year = db.Column(db.Integer, nullable=False)
    
    # Связь с категорией
    category = db.relationship("Category", backref="budgets", lazy=True)


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
                
                # Создаем категории по умолчанию для нового пользователя
                default_categories = [
                    {"name": "Продукты", "type": "expense", "color": "#28a745"},
                    {"name": "Транспорт", "type": "expense", "color": "#17a2b8"},
                    {"name": "Развлечения", "type": "expense", "color": "#ffc107"},
                    {"name": "Коммунальные услуги", "type": "expense", "color": "#6c757d"},
                    {"name": "Зарплата", "type": "income", "color": "#20c997"},
                    {"name": "Фриланс", "type": "income", "color": "#6610f2"},
                ]
                
                user_obj = User.query.filter_by(username=form.username.data).first()
                for cat_data in default_categories:
                    category = Category(**cat_data, user_id=user_obj.id)
                    db.session.add(category)
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
    
    # Получаем категории для отображения
    categories = Category.query.filter_by(user_id=current_user.id).all()
    
    # Вычисляем баланс
    total_income = sum(t.amount for t in transactions if t.category and t.category.type == "income")
    total_expense = sum(t.amount for t in transactions if t.category and t.category.type == "expense")
    
    return render_template(
        "dashboard.html", 
        transactions=transactions, 
        categories=categories,
        total_income=total_income,
        total_expense=total_expense,
        balance=total_income - total_expense
    )


@app.route("/transaction/add", methods=["GET", "POST"])
@login_required
def add_transaction():
    """Добавление транзакции"""
    form = TransactionForm()
    
    # Получаем категории пользователя
    categories = Category.query.filter_by(user_id=current_user.id).all()
    form.category_id.choices = [(0, "Без категории")] + [(c.id, c.name) for c in categories]
    
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            try:
                amount = float(data.get("amount", 0))
                date_str = data.get("date", "")
                transaction_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
                category_id = int(data.get("category_id", 0)) if data.get("category_id") else None
                if category_id == 0:
                    category_id = None
            except (ValueError, TypeError):
                return json_error("Неверный формат данных")
            
            if amount <= 0:
                return json_error("Сумма должна быть больше 0")
            
            transaction = Transaction(
                user_id=current_user.id,
                amount=amount,
                date=transaction_date,
                description=data.get("description", ""),
                category_id=category_id
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
    
    return render_template("transaction_form.html", form=form, action="Добавить", categories=categories)


@app.route("/transaction/edit/<int:transaction_id>", methods=["GET", "POST"])
@login_required
def edit_transaction(transaction_id):
    """Редактирование транзакции"""
    transaction = Transaction.query.filter_by(
        id=transaction_id, 
        user_id=current_user.id
    ).first_or_404()
    
    form = TransactionForm(obj=transaction)
    
    # Получаем категории пользователя
    categories = Category.query.filter_by(user_id=current_user.id).all()
    form.category_id.choices = [(0, "Без категории")] + [(c.id, c.name) for c in categories]
    
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            try:
                amount = float(data.get("amount", 0))
                date_str = data.get("date", "")
                transaction_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
                category_id = int(data.get("category_id", 0)) if data.get("category_id") else None
                if category_id == 0:
                    category_id = None
            except (ValueError, TypeError):
                return json_error("Неверный формат данных")
            
            if amount <= 0:
                return json_error("Сумма должна быть больше 0")
            
            transaction.amount = amount
            transaction.date = transaction_date
            transaction.description = data.get("description", "")
            transaction.category_id = category_id
            db.session.commit()
            return json_success("Транзакция обновлена!", url_for("dashboard"))
        else:
            if form.validate_on_submit():
                transaction.amount = form.amount.data
                transaction.date = form.date.data
                transaction.description = form.description.data
                db.session.commit()
                return redirect(url_for("dashboard"))
    
    return render_template(
        "transaction_form.html", 
        form=form, 
        action="Редактировать", 
        transaction=transaction,
        categories=categories
    )


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
                # Проверяем, что категория с таким именем не существует
                existing = Category.query.filter_by(
                    user_id=current_user.id, 
                    name=form.name.data
                ).first()
                if existing:
                    return json_error("Категория с таким названием уже существует.")
                
                category = Category(
                    name=form.name.data,
                    type=form.type.data,
                    color=form.color.data,
                    user_id=current_user.id
                )
                db.session.add(category)
                db.session.commit()
                return json_success("Категория добавлена!", url_for("categories"))
            else:
                errors = {field: list(form[field].errors) for field in form.errors}
                return json_error("Ошибка валидации", errors)
    
    return render_template("category_form.html", form=form, action="Добавить")


@app.route("/category/edit/<int:category_id>", methods=["GET", "POST"])
@login_required
def edit_category(category_id):
    """Редактирование категории"""
    category = Category.query.filter_by(
        id=category_id, 
        user_id=current_user.id
    ).first_or_404()
    
    form = CategoryForm(obj=category)
    
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            form.name.data = data.get("name", "")
            form.type.data = data.get("type", "expense")
            form.color.data = data.get("color", "#667eea")
            
            if form.validate():
                # Проверяем, что категория с таким именем не существует (кроме текущей)
                existing = Category.query.filter(
                    Category.user_id == current_user.id,
                    Category.name == form.name.data,
                    Category.id != category_id
                ).first()
                if existing:
                    return json_error("Категория с таким названием уже существует.")
                
                category.name = form.name.data
                category.type = form.type.data
                category.color = form.color.data
                db.session.commit()
                return json_success("Категория обновлена!", url_for("categories"))
            else:
                errors = {field: list(form[field].errors) for field in form.errors}
                return json_error("Ошибка валидации", errors)
    
    return render_template(
        "category_form.html", 
        form=form, 
        action="Редактировать", 
        category=category
    )


@app.route("/category/delete/<int:category_id>", methods=["POST"])
@login_required
def delete_category(category_id):
    """Удаление категории"""
    category = Category.query.filter_by(
        id=category_id, 
        user_id=current_user.id
    ).first_or_404()
    
    # Удаляем связь с транзакциями
    Transaction.query.filter_by(category_id=category_id).update({"category_id": None})
    
    # Удаляем бюджеты категории
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
    budgets_list = Budget.query.filter_by(user_id=current_user.id).order_by(
        Budget.year.desc(), Budget.month.desc()
    ).all()
    
    # Получаем категории для отображения
    categories = Category.query.filter_by(user_id=current_user.id).all()
    
    # Вычисляем расходы по категориям за период бюджета
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    budget_stats = []
    for budget in budgets_list:
        # Получаем транзакции за период бюджета
        spent = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.category_id == budget.category_id,
            db.extract('month', Transaction.date) == budget.month,
            db.extract('year', Transaction.date) == budget.year
        ).scalar() or 0
        
        budget_stats.append({
            "budget": budget,
            "spent": spent,
            "remaining": budget.limit - spent,
            "percentage": min(100, (spent / budget.limit * 100)) if budget.limit > 0 else 0
        })
    
    return render_template("budgets.html", budget_stats=budget_stats, categories=categories)


@app.route("/budget/add", methods=["GET", "POST"])
@login_required
def add_budget():
    """Добавление бюджета"""
    form = BudgetForm()
    
    # Получаем категории пользователя (только расходы)
    categories = Category.query.filter_by(user_id=current_user.id, type="expense").all()
    form.category_id.choices = [(c.id, c.name) for c in categories]
    
    # Годы: текущий и следующий
    current_year = datetime.now().year
    form.year.choices = [(current_year, current_year), (current_year + 1, current_year + 1)]
    
    # Месяц по умолчанию - текущий
    form.month.data = datetime.now().month
    
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            try:
                category_id = int(data.get("category_id", 0))
                limit = float(data.get("limit", 0))
                month = int(data.get("month", 1))
                year = int(data.get("year", current_year))
            except (ValueError, TypeError):
                return json_error("Неверный формат данных")
            
            if limit <= 0:
                return json_error("Лимит должен быть больше 0")
            
            if category_id <= 0:
                return json_error("Выберите категорию")
            
            # Проверяем, что бюджет на этот месяц/год для категории не существует
            existing = Budget.query.filter_by(
                user_id=current_user.id,
                category_id=category_id,
                month=month,
                year=year
            ).first()
            if existing:
                return json_error("Бюджет для этой категории на указанный период уже существует.")
            
            budget = Budget(
                user_id=current_user.id,
                category_id=category_id,
                limit=limit,
                month=month,
                year=year
            )
            db.session.add(budget)
            db.session.commit()
            return json_success("Бюджет добавлен!", url_for("budgets"))
    
    current_year = datetime.now().year
    return render_template("budget_form.html", form=form, action="Добавить", categories=categories, current_year=current_year)


@app.route("/budget/edit/<int:budget_id>", methods=["GET", "POST"])
@login_required
def edit_budget(budget_id):
    """Редактирование бюджета"""
    budget = Budget.query.filter_by(
        id=budget_id, 
        user_id=current_user.id
    ).first_or_404()
    
    form = BudgetForm(obj=budget)
    
    # Получаем категории пользователя (только расходы)
    categories = Category.query.filter_by(user_id=current_user.id, type="expense").all()
    form.category_id.choices = [(c.id, c.name) for c in categories]
    
    # Годы: текущий и следующий
    current_year = datetime.now().year
    form.year.choices = [(current_year, current_year), (current_year + 1, current_year + 1)]
    
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            try:
                category_id = int(data.get("category_id", 0))
                limit = float(data.get("limit", 0))
                month = int(data.get("month", 1))
                year = int(data.get("year", current_year))
            except (ValueError, TypeError):
                return json_error("Неверный формат данных")
            
            if limit <= 0:
                return json_error("Лимит должен быть больше 0")
            
            if category_id <= 0:
                return json_error("Выберите категорию")
            
            # Проверяем, что бюджет на этот месяц/год для категории не существует (кроме текущего)
            existing = Budget.query.filter(
                Budget.user_id == current_user.id,
                Budget.category_id == category_id,
                Budget.month == month,
                Budget.year == year,
                Budget.id != budget_id
            ).first()
            if existing:
                return json_error("Бюджет для этой категории на указанный период уже существует.")
            
            budget.category_id = category_id
            budget.limit = limit
            budget.month = month
            budget.year = year
            db.session.commit()
            return json_success("Бюджет обновлён!", url_for("budgets"))
    
    current_year = datetime.now().year
    return render_template(
        "budget_form.html", 
        form=form, 
        action="Редактировать", 
        budget=budget,
        categories=categories,
        current_year=current_year
    )


@app.route("/budget/delete/<int:budget_id>", methods=["POST"])
@login_required
def delete_budget(budget_id):
    """Удаление бюджета"""
    budget = Budget.query.filter_by(
        id=budget_id, 
        user_id=current_user.id
    ).first_or_404()
    
    db.session.delete(budget)
    db.session.commit()
    
    if request.is_json:
        return json_success("Бюджет удалён!")
    
    return redirect(url_for("budgets"))


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
