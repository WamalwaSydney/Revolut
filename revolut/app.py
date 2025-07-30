# app.py - Main application entry point
import os
from app import create_app, db
from app.models import User, Role, Official, Poll, UserFeedback, Issue, Alert
from flask_migrate import upgrade

app = create_app()

def create_default_data():
    """Create default roles and admin user"""
    with app.app_context():
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

        db.session.commit()

        # Create admin user if it doesn't exist
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_role = Role.query.filter_by(name='admin').first()
            admin_user = User(
                username='admin',
                email='admin@revolut.rw',
                active=True
            )
            admin_user.set_password('admin123')  # Change this password!
            admin_user.roles.append(admin_role)
            db.session.add(admin_user)
            db.session.commit()
            print("Default admin user created: admin/admin123")

@app.before_first_request
def deploy():
    """Run deployment tasks"""
    # Create database tables
    db.create_all()

    # Create default data
    create_default_data()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)