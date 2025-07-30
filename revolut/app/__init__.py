# app/__init__.py - Updated for production deployment
from flask import Flask, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_babel import Babel
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
babel = Babel()

def create_app():
    app = Flask(__name__)

    # Configuration - Updated for production
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

    # Database configuration - Handle both development and production
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Fix for render's postgres URL format
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///revolut.db'

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Babel configuration
    app.config['LANGUAGES'] = {
        'en': 'English',
        'sw': 'Kiswahili'
    }
    app.config['BABEL_DEFAULT_LOCALE'] = 'en'
    app.config['BABEL_DEFAULT_TIMEZONE'] = 'UTC'

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    babel.init_app(app)

    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    @babel.localeselector
    def get_locale():
        # 1. Check URL parameter
        if request.args.get('lang'):
            session['language'] = request.args.get('lang')

        # 2. Check session
        if 'language' in session:
            return session['language']

        # 3. Check user preference (if logged in)
        if current_user.is_authenticated and hasattr(current_user, 'language'):
            return current_user.language

        # 4. Check browser language
        return request.accept_languages.best_match(app.config['LANGUAGES'].keys()) or 'en'

    # Import models here to register them with SQLAlchemy
    from app import models

    # Register Blueprints
    from app.routes import main
    from app.auth import auth_bp
    from app.api import api
    from app.api.polls import polls_bp
    from app.admin import admin_bp  # Note: using admin.py instead of api.admin

    app.register_blueprint(main)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(api)  # Register the main API blueprint
    app.register_blueprint(polls_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Add error handlers for production
    @app.errorhandler(404)
    def not_found_error(error):
        return {'error': 'Not found'}, 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {'error': 'Internal server error'}, 500

    # Health check route for Render
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'service': 'revolut-wdo'}

    return app