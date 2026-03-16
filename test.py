import psycopg2
import hashlib

# Example user data
username = "admin"
password = "admin"

# Hash the password using SHA-256
hashed_password = hashlib.sha256(password.encode()).hexdigest()

# Connect to PostgreSQL
conn = psycopg2.connect(
database="mydb",
user="postgres",
password="solidify123",
host="127.0.0.1",
port=5433
)

cur = conn.cursor()

# Insert user with hashed password
cur.execute(
    "INSERT INTO users (username, password) VALUES (%s, %s)",
    (username, hashed_password)
)

conn.commit()
cur.close()
conn.close()

print("User inserted with hashed password!")