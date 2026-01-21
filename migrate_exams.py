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
        
        # Create Exams Table
        print("Creating 'exams' table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS exams (
            id INT AUTO_INCREMENT PRIMARY KEY,
            college_id INT NOT NULL,
            exam_name VARCHAR(100) NOT NULL,
            FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE
        )
        """)
        print("'exams' table created.")
        
        conn.commit()
            
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    migrate()
