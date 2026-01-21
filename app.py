from flask import Flask, render_template, request, redirect, url_for, flash, session
# Forced reload for template update v2
import mysql.connector
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from functools import wraps

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# MySQL Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Rajesh@123',
    'database': 'student_db'
}

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'home' # Redirect to home to choose login type if unauthorized

def get_db_connection():
    return mysql.connector.connect(**db_config)

# --- Role Based User Class ---
class User(UserMixin):
    def __init__(self, id, role, name, original_id):
        self.id = id # This will be "role:id"
        self.role = role
        self.name = name
        self.original_id = original_id # The actual DB ID

    def get_id(self):
        return self.id

    @property
    def is_admin(self):
        return self.role == 'SUPER_ADMIN'
        
    @property
    def is_college(self):
        return self.role == 'COLLEGE_ADMIN'

    @property
    def is_student(self):
        return self.role == 'STUDENT'

    @property
    def is_teacher(self):
        return self.role == 'TEACHER'

@login_manager.user_loader
def load_user(user_id):
    try:
        role, db_id = user_id.split(':')
    except ValueError:
        return None

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    user = None

    if role == 'SUPER_ADMIN':
        cursor.execute("SELECT * FROM users WHERE id = %s", (db_id,))
        data = cursor.fetchone()
        if data:
            user = User(id=user_id, role='SUPER_ADMIN', name=data['username'], original_id=db_id)
            
    elif role == 'COLLEGE_ADMIN':
        cursor.execute("SELECT * FROM colleges WHERE id = %s", (db_id,))
        data = cursor.fetchone()
        if data:
            user = User(id=user_id, role='COLLEGE_ADMIN', name=data['college_name'], original_id=db_id)
            
    elif role == 'STUDENT':
        cursor.execute("SELECT * FROM students WHERE id = %s", (db_id,))
        data = cursor.fetchone()
        if data:
            user = User(id=user_id, role='STUDENT', name=data['name'], original_id=db_id)

    elif role == 'TEACHER':
        cursor.execute("SELECT * FROM teachers WHERE id = %s", (db_id,))
        data = cursor.fetchone()
        if data:
            user = User(id=user_id, role='TEACHER', name=data['name'], original_id=db_id)
            
    conn.close()
    return user

