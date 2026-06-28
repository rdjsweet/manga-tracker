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


def test_api_mark_read_returns_updated_manga(logged_in_client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {'id': 7}  # UPDATE ... RETURNING id
    updated = [{
        'id': 7, 'title': 'X', 'url': 'u', 'cover_url': None,
        'latest_chapter_title': 'Ch 5', 'unread_count': 0,
        'continue_url': None, 'continue_title': None, 'chapters': [],
    }]

    with patch('utils.db.get_db_connection') as mock_conn_factory:
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn_factory.return_value = mock_conn
        with patch('views.manga._build_manga_list', return_value=updated):
            resp = logged_in_client.post('/api/manga/7/read', json={'url': 'u5'})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data['manga']['id'] == 7
    assert data['manga']['caught_up'] is True


def test_api_mark_read_404_when_not_owned(logged_in_client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None  # UPDATE matched no row

    with patch('utils.db.get_db_connection') as mock_conn_factory:
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn_factory.return_value = mock_conn
        resp = logged_in_client.post('/api/manga/999/read', json={'url': 'u5'})

    assert resp.status_code == 404


def test_api_mark_read_400_without_url(logged_in_client):
    mock_cursor = MagicMock()

    with patch('utils.db.get_db_connection') as mock_conn_factory:
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn_factory.return_value = mock_conn
        resp = logged_in_client.post('/api/manga/7/read', json={})

    assert resp.status_code == 400


def test_api_cover_serves_stored_image(logged_in_client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {
        'cover_image': b'\xff\xd8\xff-image-bytes', 'cover_mime': 'image/png',
    }

    with patch('utils.db.get_db_connection') as mock_conn_factory:
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn_factory.return_value = mock_conn
        resp = logged_in_client.get('/api/manga/1/cover')

    assert resp.status_code == 200
    assert resp.data == b'\xff\xd8\xff-image-bytes'
    assert resp.headers['Content-Type'] == 'image/png'
    assert 'max-age' in resp.headers['Cache-Control']


def test_api_cover_404_when_no_image(logged_in_client):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {'cover_image': None, 'cover_mime': None}

    with patch('utils.db.get_db_connection') as mock_conn_factory:
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn_factory.return_value = mock_conn
        resp = logged_in_client.get('/api/manga/1/cover')

    assert resp.status_code == 404


def test_download_cover_rejects_internal_url():
    from views.manga import _download_cover
    data, mime = _download_cover('http://169.254.169.254/latest/meta-data/')
    assert data is None and mime is None
