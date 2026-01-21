import mysql.connector

def add_classes_table():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Rajesh@123",
            database="student_db"
        )
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                college_id INT NOT NULL,
                class_name VARCHAR(100) NOT NULL,
                subject_name VARCHAR(100) NOT NULL,
                teacher_name VARCHAR(100) NOT NULL,
                FOREIGN KEY (college_id) REFERENCES colleges(id) ON DELETE CASCADE
            )
        """)
        
        print("Classes table created successfully!")
        conn.commit()
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    add_classes_table()
