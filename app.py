from flask import Flask, request, jsonify, render_template, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

# DB Helper Function
def get_db_connection():
    connection = sqlite3.connect('manga_tracker.sqlite3')
    connection.row_factory = sqlite3.Row # Allows us to access columns by name
    return connection

# Home Route
@app.route('/')
def index():
    connection = get_db_connection()
    manga_list = connection.execute('SELECT * FROM manga').fetchall()
    connection.close()
    return render_template('index.html', manga_list=manga_list)

# Add Manga Route
@app.route('/add', methods=('GET', 'POST'))
def add_manga():
    if request.method == 'POST':
        title = request.form['title']
        url = request.form['url']
        chapter_count = request.form.get('chapter_count', 0)
        
        connection = get_db_connection()
        connection.execute(
            'INSERT INTO manga (title,  url, last_checked, chapter_count) VALUES (?, ?, ?, ?)',
            (title, url, datetime.now(), chapter_count)
        )
        connection.commit()
        connection.close()
        return redirect(url_for('index'))
    
    return render_template('add_manga.html')

# Delete Manga Route
@app.route('/delete/<int:id>')
def delete_manga(id):
    connection = get_db_connection()
    connection.execute('DELETE FROM Manga WHERE id = ?', (id,))
    connection.commit()
    connection.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)