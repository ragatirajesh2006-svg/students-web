import mysql.connector
import datetime

def get_creds():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Rajesh@123",
            database="student_db"
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM students WHERE id=9")
        s = cursor.fetchone()
        print(f"ID: {s['student_id']}")
        print(f"DOB: {s['dob']}")
    except Exception as e:
        print(e)
    finally:
        conn.close()

if __name__ == "__main__":
    get_creds()
