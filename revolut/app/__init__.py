from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from cryptography.fernet import Fernet
import os
import base64

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
sia = SentimentIntensityAnalyzer()
login_manager = LoginManager()

# Generate or load encryption key
def generate_fernet_key():
    key = Fernet.generate_key()
    return key.decode()

ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', generate_fernet_key())
fernet = Fernet(ENCRYPTION_KEY.encode())

# Download NLTK data
nltk.download('punkt', quiet=True)
nltk.download('vader_lexicon', quiet=True)
nltk.download('stopwords', quiet=True)

def create_app():
    app = Flask(__name__)

    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        'postgresql://revolut_user:securepassword123@localhost/revolut_wdo'
    )
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['ENCRYPTION_KEY'] = ENCRYPTION_KEY

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # Import models here to avoid circular imports
    from app.models import User, Role, Official, Poll, UserFeedback, Issue, Alert

    # User loader function for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from app.api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')

    from app.auth import auth_bp as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from app.admin import admin_bp as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    from app.api.polls import polls_bp
    app.register_blueprint(polls_bp)


    # Create database tables
    with app.app_context():
        db.create_all()

        # Create default roles if they don't exist
        roles_to_create = [
            ('admin', 'System Administrator'),
            ('cso', 'Civil Society Organization'),
            ('citizen', 'Citizen'),
            ('official', 'Government Official')
        ]

        for role_name, role_desc in roles_to_create:
            if not Role.query.filter_by(name=role_name).first():
                role = Role(name=role_name, description=role_desc)
                db.session.add(role)

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error creating default roles: {e}")

    return app