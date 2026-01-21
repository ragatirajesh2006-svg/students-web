import mysql.connector
import datetime

def json_serial(obj):
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

def check_db():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Rajesh@123",
            database="student_db"
        )
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id, name, college_id FROM students")
        students = cursor.fetchall()
        print(f"Students: {len(students)}")
        for s in students:
            print(f"Student: {s}")
            
        cursor.execute("SELECT * FROM marks")
        marks = cursor.fetchall()
        print(f"Marks: {len(marks)}")
        for m in marks:
            print(f"Mark: {m}")
            
    except Exception as e:
        print(e)
    finally:
        if conn.is_connected():
            conn.close()

if __name__ == "__main__":
    check_db()
