from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
import psycopg2
import os

app = Flask(__name__)


def get_db_connection():
    conn = psycopg2.connect(
        host="postgres-service",
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )
    return conn

@app.route('/')
def hello_names():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT name FROM users;')
    names = cur.fetchall()
    cur.close()
    conn.close()

    result = "\n".join([f"Hello {name[0]}" for name in names])
    
    return result

if __name__ == '__main__':
    app.run(host='0.0.0.0')