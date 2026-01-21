import mysql.connector

def update_db():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Rajesh@123",
            database="student_db"
        )
        cursor = conn.cursor()

        print("Creating teachers table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            college_id INT NOT NULL,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            subject VARCHAR(100),
            FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE
        )
        """)

        print("Creating attendance_requests table...")
        # using attendance_requests to differentiate from existing simple attendance table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance_requests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT NOT NULL,
            teacher_id INT NOT NULL,
            date DATE NOT NULL,
            time TIME NOT NULL,
            status ENUM('Pending', 'Accepted', 'Rejected') DEFAULT 'Pending',
            accepted_by VARCHAR(100), -- Stores Teacher Name or potentially ID if needed, user asked for Name
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE
        )
        """)

        print("Checking/Adding teacher_id column to students table...")
        cursor.execute("DESCRIBE students")
        columns = [column[0] for column in cursor.fetchall()]
        
        if 'teacher_id' not in columns:
            cursor.execute("""
            ALTER TABLE students
            ADD COLUMN teacher_id INT,
            ADD CONSTRAINT fk_student_teacher FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE SET NULL
            """)
            print("Added teacher_id column to students.")
        else:
            print("teacher_id column already exists.")

        conn.commit()
        print("Database updated successfully!")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    update_db()
