# create_initial_data.py
from app import create_app
from app.models import db, Role, User

app = create_app()

with app.app_context():
    # Create roles
    roles = [
        ('admin', 'System Administrator'),
        ('cso', 'Civil Society Organization'),
        ('official', 'Government Official'),
        ('citizen', 'Regular Citizen')
    ]

    for name, description in roles:
        if not Role.query.filter_by(name=name).first():
            role = Role(name=name, description=description)
            db.session.add(role)

    # Create admin user if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@revolutwdo.org',
            phone='+254700000000'
        )
        admin.set_password('admin123')
        admin_role = Role.query.filter_by(name='admin').first()
        admin.roles.append(admin_role)
        db.session.add(admin)

    db.session.commit()
    print("Initial data created successfully")