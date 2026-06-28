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


def test_fourth_value_is_cover_url_from_og_image():
    html = '''<html><head>
        <meta property="og:image" content="https://cdn.example.com/cover/42.jpeg">
        </head><body>
        <h1 class="font-bold text-lg md:text-2xl">My Manga</h1>
        <div id="chapters">
            <a class="border border-border p-1 hover:bg-brand hover:text-white" href="/c/1">Ch 1</a>
        </div></body></html>'''
    with patch('scraper.requests.get', return_value=_mock_response(html)):
        from scraper import scrape_manga_details
        title, titles, urls, cover_url = scrape_manga_details('https://example.com')
    assert title == 'My Manga'
    assert cover_url == 'https://cdn.example.com/cover/42.jpeg'
    assert titles == ['Ch 1']


def test_cover_url_none_when_no_og_image():
    html = '''<html><body>
        <h1 class="font-bold text-lg md:text-2xl">My Manga</h1>
        <div id="chapters">
            <a class="border border-border p-1 hover:bg-brand hover:text-white" href="/c/1">Ch 1</a>
        </div></body></html>'''
    with patch('scraper.requests.get', return_value=_mock_response(html)):
        from scraper import scrape_manga_details
        _, __, ___, cover_url = scrape_manga_details('https://example.com')
    assert cover_url is None
