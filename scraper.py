import requests
from bs4 import BeautifulSoup


def _extract_cover(soup):
    """Return the cover image URL from a MangaPill page, or None.

    The og:image meta tag is the most reliable cover source on MangaPill.
    """
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        return og_image["content"].strip()
    return None


def scrape_manga_details(url):
    """Scrape a MangaPill chapter-list page.

    Returns a 4-tuple: (title, chapter_titles, chapter_urls, cover_url).
    On any failure the leading elements are None so callers can guard on title.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        title_tag = soup.find("h1", class_="font-bold text-lg md:text-2xl")
        if not title_tag:
            print("Could not find the manga title element on the page.")
            return None, None, None, None

        title = title_tag.text.strip()
        cover_url = _extract_cover(soup)

        chapters_div = soup.find("div", id="chapters")
        if not chapters_div:
            print("Could not find the 'chapters' element on the page.")
            return title, None, None, cover_url

        chapter_links = chapters_div.find_all(
            "a", class_="border border-border p-1 hover:bg-brand hover:text-white"
        )

        chapter_titles = [link.text.strip() for link in chapter_links]
        chapter_urls = ["https://www.mangapill.com" + link["href"] for link in chapter_links]

        chapter_titles.reverse()
        chapter_urls.reverse()

        if not chapter_titles:
            print("No chapters found on the page.")
            return title, [], [], cover_url

        return title, chapter_titles, chapter_urls, cover_url

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return None, None, None, None


if __name__ == "__main__":
    manga_url = "https://www.mangapill.com/manga/8/kingdom"
    title, chapter_titles, chapter_urls, cover_url = scrape_manga_details(manga_url)

    if title:
        print(f"Title: {title}")
        print(f"Cover: {cover_url}")
        print(f"Chapter Count: {len(chapter_titles)}")
        for chap_title, chap_url in zip(chapter_titles, chapter_urls):
            print(f"{chap_title} -> {chap_url}")
    else:
        print("Failed to get manga details.")
