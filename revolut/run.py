import os
import logging
from app import create_app, db
from app.models import User, Role, Official, Poll, UserFeedback, Issue, Alert
from flask_migrate import upgrade

# Set up logging for Render
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()

def create_default_data():
    """Create default roles and admin user"""
    try:
        # Create roles if they don't exist
        roles_to_create = [
            ('admin', 'System Administrator'),
            ('cso', 'Civil Society Organization'),
            ('official', 'Government Official'),
            ('citizen', 'Citizen')
        ]

        for role_name, description in roles_to_create:
            if not Role.query.filter_by(name=role_name).first():
                role = Role(name=role_name, description=description)
                db.session.add(role)
                logger.info(f"Created role: {role_name}")

        db.session.commit()

        # Create admin user if it doesn't exist
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_role = Role.query.filter_by(name='admin').first()

            # Use environment variable for admin password in production
            admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
            admin_email = os.environ.get('ADMIN_EMAIL', 'admin@revolut.rw')

            admin_user = User(
                username='admin',
                email=admin_email,
                active=True
            )
            admin_user.set_password(admin_password)
            admin_user.roles.append(admin_role)
            db.session.add(admin_user)
            db.session.commit()
            logger.info(f"Default admin user created: admin/{admin_password}")
        else:
            logger.info("Admin user already exists")

    except Exception as e:
        logger.error(f"Error creating default data: {e}")
        db.session.rollback()
        raise

def initialize_database():
    """Initialize database with tables and default data"""
    with app.app_context():
        try:
            logger.info("Checking database initialization...")

            # Try to query Role table to check if it exists
            try:
                role_count = Role.query.count()
                logger.info(f"Database already initialized. Found {role_count} roles.")

                # Still check if admin user exists
                admin_user = User.query.filter_by(username='admin').first()
                if not admin_user:
                    logger.info("Admin user missing, creating...")
                    create_default_data()

            except Exception as table_error:
                logger.info("Database tables don't exist, creating...")

                # Create all tables
                db.create_all()
                logger.info("Database tables created successfully")

                # Create default data
                create_default_data()
                logger.info("Default data created successfully")

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

# Initialize database when module is imported (on app startup)
logger.info("Starting application initialization...")
initialize_database()
logger.info("Application initialization completed")

if __name__ == '__main__':
    # Get port from environment variable (Render sets this)
    port = int(os.environ.get('PORT', 5000))

    # For Render, we need to bind to 0.0.0.0
    app.run(
        debug=False,  # Always False in production
        host='0.0.0.0',
        port=port
    )