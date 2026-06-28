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
