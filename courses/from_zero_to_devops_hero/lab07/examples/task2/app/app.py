from flask import Flask, jsonify
import psycopg2
import redis
import os
import socket

app = Flask(__name__)

# Redis connection
cache = redis.Redis(
    host=os.getenv('REDIS_HOST', 'redis'),
    port=6379,
    decode_responses=True
)

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'postgres'),
        database=os.getenv('DB_NAME', 'appdb'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'secret')
    )

@app.route('/')
def index():
    return jsonify({
        "message": "API is running",
        "hostname": socket.gethostname(),
        "endpoints": {
            "/": "This page",
            "/db": "Test database connection",
            "/cache": "Test Redis cache (with counter)",
            "/health": "Health check",
            "/hostname": "Get container hostname"
        }
    })

@app.route('/db')
def test_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT version();')
        version = cur.fetchone()[0]
        cur.close()
        conn.close()
        return jsonify({
            "database": "connected",
            "version": version
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/cache')
def test_cache():
    try:
        # Increment counter
        count = cache.incr('visit_count')
        return jsonify({
            "cache": "connected",
            "visit_count": count,
            "hostname": socket.gethostname()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "hostname": socket.gethostname()
    })

@app.route('/hostname')
def hostname():
    return jsonify({
        "hostname": socket.gethostname()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
