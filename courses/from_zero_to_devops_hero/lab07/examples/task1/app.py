from flask import Flask
import psycopg2
import os

app = Flask(__name__)

@app.route('/')
def hello():
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'postgres'),
            database=os.getenv('DB_NAME', 'testdb'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'secret')
        )
        cursor = conn.cursor()
        cursor.execute('SELECT version();')
        db_version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        return f"""
        <h1>Connected to database successfully!</h1>
        <p>Database version: {db_version}</p>
        """
    except Exception as e:
        return f"<h1>Failed to connect</h1><p>{str(e)}</p>", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
