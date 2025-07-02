from app import app
import routes  # <-- ✅ This registers all route definitions

if __name__ == "__main__":
    import os
    debug_mode = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
