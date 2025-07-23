from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from datetime import datetime
from enum import Enum
import uuid

class UserRole(Enum):
    CITIZEN = 'citizen'
    ANALYST = 'analyst'
    GOVERNMENT = 'government'
    ADMIN = 'admin'

class FeedbackCategory(Enum):
    EDUCATION = 'education'
    HEALTH = 'health'
    INFRASTRUCTURE = 'infrastructure'
    SECURITY = 'security'
    WATER = 'water'
    SANITATION = 'sanitation'
    AGRICULTURE = 'agriculture'
    TRANSPORT = 'transport'
    OTHER = 'other'

class Priority(Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    URGENT = 'urgent'

class FeedbackStatus(Enum):
    PENDING = 'pending'
    REVIEWED = 'reviewed'
    IN_PROGRESS = 'in_progress'
    RESOLVED = 'resolved'
    REJECTED = 'rejected'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(100), unique=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(128))
    role = db.Column(db.Enum(UserRole), default=UserRole.CITIZEN)
    county = db.Column(db.String(100))
    constituency = db.Column(db.String(100))
    ward = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    feedbacks = db.relationship('Feedback', backref='user', lazy=True)
    responses = db.relationship('FeedbackResponse', backref='user', lazy=True)
    poll_responses = db.relationship('PollResponse', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_government(self):
        return self.role in [UserRole.GOVERNMENT, UserRole.ADMIN]
    
    def is_admin(self):
        return self.role == UserRole.ADMIN

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(100), unique=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.Enum(FeedbackCategory), nullable=False)
    priority = db.Column(db.Enum(Priority), default=Priority.MEDIUM)
    status = db.Column(db.Enum(FeedbackStatus), default=FeedbackStatus.PENDING)
    county = db.Column(db.String(100), nullable=False)
    constituency = db.Column(db.String(100))
    ward = db.Column(db.String(100))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    sentiment_score = db.Column(db.Float)
    sentiment_label = db.Column(db.String(20))
    submission_method = db.Column(db.String(20), default='web')
    language = db.Column(db.String(10), default='en')
    is_anonymous = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    responses = db.relationship('FeedbackResponse', backref='feedback', lazy=True)
    
    def __repr__(self):
        return f'<Feedback {self.title}>'

class FeedbackResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    is_official = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    feedback_id = db.Column(db.Integer, db.ForeignKey('feedback.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    def __repr__(self):
        return f'<FeedbackResponse {self.id}>'

class Poll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(100), unique=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    question = db.Column(db.String(300), nullable=False)
    county = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Foreign keys
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    options = db.relationship('PollOption', backref='poll', lazy=True)
    responses = db.relationship('PollResponse', backref='poll', lazy=True)
    
    def __repr__(self):
        return f'<Poll {self.title}>'

class PollOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    vote_count = db.Column(db.Integer, default=0)
    
    # Foreign keys
    poll_id = db.Column(db.Integer, db.ForeignKey('poll.id'))
    
    def __repr__(self):
        return f'<PollOption {self.text}>'

class PollResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    poll_id = db.Column(db.Integer, db.ForeignKey('poll.id'))
    option_id = db.Column(db.Integer, db.ForeignKey('poll_option.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    def __repr__(self):
        return f'<PollResponse {self.id}>'
