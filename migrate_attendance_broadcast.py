import mysql.connector

def migrate():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Rajesh@123",
            database="student_db"
        )
        cursor = conn.cursor()

        print("Altering attendance_requests table...")
        # Modify teacher_id to be NULLABLE
        cursor.execute("ALTER TABLE attendance_requests MODIFY teacher_id INT NULL")
        
        # Verify
        cursor.execute("DESCRIBE attendance_requests")
        columns = cursor.fetchall()
        for col in columns:
            if col[0] == 'teacher_id':
                print(f"Column teacher_id: {col}")

        conn.commit()
        print("Migration successful: teacher_id is now nullable.")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    migrate()
