# init_db.py - Database initialization script
from app import create_app, db
from app.models import User, Role, Official, Poll
from datetime import datetime, timedelta

def init_database():
    """Initialize database with default data"""
    app = create_app()

    with app.app_context():
        # Create all tables
        db.create_all()

        print("Creating roles...")
        # Create roles if they don't exist
        roles_data = [
            {'name': 'admin', 'description': 'System administrator'},
            {'name': 'cso', 'description': 'Civil Society Organization'},
            {'name': 'citizen', 'description': 'Regular citizen'},
            {'name': 'official', 'description': 'Government official'}
        ]

        for role_data in roles_data:
            role = Role.query.filter_by(name=role_data['name']).first()
            if not role:
                role = Role(**role_data)
                db.session.add(role)
                print(f"Created role: {role_data['name']}")

        db.session.commit()

        print("Creating test users...")
        # Create test users
        test_users = [
            {
                'username': 'admin',
                'email': 'admin@revolut.com',
                'password': 'admin123',
                'role': 'admin'
            },
            {
                'username': 'cso_user',
                'email': 'cso@revolut.com',
                'password': 'cso123',
                'role': 'cso'
            },
            {
                'username': 'citizen',
                'email': 'citizen@revolut.com',
                'password': 'citizen123',
                'role': 'citizen'
            },
            {
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'password123',
                'role': 'citizen'
            }
        ]

        for user_data in test_users:
            # Check if user already exists
            existing_user = User.query.filter_by(username=user_data['username']).first()
            if existing_user:
                print(f"User {user_data['username']} already exists, skipping...")
                continue

            # Create new user
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                active=True,
                created_at=datetime.utcnow()
            )

            # Set password using the model method
            user.set_password(user_data['password'])

            # Add role
            role = Role.query.filter_by(name=user_data['role']).first()
            if role:
                user.roles.append(role)

            db.session.add(user)
            print(f"Created user: {user_data['username']} with password: {user_data['password']}")

        db.session.commit()

        print("Creating sample officials...")
        # Create sample officials
        sample_officials = [
            {
                'name': 'John Doe',
                'position': 'Governor',
                'constituency': 'Nairobi',
                'department': 'Executive',
                'ratings': [],
                'average_score': 0.0,
                'rating_count': 0
            },
            {
                'name': 'Jane Smith',
                'position': 'MP',
                'constituency': 'Westlands',
                'department': 'Legislative',
                'ratings': [],
                'average_score': 0.0,
                'rating_count': 0
            }
        ]

        for official_data in sample_officials:
            existing_official = Official.query.filter_by(
                name=official_data['name'],
                position=official_data['position']
            ).first()

            if not existing_official:
                official = Official(**official_data)
                db.session.add(official)
                print(f"Created official: {official_data['name']}")

        db.session.commit()

        print("Creating sample poll...")
        # Create a sample poll
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user:
            existing_poll = Poll.query.first()
            if not existing_poll:
                poll = Poll(
                    question="How would you rate the current education system?",
                    options=[
                        {"id": 1, "text": "Excellent", "votes": 0},
                        {"id": 2, "text": "Good", "votes": 0},
                        {"id": 3, "text": "Fair", "votes": 0},
                        {"id": 4, "text": "Poor", "votes": 0}
                    ],
                    created_by=admin_user.id,
                    expires_at=datetime.utcnow() + timedelta(days=30)
                )
                db.session.add(poll)
                print("Created sample poll")

        db.session.commit()

        print("Database initialization completed!")
        print("\n=== TEST USERS CREATED ===")
        print("Admin: username='admin', password='admin123'")
        print("CSO: username='cso_user', password='cso123'")
        print("Citizen: username='citizen', password='citizen123'")
        print("Test: username='testuser', password='password123'")
        print("============================")

def test_user_passwords():
    """Test that user passwords work correctly"""
    app = create_app()

    with app.app_context():
        print("\n=== TESTING USER PASSWORDS ===")

        test_users = [
            ('admin', 'admin123'),
            ('cso_user', 'cso123'),
            ('citizen', 'citizen123'),
            ('testuser', 'password123')
        ]

        for username, password in test_users:
            user = User.query.filter_by(username=username).first()
            if user:
                can_login = user.check_password(password)
                print(f"User: {username}")
                print(f"  Password: {password}")
                print(f"  Can login: {can_login}")
                print(f"  Hash exists: {user.password_hash is not None}")
                print(f"  Hash length: {len(user.password_hash) if user.password_hash else 0}")
                print(f"  Active: {user.active}")
                print("---")
            else:
                print(f"User {username} not found!")

        print("=== END PASSWORD TEST ===\n")

if __name__ == '__main__':
    print("Initializing database...")
    init_database()
    test_user_passwords()