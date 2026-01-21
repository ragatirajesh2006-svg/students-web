import mysql.connector

def add_subjects_table():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Rajesh@123",
            database="student_db"
        )
        cursor = conn.cursor()
        
        # Create Subjects Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INT AUTO_INCREMENT PRIMARY KEY,
            college_id INT NOT NULL,
            subject_name VARCHAR(100) NOT NULL,
            FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE
        )
        """)
        
        conn.commit()
        print("Subjects table created successfully!")
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    add_subjects_table()
