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

@app.route('/', methods=['GET'])
def hello_names():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT name FROM users;')
    names = cur.fetchall()
    cur.close()
    conn.close()

    result = "\n".join([f"Hello {name[0]}" for name in names])
    
    return result

@app.route('/liveness', methods=['GET'])
def health_check():
    return 'Alive', 200

@app.route('/readiness', methods=['GET'])
def readiness_check():
    try:
        conn = get_db_connection()
        conn.close()
        return 'Ready', 200
    except Exception as e:
        return f'Not Ready: {str(e)}', 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)