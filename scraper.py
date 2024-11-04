import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Function to scrape the chapter count from the given URL
def scrape_manga_details(url):
    try:
        #Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status() # This will raise an HTTPError if the response is not 200
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        title_tag = soup.find('h1', class_='font-bold text-lg md:text-2xl')
        if not title_tag:
            print("Could not find the manga title element on the page.")
            return None, None, None, None
        
        title = title_tag.text.strip()
        
        chapters_div = soup.find('div', id='chapters')
        if not chapters_div:
            print("Could not find the 'chapters' element on the page.")
            return title, None, None, None
        
        chapter_links = chapters_div.find_all('a', class_='border border-border p-1 hover:bg-brand hover:text-white')
        
        latest_chapter_title = chapter_links[0].text.strip()
        
        chapter_count = len(chapter_links)

        return title, latest_chapter_title, chapter_count
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return None
    except ValueError:
        print("Error parsing chapter count. Make sure the HTML element contains a valid integer.")
        return None
    
    
if __name__ == "__main__":
    manga_url = "https://www.mangapill.com/manga/8/kingdom"  # Replace with an actual manga URL from MangaPill
    chapter_count = scrape_manga_details(manga_url)
    if chapter_count is not None:
        print(f"The current chapter count for the manga is: {chapter_count}")
    else:
        print("Failed to get the chapter count.")