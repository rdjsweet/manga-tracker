from . import db

class Manga(db.Model):
    __tablename__ = 'manga'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    url = db.Column(db.Text, nullable=False)
    last_checked = db.Column(db.DateTime)
    chapter_count = db.Column(db.Integer)
    latest_chapter_title = db.Column(db.String(255))
    new_chapters_count = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    user = db.relationship('User', backref='manga')

    def __repr__(self):
        return f'<Manga {self.title}>'
