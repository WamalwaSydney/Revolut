#!/usr/bin/env python3
"""
Database Migration and Fix Script for Revolut App
This script will:
1. Create missing database tables and columns
2. Fix password hashing issues for existing users
3. Set up initial roles and admin user
"""

import os
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app, db
    from app.models import User, Role, UserFeedback, Issue, Official, Poll, Alert
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)

def create_missing_columns():
    """Add missing columns to existing tables"""
    print("Creating missing database columns...")

    try:
        # Check if tags column exists in user_feedback table
        with db.engine.connect() as conn:
            # For PostgreSQL
            result = conn.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='user_feedback' AND column_name='tags'
            """)

            if not result.fetchone():
                print("Adding 'tags' column to user_feedback table...")
                conn.execute("ALTER TABLE user_feedback ADD COLUMN tags JSON")
                conn.commit()
                print("✓ Added tags column")
            else:
                print("✓ Tags column already exists")

            # Check if password_hash column length is sufficient
            result = conn.execute("""
                SELECT character_maximum_length
                FROM information_schema.columns
                WHERE table_name='user' AND column_name='password_hash'
            """)

            length_result = result.fetchone()
            if length_result and length_result[0] < 255:
                print("Extending password_hash column length...")
                conn.execute("ALTER TABLE \"user\" ALTER COLUMN password_hash TYPE VARCHAR(255)")
                conn.commit()
                print("✓ Extended password_hash column length")
            else:
                print("✓ Password hash column length is sufficient")

    except Exception as e:
        print(f"Error creating columns: {e}")
        # For SQLite fallback
        try:
            print("Attempting SQLite column creation...")
            db.engine.execute("ALTER TABLE user_feedback ADD COLUMN tags TEXT")
            print("✓ Added tags column (SQLite)")
        except Exception as sqlite_error:
            print(f"SQLite error: {sqlite_error}")

def create_roles():
    """Create default roles if they don't exist"""
    print("Creating default roles...")

    default_roles = [
        {'name': 'admin', 'description': 'System administrator'},
        {'name': 'cso', 'description': 'Civil Society Organization'},
        {'name': 'citizen', 'description': 'Regular citizen'},
        {'name': 'official', 'description': 'Government official'}
    ]

    for role_data in default_roles:
        role = Role.query.filter_by(name=role_data['name']).first()
        if not role:
            role = Role(name=role_data['name'], description=role_data['description'])
            db.session.add(role)
            print(f"✓ Created role: {role_data['name']}")
        else:
            print(f"✓ Role already exists: {role_data['name']}")

    try:
        db.session.commit()
        print("✓ All roles created successfully")
    except Exception as e:
        db.session.rollback()
        print(f"Error creating roles: {e}")

def fix_user_passwords():
    """Fix password hashing for existing users"""
    print("Fixing user passwords...")

    users = User.query.all()
    print(f"Found {len(users)} users to check")

    for user in users:
        print(f"Checking user: {user.username}")

        # Check if password hash exists and is valid length
        if not user.password_hash:
            print(f"  - No password hash for {user.username}")
            continue

        # Test with a common password to see if it's working
        try:
            from werkzeug.security import check_password_hash
            # This is just to test if the hash format is valid
            test_result = check_password_hash(user.password_hash, "test123")
            print(f"  - Password hash format is valid for {user.username}")
        except Exception as e:
            print(f"  - Invalid password hash for {user.username}: {e}")
            # Could regenerate hash here if needed

    print("✓ Password check completed")

def create_admin_user():
    """Create an admin user if none exists"""
    print("Creating admin user...")

    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        print("❌ Admin role not found. Create roles first.")
        return

    # Check if admin user exists
    admin_user = User.query.join(User.roles).filter(Role.name == 'admin').first()

    if not admin_user:
        # Create admin user
        admin_user = User(
            username='admin',
            email='admin@revolut-wdo.com',
            phone='254700000000',
            created_at=datetime.utcnow(),
            active=True
        )

        # Set password
        admin_user.set_password('admin123')  # Change this in production!

        # Assign admin role
        admin_user.roles.append(admin_role)

        db.session.add(admin_user)

        try:
            db.session.commit()
            print("✓ Created admin user")
            print("  Username: admin")
            print("  Password: admin123")
            print("  ⚠️  CHANGE THIS PASSWORD IN PRODUCTION!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating admin user: {e}")
    else:
        print("✓ Admin user already exists")

