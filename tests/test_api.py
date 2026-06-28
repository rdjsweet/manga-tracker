import pytest
from unittest.mock import patch, MagicMock


def test_api_check_updates_returns_json(logged_in_client):
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_cursor.fetchone.return_value = None

    with patch('utils.db.get_db_connection') as mock_conn_factory:
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn_factory.return_value = mock_conn

        resp = logged_in_client.post('/api/check_updates')

    assert resp.status_code == 200
    data = resp.get_json()
    assert 'manga' in data
    assert 'total_new' in data
    assert 'logs' in data
    assert 'last_checked' in data
    assert isinstance(data['manga'], list)


def test_api_delete_returns_ok(logged_in_client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {'id': 42}

    with patch('utils.db.get_db_connection') as mock_conn_factory:
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn_factory.return_value = mock_conn

        resp = logged_in_client.delete('/api/manga/42')

    assert resp.status_code == 200
    assert resp.get_json() == {'ok': True}


def test_api_delete_returns_404_when_not_found(logged_in_client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None

    with patch('utils.db.get_db_connection') as mock_conn_factory:
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn_factory.return_value = mock_conn

        resp = logged_in_client.delete('/api/manga/999')

    assert resp.status_code == 404


def test_api_add_duplicate_returns_409(logged_in_client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {'id': 1, 'title': 'Naruto', 'url': 'https://example.com', 'user_id': 1}

    with patch('utils.db.get_db_connection') as mock_conn_factory:
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn_factory.return_value = mock_conn

        resp = logged_in_client.post(
            '/api/add',
            json={'url': 'https://example.com'},
        )

    assert resp.status_code == 409
    assert 'error' in resp.get_json()


def test_api_add_bad_url_returns_422(logged_in_client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None

    with patch('utils.db.get_db_connection') as mock_conn_factory:
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn_factory.return_value = mock_conn
        with patch('views.manga.scrape_manga_details', return_value=(None, None, None, None)):
            resp = logged_in_client.post(
                '/api/add',
                json={'url': 'https://bad-url.com'},
            )

    assert resp.status_code == 422
    assert 'error' in resp.get_json()
