import pytest
from unittest.mock import MagicMock, patch
from app import app as flask_app
from models import User


@pytest.fixture
def app():
    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
    })
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def logged_in_client(app, client):
    test_user = User(id=1, username='testuser', password_hash='hash')
    with patch('app.load_user', return_value=test_user):
        with client.session_transaction() as sess:
            sess['_user_id'] = '1'
            sess['_fresh'] = True
        yield client
