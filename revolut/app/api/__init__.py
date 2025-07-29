# app/api/__init__.py - Fixed Main API
from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models import UserFeedback, Poll, Alert, Role, User, Issue, Official
from datetime import datetime
import traceback
from flask_login import current_user

api = Blueprint('api', __name__, url_prefix='/api')

@api.route('/feedback', methods=['POST'])
def submit_feedback():
    """Submit citizen feedback and optionally link to existing issue"""
    try:
        data = request.get_json()

        current_app.logger.info(f"Feedback submission request: {data}")

        # Validate required fields
        if not data or not data.get('content'):
            return jsonify({"error": "Feedback content is required"}), 400

        content = data.get('content', '').strip()
        if len(content) < 5:
            return jsonify({"error": "Feedback must be at least 5 characters long"}), 400

        # Link to existing issue if provided
        issue_id = data.get('issue_id')
        issue = None
        if issue_id:
            try:
                issue_id = int(issue_id)
                issue = Issue.query.get(issue_id)
                if not issue:
                    return jsonify({"error": "Issue not found"}), 404
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid issue ID"}), 400

        # Create feedback
        feedback = UserFeedback(
            user_id = current_user.id if current_user.is_authenticated else 'anonymous',
            content=content,
            issue_id=issue_id,
            location=data.get('location', '').strip() if data.get('location') else None,
            gender=data.get('gender', '').strip() if data.get('gender') else None,
            contact=data.get('contact', '').strip() if data.get('contact') else None,
            language=data.get('language', 'en'),
            source=data.get('source', 'web'),
            sentiment_score=0.0,  # Default sentiment, can be updated later
            tags=data.get('tags', []),
            is_processed=False,
            created_at=datetime.utcnow()
        )

        db.session.add(feedback)
        db.session.commit()

        current_app.logger.info(f"Feedback created successfully: ID {feedback.id}")

        # Process feedback (NLP and alerts) - optional, can be implemented later
        try:
            # from app.utils.nlp_processor import process_feedback
            # from app.utils.alerts import check_for_trending_issues
            # process_feedback(feedback.id)
            # check_for_trending_issues()
            pass
        except Exception as e:
            current_app.logger.warning(f"Failed to process feedback: {str(e)}")

        # Send SMS confirmation if contact provided
        if feedback.contact and feedback.source != 'sms':
            try:
                # from app.utils.sms import send_sms
                # message = f"Thank you for your feedback! Ref: {feedback.id}"
                # if issue:
                #     message += f"\nLinked to issue: {issue.title}"
                # send_sms(feedback.contact, message)
                current_app.logger.info(f"SMS confirmation would be sent to {feedback.contact}")
            except Exception as e:
                current_app.logger.error(f"SMS send failed: {str(e)}")

        return jsonify({
            "status": "success",
            "feedback_id": feedback.id,
            "issue_linked": bool(issue),
            "message": "Feedback submitted successfully"
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error submitting feedback: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Failed to submit feedback: {str(e)}"}), 500

@api.route('/feedback', methods=['GET'])
def get_feedback():
    """Get all feedback with optional filtering"""
    try:
        sentiment = request.args.get('sentiment')
        location = request.args.get('location')
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)  # Limit per_page

        query = UserFeedback.query

        if sentiment:
            if sentiment == 'positive':
                query = query.filter(UserFeedback.sentiment_score > 0.1)
            elif sentiment == 'negative':
                query = query.filter(UserFeedback.sentiment_score < -0.1)
            elif sentiment == 'neutral':
                query = query.filter(UserFeedback.sentiment_score.between(-0.1, 0.1))

        if location:
            query = query.filter(UserFeedback.location.ilike(f'%{location}%'))

        # Paginate results
        pagination = query.order_by(UserFeedback.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        feedback_items = pagination.items

        return jsonify({
            'feedback': [{
                'id': f.id,
                'content': f.content,
                'issue_id': f.issue_id,
                'location': f.location,
                'sentiment_score': f.sentiment_score,
                'created_at': f.created_at.isoformat(),
                'source': f.source,
                'is_processed': f.is_processed
            } for f in feedback_items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        })
    except Exception as e:
        current_app.logger.error(f"Error getting feedback: {str(e)}")
        return jsonify({"error": f"Failed to get feedback: {str(e)}"}), 500

@api.route('/issues', methods=['POST'])
def create_issue():
    """Allow citizens to create new issues"""
    try:
        data = request.get_json()

        current_app.logger.info(f"Issue creation request: {data}")

        # Validate required fields
        if not data:
            return jsonify({"error": "No data provided"}), 400

        required_fields = ['title', 'description', 'location']
        missing_fields = [field for field in required_fields if not data.get(field, '').strip()]

        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        title = str(data.get('title') or '').strip()
        description = str(data.get('description') or '').strip()
        location = str(data.get('location') or '').strip()

        # Additional validation
        if len(title) < 5:
            return jsonify({"error": "Issue title must be at least 5 characters long"}), 400
        if len(description) < 10:
            return jsonify({"error": "Issue description must be at least 10 characters long"}), 400

        # Create new issue
        issue = Issue(
            title=title,
            description=description,
            location=location,
            category=data.get('category', 'General'),
            priority=data.get('priority', 'Medium'),
            status='Open',
            created_by=current_user.id if current_user.is_authenticated else None,
            contact=data.get('contact', '').strip() if data.get('contact') else None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.session.add(issue)
        db.session.commit()

        current_app.logger.info(f"Issue created successfully: ID {issue.id}")

        # Send SMS confirmation if contact provided
        if issue.contact:
            try:
                # from app.utils.sms import send_sms
                # message = f"Issue created successfully! Ref: {issue.id}\nTitle: {issue.title[:50]}..."
                # send_sms(issue.contact, message)
                current_app.logger.info(f"SMS confirmation would be sent to {issue.contact}")
            except Exception as e:
                current_app.logger.error(f"SMS send failed: {str(e)}")

        return jsonify({
            "status": "success",
            "issue_id": issue.id,
            "message": "Issue created successfully"
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating issue: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Failed to create issue: {str(e)}"}), 500

@api.route('/issues', methods=['GET'])
def get_issues():
    """Get issues with optional filtering"""
    try:
        location = request.args.get('location')
        search = request.args.get('search')
        status = request.args.get('status', 'Open')
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)

        current_app.logger.info(f"Fetching issues: location={location}, search={search}, status={status}")

        query = Issue.query

        if location:
            query = query.filter(Issue.location.ilike(f'%{location}%'))

        if search:
            query = query.filter(
                db.or_(
                    Issue.title.ilike(f'%{search}%'),
                    Issue.description.ilike(f'%{search}%')
                )
            )

        if status != 'all':
            query = query.filter(Issue.status == status)

        # Paginate results
        pagination = query.order_by(Issue.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        issues = pagination.items

        return jsonify({
            'issues': [{
                'id': issue.id,
                'title': issue.title,
                'description': issue.description,
                'location': issue.location,
                'category': issue.category,
                'status': issue.status,
                'priority': issue.priority,
                'created_at': issue.created_at.isoformat(),
                'updated_at': issue.updated_at.isoformat(),
                'feedback_count': UserFeedback.query.filter_by(issue_id=issue.id).count()
            } for issue in issues],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        })
    except Exception as e:
        current_app.logger.error(f"Error getting issues: {str(e)}")
        return jsonify({"error": f"Failed to get issues: {str(e)}"}), 500

@api.route('/issues/<int:issue_id>', methods=['GET'])
def get_issue_details(issue_id):
    """Get detailed issue information with feedback"""
    try:
        issue = Issue.query.get_or_404(issue_id)

        # Get feedback for this issue
        feedback = UserFeedback.query.filter_by(issue_id=issue_id).order_by(
            UserFeedback.created_at.desc()
        ).all()

        return jsonify({
            'id': issue.id,
            'title': issue.title,
            'description': issue.description,
            'location': issue.location,
            'category': issue.category,
            'status': issue.status,
            'priority': issue.priority,
            'created_at': issue.created_at.isoformat(),
            'updated_at': issue.updated_at.isoformat(),
            'feedback': [{
                'id': f.id,
                'content': f.content,
                'created_at': f.created_at.isoformat(),
                'sentiment_score': f.sentiment_score,
                'location': f.location
            } for f in feedback]
        })
    except Exception as e:
        current_app.logger.error(f"Error getting issue details: {str(e)}")
        return jsonify({"error": f"Failed to get issue details: {str(e)}"}), 500

@api.route('/scorecards/officials', methods=['GET'])
def get_officials():
    """Get list of all officials for selection"""
    try:
        officials = Official.query.order_by(Official.name).all()

        # Group by position/constituency for easier selection
        officials_by_position = {}
        for official in officials:
            key = f"{official.position} - {official.constituency}"
            if key not in officials_by_position:
                officials_by_position[key] = []
            officials_by_position[key].append({
                'id': official.id,
                'name': official.name,
                'department': official.department,
                'average_score': official.average_score,
                'rating_count': official.rating_count
            })

        return jsonify({
            "officials": officials_by_position,
            "count": len(officials)
        })
    except Exception as e:
        current_app.logger.error(f"Error getting officials: {str(e)}")
        return jsonify({"error": "Failed to get officials"}), 500

@api.route('/scorecards/rate', methods=['POST'])
def rate_official():
    """Submit rating for an official with case-insensitive matching"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['name', 'position', 'constituency', 'score']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        try:
            score = int(data['score'])
            if not (1 <= score <= 5):
                return jsonify({"error": "Score must be between 1-5"}), 400
        except ValueError:
            return jsonify({"error": "Invalid score format"}), 400

        # Case-insensitive search with position and constituency matching
        official = Official.query.filter(
            db.func.lower(Official.name) == db.func.lower(data['name'].strip()),
            db.func.lower(Official.position) == db.func.lower(data['position'].strip()),
            db.func.lower(Official.constituency) == db.func.lower(data['constituency'].strip())
        ).first()

        if not official:
            return jsonify({"error": "Official not found. Please check name and location."}), 404

        # Create new rating
        rating = {
            'score': score,
            'comment': data.get('comment', ''),
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': data.get('user_id', 'anonymous')
        }

        # Update official's ratings
        if not official.ratings:
            official.ratings = []

        official.ratings.append(rating)

        # Recalculate average
        scores = [r['score'] for r in official.ratings]
        official.average_score = sum(scores) / len(scores)
        official.rating_count = len(scores)
        official.last_updated = datetime.utcnow()

        db.session.commit()

        return jsonify({
            "status": "success",
            "official_id": official.id,
            "official_name": official.name,
            "new_average": round(official.average_score, 2),
            "total_ratings": official.rating_count
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error rating official: {str(e)}")
        return jsonify({"error": "Failed to submit rating"}), 500

@api.route('/scorecards/search', methods=['GET'])
def search_officials():
    """Search officials by name (case-insensitive partial match)"""
    try:
        name = request.args.get('name', '').strip()
        if not name:
            return jsonify({"error": "Name parameter is required"}), 400

        officials = Official.query.filter(
            Official.name.ilike(f'%{name}%')
        ).limit(10).all()

        return jsonify([{
            'id': o.id,
            'name': o.name,
            'position': o.position,
            'constituency': o.constituency,
            'current_rating': round(o.average_score, 2) if o.average_score else 0
        } for o in officials])
    except Exception as e:
        current_app.logger.error(f"Error searching officials: {str(e)}")
        return jsonify({"error": "Failed to search officials"}), 500

@api.route('/dashboard-data', methods=['GET'])
def get_dashboard_data():
    """Get dashboard data with proper error handling"""
    try:
        # Get feedback stats
        feedback_stats = db.session.query(
            UserFeedback.location,
            db.func.avg(UserFeedback.sentiment_score).label('avg_sentiment'),
            db.func.count().label('count')
        ).filter(UserFeedback.location.isnot(None)).group_by(UserFeedback.location).all()

        # Get active polls
        active_polls = Poll.query.filter(
            Poll.expires_at > datetime.utcnow()
        ).all()

        # Format active polls
        formatted_active_polls = []
        for poll in active_polls:
            options = poll.options if isinstance(poll.options, list) else []
            total_votes = sum(opt.get('votes', 0) for opt in options if isinstance(opt, dict))
            formatted_active_polls.append({
                'id': poll.id,
                'question': poll.question,
                'options': options,
                'total_votes': total_votes
            })

        # Get recent alerts
        recent_alerts = Alert.query.order_by(
            Alert.created_at.desc()
        ).limit(5).all()

        # Get counts
        total_users = User.query.count()
        officials_count = Official.query.count()
        total_issues = Issue.query.count()
        total_feedback = UserFeedback.query.count()

        return jsonify({
            "total_users": total_users,
            "officials_count": officials_count,
            "total_issues": total_issues,
            "total_feedback": total_feedback,
            "feedback_stats": [
                {
                    "location": loc or "Unknown",
                    "avg_sentiment": float(avg) if avg else 0.0,
                    "count": cnt
                }
                for loc, avg, cnt in feedback_stats
            ],
            "active_polls": formatted_active_polls,
            "recent_alerts": [
                {
                    "topic": a.topic,
                    "severity": a.severity,
                    "created_at": a.created_at.isoformat()
                }
                for a in recent_alerts
            ]
        })
    except Exception as e:
        current_app.logger.error(f"Error getting dashboard data: {str(e)}")
        return jsonify({"error": "Failed to get dashboard data"}), 500