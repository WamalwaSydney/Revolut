from flask import Flask, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_babel import Babel, get_locale
from flask_bootstrap5 import Bootstrap
import os
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
jwt = JWTManager()
babel = Babel()
bootstrap = Bootstrap()

def create_app():
    app = Flask(__name__)

    @app.template_filter('time_ago')
    def time_ago_filter(dt):
        """Custom Jinja2 filter for displaying time since creation"""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        diff = now - dt

        if diff.days > 365:
            years = diff.days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
        if diff.days > 30:
            months = diff.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        if diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        if diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        return "just now"
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///revolut_wdo.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # JWT Configuration
    app.config['JWT_SECRET_KEY'] = os.environ.get('SECRET_KEY', 'jwt-secret-string')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False

    # Mail Configuration
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', '1', 't']
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

    # Babel Configuration for multilingual support
    app.config['LANGUAGES'] = {
        'en': 'English',
        'sw': 'Kiswahili',
        'ki': 'Kikuyu'
    }
    app.config['BABEL_DEFAULT_LOCALE'] = 'en'
    app.config['BABEL_DEFAULT_TIMEZONE'] = 'Africa/Nairobi'

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    jwt.init_app(app)
    babel.init_app(app)
    bootstrap.init_app(app)
    CORS(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # Updated locale selector for newer Flask-Babel versions
    def select_locale():
        # 1. Check URL parameter
        if request.args.get('lang'):
            session['language'] = request.args.get('lang')

        # 2. Check session
        if 'language' in session:
            return session['language']

        # 3. Check Accept-Language header
        return request.accept_languages.best_match(app.config['LANGUAGES'].keys()) or 'en'

    # Set the locale selector function
    babel.locale_selector_func = select_locale

    # Register blueprints
    from app.routes.main import main
    from app.routes.auth import auth
    from app.routes.feedback import feedback
    from app.routes.dashboard import dashboard
    from app.routes.admin import admin
    from app.routes.api import api
    from app.routes.sms_ussd import sms_ussd
    from app.routes.polls import polls
    from app.models import User, UserRole  # Add UserRole to the import
    from flask_moment import Moment

    app.register_blueprint(main)
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(feedback, url_prefix='/feedback')
    app.register_blueprint(dashboard, url_prefix='/dashboard')
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(api, url_prefix='/api')
    app.register_blueprint(sms_ussd, url_prefix='/sms')
    app.register_blueprint(polls, url_prefix='/polls')

    # Create database tables
    with app.app_context():
        db.create_all()

        # Create admin user if not exists
        from app.models import User
        admin_email = os.environ.get('ADMIN_EMAIL')
        admin_password = os.environ.get('ADMIN_PASSWORD')
        if admin_email and admin_password:  # Add safety check
            if not User.query.filter_by(email=admin_email).first():
                admin_user = User(
                    username='admin',
                    email=admin_email,
                    role=UserRole.ADMIN,
                    is_active=True
                )
                admin_user.set_password(admin_password)
                db.session.add(admin_user)
                db.session.commit()
    moment=Moment(app)
    return app