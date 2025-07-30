from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import JSON

# Association table for many-to-many roles
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    description = db.Column(db.String(200))

    def __repr__(self):
        return f'<Role {self.name}>'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(288))
    phone = db.Column(db.String(20))
    active = db.Column(db.Boolean(), default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    roles = db.relationship('Role', secondary=user_roles, backref=db.backref('users', lazy='dynamic'))

    language = db.Column(db.String(2), default='en')

    def get_locale(self):
        return self.language or 'en'

    def set_password(self, password):
        # Use method='pbkdf2:sha256' with a shorter salt_length to ensure hash fits in column
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, role_name):
        """Check if user has a specific role"""
        return any(role.name == role_name for role in self.roles)

    def get_role_names(self):
        """Get list of role names for this user"""
        return [role.name for role in self.roles]

    def is_active(self):
        """Override Flask-Login's is_active method"""
        return self.active

    def __repr__(self):
        return f'<User {self.username}>'

class UserFeedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), default='anonymous')
    content = db.Column(db.Text, nullable=False)
    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'), nullable=True)
    location = db.Column(db.String(100))
    gender = db.Column(db.String(10))
    contact = db.Column(db.String(20))
    language = db.Column(db.String(10), default='en')
    source = db.Column(db.String(20), default='web')
    sentiment_score = db.Column(db.Float, default=0.0)
    tags = db.Column(JSON)
    is_processed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), default='General')
    priority = db.Column(db.String(20), default='Medium')
    status = db.Column(db.String(20), default='Open')
    created_by = db.Column(db.String(50), default='anonymous')
    contact = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to feedback
    feedback = db.relationship('UserFeedback', backref='related_issue', lazy=True)

class Official(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    constituency = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100))
    ratings = db.Column(JSON)
    average_score = db.Column(db.Float)
    rating_count = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class Poll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    options = db.Column(JSON, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    user = db.relationship('User', backref=db.backref('polls', lazy='dynamic'))

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), nullable=False)
    affected_locations = db.Column(JSON)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('alerts', lazy='dynamic'))
