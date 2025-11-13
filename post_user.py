import sqlite3
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os

app = FastAPI()

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

class User(BaseModel):
    username: str
    password: str
    role: str = "normal"  # "admin" or "normal"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'normal'))
        )
    """)
    conn.commit()
    conn.close()

init_db()

def add_user_to_db(username: str, password: str, role: str = "normal") -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password, role))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return {"success": False, "detail": "User already exists"}
    conn.close()
    return {"success": True, "message": "User added successfully"}

# Add a dummy user for demonstration
if __name__ == "__main__":
    result = add_user_to_db("haseeb", "Abl1025@work", "admin")
    print(result)
