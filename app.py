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

# ================= LOGIN =================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "admin_login"

# ================= USER =================
class User(UserMixin):
    def __init__(self, uid, role):
        self.id = uid
        self.role = role

    @property
    def is_admin(self):
        return self.role == "SUPER_ADMIN"

# ================= USER LOADER =================
@login_manager.user_loader
def load_user(user_id):
    try:
        role, db_id = user_id.split(":")
    except:
        return None

    if role != "SUPER_ADMIN":
        return None

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM super_admin WHERE id=%s", (db_id,))
    data = cursor.fetchone()
    conn.close()

    if not data:
        return None

    return User(f"SUPER_ADMIN:{db_id}", "SUPER_ADMIN")

# ================= HOME =================
@app.route("/")
def home():
    return redirect(url_for("admin_login"))

# ================= ADMIN LOGIN =================
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
        admin = cursor.fetchone()
        conn.close()

        if admin:
            user = User(f"SUPER_ADMIN:{admin['id']}", "SUPER_ADMIN")
            login_user(user)
            return redirect(url_for("admin_dashboard"))

        flash("Invalid Admin Credentials")

    return render_template("admin/login.html")

# ================= ADMIN DASHBOARD =================
@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("Unauthorized")
        return redirect(url_for("admin_login"))
    return render_template("admin/dashboard.html")

# ================= ADMIN SETTINGS (FIXED) =================
@app.route("/admin/settings")
@login_required
def admin_settings():
    if not current_user.is_admin:
        flash("Unauthorized")
        return redirect(url_for("admin_login"))
    return render_template("admin/settings.html")

# ================= LOGOUT =================
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("admin_login"))

# ================= LOCAL =================
if __name__ == "__main__":
    app.run(debug=True)