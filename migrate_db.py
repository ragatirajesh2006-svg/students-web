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
        
        print("Checking if 'exam_type' column exists in 'marks' table...")
        
        # Check if column exists
        cursor.execute("SHOW COLUMNS FROM marks LIKE 'exam_type'")
        result = cursor.fetchone()
        
        if not result:
            print("Column 'exam_type' not found. Adding it...")
            cursor.execute("ALTER TABLE marks ADD COLUMN exam_type VARCHAR(50) DEFAULT 'Semester'")
            conn.commit()
            print("Column 'exam_type' added successfully.")
        else:
            print("Column 'exam_type' already exists.")
            
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    migrate()
