import mysql.connector

def add_group_column():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Rajesh@123",
            database="student_db"
        )
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("SHOW COLUMNS FROM students LIKE 'group_name'")
        result = cursor.fetchone()
        
        if not result:
            cursor.execute("ALTER TABLE students ADD COLUMN group_name VARCHAR(50) DEFAULT 'General'")
            print("Column 'group_name' added to 'students' table.")
        else:
            print("Column 'group_name' already exists.")
            
        conn.commit()
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    add_group_column()
