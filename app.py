from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from flask import make_response
from reportlab.pdfgen import canvas
from io import BytesIO
import os
import uuid
from urllib.parse import urlparse
from werkzeug.utils import secure_filename
from models import db, User, Project, Note
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# ==========================================
# Upload Configuration
# ==========================================

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "static",
    "uploads"
)

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "pdf",
    "doc",
    "docx"
}


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ==========================================
# Secret Key
# ==========================================

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "devpilot_secret_key"
)

# ==========================================
# Database Configuration
# ==========================================

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:

    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace(
            "postgres://",
            "postgresql://",
            1
        )

    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL

else:

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

        # Remove unwanted spaces
        fullname = request.form["fullname"].strip()
        email = request.form["email"].strip()
        password = request.form["password"].strip()

        # ----------------------------
        # Server-side Validation
        # ----------------------------

        if len(fullname) < 3 or len(fullname) > 100:
            flash("Full name must be between 3 and 100 characters.", "danger")
            return redirect(url_for("register"))

        if not email:
            flash("Email is required.", "danger")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("Email already registered!", "danger")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        new_user = User(
            fullname=fullname,
            email=email,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")

        return redirect(url_for("login"))

    return render_template("register.html")
# ==========================================
# Login
# ==========================================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        # Remove unwanted spaces
        email = request.form["email"].strip()
        password = request.form["password"].strip()

        # ----------------------------
        # Server-side Validation
        # ----------------------------

        if not email:
            flash("Email is required.", "danger")
            return redirect(url_for("login"))

        if not password:
            flash("Password is required.", "danger")
            return redirect(url_for("login"))

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):

            session["user"] = user.fullname
            session["email"] = user.email

            flash(f"Welcome back, {user.fullname}!", "success")

            return redirect(url_for("dashboard"))

        flash("Invalid email or password!", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


# ==========================================
# Dashboard
# ==========================================

@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect(url_for("login"))

    user_email = session["email"]

    today = datetime.today().date()

    # =====================================
    # Basic Statistics
    # =====================================

    projects_count = Project.query.filter_by(
        user_email=user_email
    ).count()

    notes_count = Note.query.filter_by(
        user_email=user_email
    ).count()

    pending_count = Project.query.filter_by(
        user_email=user_email,
        status="Pending"
    ).count()

    in_progress_count = Project.query.filter_by(
        user_email=user_email,
        status="In Progress"
    ).count()

    completed_count = Project.query.filter_by(
        user_email=user_email,
        status="Completed"
    ).count()

    high_priority_count = Project.query.filter_by(
        user_email=user_email,
        priority="High"
    ).count()

    medium_priority_count = Project.query.filter_by(
        user_email=user_email,
        priority="Medium"
    ).count()

    low_priority_count = Project.query.filter_by(
        user_email=user_email,
        priority="Low"
    ).count()

    # =====================================
    # Completion Percentage
    # =====================================

    if projects_count:

        completion_percentage = int(
            (completed_count / projects_count) * 100
        )

    else:

        completion_percentage = 0

    # =====================================
    # Overdue Projects
    # =====================================

    overdue_projects = Project.query.filter(

        Project.user_email == user_email,

        Project.due_date != None,

        Project.due_date < today,

        Project.status != "Completed"

    ).order_by(Project.due_date.asc()).all()

    # =====================================
    # Upcoming Deadlines
    # =====================================

    upcoming_projects = Project.query.filter(

        Project.user_email == user_email,

        Project.due_date != None,

        Project.due_date >= today

    ).order_by(Project.due_date.asc()).limit(5).all()

    # =====================================
    # Recent Projects
    # =====================================

    recent_projects = Project.query.filter_by(

        user_email=user_email

    ).order_by(Project.id.desc()).limit(5).all()

    # =====================================
    # Category Statistics
    # =====================================

    categories = [

        "Web",

        "Python",

        "Java",

        "Machine Learning",

        "Database",

        "Other"

    ]

    category_counts = []

    for category in categories:

        count = Project.query.filter_by(

            user_email=user_email,

            category=category

        ).count()

        category_counts.append(count)

    # =====================================
    # Status Chart
    # =====================================

    status_labels = [

        "Pending",

        "In Progress",

        "Completed"

    ]

    status_counts = [

        pending_count,

        in_progress_count,

        completed_count

    ]

    # =====================================
    # Priority Chart
    # =====================================

    priority_labels = [

        "High",

        "Medium",

        "Low"

    ]

    priority_counts = [

        high_priority_count,

        medium_priority_count,

        low_priority_count

    ]

    # =====================================
    # Render
    # =====================================

    return render_template(

        "dashboard.html",

        username=session["user"],

        email=session["email"],

        projects_count=projects_count,

        notes_count=notes_count,

        pending_count=pending_count,

        in_progress_count=in_progress_count,

        completed_count=completed_count,

        completion_percentage=completion_percentage,

        high_priority_count=high_priority_count,

        recent_projects=recent_projects,

        upcoming_projects=upcoming_projects,

        overdue_projects=overdue_projects,

        category_labels=categories,

        category_counts=category_counts,

        status_labels=status_labels,

        status_counts=status_counts,

        priority_labels=priority_labels,

        priority_counts=priority_counts

    )
# ==========================================
# Projects
# ==========================================

@app.route("/projects", methods=["GET", "POST"])
def projects():

    if "user" not in session:
        return redirect(url_for("login"))

    user_email = session["email"]

    # =====================================
    # Create Project
    # =====================================

    if request.method == "POST":

        title = request.form["title"].strip()

        description = request.form["description"].strip()

        status = request.form["status"]

        category = request.form["category"]

        priority = request.form["priority"]

        due_date = request.form.get("due_date")

        if due_date:

            due_date = datetime.strptime(
                due_date,
                "%Y-%m-%d"
            ).date()

        else:

            due_date = None

        # =====================================
        # File Upload
        # =====================================

        uploaded_file = request.files.get("project_file")

        filename = None

        if uploaded_file and uploaded_file.filename:

            if not allowed_file(uploaded_file.filename):

                flash(
                    "Only PNG, JPG, JPEG, PDF, DOC and DOCX files are allowed.",
                    "danger"
                )

                return redirect(
                    url_for("projects")
                )

            extension = uploaded_file.filename.rsplit(
                ".",
                1
            )[1].lower()

            filename = f"{uuid.uuid4()}.{extension}"

            uploaded_file.save(

                os.path.join(

                    app.config["UPLOAD_FOLDER"],

                    filename

                )

            )
            # =====================================
        # Validation
        # =====================================

        if len(title) < 3 or len(title) > 100:

            flash(
                "Project title must be between 3 and 100 characters.",
                "danger"
            )

            return redirect(
                url_for("projects")
            )

        if len(description) < 10:

            flash(
                "Description must contain at least 10 characters.",
                "danger"
            )

            return redirect(
                url_for("projects")
            )

        project = Project(

            title=title,

            description=description,

            status=status,

            category=category,

            priority=priority,

            due_date=due_date,

            project_file=filename,

            user_email=user_email

        )

        db.session.add(project)

        db.session.commit()

        flash(

            "Project created successfully!",

            "success"

        )

        return redirect(
            url_for("projects")
        )

    # =====================================
    # Search / Filter / Sort
    # =====================================

    search_query = request.args.get(
        "search",
        ""
    ).strip()

    category_filter = request.args.get(
        "category",
        ""
    ).strip()

    status_filter = request.args.get(
        "status",
        ""
    ).strip()

    priority_filter = request.args.get(
        "priority",
        ""
    ).strip()

    due_filter = request.args.get(
        "due",
        ""
    ).strip()

    sort_by = request.args.get(
        "sort",
        ""
    )

    page = request.args.get(
        "page",
        1,
        type=int
    )

    per_page = 5

    query = Project.query.filter_by(
        user_email=user_email
    )
        # =====================================
    # Search
    # =====================================

    if search_query:

        query = query.filter(

            or_(

                Project.title.ilike(
                    f"%{search_query}%"
                ),

                Project.description.ilike(
                    f"%{search_query}%"
                )

            )

        )

    # =====================================
    # Category Filter
    # =====================================

    if category_filter:

        query = query.filter(

            Project.category == category_filter

        )

    # =====================================
    # Status Filter
    # =====================================

    if status_filter:

        query = query.filter(

            Project.status == status_filter

        )

    # =====================================
    # Priority Filter
    # =====================================

    if priority_filter:

        query = query.filter(

            Project.priority == priority_filter

        )

    # =====================================
    # Due Date Filter
    # =====================================

    today = datetime.today().date()

    if due_filter == "today":

        query = query.filter(

            Project.due_date == today

        )

    elif due_filter == "upcoming":

        query = query.filter(

            Project.due_date > today

        )

    elif due_filter == "overdue":

        query = query.filter(

            Project.due_date < today,

            Project.status != "Completed"

        )

    # =====================================
    # Sorting
    # =====================================

    if sort_by == "title_asc":

        query = query.order_by(

            Project.title.asc()

        )

    elif sort_by == "title_desc":

        query = query.order_by(

            Project.title.desc()

        )

    elif sort_by == "due_asc":

        query = query.order_by(

            Project.due_date.asc()

        )

    elif sort_by == "due_desc":

        query = query.order_by(

            Project.due_date.desc()

        )

    elif sort_by == "status":

        query = query.order_by(

            Project.status.asc()

        )

    else:

        query = query.order_by(

            Project.id.desc()

        )
        # =====================================
    # Pagination
    # =====================================

    pagination = query.paginate(

        page=page,

        per_page=per_page,

        error_out=False

    )

    all_projects = pagination.items

    # =====================================
    # Statistics
    # =====================================

    total_projects = Project.query.filter_by(

        user_email=user_email

    ).count()

    completed_projects = Project.query.filter_by(

        user_email=user_email,

        status="Completed"

    ).count()

    in_progress_projects = Project.query.filter_by(

        user_email=user_email,

        status="In Progress"

    ).count()

    pending_projects = Project.query.filter_by(

        user_email=user_email,

        status="Pending"

    ).count()

    if total_projects:

        completion_percentage = int(

            (completed_projects / total_projects) * 100

        )

    else:

        completion_percentage = 0

    # =====================================
    # Render Page
    # =====================================

    return render_template(

        "projects.html",

        projects=all_projects,

        pagination=pagination,

        search_query=search_query,

        category_filter=category_filter,

        status_filter=status_filter,

        priority_filter=priority_filter,

        due_filter=due_filter,

        sort_by=sort_by,

        total_projects=total_projects,

        completed_projects=completed_projects,

        in_progress_projects=in_progress_projects,

        pending_projects=pending_projects,

        completion_percentage=completion_percentage,

        today=today

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

        title = request.form["title"].strip()

        description = request.form["description"].strip()

        status = request.form["status"]

        category = request.form["category"]

        priority = request.form["priority"]

        due_date = request.form.get("due_date")

        if due_date:

            due_date = datetime.strptime(
                due_date,
                "%Y-%m-%d"
            ).date()

        else:

            due_date = None

        # =====================================
        # File Upload
        # =====================================

        uploaded_file = request.files.get("project_file")

        if uploaded_file and uploaded_file.filename:

            if not allowed_file(uploaded_file.filename):

                flash(

                    "Only PNG, JPG, JPEG, PDF, DOC and DOCX files are allowed.",

                    "danger"

                )

                return redirect(

                    url_for(

                        "edit_project",

                        project_id=project.id

                    )

                )

            # Delete old file

            if project.project_file:

                old_file = os.path.join(

                    app.config["UPLOAD_FOLDER"],

                    project.project_file

                )

                if os.path.exists(old_file):

                    os.remove(old_file)

            extension = uploaded_file.filename.rsplit(
                ".",
                1
            )[1].lower()

            filename = f"{uuid.uuid4()}.{extension}"

            uploaded_file.save(

                os.path.join(

                    app.config["UPLOAD_FOLDER"],

                    filename

                )

            )

            project.project_file = filename
                    # =====================================
        # Server-side Validation
        # =====================================

        if len(title) < 3 or len(title) > 100:

            flash(
                "Project title must be between 3 and 100 characters.",
                "danger"
            )

            return redirect(
                url_for(
                    "edit_project",
                    project_id=project.id
                )
            )

        if len(description) < 10:

            flash(
                "Project description must be at least 10 characters long.",
                "danger"
            )

            return redirect(
                url_for(
                    "edit_project",
                    project_id=project.id
                )
            )

        # =====================================
        # Update Project
        # =====================================

        project.title = title

        project.description = description

        project.status = status

        project.category = category

        project.priority = priority

        project.due_date = due_date

        db.session.commit()

        flash(

            "Project updated successfully!",

            "success"

        )

        return redirect(
            url_for("projects")
        )

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

        flash(
            "Unauthorized access.",
            "danger"
        )

        return redirect(
            url_for("projects")
        )

    # =====================================
    # Delete Uploaded File
    # =====================================

    if project.project_file:

        file_path = os.path.join(

            app.config["UPLOAD_FOLDER"],

            project.project_file

        )

        if os.path.exists(file_path):

            os.remove(file_path)

    # =====================================
    # Delete Project
    # =====================================

    db.session.delete(project)

    db.session.commit()

    flash(

        "Project deleted successfully!",

        "success"

    )

    return redirect(
        url_for("projects")
    )


# ==========================================
# Export Projects to PDF
# ==========================================
@app.route("/export_pdf")
def export_pdf():

    if "user" not in session:
        return redirect(url_for("login"))

    projects = Project.query.filter_by(
        user_email=session["email"]
    ).order_by(
        Project.title.asc()
    ).all()

    buffer = BytesIO()

    pdf = canvas.Canvas(buffer)

    pdf.setTitle("DevPilot Projects Report")

    y = 800

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(
        180,
        y,
        "DevPilot Projects Report"
    )

    y -= 40

    pdf.setFont("Helvetica", 11)

    for project in projects:

        pdf.drawString(
            50,
            y,
            f"Title: {project.title}"
        )
        y -= 20

        pdf.drawString(
            50,
            y,
            f"Category: {project.category}"
        )
        y -= 20

        pdf.drawString(
            50,
            y,
            f"Status: {project.status}"
        )
        y -= 20

        if project.due_date:

            pdf.drawString(
                50,
                y,
                f"Due Date: {project.due_date.strftime('%d %b %Y')}"
            )

        else:

            pdf.drawString(
                50,
                y,
                "Due Date: Not Set"
            )

        y -= 20

        pdf.drawString(
            50,
            y,
            f"Description: {project.description[:80]}"
        )

        y -= 35

        # New Page
        if y < 80:

            pdf.showPage()

            pdf.setFont(
                "Helvetica",
                11
            )

            y = 800

    pdf.save()

    buffer.seek(0)

    response = make_response(
        buffer.getvalue()
    )

    response.headers["Content-Type"] = "application/pdf"

    response.headers["Content-Disposition"] = (
        "attachment; filename=DevPilot_Projects_Report.pdf"
    )

    return response
# ==========================================
# Notes
# ==========================================
@app.route("/notes", methods=["GET", "POST"])
def notes():

    if "user" not in session:
        return redirect(url_for("login"))

    # ---------------------------------------
    # Create Note
    # ---------------------------------------
    if request.method == "POST":

        title = request.form["title"].strip()
        content = request.form["content"].strip()

        # ----------------------------
        # Server-side Validation
        # ----------------------------

        if len(title) < 3 or len(title) > 100:
            flash(
                "Note title must be between 3 and 100 characters.",
                "danger"
            )
            return redirect(url_for("notes"))

        if len(content) < 5:
            flash(
                "Note content must be at least 5 characters long.",
                "danger"
            )
            return redirect(url_for("notes"))

        new_note = Note(
            title=title,
            content=content,
            user_email=session["email"]
        )

        db.session.add(new_note)
        db.session.commit()

        flash("Note created successfully!", "success")

        return redirect(url_for("notes"))

    # ---------------------------------------
    # Search Notes
    # ---------------------------------------

    search_query = request.args.get(
        "search",
        ""
    ).strip()

    query = Note.query.filter_by(
        user_email=session["email"]
    )

    if search_query:

        query = query.filter(

            or_(

                Note.title.ilike(
                    f"%{search_query}%"
                ),

                Note.content.ilike(
                    f"%{search_query}%"
                )

            )

        )

    all_notes = query.all()

    return render_template(

        "notes.html",

        notes=all_notes,

        search_query=search_query

    )


# ==========================================
# Edit Note
# ==========================================
@app.route("/edit_note/<int:note_id>", methods=["GET", "POST"])
def edit_note(note_id):

    if "user" not in session:
        return redirect(url_for("login"))

    note = Note.query.get_or_404(note_id)

    if note.user_email != session["email"]:
        return "Unauthorized!"

    if request.method == "POST":

        title = request.form["title"].strip()
        content = request.form["content"].strip()

        # ----------------------------
        # Server-side Validation
        # ----------------------------

        if len(title) < 3 or len(title) > 100:

            flash(
                "Note title must be between 3 and 100 characters.",
                "danger"
            )

            return redirect(
                url_for(
                    "edit_note",
                    note_id=note.id
                )
            )

        if len(content) < 5:

            flash(
                "Note content must be at least 5 characters long.",
                "danger"
            )

            return redirect(
                url_for(
                    "edit_note",
                    note_id=note.id
                )
            )

        note.title = title
        note.content = content

        db.session.commit()

        flash(
            "Note updated successfully!",
            "info"
        )

        return redirect(url_for("notes"))

    return render_template(

        "edit_note.html",

        note=note

    )


# ==========================================
# Delete Note
# ==========================================
@app.route("/delete_note/<int:note_id>")
def delete_note(note_id):

    if "user" not in session:
        return redirect(url_for("login"))

    note = Note.query.get_or_404(note_id)

    if note.user_email != session["email"]:
        return "Unauthorized!"

    db.session.delete(note)
    db.session.commit()

    flash(
        "Note deleted successfully!",
        "warning"
    )

    return redirect(url_for("notes"))
# ==========================================
# Logout
# ==========================================
@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out successfully.",
        "info"
    )

    return redirect(url_for("home"))


# ==========================================
# Run Application
# ==========================================
# ==========================================
# Error Handlers
# ==========================================

@app.errorhandler(404)
def page_not_found(error):

    return render_template(
        "404.html"
    ), 404


@app.errorhandler(500)
def internal_server_error(error):

    db.session.rollback()

    return render_template(
        "500.html"
    ), 500
if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    app.run(debug=True)