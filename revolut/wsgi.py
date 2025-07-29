
from app import create_app, db
from app.models import User, Role, Official, Poll, UserFeedback, Issue, Alert
import os

app = create_app()

# Create tables and initial data
with app.app_context():
    try:
        db.create_all()
        
        # Create roles if they don't exist
        roles_to_create = ['admin', 'cso', 'official', 'citizen']
        for role_name in roles_to_create:
            if not Role.query.filter_by(name=role_name).first():
                role = Role(name=role_name, description=f'{role_name.title()} role')
                db.session.add(role)
        
        # Create default admin user if it doesn't exist
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_role = Role.query.filter_by(name='admin').first()
            admin_user = User(
                username='admin',
                email='admin@revolut.com',
                active=True
            )
            admin_user.set_password('admin123')
            if admin_role:
                admin_user.roles.append(admin_role)
            db.session.add(admin_user)
        
        db.session.commit()
        print("Database initialized successfully!")
        
    except Exception as e:
        print(f"Database initialization error: {e}")
        db.session.rollback()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
