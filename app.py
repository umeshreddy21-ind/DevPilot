from flask import Flask, render_template, request, redirect, url_for, session
from models import db, User, Project, Note
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# ==========================================
# Secret Key
# ==========================================
app.secret_key = "devpilot_secret_key"

# ==========================================
# Database Configuration
# ==========================================
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///devpilot.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# ==========================================
# Home Page
# ==========================================
@app.route("/")
def home():
    return render_template("home.html")


# ==========================================
# Register
# ==========================================
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        fullname = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            return "Email already registered!"

        hashed_password = generate_password_hash(password)

        new_user = User(
            fullname=fullname,
            email=email,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


# ==========================================
# Login
# ==========================================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):

            session["user"] = user.fullname
            session["email"] = user.email

            return redirect(url_for("dashboard"))

        return "Invalid Email or Password!"

    return render_template("login.html")


# ==========================================
# Dashboard
# ==========================================
@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect(url_for("login"))

    projects_count = Project.query.filter_by(
        user_email=session["email"]
    ).count()

    return render_template(
        "dashboard.html",
        username=session["user"],
        email=session["email"],
        projects_count=projects_count
    )


# ==========================================
# Projects
# ==========================================
@app.route("/projects", methods=["GET", "POST"])
def projects():

    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]

        new_project = Project(
            title=title,
            description=description,
            user_email=session["email"]
        )

        db.session.add(new_project)
        db.session.commit()

        return redirect(url_for("projects"))

    all_projects = Project.query.filter_by(
        user_email=session["email"]
    ).all()

    return render_template(
        "projects.html",
        projects=all_projects
    )


# ==========================================
# Edit Project
# ==========================================
@app.route("/edit_project/<int:project_id>", methods=["GET", "POST"])
def edit_project(project_id):

    if "user" not in session:
        return redirect(url_for("login"))

    project = Project.query.get_or_404(project_id)

    if project.user_email != session["email"]:
        return "Unauthorized!"

    if request.method == "POST":

        project.title = request.form["title"]
        project.description = request.form["description"]

        db.session.commit()

        return redirect(url_for("projects"))

    return render_template(
        "edit_project.html",
        project=project
    )


# ==========================================
# Delete Project
# ==========================================
@app.route("/delete_project/<int:project_id>")
def delete_project(project_id):

    if "user" not in session:
        return redirect(url_for("login"))

    project = Project.query.get_or_404(project_id)

    if project.user_email != session["email"]:
        return "Unauthorized!"

    db.session.delete(project)
    db.session.commit()

    return redirect(url_for("projects"))


# ==========================================
# Logout
# ==========================================
@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# ==========================================
# Run Application
# ==========================================
if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    app.run(debug=True)