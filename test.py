# import psycopg2
# import hashlib
from passlib.context import CryptContext

# 
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# def insert_user(username: str, password: str):
#     # Hash password (same as your FastAPI login logic)
#     hashed_password = pwd_context.hash(password)

#     try:
#         conn = psycopg2.connect(
#             database="mydb",
#             user="postgres",
#             password="solidify123",
#             host="127.0.0.1",
#             port=5433
#         )

#         cur = conn.cursor()

#         # Insert user
#         cur.execute(
#             """
#             INSERT INTO users (username, password)
#             VALUES (%s, %s)
#             """,
#             (username, hashed_password)
#         )

#         conn.commit()
#         print("✅ User inserted successfully!")

#     except Exception as e:
#         conn.rollback()
#         print("❌ Error inserting user:", e)

#     finally:
#         if cur:
#             cur.close()
#         if conn:
#             conn.close()


# # # Example usage
# insert_user("admin12", "admin12")

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


hashed_password = pwd_context.hash("admin12")


print(verify_password('admin12', hashed_password))

# print(hash_password('admin12'))