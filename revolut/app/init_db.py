# init_db.py - Run this script to initialize your database
from app import create_app, db
from app.models import User, Role, Official
from werkzeug.security import generate_password_hash

def init_database():
    """Initialize the database with basic data"""
    app = create_app()

    with app.app_context():
        # Create all tables
        db.create_all()

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

        # Create admin user if doesn't exist
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@revolut.co.ke',
                active=True
            )
            admin_user.set_password('admin123')  # Change this password!

            admin_role = Role.query.filter_by(name='admin').first()
            if admin_role:
                admin_user.roles.append(admin_role)

            db.session.add(admin_user)
            print("Created admin user (username: admin, password: admin123)")

        # Create sample CSO user
        cso_user = User.query.filter_by(username='cso_demo').first()
        if not cso_user:
            cso_user = User(
                username='cso_demo',
                email='cso@demo.co.ke',
                active=True
            )
            cso_user.set_password('cso123')

            cso_role = Role.query.filter_by(name='cso').first()
            if cso_role:
                cso_user.roles.append(cso_role)

            db.session.add(cso_user)
            print("Created CSO demo user (username: cso_demo, password: cso123)")

        # Create sample officials
        sample_officials = [
            {
                'name': 'John Kamau',
                'position': 'Governor',
                'constituency': 'Nairobi County',
                'department': 'County Government',
                'ratings': [],
                'average_score': 0.0,
                'rating_count': 0
            },
            {
                'name': 'Mary Wanjiku',
                'position': 'MP',
                'constituency': 'Westlands',
                'department': 'Parliament',
                'ratings': [],
                'average_score': 0.0,
                'rating_count': 0
            },
            {
                'name': 'Peter Ochieng',
                'position': 'Senator',
                'constituency': 'Kisumu County',
                'department': 'Senate',
                'ratings': [],
                'average_score': 0.0,
                'rating_count': 0
            }
        ]

        for official_data in sample_officials:
            official = Official.query.filter_by(
                name=official_data['name'],
                constituency=official_data['constituency']
            ).first()
            if not official:
                official = Official(**official_data)
                db.session.add(official)
                print(f"Created official: {official_data['name']}")

        # Commit all changes
        db.session.commit()
        print("Database initialized successfully!")

        return True

if __name__ == "__main__":
    init_database()