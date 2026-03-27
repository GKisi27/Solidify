import psycopg2
import hashlib
import os

DATABASE_URL = os.getenv("DATABASE_URL")

username = "prashant"
password = "prashant"

hashed_password = hashlib.sha256(password.encode()).hexdigest()

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

cur.execute(
    "INSERT INTO users (username, password) VALUES (%s, %s)",
    (username, hashed_password)
)

conn.commit()
cur.close()
conn.close()

print(f"User '{username}' inserted with hashed password!")