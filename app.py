from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from flask_login import (
    LoginManager, UserMixin,
    login_user, login_required,
    logout_user, current_user
)
from functools import wraps
import os
from dotenv import load_dotenv
load_dotenv()
# ---------------- APP SETUP ----------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

# ---------------- DATABASE CONFIG (RAILWAY SAFE) ----------------
db_config = {
    "host": os.getenv("MYSQLHOST"),
    "user": os.getenv("MYSQLUSER"),
    "password": os.getenv("MYSQLPASSWORD"),
    "database": os.getenv("MYSQLDATABASE"),
    "port": int(os.getenv("MYSQLPORT", 3306))
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# ---------------- LOGIN SETUP ----------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "home"

# ---------------- USER MODEL ----------------
class User(UserMixin):
    def __init__(self, uid, role, name, db_id):
        self.id = uid
        self.role = role
        self.name = name
        self.db_id = db_id

    @property
    def is_admin(self):
        return self.role == "SUPER_ADMIN"

    @property
    def is_college(self):
        return self.role == "COLLEGE_ADMIN"

    @property
    def is_teacher(self):
        return self.role == "TEACHER"

    @property
    def is_student(self):
        return self.role == "STUDENT"

# ---------------- USER LOADER ----------------
@login_manager.user_loader
def load_user(user_id):
    try:
        role, db_id = user_id.split(":")
    except ValueError:
        return None

    tables = {
        "SUPER_ADMIN": ("users", "username"),
        "COLLEGE_ADMIN": ("colleges", "college_name"),
        "TEACHER": ("teachers", "name"),
        "STUDENT": ("students", "name"),
    }

    if role not in tables:
        return None

    table, name_col = tables[role]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"SELECT * FROM {table} WHERE id=%s", (db_id,))
    data = cursor.fetchone()
    conn.close()

    if not data:
        return None

    return User(f"{role}:{db_id}", role, data[name_col], db_id)

# ---------------- ROLE DECORATORS ----------------
def role_required(check):
    def decorator(f):
        @wraps(f)
        @login_required
        def wrapped(*args, **kwargs):
            if not check():
                flash("Unauthorized access")
                return redirect(url_for("home"))
            return f(*args, **kwargs)
        return wrapped
    return decorator

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

# ================= COLLEGE =================
@app.route("/college/login", methods=["GET", "POST"])
def college_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

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

        flash("Invalid college credentials")

    return render_template("college/login.html")

@app.route("/college/dashboard")
@college_required
def college_dashboard():
    return render_template("college/dashboard.html")

# ================= TEACHER =================
@app.route("/teacher/login", methods=["GET", "POST"])
def teacher_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            flash("Email and Password required")
            return redirect(url_for("teacher_login"))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM teachers WHERE email=%s AND password=%s",
            (email, password)
        )
        data = cursor.fetchone()
        conn.close()

        if data:
            user = User(
                f"TEACHER:{data['id']}",
                "TEACHER",
                data["name"],
                data["id"]
            )
            login_user(user)
            return redirect(url_for("teacher_dashboard"))

        flash("Invalid Teacher Credentials")
        return redirect(url_for("teacher_login"))

    return render_template("teacher/login.html")

@app.route("/teacher/dashboard")
@teacher_required
def teacher_dashboard():
    return render_template("teacher/dashboard.html")

# ================= ADMIN =================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM super_admin WHERE email=%s AND password=%s",
            (email, password)
        )

        data = cursor.fetchone()
        conn.close()

        if data:
            user = User(
                f"SUPER_ADMIN:{data['id']}",
                "SUPER_ADMIN",
                data["email"],   # 👈 username kaadu, email
                data["id"]
            )
            login_user(user)
            return redirect(url_for("admin_dashboard"))

        flash("Invalid admin credentials")

    return render_template("admin/login.html")
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    return render_template("admin/dashboard.html")

# ================= STUDENT =================
@app.route("/student/login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        student_id = request.form.get("student_id")
        dob = request.form.get("dob")

        if not student_id or not dob:
            flash("Student ID and DOB required")
            return redirect(url_for("student_login"))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM students WHERE student_id=%s AND dob=%s",
            (student_id, dob)
        )
        data = cursor.fetchone()
        conn.close()

        if data:
            user = User(
                f"STUDENT:{data['id']}",
                "STUDENT",
                data["name"],
                data["id"]
            )
            login_user(user)
            return redirect(url_for("student_dashboard"))

        flash("Invalid Student ID or Date of Birth")
        return redirect(url_for("student_login"))

    return render_template("student/login.html")

@app.route("/student/dashboard")
@student_required
def student_dashboard():
    return render_template("student/dashboard.html")

# ❌ app.run() NOT needed (Gunicorn handles it)
if __name__ == "__main__":
    app.run(debug=True)