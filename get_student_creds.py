import mysql.connector

try:
    conn = mysql.connector.connect(host='localhost', user='root', password='Rajesh@123', database='student_db')
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM students LIMIT 1')
    student = cursor.fetchone()
    if student:
        print(f"ID: {student['student_id']}")
        print(f"DOB: {student['dob']}")
    else:
        print("No students found")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
