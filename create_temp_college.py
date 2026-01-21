import mysql.connector

def create_temp():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Rajesh@123",
            database="student_db"
        )
        cursor = conn.cursor()
        
        # Check if exists
        cursor.execute("SELECT * FROM colleges WHERE email = 'temp@test.com'")
        if cursor.fetchone():
            print("Temp college already exists.")
        else:
            cursor.execute("INSERT INTO colleges (college_name, email, password, status) VALUES ('Test College', 'temp@test.com', 'temp123', 'active')")
            conn.commit()
            print("Created temp college: temp@test.com / temp123")
            
    except Exception as e:
        print(e)
    finally:
        conn.close()

if __name__ == "__main__":
    create_temp()