def reset_user_password(username, new_password):
    """Reset a specific user's password"""
    print(f"Resetting password for user: {username}")

    user = User.query.filter_by(username=username).first()
    if not user:
        print(f"❌ User '{username}' not found")
        return False

    try:
        user.set_password(new_password)
        db.session.commit()

        # Test the new password
        if user.check_password(new_password):
            print(f"✓ Password reset successful for {username}")
            print(f"  New password: {new_password}")
            return True
        else:
            print(f"❌ Password reset failed - verification failed")
            return False

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error resetting password: {e}")
        return False

def create_sample_data():
    """Create sample officials and categories for testing"""
    print("Creating sample data...")

    # Sample officials
    officials_data = [
        {
            'name': 'John Doe',
            'position': 'Governor',
            'constituency': 'Nairobi',
            'department': 'County Government'
        },
        {
            'name': 'Jane Smith',
            'position': 'MP',
            'constituency': 'Westlands',
            'department': 'Parliament'
        },
        {
            'name': 'Bob Johnson',
            'position': 'Senator',
            'constituency': 'Nairobi',
            'department': 'Senate'
        }
    ]

    for official_data in officials_data:
        existing = Official.query.filter_by(
            name=official_data['name'],
            position=official_data['position']
        ).first()

        if not existing:
            official = Official(
                name=official_data['name'],
                position=official_data['position'],
                constituency=official_data['constituency'],
                department=official_data['department'],
                ratings=[],
                average_score=0.0,
                rating_count=0,
                last_updated=datetime.utcnow()
            )
            db.session.add(official)
            print(f"✓ Created official: {official_data['name']}")

    try:
        db.session.commit()
        print("✓ Sample data created")
    except Exception as e:
        db.session.rollback()
        print(f"Error creating sample data: {e}")

def main():
    """Main migration function"""
    print("=" * 50)
    print("REVOLUT DATABASE MIGRATION AND FIX")
    print("=" * 50)

    # Create Flask app context
    app = create_app()

    with app.app_context():
        print("Connected to database")

        # Create all tables
        print("Creating database tables...")
        db.create_all()
        print("✓ Database tables created")

        # Run migrations
        create_missing_columns()
        create_roles()
        fix_user_passwords()
        create_admin_user()
        create_sample_data()

        print("\n" + "=" * 50)
        print("MIGRATION COMPLETED")
        print("=" * 50)

        # Show summary
        print("\nDATABASE SUMMARY:")
        print(f"Users: {User.query.count()}")
        print(f"Roles: {Role.query.count()}")
        print(f"Officials: {Official.query.count()}")
        print(f"Issues: {Issue.query.count()}")
        print(f"Feedback: {UserFeedback.query.count()}")

        print("\nNEXT STEPS:")
        print("1. Try logging in with admin/admin123")
        print("2. Reset your user password if needed:")
        print("   python fix_db.py --reset-password username newpassword")
        print("3. Start your Flask app: flask run")

def reset_password_cli():
    """CLI function to reset user password"""
    if len(sys.argv) >= 4 and sys.argv[1] == '--reset-password':
        username = sys.argv[2]
        new_password = sys.argv[3]

        app = create_app()
        with app.app_context():
            success = reset_user_password(username, new_password)
            if success:
                print(f"\n✓ You can now login with:")
                print(f"   Username: {username}")
                print(f"   Password: {new_password}")
    else:
        print("Usage: python fix_db.py --reset-password <username> <new_password>")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--reset-password':
        reset_password_cli()
    else:
        main()