# --- Decorators ---
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash("Unauthorized Access: Super Admin only.")
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def college_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_college:
            flash("Unauthorized Access: College Admin only.")
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_student:
            flash("Unauthorized Access: Students only.")
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def teacher_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_teacher:
            flash("Unauthorized Access: Teachers only.")
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@app.route("/")
def home():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        elif current_user.is_college:
            return redirect(url_for('college_dashboard'))
        elif current_user.is_student:
            return redirect(url_for('student_dashboard'))
        elif current_user.is_teacher:
            return redirect(url_for('teacher_dashboard'))
    return render_template("index.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

# --- TEACHER PANEL ---

@app.route("/teacher/login", methods=["GET", "POST"])
def teacher_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM teachers WHERE email = %s AND password = %s", (email, password))
        data = cursor.fetchone()
        conn.close()
        
        if data:
            user = User(id=f"TEACHER:{data['id']}", role='TEACHER', name=data['name'], original_id=data['id'])
            login_user(user)
            return redirect(url_for("teacher_dashboard"))
        else:
            flash("Invalid Teacher Credentials")
            
    return render_template("teacher/login.html")

@app.route("/teacher/dashboard")
@teacher_required
def teacher_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get requests for this college (Broadcast)
    cursor.execute("""
        SELECT ar.*, s.name as student_name, s.student_id as student_roll 
        FROM attendance_requests ar
        JOIN students s ON ar.student_id = s.id
        WHERE s.college_id = (SELECT college_id FROM teachers WHERE id = %s)
        ORDER BY ar.date DESC, ar.time DESC
    """, (current_user.original_id,))
    requests = cursor.fetchall()
    
    conn.close()
    return render_template("teacher/dashboard.html", requests=requests)

@app.route("/teacher/handle_request/<int:req_id>/<action>")
@teacher_required
def handle_request(req_id, action):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    new_status = 'Accepted' if action == 'accept' else 'Rejected'
    
    try:
        cursor.execute("""
            UPDATE attendance_requests 
            SET status = %s, accepted_by = %s, teacher_id = %s
            WHERE id = %s
        """, (new_status, current_user.name, current_user.original_id, req_id))
        
        if cursor.rowcount > 0:
            # If accepted, we might also want to update the main attendance summary table?
            # User requirement: "Teacher → Accept → attendance table lo status = Accepted"
            # It seems they want the 'attendance_requests' table to be THE status table.
            # But earlier logic used 'attendance' table for calculation.
            # I will Stick to upgrading the request status. 
            # If the user wants this to count towards "Total Present Days" percentage, I would need to update that too.
            # For now, I'll stick to the specific requirement: update status and accepted_by.
            
            # OPTIONAL: If accepted, increment present_days in main attendance table?
            # Requirement doesn't explicitly say "Update percentage". 
            # It mainly focuses on the "Pending/Accepted" flow.
            # I will add a small logic to update the main attendance table if Accepted, just to be safe and useful.
            
            if new_status == 'Accepted':
                 # Get student ID
                cursor.execute("SELECT student_id FROM attendance_requests WHERE id = %s", (req_id,))
                res = cursor.fetchone() # returns tuple (student_id,)
                if res:
                    s_id = res[0]
                    # Check if entry exists for this student in 'attendance' (summary table)
                    # Actually, the summary table structure is: total_days, present_days.
                    # It's hard to map a single request to 'total_days'. 
                    # So I will LEAVE the summary table alone to avoid messing up manual calculations unless requested.
                    pass

            conn.commit()
            flash(f"Request {new_status} successfully.")
        else:
             flash("Request not found or unauthorized.")
             
    except Exception as e:
        flash(f"Error: {e}")
    finally:
        conn.close()
        
    return redirect(url_for("teacher_dashboard"))

# --- SUPER ADMIN PANEL ---

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            user = User(id=f"SUPER_ADMIN:{user_data['id']}", role='SUPER_ADMIN', name=user_data['username'], original_id=user_data['id'])
            login_user(user)
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid Admin Credentials")
            
    return render_template("admin/login.html")

@app.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def admin_settings():
    if request.method == "POST":
        new_username = request.form["username"]
        new_password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        
        if not new_username:
             flash("Username cannot be empty")
             return redirect(url_for("admin_settings"))
             
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Update Username/Email
            if new_password:
                if new_password != confirm_password:
                    flash("Passwords do not match!")
                    conn.close()
                    return redirect(url_for("admin_settings"))
                else:
                    cursor.execute("UPDATE users SET username=%s, password=%s WHERE id=%s", (new_username, new_password, current_user.original_id))
            else:
                 cursor.execute("UPDATE users SET username=%s WHERE id=%s", (new_username, current_user.original_id))
            
            conn.commit()
            
            # Update current session user name
            current_user.name = new_username
            flash("Settings Updated Successfully! Login again with new credentials.")
            
        except mysql.connector.Error as err:
            flash(f"Error: {err}")
        finally:
            conn.close()
            
        return redirect(url_for("admin_settings"))

    return render_template("admin/settings.html")

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM colleges")
    colleges = cursor.fetchall()
    conn.close()
    return render_template("admin/dashboard.html", colleges=colleges)

@app.route("/admin/create_college", methods=["POST"])
@admin_required
def create_college():
    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO colleges (college_name, email, password) VALUES (%s, %s, %s)", (name, email, password))
        conn.commit()
    except mysql.connector.Error as err:
        flash(f"Error: {err}")
    finally:
        conn.close()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/block_college/<int:college_id>")
@admin_required
def block_college(college_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE colleges SET status = CASE WHEN status='active' THEN 'blocked' ELSE 'active' END WHERE id = %s", (college_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/edit_college/<int:college_id>", methods=["GET", "POST"])
@admin_required
def edit_college(college_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        
        try:
            if password:
                cursor.execute("UPDATE colleges SET college_name=%s, email=%s, password=%s WHERE id=%s", (name, email, password, college_id))
            else:
                cursor.execute("UPDATE colleges SET college_name=%s, email=%s WHERE id=%s", (name, email, college_id))
                
            conn.commit()
            flash("College details updated successfully!")
            return redirect(url_for("admin_dashboard"))
        except mysql.connector.Error as err:
            flash(f"Error: {err}")
            
    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()
    conn.close()
    
    return render_template("admin/edit_college.html", college=college)

@app.route("/admin/view_college/<int:college_id>")
@admin_required
def view_college(college_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get College Details
    cursor.execute("SELECT * FROM colleges WHERE id = %s", (college_id,))
    college = cursor.fetchone()
    
    # Get Students
    cursor.execute("SELECT * FROM students WHERE college_id = %s", (college_id,))
    students = cursor.fetchall()
    
    # Enhance Data
    for s in students:
        cursor.execute("SELECT grade FROM grades WHERE student_id = %s", (s['id'],))
        g = cursor.fetchone()
        s['grade'] = g['grade'] if g else 'N/A'
        
        cursor.execute("SELECT SUM(marks) as total FROM marks WHERE student_id = %s", (s['id'],))
        m = cursor.fetchone()
        s['total'] = m['total'] if m and m['total'] else 0
        
        cursor.execute("SELECT * FROM attendance WHERE student_id = %s", (s['id'],))
        a = cursor.fetchone()
        if a and a['total_days'] > 0:
            s['attendance'] = f"{round((a['present_days'] / a['total_days']) * 100, 1)}%"
        else:
            s['attendance'] = '0%'

        cursor.execute("SELECT * FROM marks WHERE student_id = %s", (s['id'],))
        s['subjects'] = cursor.fetchall() # Fetch specific subjects for detail view if needed

    conn.close()
    return render_template("admin/view_college.html", college=college, students=students)

# --- COLLEGE PANEL ---

@app.route("/college/login", methods=["GET", "POST"])
def college_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM colleges WHERE email = %s AND password = %s", (email, password))
        data = cursor.fetchone()
        conn.close()
        
        if data:
            if data['status'] == 'blocked':
                flash("Your College Account is BLOCKED. Contact Super Admin.")
                return render_template("college/login.html")
                
            user = User(id=f"COLLEGE_ADMIN:{data['id']}", role='COLLEGE_ADMIN', name=data['college_name'], original_id=data['id'])
            login_user(user)
            return redirect(url_for("college_dashboard"))
        else:
            flash("Invalid College Credentials")
            
    return render_template("college/login.html")

@app.route("/college/dashboard")
@college_required
def college_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get Filter
    group_filter = request.args.get('group')
    
    # List all students for THIS college
    query = "SELECT * FROM students WHERE college_id = %s"
    params = [current_user.original_id]
    
    if group_filter:
        query += " AND group_name = %s"
        params.append(group_filter)
        
    cursor.execute(query, tuple(params))
    students = cursor.fetchall()
    
    # Get Groups for Filter UI
    cursor.execute("SELECT DISTINCT group_name FROM students WHERE college_id = %s", (current_user.original_id,))
    groups_res = cursor.fetchall()
    groups = [g['group_name'] for g in groups_res if g['group_name']]
    
    # List all subjects for THIS college
    cursor.execute("SELECT * FROM subjects WHERE college_id = %s", (current_user.original_id,))
    subjects = cursor.fetchall()

    # List all EXAMS for THIS college
    cursor.execute("SELECT * FROM exams WHERE college_id = %s", (current_user.original_id,))
    exams = cursor.fetchall()
    
    # Enhance student data with Marks and Attendance
    for s in students:
        # Get Grade
        cursor.execute("SELECT grade FROM grades WHERE student_id = %s", (s['id'],))
        g = cursor.fetchone()
        s['grade'] = g['grade'] if g else 'N/A'
        
        # Get Total Marks
        cursor.execute("SELECT SUM(marks) as total FROM marks WHERE student_id = %s", (s['id'],))
        m = cursor.fetchone()
        s['total'] = m['total'] if m and m['total'] else 0
        
        # Get Attendance
        cursor.execute("SELECT * FROM attendance WHERE student_id = %s", (s['id'],))
        a = cursor.fetchone()
        if a and a['total_days'] > 0:
            s['attendance'] = f"{round((a['present_days'] / a['total_days']) * 100, 1)}%"
        else:
            s['attendance'] = '0%'
        
    conn.close()
    conn.close()
    return render_template("college/dashboard.html", students=students, subjects=subjects, groups=groups, selected_group=group_filter, exams=exams)

@app.route("/college/manage_teachers")
@college_required
def manage_teachers():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM teachers WHERE college_id = %s", (current_user.original_id,))
    teachers = cursor.fetchall()
    conn.close()
    return render_template("college/manage_teachers.html", teachers=teachers)

@app.route("/college/monitor_attendance")
@college_required
def monitor_attendance():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get all attendance requests for students of this college
    cursor.execute("""
        SELECT ar.*, s.name as student_name, t.name as teacher_name 
        FROM attendance_requests ar
        JOIN students s ON ar.student_id = s.id
        LEFT JOIN teachers t ON ar.teacher_id = t.id
        WHERE s.college_id = %s
        ORDER BY ar.date DESC, ar.time DESC
    """, (current_user.original_id,))
    requests = cursor.fetchall()
    
    conn.close()
    return render_template("college/monitor_attendance.html", requests=requests)

@app.route("/college/add_teacher", methods=["POST"])
@college_required
def add_teacher():
    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]
    subject = request.form["subject"]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO teachers (college_id, name, email, password, subject) VALUES (%s, %s, %s, %s, %s)", 
                       (current_user.original_id, name, email, password, subject))
        conn.commit()
        flash("Teacher added successfully!")
    except mysql.connector.Error as err:
        flash(f"Error: {err}")
    finally:
        conn.close()
    return redirect(url_for("manage_teachers"))

@app.route("/college/delete_teacher/<int:id>")
@college_required
def delete_teacher(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM teachers WHERE id = %s AND college_id = %s", (id, current_user.original_id))
    conn.commit()
    conn.close()
    flash("Teacher deleted.")
    return redirect(url_for("manage_teachers"))

@app.route("/college/add_subject", methods=["POST"])
@college_required
def add_subject():
    subject_name = request.form["subject_name"]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO subjects (college_id, subject_name) VALUES (%s, %s)", (current_user.original_id, subject_name))
        conn.commit()
        flash("Subject added successfully!")
    except mysql.connector.Error as err:
        flash(f"Error: {err}")
    finally:
        conn.close()
    return redirect(url_for("college_dashboard"))

@app.route("/college/delete_subject/<int:subject_id>")
@college_required
def delete_subject(subject_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Verify subject belongs to this college
    cursor.execute("SELECT * FROM subjects WHERE id = %s AND college_id = %s", (subject_id, current_user.original_id))
    subject = cursor.fetchone()
    
    if subject:
        cursor.execute("DELETE FROM subjects WHERE id = %s", (subject_id,))
        conn.commit()
        flash("Subject deleted successfully!")
    else:
        flash("Unauthorized deletion or Subject not found.")
        
    conn.close()
    conn.close()
    return redirect(url_for("college_dashboard"))

@app.route("/college/add_exam", methods=["POST"])
@college_required
def add_exam():
    exam_name = request.form["exam_name"]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO exams (college_id, exam_name) VALUES (%s, %s)", (current_user.original_id, exam_name))
        conn.commit()
        flash("Exam added successfully!")
    except mysql.connector.Error as err:
        flash(f"Error: {err}")
    finally:
        conn.close()
    return redirect(url_for("college_dashboard"))

@app.route("/college/delete_exam/<int:exam_id>")
@college_required
def delete_exam(exam_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM exams WHERE id = %s AND college_id = %s", (exam_id, current_user.original_id))
    exam = cursor.fetchone()
    
    if exam:
        cursor.execute("DELETE FROM exams WHERE id = %s", (exam_id,))
        conn.commit()
        flash("Exam deleted successfully!")
    else:
        flash("Unauthorized deletion.")
        
    conn.close()
    return redirect(url_for("college_dashboard"))

@app.route("/college/manage_classes", methods=["GET"])
@college_required
def manage_classes():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # List all classes for THIS college
    cursor.execute("SELECT * FROM classes WHERE college_id = %s", (current_user.original_id,))
    classes = cursor.fetchall()

    # Get Teachers for Dropdown
    cursor.execute("SELECT * FROM teachers WHERE college_id = %s", (current_user.original_id,))
    teachers = cursor.fetchall()
            
    conn.close()
    return render_template("college/manage_classes.html", classes=classes, teachers=teachers)

@app.route("/college/add_class", methods=["POST"])
@college_required
def add_class():
    class_name = request.form["class_name"]
    subject_name = request.form["subject_name"]
    teacher_name = request.form["teacher_name"]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO classes (college_id, class_name, subject_name, teacher_name) VALUES (%s, %s, %s, %s)", 
                       (current_user.original_id, class_name, subject_name, teacher_name))
        conn.commit()
        flash("Class added successfully!")
    except mysql.connector.Error as err:
        flash(f"Error: {err}")
    finally:
        conn.close()
    return redirect(url_for("manage_classes"))

@app.route("/college/delete_class/<int:class_id>")
@college_required
def delete_class(class_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Verify class belongs to this college
    cursor.execute("SELECT * FROM classes WHERE id = %s AND college_id = %s", (class_id, current_user.original_id))
    class_item = cursor.fetchone()
    
    if class_item:
        cursor.execute("DELETE FROM classes WHERE id = %s", (class_id,))
        conn.commit()
        flash("Class deleted successfully!")
    else:
        flash("Unauthorized deletion or Class not found.")
        
    conn.close()
    return redirect(url_for("manage_classes"))

@app.route("/college/add_mark_dashboard", methods=["POST"])
@college_required
def add_mark_dashboard():
    student_id_str = request.form["student_id"] # ID from form selection
    subject_name = request.form["subject"]
    exam_type = request.form.get("exam_type", "Semester")
    marks_val = float(request.form["marks"])
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) # Dictionary cursor for selects

    try:
        # Verify student belongs to this college
        cursor.execute("SELECT id FROM students WHERE id = %s AND college_id = %s", (str(student_id_str), current_user.original_id))
        student = cursor.fetchone()

        if not student:
            flash("Invalid Student selected.")
            conn.close()
            return redirect(url_for("college_dashboard"))
        
        student_id = student['id']

        # Upsert Mark
        cursor.execute("DELETE FROM marks WHERE student_id=%s AND subject=%s AND exam_type=%s", (student_id, subject_name, exam_type))
        cursor.execute("INSERT INTO marks (student_id, subject, exam_type, marks) VALUES (%s, %s, %s, %s)",
                       (student_id, subject_name, exam_type, marks_val))
        
        # Recalculate Grade (Average of all marks)
        cursor.execute("SELECT AVG(marks) as average FROM marks WHERE student_id = %s", (student_id,))
        avg_data = cursor.fetchone()
        average = avg_data['average'] if avg_data and avg_data['average'] is not None else 0
        
        grade = 'F'
        if average >= 90: grade = 'A'
        elif average >= 75: grade = 'B'
        elif average >= 60: grade = 'C'
        elif average >= 40: grade = 'D'
        
        cursor.execute("DELETE FROM grades WHERE student_id=%s", (student_id,))
        cursor.execute("INSERT INTO grades (student_id, grade) VALUES (%s, %s)", (student_id, grade))
    
        conn.commit()
        flash(f"Marks for {subject_name} ({exam_type}) updated successfully!")
        
    except Exception as e:
        print(f"Error in add_mark: {e}")
        flash(f"Error adding marks: {str(e)}")
        
    finally:
        conn.close()
    
    return redirect(url_for("college_dashboard"))

@app.route("/college/add_student", methods=["POST"])
@college_required
def add_student():
    name = request.form["name"]
    roll = request.form["roll"]
    phone = request.form["phone"]
    dob = request.form["dob"]
    group = request.form["group"]
    teacher_id = request.form.get("teacher_id") # Optional
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO students (college_id, name, student_id, phone, dob, group_name, teacher_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (current_user.original_id, name, roll, phone, dob, group, teacher_id)
        )
        conn.commit()
    except mysql.connector.Error as err:
        flash(f"Error: {err}")
    finally:
        conn.close()
    return redirect(url_for("college_dashboard"))

@app.route("/college/manage_student/<int:student_id>", methods=["GET", "POST"])
@college_required
def manage_student(student_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Verify student belongs to this college
    cursor.execute("SELECT * FROM students WHERE id = %s AND college_id = %s", (student_id, current_user.original_id))
    student = cursor.fetchone()
    
    if not student:
        conn.close()
        flash("Student not found or access denied.")
        return redirect(url_for("college_dashboard"))
        
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "update_attendance":
            total_days = request.form["total_days"]
            present_days = request.form["present_days"]
            
            cursor.execute("DELETE FROM attendance WHERE student_id=%s", (student_id,))
            cursor.execute("INSERT INTO attendance (student_id, total_days, present_days) VALUES (%s, %s, %s)", 
                           (student_id, total_days, present_days))
            flash("Attendance updated successfully!")
            
        elif action == "add_mark":
            subject = request.form["subject"]
            exam_type = request.form.get("exam_type", "Semester")
            marks_val = float(request.form["marks"])
            
            # Upsert Mark
            cursor.execute("DELETE FROM marks WHERE student_id=%s AND subject=%s AND exam_type=%s", (student_id, subject, exam_type))
            cursor.execute("INSERT INTO marks (student_id, subject, exam_type, marks) VALUES (%s, %s, %s, %s)",
                           (student_id, subject, exam_type, marks_val))
            flash(f"Marks for {subject} ({exam_type}) updated successfully!")

        # Recalculate Grade (Average of all marks)
        cursor.execute("SELECT AVG(marks) as average FROM marks WHERE student_id = %s", (student_id,))
        avg_data = cursor.fetchone()
        average = avg_data['average'] if avg_data and avg_data['average'] is not None else 0
        
        grade = 'F'
        if average >= 90: grade = 'A'
        elif average >= 75: grade = 'B'
        elif average >= 60: grade = 'C'
        elif average >= 40: grade = 'D'
        
        cursor.execute("DELETE FROM grades WHERE student_id=%s", (student_id,))
        cursor.execute("INSERT INTO grades (student_id, grade) VALUES (%s, %s)", (student_id, grade))
        
        conn.commit()
        
    # Fetch existing data
    cursor.execute("SELECT * FROM attendance WHERE student_id = %s", (student_id,))
    attendance = cursor.fetchone()
    
    cursor.execute("SELECT * FROM marks WHERE student_id = %s", (student_id,))
    marks_list = cursor.fetchall()
    
    cursor.execute("SELECT * FROM grades WHERE student_id = %s", (student_id,))
    grade_data = cursor.fetchone()

    # Get Exams list for dropdown
    cursor.execute("SELECT * FROM exams WHERE college_id = %s", (current_user.original_id,))
    exams = cursor.fetchall()

    conn.close()
    return render_template("college/manage_student.html", student=student, attendance=attendance, marks=marks_list, grade=grade_data, exams=exams)

@app.route("/college/delete_mark/<int:mark_id>")
@college_required
def delete_mark(mark_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get student_id to verify ownership and redirect back
    cursor.execute("SELECT student_id FROM marks WHERE id = %s", (mark_id,))
    mark = cursor.fetchone()
    
    if mark:
        student_id = mark['student_id']
        # Verify college access (implicitly done by verifying student belongs to college, but shortcut here for speed, 
        # ideally check student->college linkage. Let's do it safe.)
        cursor.execute("""
            SELECT s.college_id FROM students s 
            JOIN marks m ON s.id = m.student_id 
            WHERE m.id = %s
        """, (mark_id,))
        check = cursor.fetchone()
        
        if check and check['college_id'] == current_user.original_id:
            cursor.execute("DELETE FROM marks WHERE id = %s", (mark_id,))
            
            # Recalculate Grade
            cursor.execute("SELECT AVG(marks) as average FROM marks WHERE student_id = %s", (student_id,))
            avg_data = cursor.fetchone()
            average = avg_data['average'] if avg_data and avg_data['average'] is not None else 0
            
            grade = 'F'
            if average >= 90: grade = 'A'
            elif average >= 75: grade = 'B'
            elif average >= 60: grade = 'C'
            elif average >= 40: grade = 'D'
            
            cursor.execute("DELETE FROM grades WHERE student_id=%s", (student_id,))
            cursor.execute("INSERT INTO grades (student_id, grade) VALUES (%s, %s)", (student_id, grade))
            
            conn.commit()
            flash("Subject deleted.")
        else:
            flash("Unauthorized deletion.")
            
        conn.close()
        return redirect(url_for('manage_student', student_id=student_id))
    
    conn.close()
    return redirect(url_for('college_dashboard'))

# --- STUDENT PANEL ---

@app.route("/student/login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        student_id = request.form["student_id"]
        dob = request.form["dob"] # or Phone
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Using DOB for auth
        cursor.execute("SELECT * FROM students WHERE student_id = %s AND dob = %s", (student_id, dob))
        data = cursor.fetchone()
        conn.close()
        
        if data:
            user = User(id=f"STUDENT:{data['id']}", role='STUDENT', name=data['name'], original_id=data['id'])
            login_user(user)
            return redirect(url_for("student_dashboard"))
        else:
            flash("Invalid Student ID or DOB")
            
    return render_template("student/login.html")

@app.route("/student/dashboard")
@login_required
def student_dashboard():
    try:
        if current_user.role != 'STUDENT':
            return redirect(url_for('home'))
            
        student_id = current_user.original_id
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM students WHERE id = %s", (student_id,))
        student = cursor.fetchone()
        
        if not student:
            return "Student not found", 404

        # Get College Name
        cursor.execute("SELECT college_name FROM colleges WHERE id = %s", (student['college_id'],))
        c_data = cursor.fetchone()
        college_name = c_data['college_name'] if c_data else "College"

        # Fetch marks
        cursor.execute("SELECT * FROM marks WHERE student_id = %s", (student_id,))
        marks = cursor.fetchall()
        
        # Group marks by Exam Type
        grouped_marks = {}
        for m in marks:
            # Handle potential missing key or None
            e_type = m.get('exam_type') 
            if not e_type:
                e_type = "Unspecified"
                
            if e_type not in grouped_marks:
                grouped_marks[e_type] = []
            grouped_marks[e_type].append(m)
            
        cursor.execute("SELECT * FROM attendance WHERE student_id = %s", (student_id,))
        attendance = cursor.fetchone()
        
        cursor.execute("SELECT * FROM grades WHERE student_id = %s", (student_id,))
        grade = cursor.fetchone()
        
        # Calculate Total Marks
        total_marks = sum([float(m['marks']) for m in marks]) # Ensure mark is float/int
        
        # Get Assigned Teacher
        assigned_teacher = None
        if student.get('teacher_id'):
            cursor.execute("SELECT * FROM teachers WHERE id = %s", (student['teacher_id'],))
            assigned_teacher = cursor.fetchone()
            
        # Get Today's Attendance Request Status
        import datetime
        today = datetime.date.today()
        cursor.execute("SELECT * FROM attendance_requests WHERE student_id = %s AND date = %s", (student_id, today))
        today_request = cursor.fetchone()

        conn.close()
        return render_template("student/dashboard.html", student=student, grouped_marks=grouped_marks, attendance=attendance, grade=grade, college_name=college_name, total_marks=total_marks, assigned_teacher=assigned_teacher, today_request=today_request)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Internal Server Error: {str(e)}", 500

@app.route("/student/request_attendance", methods=["POST"])
@login_required
def request_attendance():
    if not current_user.is_student:
        return redirect(url_for('home'))
        
    student_id = current_user.original_id
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Check if already requested today
        import datetime
        today = datetime.date.today()
        now_time = datetime.datetime.now().time()
        
        cursor.execute("SELECT * FROM attendance_requests WHERE student_id = %s AND date = %s", (student_id, today))
        existing = cursor.fetchone()
        
        if existing:
            flash("Already requested for today.")
        else:
            cursor.execute("""
                INSERT INTO attendance_requests (student_id, teacher_id, date, time, status) 
                VALUES (%s, NULL, %s, %s, 'Pending')
            """, (student_id, today, now_time))
            conn.commit()
            flash("Attendance Request Sent!")
            
    except Exception as e:
        flash(f"Error: {e}")
    finally:
        conn.close()
        
    return redirect(url_for('student_dashboard'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)