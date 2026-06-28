import pytest
from unittest.mock import MagicMock, patch


def test_db_cursor_commits_on_success():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch('utils.db.get_db_connection', return_value=mock_conn):
        from utils.db import db_cursor
        with db_cursor() as cursor:
            cursor.execute('SELECT 1')

    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


def test_db_cursor_rolls_back_on_exception():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch('utils.db.get_db_connection', return_value=mock_conn):
        from utils.db import db_cursor
        with pytest.raises(ValueError):
            with db_cursor() as cursor:
                raise ValueError('test error')

    mock_conn.rollback.assert_called_once()
    mock_conn.commit.assert_not_called()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()
