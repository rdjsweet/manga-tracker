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
- PostgreSQL
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

3. **Set up the PostgreSQL database**

   You need to create a PostgreSQL database and configure the connection settings:

   - Create a database named `manga_tracker` (or your preferred name).
   - Create an environment file `.env` in the root directory with the following variable (update with your credentials):

     ```env
     DATABASE_URL=postgresql://<username>:<password>@localhost:5432/manga_tracker
     ```

   - **Create tables:**

   Open your PostgreSQL client or connect using `psql` and execute the following SQL to create the necessary tables:

   ```sql
   CREATE TABLE users (
       id SERIAL PRIMARY KEY,
       username VARCHAR(150) UNIQUE NOT NULL,
       password_hash TEXT NOT NULL,
       first_login BOOLEAN DEFAULT TRUE
   );

   CREATE TABLE manga (
       id SERIAL PRIMARY KEY,
       title VARCHAR(255) NOT NULL,
       url TEXT NOT NULL,
       last_checked TIMESTAMP,
       chapter_count INTEGER,
       latest_chapter_title VARCHAR(255),
       new_chapters_count INTEGER DEFAULT 0,
       user_id INTEGER NOT NULL,
       FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
   );

   CREATE TABLE log (
       id SERIAL PRIMARY KEY,
       manga_title VARCHAR(255),
       chapters_added INTEGER,
       date_added TIMESTAMP,
       user_id INTEGER NOT NULL,
       FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
   );
   ```

4. **Run the Application**
   ```sh
   flask run
   ```
   Open your browser and navigate to `http://127.0.0.1:5000/`

## Project Structure

- **app.py**: Main application file initializing the Flask app, registering Blueprints, and configuring settings.
- **views/**: Contains all route-related code, divided for better separation of concerns:
  - **auth.py**: Handles user registration, login, and logout functionality.
  - **manga.py**: Handles manga tracking, adding, updating, and deleting.
- **models/**: Contains database models (e.g., `User`, `Manga`, `Log`) to define the structure and handle data-related operations.
- **utils/**:
  - **db.py**: Contains helper functions for managing database connections.
- **templates/**: HTML templates for rendering pages.
- **static/**: Contains CSS and other static assets for styling and frontend purposes.

## Technologies Used

- **Python**: Backend scripting language.
- **Flask**: Web framework used to build the application.
- **PostgreSQL**: Database for storing users, manga, and logs.
- **BeautifulSoup**: For web scraping manga details from MangaPill.
- **Flask-Login**: Manages user authentication.
- **WTForms**: Provides form validation for registration and login.

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
```