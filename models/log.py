from . import db

class Log(db.Model):
    __tablename__ = 'log'

    id = db.Column(db.Integer, primary_key=True)
    manga_title = db.Column(db.String(255))
    chapters_added = db.Column(db.Integer)
    date_added = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    user = db.relationship('User', backref='logs')

    def __repr__(self):
        return f'<Log {self.manga_title} - {self.date_added}>'
