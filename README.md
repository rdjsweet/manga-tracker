# MangaPill Chapter Tracker

Welcome to the **MangaPill Chapter Tracker**! This project helps you easily track manga chapter releases from [MangaPill](https://mangapill.com), allowing users to stay updated with the latest chapters of their favorite series. It's built to give each user a personalized experience, making manga tracking simple and intuitive.

## Features

- **Track Manga Releases**: Add manga by pasting a URL from MangaPill, and the tracker will keep track of new chapters.
- **User Accounts**: Sign up and log in to create a personalized manga list.
- **Activity Log**: Each user has their own activity log, showing the latest updates and changes to their tracked manga, such as new chapter releases.
- **One-Page Interface**: Add new manga, view tracked manga, and check updates—all from a single page.
- **Notification System**: Get notified when new chapters are available, with easy links to read them on MangaPill.
- **Logs for History**: Keep a history of notifications, so you can always know when new chapters were added.

## Getting Started

To get started with the MangaPill Chapter Tracker locally:

### Prerequisites

- Python 3.x
- SQLite
- Flask and required Python packages (see requirements.txt)

### Installation

1. **Clone the repository**
   ```sh
   git clone https://github.com/yourusername/manga-tracker.git
   cd manga-tracker
   ```

2. **Install dependencies**
   ```sh
   pip install -r requirements.txt
   ```

3. **Set up the database**
   ```sh
   python
   >>> from app import get_db_connection
   >>> connection = get_db_connection()
   >>> connection.execute("""
   CREATE TABLE IF NOT EXISTS User (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       username TEXT UNIQUE NOT NULL,
       password_hash TEXT NOT NULL,
       first_login BOOLEAN DEFAULT 1
   );
   CREATE TABLE IF NOT EXISTS Manga (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       title TEXT NOT NULL,
       url TEXT NOT NULL,
       last_checked DATETIME,
       chapter_count INTEGER,
       latest_chapter_title TEXT,
       new_chapters_count INTEGER,
       user_id INTEGER,
       FOREIGN KEY(user_id) REFERENCES User(id)
   );
   CREATE TABLE IF NOT EXISTS Log (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       manga_title TEXT,
       chapters_added INTEGER,
       date_added DATETIME,
       user_id INTEGER,
       FOREIGN KEY(user_id) REFERENCES User(id)
   );
   """
   >>> connection.close()
   ```

4. **Run the Application**
   ```sh
   flask run
   ```
   Open your browser and navigate to `http://127.0.0.1:5000/`

## Project Structure

- **app.py**: Main application file containing routes for user authentication, manga management, and logging.
- **scraper.py**: Handles scraping of manga information from MangaPill.
- **helpers.py**: Contains reusable utility functions like database connections.
- **routes/**: Directory with separate route modules to keep concerns organized (e.g., `auth.py` for user routes, `manga.py` for manga-related routes).
- **templates/**: HTML templates for rendering pages.
- **static/**: Contains CSS and other static assets.

## Technologies Used

- **Python**: Backend scripting language.
- **Flask**: Web framework used to build the application.
- **SQLite**: Simple database for local storage of users, manga, and logs.
- **BeautifulSoup**: For web scraping manga details from MangaPill.
- **Flask-Login**: Manages user authentication.

## Future Improvements

- **Advanced User Preferences**: Allow users to customize how frequently they want to check for updates.
- **Automated Notifications**: Send notifications via email when a new chapter is available.
- **Deployment**: Deploy the app to a cloud platform like Heroku for broader access.

## Contributing

Contributions are welcome! If you'd like to help make MangaPill Chapter Tracker even better:
1. Fork the repository.
2. Create a new branch.
3. Make your changes.
4. Submit a pull request.

## License

This project is open-source, licensed under the MIT License. Feel free to use and modify it as you see fit!

---

Thanks for checking out the MangaPill Chapter Tracker! If you have any questions or feedback, feel free to open an issue or reach out.