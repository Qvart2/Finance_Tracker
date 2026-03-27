"""
Тесты для финансового трекера
"""

import pytest
import sys
import os

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Category, Transaction, Budget


@pytest.fixture
def client():
    """Создает тестовый клиент"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()


@pytest.fixture
def authenticated_client(client):
    """Создает аутентифицированный тестовый клиент"""
    with app.app_context():
        # Регистрируем тестового пользователя
        user = User(username='testuser')
        user.set_password('testpassword')
        db.session.add(user)
        db.session.commit()
        
        # Логинимся
        client.post('/login', json={
            'username': 'testuser',
            'password': 'testpassword'
        })
        
        yield client


class TestAuth:
    """Тесты авторизации"""
    
    def test_register_page_loads(self, client):
        """Тест загрузки страницы регистрации"""
        response = client.get('/register')
        assert response.status_code == 200
    
    def test_login_page_loads(self, client):
        """Тест загрузки страницы входа"""
        response = client.get('/login')
        assert response.status_code == 200
    
    def test_register_success(self, client):
        """Тест успешной регистрации"""
        response = client.post('/register', json={
            'username': 'newuser',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
    
    def test_register_duplicate_username(self, client):
        """Тест регистрации с существующим именем"""
        # Первый пользователь
        client.post('/register', json={
            'username': 'existinguser',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        
        # Попытка регистрации с тем же именем
        response = client.post('/register', json={
            'username': 'existinguser',
            'password': 'password456',
            'confirm_password': 'password456'
        })
        data = response.get_json()
        assert data['success'] is False
    
    def test_login_success(self, client):
        """Тест успешного входа"""
        # Регистрируем
        client.post('/register', json={
            'username': 'loginuser',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        
        # Логинимся
        response = client.post('/login', json={
            'username': 'loginuser',
            'password': 'password123'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
    
    def test_login_wrong_password(self, client):
        """Тест входа с неверным паролем"""
        # Регистрируем
        client.post('/register', json={
            'username': 'wrongpass',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        
        # Логинимся с неверным паролем
        response = client.post('/login', json={
            'username': 'wrongpass',
            'password': 'wrongpassword'
        })
        data = response.get_json()
        assert data['success'] is False


class TestCategories:
    """Тесты категорий"""
    
    def test_categories_page_requires_auth(self, client):
        """Тест требования авторизации"""
        response = client.get('/categories')
        assert response.status_code == 302  # Redirect to login
    
    def test_categories_page_loads(self, authenticated_client):
        """Тест загрузки страницы категорий"""
        response = authenticated_client.get('/categories')
        assert response.status_code == 200
    
    def test_add_category(self, authenticated_client):
        """Тест добавления категории"""
        response = authenticated_client.post('/category/add', json={
            'name': 'Тестовая категория',
            'type': 'expense',
            'color': '#FF5733'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
    
    def test_add_duplicate_category(self, authenticated_client):
        """Тест добавления дубликата категории"""
        # Первая категория
        authenticated_client.post('/category/add', json={
            'name': 'Дубликат',
            'type': 'expense',
            'color': '#FF5733'
        })
        
        # Попытка добавить вторую с тем же именем
        response = authenticated_client.post('/category/add', json={
            'name': 'Дубликат',
            'type': 'income',
            'color': '#33FF57'
        })
        data = response.get_json()
        assert data['success'] is False


class TestTransactions:
    """Тесты транзакций"""
    
    def test_dashboard_requires_auth(self, client):
        """Тест требования авторизации для дашборда"""
        response = client.get('/dashboard')
        assert response.status_code == 302
    
    def test_dashboard_loads(self, authenticated_client):
        """Тест загрузки дашборда"""
        response = authenticated_client.get('/dashboard')
        assert response.status_code == 200
    
    def test_add_transaction(self, authenticated_client):
        """Тест добавления транзакции"""
        response = authenticated_client.post('/transaction/add', json={
            'amount': 100.50,
            'date': '2026-03-27',
            'description': 'Тестовая транзакция'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
    
    def test_add_transaction_invalid_amount(self, authenticated_client):
        """Тест добавления транзакции с неверной суммой"""
        response = authenticated_client.post('/transaction/add', json={
            'amount': -100,
            'date': '2026-03-27',
            'description': 'Тест'
        })
        data = response.get_json()
        assert data['success'] is False


class TestBudgets:
    """Тесты бюджетов"""
    
    def test_budgets_page_requires_auth(self, client):
        """Тест требования авторизации"""
        response = client.get('/budgets')
        assert response.status_code == 302
    
    def test_budgets_page_loads(self, authenticated_client):
        """Тест загрузки страницы бюджетов"""
        response = authenticated_client.get('/budgets')
        assert response.status_code == 200
    
    def test_add_budget(self, authenticated_client):
        """Тест добавления бюджета"""
        # Сначала создаем категорию
        authenticated_client.post('/category/add', json={
            'name': 'Бюджетная категория',
            'type': 'expense',
            'color': '#FF5733'
        })
        
        # Добавляем бюджет
        response = authenticated_client.post('/budget/add', json={
            'category_id': 1,
            'limit': 5000,
            'month': 3,
            'year': 2026
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
