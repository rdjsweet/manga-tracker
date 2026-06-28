from unittest.mock import patch, MagicMock
import pytest
import requests as req_lib


def _mock_response(html):
    mock_resp = MagicMock()
    mock_resp.content = html.encode('utf-8')
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def test_returns_four_values_on_missing_title():
    html = '<html><body><p>No title</p></body></html>'
    with patch('scraper.requests.get', return_value=_mock_response(html)):
        from scraper import scrape_manga_details
        result = scrape_manga_details('https://example.com')
    assert len(result) == 4


def test_returns_four_values_on_request_error():
    with patch('scraper.requests.get', side_effect=req_lib.exceptions.RequestException('fail')):
        from scraper import scrape_manga_details
        result = scrape_manga_details('https://example.com')
    assert len(result) == 4


def test_returns_four_values_on_missing_chapters_div():
    html = '<html><body><h1 class="font-bold text-lg md:text-2xl">My Manga</h1></body></html>'
    with patch('scraper.requests.get', return_value=_mock_response(html)):
        from scraper import scrape_manga_details
        result = scrape_manga_details('https://example.com')
    assert len(result) == 4


def test_first_value_is_none_on_request_error():
    with patch('scraper.requests.get', side_effect=req_lib.exceptions.RequestException('fail')):
        from scraper import scrape_manga_details
        title, _, __, ___ = scrape_manga_details('https://example.com')
    assert title is None
