from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from functools import wraps
import os

# ---------------- APP SETUP ----------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

# ---------------- DATABASE CONFIG ----------------
db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "student_db"),
    "port": int(os.getenv("DB_PORT", 3306))
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# ---------------- LOGIN SETUP ----------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "home"

# ---------------- USER MODEL ----------------
class User(UserMixin):
    def __init__(self, id, role, name, original_id):
        self.id = id
        self.role = role
        self.name = name
        self.original_id = original_id

    def get_id(self):
        return self.id

    @property
    def is_admin(self):
        return self.role == "SUPER_ADMIN"

    @property
    def is_college(self):
        return self.role == "COLLEGE_ADMIN"

    @property
    def is_student(self):
        return self.role == "STUDENT"

    @property
    def is_teacher(self):
        return self.role == "TEACHER"

# ---------------- USER LOADER ----------------
@login_manager.user_loader
def load_user(user_id):
    try:
        role, db_id = user_id.split(":")
    except ValueError:
        return None

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    tables = {
        "SUPER_ADMIN": ("users", "username"),
        "COLLEGE_ADMIN": ("colleges", "college_name"),
        "STUDENT": ("students", "name"),
        "TEACHER": ("teachers", "name")
    }

    user = None
    if role in tables:
        table, name_col = tables[role]
        cursor.execute(f"SELECT * FROM {table} WHERE id=%s", (db_id,))
        data = cursor.fetchone()
        if data:
            user = User(user_id, role, data[name_col], db_id)

    conn.close()
    return user

# ---------------- DECORATORS ----------------
def role_required(check):
    def wrapper(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            if not check():
                flash("Unauthorized Access")
                return redirect(url_for("home"))
            return f(*args, **kwargs)
        return decorated
    return wrapper

admin_required   = role_required(lambda: current_user.is_admin)
college_required = role_required(lambda: current_user.is_college)
teacher_required = role_required(lambda: current_user.is_teacher)
student_required = role_required(lambda: current_user.is_student)

# ---------------- HOME ----------------
@app.route("/")
def home():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin_dashboard"))
        if current_user.is_college:
            return redirect(url_for("college_dashboard"))
        if current_user.is_teacher:
            return redirect(url_for("teacher_dashboard"))
        if current_user.is_student:
            return redirect(url_for("student_dashboard"))
    return render_template("index.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

# ================= COLLEGE LOGIN (🔥 FIX) =================
@app.route("/college/login", methods=["GET", "POST"], endpoint="college_login")
def college_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM colleges WHERE email=%s AND password=%s",
            (email, password)
        )
        data = cursor.fetchone()
        conn.close()

        if data:
            user = User(
                f"COLLEGE_ADMIN:{data['id']}",
                "COLLEGE_ADMIN",
                data["college_name"],
                data["id"]
            )
            login_user(user)
            return redirect(url_for("college_dashboard"))

        flash("Invalid College Credentials")

    return render_template("college/login.html")

@app.route("/college/dashboard")
@college_required
def college_dashboard():
    return render_template("college/dashboard.html")

# ---------------- TEACHER ----------------
@app.route("/teacher/login", methods=["GET", "POST"])
def teacher_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM teachers WHERE email=%s AND password=%s",
            (email, password)
        )
        data = cursor.fetchone()
        conn.close()

        if data:
            user = User(f"TEACHER:{data['id']}", "TEACHER", data["name"], data["id"])
            login_user(user)
            return redirect(url_for("teacher_dashboard"))

        flash("Invalid Teacher Credentials")

    return render_template("teacher/login.html")

@app.route("/teacher/dashboard")
@teacher_required
def teacher_dashboard():
    return render_template("teacher/dashboard.html")

# ---------------- ADMIN ----------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username, password)
        )
        data = cursor.fetchone()
        conn.close()

        if data:
            user = User(
                f"SUPER_ADMIN:{data['id']}",
                "SUPER_ADMIN",
                data["username"],
                data["id"]
            )
            login_user(user)
            return redirect(url_for("admin_dashboard"))

        flash("Invalid Admin Credentials")

    return render_template("admin/login.html")

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    return render_template("admin/dashboard.html")

# ---------------- STUDENT ----------------
@app.route("/student/login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        student_id = request.form["student_id"]
        dob = request.form["dob"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM students WHERE student_id=%s AND dob=%s",
            (student_id, dob)
        )
        data = cursor.fetchone()
        conn.close()

        if data:
            user = User(f"STUDENT:{data['id']}", "STUDENT", data["name"], data["id"])
            login_user(user)
            return redirect(url_for("student_dashboard"))

        flash("Invalid Student Login")

    return render_template("student/login.html")

@app.route("/student/dashboard")
@student_required
def student_dashboard():
    return render_template("student/dashboard.html")