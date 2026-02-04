from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager, UserMixin,
    login_user, login_required,
    logout_user, current_user
)
import mysql.connector
import os

# ================= APP =================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

# ================= DB CONFIG =================
db_config = {
    "host": os.getenv("MYSQLHOST"),
    "user": os.getenv("MYSQLUSER"),
    "password": os.getenv("MYSQLPASSWORD"),
    "database": os.getenv("MYSQLDATABASE"),
    "port": int(os.getenv("MYSQLPORT", 3306))
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# ================= LOGIN MANAGER =================
login_manager = LoginManager()
login_manager.init_app(app)

# 🔥 VERY IMPORTANT (fixes direct admin redirect issue)
login_manager.login_view = "home"

# ================= USER MODEL =================
class User(UserMixin):
    def __init__(self, uid, role, name=None):
        self.id = uid
        self.role = role
        self.name = name

    @property
    def is_admin(self):
        return self.role == "SUPER_ADMIN"

# ================= USER LOADER =================
@login_manager.user_loader
def load_user(user_id):
    try:
        role, db_id = user_id.split(":")
    except ValueError:
        return None

    if role != "SUPER_ADMIN":
        return None

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM super_admin WHERE id=%s",
        (db_id,)
    )
    admin = cursor.fetchone()
    conn.close()

    if not admin:
        return None

    return User(
        f"SUPER_ADMIN:{admin['id']}",
        "SUPER_ADMIN",
        admin["email"]
    )

# ================= HOME (CARDS PAGE) =================
@app.route("/")
def home():
    # 🔥 This MUST open first
    return render_template("index.html")

# ================= SUPER ADMIN LOGIN =================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM super_admin WHERE email=%s AND password=%s",
            (email, password)
        )
        admin = cursor.fetchone()
        conn.close()

        if admin:
            user = User(
                f"SUPER_ADMIN:{admin['id']}",
                "SUPER_ADMIN",
                admin["email"]
            )
            login_user(user)
            return redirect(url_for("admin_dashboard"))

        flash("Invalid Admin Credentials ❌")

    return render_template("admin/login.html")

# ================= ADMIN DASHBOARD =================
@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM colleges")
    colleges = cursor.fetchall()
    conn.close()

    return render_template(
        "admin/dashboard.html",
        colleges=colleges
    )
# ================= COLLEGE LOGIN =================
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
        college = cursor.fetchone()
        conn.close()

        if college:
            # future lo college dashboard redirect cheyochu
            return "College Login Success ✅"

        flash("Invalid College Credentials ❌")

    return render_template("college/login.html")
# ================= CREATE COLLEGE =================
@app.route("/admin/create_college", methods=["POST"])
@login_required
def create_college():
    if not current_user.is_admin:
        return redirect(url_for("home"))

    # 🔥 MUST match HTML input names
    college_name = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("password")

    if not college_name or not email or not password:
        flash("All fields are required ❌")
        return redirect(url_for("admin_dashboard"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO colleges (college_name, email, password) VALUES (%s,%s,%s)",
        (college_name, email, password)
    )
    conn.commit()
    conn.close()

    flash("College created successfully ✅")
    return redirect(url_for("admin_dashboard"))

# ================= LOGOUT =================
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)