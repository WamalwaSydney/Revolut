from flask import Blueprint, request, jsonify
from app import db
from app.models import UserFeedback, Poll, Alert,Role, User,Issue,Official
from app.utils.nlp_processor import process_feedback
from app.utils.alerts import check_for_trending_issues
import datetime

api = Blueprint('api', __name__)

@api.route('/feedback', methods=['POST'])
def submit_feedback():
    """Submit citizen feedback and optionally link to existing issue"""
    data = request.get_json()

    # Validate required fields
    if not data.get('content'):
        return jsonify({"error": "Feedback content is required"}), 400

    # Link to existing issue if provided
    issue_id = data.get('issue_id')
    issue = None
    if issue_id:
        issue = Issue.query.get(issue_id)
        if not issue:
            return jsonify({"error": "Issue not found"}), 404

    # Create feedback
    feedback = UserFeedback(
        user_id=data.get('user_id', 'anonymous'),
        content=data['content'],
        issue_id=issue_id,
        location=data.get('location'),
        gender=data.get('gender'),
        contact=data.get('contact'),  # For SMS confirmation
        language=data.get('language', 'en'),
        source=data.get('source', 'web')  # web, ussd, sms
    )

    db.session.add(feedback)
    db.session.commit()

    # Process feedback (NLP and alerts)
    process_feedback(feedback.id)
    check_for_trending_issues()

    # Send SMS confirmation if contact provided
    if feedback.contact and feedback.source != 'sms':
        try:
            from app.utils.sms import send_sms
            message = f"Thank you for your feedback! Ref: {feedback.id}"
            if issue:
                message += f"\nLinked to issue: {issue.title}"
            send_sms(feedback.contact, message)
        except Exception as e:
            current_app.logger.error(f"SMS send failed: {str(e)}")

    return jsonify({
        "status": "success",
        "feedback_id": feedback.id,
        "issue_linked": bool(issue)
    })

# Remove duplicate poll functions since they're handled in app/api/polls.py
# This avoids conflicts between the two implementations

@api.route('/scorecards/officials', methods=['GET'])
def get_officials():
    """Get list of all officials for selection"""
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
            'department': official.department
        })

    return jsonify({
        "officials": officials_by_position,
        "count": len(officials)
    })

@api.route('/scorecards/rate', methods=['POST'])
def rate_official():
    """Submit rating for an official with case-insensitive matching"""
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
        "new_average": official.average_score,
        "total_ratings": official.rating_count
    })

@api.route('/scorecards/search', methods=['GET'])
def search_officials():
    """Search officials by name (case-insensitive partial match)"""
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
        'current_rating': o.average_score
    } for o in officials])

@api.route('/dashboard-data', methods=['GET'])
def get_dashboard_data():
    # Get feedback stats
    feedback_stats = db.session.query(
        UserFeedback.location,
        db.func.avg(UserFeedback.sentiment_score).label('avg_sentiment'),
        db.func.count().label('count')
    ).group_by(UserFeedback.location).all()

    # Get active polls
    active_polls = Poll.query.filter(
        Poll.expires_at > datetime.datetime.utcnow()
    ).all()

    # Get recent alerts
    recent_alerts = Alert.query.order_by(
        Alert.created_at.desc()
    ).limit(5).all()

    return jsonify({
        "feedback_stats": [
            {"location": loc, "avg_sentiment": float(avg), "count": cnt}
            for loc, avg, cnt in feedback_stats
        ],
        "active_polls": [
            {"id": p.id, "question": p.question, "options": p.options}
            for p in active_polls
        ],
        "recent_alerts": [
            {"topic": a.topic, "severity": a.severity}
            for a in recent_alerts
        ]
    })

@api.route('/issues', methods=['POST'])
def create_issue():
    """Allow citizens to create new issues"""
    data = request.get_json()

    # Validate required fields
    required_fields = ['title', 'description', 'location']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields: title, description, location"}), 400

    # Create new issue
    issue = Issue(
        title=data['title'].strip(),
        description=data['description'].strip(),
        location=data['location'],
        category=data.get('category', 'General'),
        priority=data.get('priority', 'Medium'),
        status='Open',
        created_by=data.get('user_id', 'anonymous'),
        created_at=datetime.datetime.utcnow(),
        contact=data.get('contact')  # For SMS updates
    )

    db.session.add(issue)
    db.session.commit()

    # Send SMS confirmation if contact provided
    if issue.contact:
        try:
            from app.utils.sms import send_sms
            message = f"Issue created successfully! Ref: {issue.id}\nTitle: {issue.title[:50]}..."
            send_sms(issue.contact, message)
        except Exception as e:
            print(f"SMS send failed: {str(e)}")

    return jsonify({
        "status": "success",
        "issue_id": issue.id,
        "message": "Issue created successfully"
    })

@api.route('/issues', methods=['GET'])
def get_issues():
    """Get issues with optional filtering"""
    location = request.args.get('location')
    search = request.args.get('search')
    status = request.args.get('status', 'Open')

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

    issues = query.order_by(Issue.created_at.desc()).limit(20).all()

    return jsonify([{
        'id': issue.id,
        'title': issue.title,
        'description': issue.description,
        'location': issue.location,
        'category': issue.category,
        'status': issue.status,
        'priority': issue.priority,
        'created_at': issue.created_at.isoformat(),
        'feedback_count': len(issue.feedback) if hasattr(issue, 'feedback') else 0
    } for issue in issues])

@api.route('/issues/<int:issue_id>', methods=['GET'])
def get_issue_details(issue_id):
    """Get detailed issue information with feedback"""
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
        'feedback': [{
            'id': f.id,
            'content': f.content,
            'created_at': f.created_at.isoformat(),
            'sentiment_score': f.sentiment_score,
            'location': f.location
        } for f in feedback]
    })