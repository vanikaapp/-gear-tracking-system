from app import app

if __name__ == "__main__":
    # Use environment variable or default to debug mode for local development
    import os
    debug_mode = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
