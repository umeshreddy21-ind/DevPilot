from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    fullname = db.Column(db.String(100), nullable=False)

    email = db.Column(db.String(100), unique=True, nullable=False)

    password = db.Column(db.String(255), nullable=False)
class Project(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(100), nullable=False)

    description = db.Column(db.Text, nullable=False)

    status = db.Column(db.String(20), nullable=False, default="Pending")
    category = db.Column(db.String(50), nullable=False, default="Other")
    priority = db.Column(
        db.String(20),
        nullable=False,
        default="Medium"
    ) 
    due_date = db.Column(db.Date, nullable=True)
    project_file = db.Column(db.String(255))
    user_email = db.Column(db.String(100), nullable=False)
class Note(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), nullable=False)

    content = db.Column(db.Text, nullable=False)

    user_email = db.Column(db.String(100), nullable=False)

