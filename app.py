from flask import Flask, render_template, request, redirect, url_for, session
from models import db, User
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Secret Key
app.secret_key = "devpilot_secret_key"

# Database Configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///devpilot.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize Database
db.init_app(app)


# ==========================
# Home Page
# ==========================

@app.route("/")
def home():
    return render_template("home.html")


# ==========================
# Register Page
# ==========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        fullname = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            return "Email already registered!"

        # Hash Password
        hashed_password = generate_password_hash(password)

        # Create User
        new_user = User(
            fullname=fullname,
            email=email,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


# ==========================
# Login Page
# ==========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        print("\n========== LOGIN DEBUG ==========")
        print("Entered Email:", email)
        print("Entered Password:", password)

        user = User.query.filter_by(email=email).first()

        print("User Found:", user)

        if user:
            print("Stored Password Hash:", user.password)

            password_match = check_password_hash(user.password, password)
            print("Password Match:", password_match)

            if password_match:
                session["user"] = user.fullname
                session["email"] = user.email

                print("Login Successful!")
                print("===============================\n")

                return redirect(url_for("dashboard"))

        print("Login Failed!")
        print("===============================\n")

        return "Invalid Email or Password!"

    return render_template("login.html")


# ==========================
# Dashboard
# ==========================

@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        username=session["user"],
        email=session["email"]
    )


# ==========================
# Logout
# ==========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# ==========================
# Run Application
# ==========================

if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    app.run(debug=True)