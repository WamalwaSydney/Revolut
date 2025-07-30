import os
import logging
from app import create_app, db
from app.models import User, Role, Official, Poll, UserFeedback, Issue, Alert
from flask_migrate import upgrade
from sqlalchemy import inspect

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

def check_table_exists(table_name):
    """Check if a table exists in the database"""
    try:
        inspector = inspect(db.engine)
        return table_name in inspector.get_table_names()
    except Exception:
        return False

def check_column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False

def handle_database_migration():
    """Handle database migrations and schema updates"""
    try:
        logger.info("Checking for database migrations...")

        # Check if user table exists but is missing columns
        if check_table_exists('user'):
            # Check for missing columns that might have been added to the model
            missing_columns = []

            # Common columns that might be missing
            potential_columns = ['language', 'phone', 'last_login']

            for col in potential_columns:
                if not check_column_exists('user', col):
                    missing_columns.append(col)

            if missing_columns:
                logger.info(f"Missing columns detected: {missing_columns}")
                logger.info("Recreating database with updated schema...")

                # Drop and recreate all tables
                db.drop_all()
                db.create_all()
                logger.info("Database schema updated successfully")
                return True

        return False

    except Exception as e:
        logger.error(f"Migration check failed: {e}")
        return False

def initialize_database():
    """Initialize database with tables and default data"""
    with app.app_context():
        try:
            logger.info("Starting database initialization...")

            # First, check if we need to handle migrations
            migration_needed = handle_database_migration()

            # Check if tables exist
            if not check_table_exists('role') or not check_table_exists('user') or migration_needed:
                logger.info("Creating database tables...")
                db.create_all()
                logger.info("Database tables created successfully")

                # Create default data
                create_default_data()
                logger.info("Default data created successfully")
            else:
                logger.info("Database tables already exist")

                # Check if we need to create default data
                try:
                    role_count = Role.query.count()
                    logger.info(f"Found {role_count} roles in database")

                    if role_count == 0:
                        logger.info("No roles found, creating default data...")
                        create_default_data()
                    else:
                        # Check if admin user exists
                        admin_user = User.query.filter_by(username='admin').first()
                        if not admin_user:
                            logger.info("Admin user missing, creating...")
                            # Create just the admin user
                            admin_role = Role.query.filter_by(name='admin').first()
                            if admin_role:
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
                                logger.info("Admin user created successfully")
                        else:
                            logger.info("Admin user already exists")

                except Exception as query_error:
                    logger.error(f"Error querying existing data: {query_error}")
                    # If we can't query, probably need to recreate
                    logger.info("Recreating database due to query errors...")
                    db.drop_all()
                    db.create_all()
                    create_default_data()

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