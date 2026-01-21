import mysql.connector

def fix_setup():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Rajesh@123",
            database="student_db"
        )
        cursor = conn.cursor(dictionary=True)

        # 1. Check if any colleges exist (needed for FK)
        cursor.execute("SELECT id FROM colleges LIMIT 1")
        college = cursor.fetchone()
        
        if not college:
            print("No colleges found! Cannot create teacher.")
            return

        college_id = college['id']

        # 2. Check if any teacher exists
        cursor.execute("SELECT id FROM teachers LIMIT 1")
        teacher = cursor.fetchone()
        
        teacher_id = None
        
        if not teacher:
            print("No teachers found. Creating a default teacher...")
            cursor.execute("""
                INSERT INTO teachers (college_id, name, email, password, subject) 
                VALUES (%s, 'Suresh Sir', 'suresh@college.com', '12345', 'General')
            """, (college_id,))
            conn.commit()
            teacher_id = cursor.lastrowid
            print(f"Created Teacher: Suresh Sir (ID: {teacher_id})")
        else:
            teacher_id = teacher['id']
            print(f"Found existing Teacher ID: {teacher_id}")

        # 3. Assign this teacher to ALL students who don't have one
        cursor.execute("UPDATE students SET teacher_id = %s WHERE teacher_id IS NULL OR teacher_id = 0", (teacher_id,))
        conn.commit()
        
        print(f"Updated {cursor.rowcount} students with Teacher ID {teacher_id}.")
        print("Attendance feature should now work for all students.")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    fix_setup()
