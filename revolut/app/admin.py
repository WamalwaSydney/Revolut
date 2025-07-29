# app/admin.py - Complete Admin Blueprint
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
from app import db
from app.models import User, Role, Official, Poll, UserFeedback, Issue, Alert, user_roles
from app.auth import role_required
import json

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Dashboard Routes
@admin_bp.route('/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    """Render the admin dashboard page"""
    return render_template('admin_dashboard.html')

@admin_bp.route('/api/dashboard-data')
@login_required
@role_required('admin')
def get_dashboard_data():
    """Get comprehensive dashboard data"""
    try:
        # Get basic statistics
        total_users = User.query.count()
        active_polls = Poll.query.filter(
            and_(Poll.expires_at > datetime.utcnow() if Poll.expires_at else True)
        ).all()
        officials_count = Official.query.count()

        # Get feedback statistics by location
        feedback_stats = db.session.query(
            UserFeedback.location,
            func.count(UserFeedback.id).label('count'),
            func.avg(UserFeedback.sentiment_score).label('avg_sentiment')
        ).group_by(UserFeedback.location).all()

        feedback_stats_data = []
        for stat in feedback_stats:
            feedback_stats_data.append({
                'location': stat.location or 'Unknown',
                'count': stat.count,
                'avg_sentiment': float(stat.avg_sentiment) if stat.avg_sentiment else 0.0
            })

        # Format active polls data
        polls_data = []
        for poll in active_polls:
            options = poll.options if isinstance(poll.options, list) else []
            total_votes = sum(opt.get('votes', 0) for opt in options)

            formatted_options = []
            for opt in options:
                votes = opt.get('votes', 0)
                percentage = (votes / total_votes * 100) if total_votes > 0 else 0
                formatted_options.append({
                    'text': opt.get('text', ''),
                    'votes': votes,
                    'percentage': round(percentage, 1)
                })

            polls_data.append({
                'id': poll.id,
                'question': poll.question,
                'options': formatted_options,
                'total_votes': total_votes,
                'created_at': poll.created_at.isoformat(),
                'expires_at': poll.expires_at.isoformat() if poll.expires_at else None,
                'is_active': poll.expires_at > datetime.utcnow() if poll.expires_at else True,
                'status': 'Active' if (poll.expires_at > datetime.utcnow() if poll.expires_at else True) else 'Expired'
            })

        return jsonify({
            'total_users': total_users,
            'active_polls': polls_data,
            'officials_count': officials_count,
            'feedback_stats': feedback_stats_data
        })

    except Exception as e:
        print(f"Dashboard data error: {e}")
        return jsonify({'error': str(e)}), 500

# User Management Routes
@admin_bp.route('/users', methods=['GET'])
@login_required
@role_required('admin')
def list_users():
    """Get all users with their roles"""
    try:
        users = User.query.all()
        users_data = []

        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'roles': [role.name for role in user.roles],
                'active': user.active,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'created_at': user.created_at.isoformat()
            })

        return jsonify(users_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@login_required
@role_required('admin')
def update_user(user_id):
    """Update user information"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()

        if 'username' in data:
            user.username = data['username']
        if 'email' in data:
            user.email = data['email']
        if 'active' in data:
            user.active = data['active']
        if 'roles' in data:
            # Clear existing roles
            user.roles.clear()
            # Add new roles
            for role_name in data['roles']:
                role = Role.query.filter_by(name=role_name).first()
                if role:
                    user.roles.append(role)

        db.session.commit()
        return jsonify({'message': 'User updated successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@login_required
@role_required('admin')
def delete_user(user_id):
    """Delete a user"""
    try:
        user = User.query.get_or_404(user_id)

        # Don't allow deleting the current admin user
        if user.id == current_user.id:
            return jsonify({'error': 'Cannot delete your own account'}), 400

        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'User deleted successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Officials Management Routes
@admin_bp.route('/officials', methods=['GET'])
@login_required
@role_required('admin')
def list_officials():
    """Get all officials with their ratings"""
    try:
        officials = Official.query.all()
        officials_data = []

        for official in officials:
            officials_data.append({
                'id': official.id,
                'name': official.name,
                'position': official.position,
                'constituency': official.constituency,
                'department': official.department,
                'average_score': official.average_score,
                'rating_count': official.rating_count,
                'last_updated': official.last_updated.isoformat() if official.last_updated else None
            })

        return jsonify(officials_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/officials', methods=['POST'])
@login_required
@role_required('admin')
def create_official():
    """Create a new official"""
    try:
        data = request.get_json()

        official = Official(
            name=data['name'],
            position=data['position'],
            constituency=data['constituency'],
            department=data.get('department'),
            ratings=[],
            average_score=0.0,
            rating_count=0
        )

        db.session.add(official)
        db.session.commit()

        return jsonify({'message': 'Official created successfully', 'id': official.id})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/officials/<int:official_id>', methods=['PUT'])
@login_required
@role_required('admin')
def update_official(official_id):
    """Update official information"""
    try:
        official = Official.query.get_or_404(official_id)
        data = request.get_json()

        if 'name' in data:
            official.name = data['name']
        if 'position' in data:
            official.position = data['position']
        if 'constituency' in data:
            official.constituency = data['constituency']
        if 'department' in data:
            official.department = data['department']

        official.last_updated = datetime.utcnow()
        db.session.commit()

        return jsonify({'message': 'Official updated successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/officials/<int:official_id>', methods=['DELETE'])
@login_required
@role_required('admin')
def delete_official(official_id):
    """Delete an official"""
    try:
        official = Official.query.get_or_404(official_id)
        db.session.delete(official)
        db.session.commit()

        return jsonify({'message': 'Official deleted successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Poll Management Routes
@admin_bp.route('/api/polls/results')
@login_required
@role_required('admin')
def get_poll_results():
    """Get all polls with results"""
    try:
        polls = Poll.query.order_by(desc(Poll.created_at)).all()
        polls_data = []

        for poll in polls:
            options = poll.options if isinstance(poll.options, list) else []
            total_votes = sum(opt.get('votes', 0) for opt in options)

            formatted_options = []
            for opt in options:
                votes = opt.get('votes', 0)
                percentage = (votes / total_votes * 100) if total_votes > 0 else 0
                formatted_options.append({
                    'text': opt.get('text', ''),
                    'votes': votes,
                    'percentage': round(percentage, 1)
                })

            is_active = poll.expires_at > datetime.utcnow() if poll.expires_at else True

            polls_data.append({
                'id': poll.id,
                'question': poll.question,
                'options': formatted_options,
                'total_votes': total_votes,
                'created_at': poll.created_at.isoformat(),
                'expires_at': poll.expires_at.isoformat() if poll.expires_at else None,
                'is_active': is_active,
                'status': 'Active' if is_active else 'Expired',
                'created_by': poll.user.username if poll.user else 'Unknown'
            })

        return jsonify({'polls': polls_data})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/polls', methods=['POST'])
@login_required
@role_required('admin')
def create_poll():
    """Create a new poll"""
    try:
        data = request.get_json()

        # Calculate expiry date
        expires_at = None
        if data.get('duration_days'):
            expires_at = datetime.utcnow() + timedelta(days=int(data['duration_days']))

        # Format options
        options = []
        for option_text in data['options']:
            options.append({
                'text': option_text,
                'votes': 0
            })

        poll = Poll(
            question=data['question'],
            options=options,
            created_by=current_user.id,
            expires_at=expires_at
        )

        db.session.add(poll)
        db.session.commit()

        # TODO: Send SMS notifications if notify_citizens is True
        if data.get('notify_citizens'):
            # Implement SMS notification logic here
            pass

        return jsonify({'message': 'Poll created successfully', 'id': poll.id})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/polls/<int:poll_id>', methods=['PUT'])
@login_required
@role_required('admin')
def update_poll(poll_id):
    """Update a poll"""
    try:
        poll = Poll.query.get_or_404(poll_id)
        data = request.get_json()

        if 'question' in data:
            poll.question = data['question']
        if 'expires_at' in data:
            poll.expires_at = datetime.fromisoformat(data['expires_at']) if data['expires_at'] else None

        db.session.commit()
        return jsonify({'message': 'Poll updated successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/polls/<int:poll_id>', methods=['DELETE'])
@login_required
@role_required('admin')
def delete_poll(poll_id):
    """Delete a poll"""
    try:
        poll = Poll.query.get_or_404(poll_id)
        db.session.delete(poll)
        db.session.commit()

        return jsonify({'message': 'Poll deleted successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Feedback Management Routes
@admin_bp.route('/api/feedback')
@login_required
@role_required('admin')
def get_feedback():
    """Get all feedback with filtering options"""
    try:
        query = UserFeedback.query

        # Apply filters if provided
        sentiment_filter = request.args.get('sentiment')
        if sentiment_filter:
            if sentiment_filter == 'positive':
                query = query.filter(UserFeedback.sentiment_score > 0.1)
            elif sentiment_filter == 'negative':
                query = query.filter(UserFeedback.sentiment_score < -0.1)
            elif sentiment_filter == 'neutral':
                query = query.filter(
                    and_(UserFeedback.sentiment_score >= -0.1, UserFeedback.sentiment_score <= 0.1)
                )

        feedback_items = query.order_by(desc(UserFeedback.created_at)).limit(100).all()

        feedback_data = []
        for feedback in feedback_items:
            feedback_data.append({
                'id': feedback.id,
                'content': feedback.content,
                'sentiment_score': feedback.sentiment_score,
                'location': feedback.location,
                'language': feedback.language,
                'gender': feedback.gender,
                'created_at': feedback.created_at.isoformat(),
                'is_processed': feedback.is_processed,
                'tags': feedback.tags,
                'user': feedback.user.username if feedback.user else 'Anonymous',
                'source': 'web'  # You can enhance this based on your needs
            })

        return jsonify(feedback_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/feedback/<int:feedback_id>')
@login_required
@role_required('admin')
def get_feedback_details(feedback_id):
    """Get detailed feedback information"""
    try:
        feedback = UserFeedback.query.get_or_404(feedback_id)

        return jsonify({
            'id': feedback.id,
            'content': feedback.content,
            'audio_url': feedback.audio_url,
            'sentiment_score': feedback.sentiment_score,
            'location': feedback.location,
            'language': feedback.language,
            'gender': feedback.gender,
            'created_at': feedback.created_at.isoformat(),
            'is_processed': feedback.is_processed,
            'tags': feedback.tags,
            'user': feedback.user.username if feedback.user else 'Anonymous'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/feedback/<int:feedback_id>/respond', methods=['POST'])
@login_required
@role_required('admin')
def respond_to_feedback(feedback_id):
    """Respond to feedback (placeholder for future implementation)"""
    try:
        feedback = UserFeedback.query.get_or_404(feedback_id)
        data = request.get_json()

        # Mark as processed
        feedback.is_processed = True
        db.session.commit()

        # TODO: Implement actual response mechanism (email, SMS, etc.)
        response_text = data.get('response', '')

        return jsonify({'message': 'Response sent successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Analytics Routes
@admin_bp.route('/api/analytics/engagement')
@login_required
@role_required('admin')
def get_engagement_analytics():
    """Get user engagement analytics"""
    try:
        # Calculate engagement metrics
        total_users = User.query.count()
        active_users = User.query.filter(User.last_login >= datetime.utcnow() - timedelta(days=30)).count()

        engagement_rate = (active_users / total_users * 100) if total_users > 0 else 0

        # Get feedback satisfaction score
        avg_sentiment = db.session.query(func.avg(UserFeedback.sentiment_score)).scalar()
        satisfaction_score = ((avg_sentiment + 1) / 2 * 5) if avg_sentiment else 0  # Convert to 0-5 scale

        # Calculate growth rate (simplified)
        last_month_users = User.query.filter(
            User.created_at >= datetime.utcnow() - timedelta(days=60),
            User.created_at < datetime.utcnow() - timedelta(days=30)
        ).count()
        this_month_users = User.query.filter(
            User.created_at >= datetime.utcnow() - timedelta(days=30)
        ).count()

        growth_rate = ((this_month_users - last_month_users) / last_month_users * 100) if last_month_users > 0 else 0

        return jsonify({
            'engagement_rate': round(engagement_rate, 1),
            'satisfaction_score': round(satisfaction_score, 1),
            'growth_rate': round(growth_rate, 1),
            'total_users': total_users,
            'active_users': active_users
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# System Settings Routes
@admin_bp.route('/api/settings/general', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def manage_general_settings():
    """Manage general system settings"""
    if request.method == 'GET':
        # Return current settings (you might want to store these in a Settings model)
        return jsonify({
            'system_name': 'Revolut & WDO',
            'default_language': 'en',
            'timezone': 'UTC'
        })

    elif request.method == 'POST':
        try:
            data = request.get_json()
            # TODO: Save settings to database or config file
            return jsonify({'message': 'Settings updated successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/settings/sms', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def manage_sms_settings():
    """Manage SMS configuration settings"""
    if request.method == 'GET':
        # Return current SMS settings (without sensitive data)
        return jsonify({
            'username': '****',  # Masked for security
            'api_key': '****'    # Masked for security
        })

    elif request.method == 'POST':
        try:
            data = request.get_json()
            # TODO: Save SMS settings securely
            return jsonify({'message': 'SMS settings updated successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

# Additional API Routes for Dashboard Functionality
@admin_bp.route('/api/scorecards/officials')
@login_required
@role_required('admin')
def get_officials_scorecards():
    """Get officials data formatted for scorecards"""
    try:
        officials = Official.query.all()

        # Group by department for easier display
        grouped_officials = {}
        for official in officials:
            dept = official.department or 'Other'
            if dept not in grouped_officials:
                grouped_officials[dept] = []

            grouped_officials[dept].append({
                'id': official.id,
                'name': official.name,
                'position': official.position,
                'constituency': official.constituency,
                'department': official.department,
                'average_score': official.average_score,
                'rating_count': official.rating_count
            })

        return jsonify({'officials': grouped_officials})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Authentication helper route
@admin_bp.route('/auth/logout')
@login_required
def logout():
    """Logout the current user"""
    from flask_login import logout_user
    logout_user()
    return jsonify({'message': 'Logged out successfully'})

# User registration route for admin to create users
@admin_bp.route('/auth/register', methods=['POST'])
@login_required
@role_required('admin')
def admin_create_user():
    """Admin route to create new users"""
    try:
        data = request.get_json()

        # Check if user already exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already exists'}), 400

        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 400

        # Create new user
        user = User(
            username=data['username'],
            email=data['email'],
            active=True,
            created_at=datetime.utcnow()
        )
        user.set_password(data['password'])

        # Assign role
        role = Role.query.filter_by(name=data['role']).first()
        if role:
            user.roles.append(role)

        db.session.add(user)
        db.session.commit()

        return jsonify({'message': 'User created successfully', 'id': user.id})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500