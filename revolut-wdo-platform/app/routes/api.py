from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models import User, Feedback, Poll, PollOption, PollResponse
from app import db
import json

api = Blueprint('api', __name__)

@api.route('/login', methods=['POST'])
def api_login():
    """API endpoint for user authentication"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400

        # Try to find user by username or email
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()

        if user and user.check_password(password) and user.is_active:
            access_token = create_access_token(identity=user.id)
            return jsonify({
                'access_token': access_token,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role
                }
            }), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/register', methods=['POST'])
def api_register():
    """API endpoint for user registration"""
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not all([username, email, password]):
            return jsonify({'error': 'Username, email and password required'}), 400

        # Check if user already exists
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400

        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(identity=user.id)
        return jsonify({
            'message': 'User created successfully',
            'access_token': access_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api.route('/user/profile', methods=['GET'])
@jwt_required()
def get_user_profile():
    """Get current user profile"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'phone': getattr(user, 'phone', None),
                'bio': getattr(user, 'bio', None),
                'role': user.role,
                'created_at': user.created_at.isoformat() if hasattr(user, 'created_at') else None
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/feedback', methods=['POST'])
@jwt_required()
def create_feedback():
    """Create new feedback"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        title = data.get('title')
        content = data.get('content')
        category = data.get('category', 'general')

        if not title or not content:
            return jsonify({'error': 'Title and content required'}), 400

        feedback = Feedback(
            title=title,
            content=content,
            category=category,
            user_id=user_id
        )

        db.session.add(feedback)
        db.session.commit()

        return jsonify({
            'message': 'Feedback created successfully',
            'feedback': {
                'id': feedback.id,
                'title': feedback.title,
                'content': feedback.content,
                'category': feedback.category,
                'status': getattr(feedback, 'status', 'pending')
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api.route('/feedback', methods=['GET'])
@jwt_required()
def get_user_feedback():
    """Get user's feedback"""
    try:
        user_id = get_jwt_identity()
        feedbacks = Feedback.query.filter_by(user_id=user_id).all()

        feedback_list = []
        for feedback in feedbacks:
            feedback_list.append({
                'id': feedback.id,
                'title': feedback.title,
                'content': feedback.content,
                'category': feedback.category,
                'status': getattr(feedback, 'status', 'pending'),
                'created_at': feedback.created_at.isoformat() if hasattr(feedback, 'created_at') else None
            })

        return jsonify({'feedbacks': feedback_list}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/polls', methods=['GET'])
def get_polls():
    """Get all active polls"""
    try:
        polls = Poll.query.filter_by(is_active=True).all()

        poll_list = []
        for poll in polls:
            options = []
            if hasattr(poll, 'options'):
                for option in poll.options:
                    options.append({
                        'id': option.id,
                        'text': option.text,
                        'votes': option.vote_count if hasattr(option, 'vote_count') else 0
                    })

            poll_list.append({
                'id': poll.id,
                'question': poll.question,
                'options': options,
                'created_at': poll.created_at.isoformat() if hasattr(poll, 'created_at') else None
            })

        return jsonify({'polls': poll_list}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/polls/<int:poll_id>/vote', methods=['POST'])
@jwt_required()
def vote_poll(poll_id):
    """Vote in a poll"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        option_id = data.get('option_id')

        if not option_id:
            return jsonify({'error': 'Option ID required'}), 400

        # Check if poll exists
        poll = Poll.query.get(poll_id)
        if not poll:
            return jsonify({'error': 'Poll not found'}), 404

        # Check if user already voted
        existing_vote = PollResponse.query.filter_by(user_id=user_id, poll_id=poll_id).first()
        if existing_vote:
            return jsonify({'error': 'You have already voted in this poll'}), 400

        # Create vote
        vote = PollResponse(user_id=user_id, poll_id=poll_id, option_id=option_id)
        db.session.add(vote)
        db.session.commit()

        return jsonify({'message': 'Vote recorded successfully'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api.route('/stats', methods=['GET'])
@jwt_required()
def get_stats():
    """Get basic statistics"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        stats = {
            'total_users': User.query.count(),
            'total_feedback': Feedback.query.count(),
            'total_polls': Poll.query.count(),
            'user_feedback_count': Feedback.query.filter_by(user_id=user_id).count(),
            'user_votes_count': PollResponse.query.filter_by(user_id=user_id).count()
        }

        return jsonify({'stats': stats}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'API is running'
    }), 200