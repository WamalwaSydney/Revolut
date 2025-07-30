from flask import Blueprint, render_template, request, jsonify,Response,current_app, session, redirect, url_for
from flask_login import login_required, current_user
from app.auth import role_required
from app import db
import logging
from flask_babel import gettext, ngettext


main = Blueprint('main', __name__)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@main.route('/')
def index():
    return render_template('dashboard.html')

@main.route('/dashboard')
@login_required
def dashboard():
    if 'admin' in [role.name for role in current_user.roles]:
        return render_template('admin/dashboard.html')
    elif 'cso' in [role.name for role in current_user.roles]:
        return render_template('cso/dashboard.html')
    else:
        return render_template('dashboard.html')

@main.route('/feedback')
def feedback():
    return render_template('feedback.html')

@main.route('/polls')
def polls():
    return render_template('polls.html')

@main.route('/scorecards')
def scorecards():
    return render_template('scorecards.html')

@main.route('/api/dashboard-data')
def dashboard_data():
    """Get dashboard data"""
    from app.models import Poll, UserFeedback, Issue, Official, User
    from datetime import datetime

    try:
        # Get basic statistics
        total_users = User.query.count()
        total_polls = Poll.query.count()
        active_polls = Poll.query.filter(Poll.expires_at > datetime.utcnow()).all()
        total_feedback = UserFeedback.query.count()
        total_issues = Issue.query.count()
        total_officials = Official.query.count()

        # Get feedback stats by location
        feedback_stats = db.session.query(
            UserFeedback.location,
            db.func.avg(UserFeedback.sentiment_score).label('avg_sentiment'),
            db.func.count().label('count')
        ).filter(UserFeedback.location.isnot(None)).group_by(UserFeedback.location).all()

        # Format feedback stats
        formatted_feedback_stats = []
        for location, avg_sentiment, count in feedback_stats:
            formatted_feedback_stats.append({
                'location': location,
                'avg_sentiment': float(avg_sentiment) if avg_sentiment else 0.0,
                'count': count
            })

        # Format active polls with vote counts
        formatted_active_polls = []
        for poll in active_polls:
            total_votes = sum(opt.get('votes', 0) for opt in poll.options if isinstance(opt, dict))
            formatted_active_polls.append({
                'id': poll.id,
                'question': poll.question,
                'options': poll.options,
                'total_votes': total_votes,
                'expires_at': poll.expires_at.isoformat(),
                'created_at': poll.created_at.isoformat()
            })

        # Get recent alerts
        from app.models import Alert
        recent_alerts = Alert.query.order_by(Alert.created_at.desc()).limit(5).all()
        formatted_alerts = []
        for alert in recent_alerts:
            formatted_alerts.append({
                'topic': alert.topic,
                'severity': alert.severity,
                'affected_locations': alert.affected_locations if hasattr(alert, 'affected_locations') else ['All'],
                'created_at': alert.created_at.isoformat()
            })

        # Calculate positive sentiment percentage
        positive_count = UserFeedback.query.filter(UserFeedback.sentiment_score > 0.3).count()
        positive_sentiment = int((positive_count / total_feedback) * 100) if total_feedback > 0 else 0

        # Get active issues count
        active_issues = Issue.query.filter_by(status='Open').count()

        # Calculate average official rating
        avg_rating = db.session.query(db.func.avg(Official.average_score)).scalar() or 0.0

        # Prepare sentiment chart data (last 7 days)
        from datetime import datetime, timedelta
        sentiment_data = []
        sentiment_labels = []
        for i in range(7, 0, -1):
            day = datetime.utcnow() - timedelta(days=i)
            day_str = day.strftime('%Y-%m-%d')
            sentiment_labels.append(day_str)

            # Get average sentiment for this day
            day_sentiment = db.session.query(
                db.func.avg(UserFeedback.sentiment_score)
            ).filter(
                db.func.date(UserFeedback.created_at) == day.date()
            ).scalar() or 0

            sentiment_data.append(float(day_sentiment))

        # Prepare issue categories data
        issue_categories = db.session.query(
            Issue.category, db.func.count().label('count')
        ).group_by(Issue.category).all()

        issue_labels = [category for category, _ in issue_categories]
        issue_data = [count for _, count in issue_categories]

        return jsonify({
            'total_users': total_users,
            'total_polls': total_polls,
            'polls': formatted_active_polls,
            'total_feedback': total_feedback,
            'total_issues': total_issues,
            'officials_count': total_officials,
            'feedback_stats': formatted_feedback_stats,
            'alerts': formatted_alerts,
            'stats': {
                'total_polls': total_polls,
                'total_feedback': total_feedback,
                'active_issues': active_issues,
                'positive_sentiment': positive_sentiment,
                'avg_rating': float(avg_rating)
            },
            'charts': {
                'sentiment': {
                    'labels': sentiment_labels,
                    'data': sentiment_data
                },
                'issues': {
                    'labels': issue_labels,
                    'data': issue_data
                }
            },
            'recent_activity': []
        })
    except Exception as e:
        logger.error(f"Dashboard data error: {str(e)}")
        return jsonify({'error': 'Failed to load dashboard data'}), 500

@main.route('/at/ussd', methods=['POST'])
def ussd_callback():
    """Handle USSD callback from Africa's Talking"""

    # Log all incoming data for debugging
    logger.info("=== USSD REQUEST RECEIVED ===")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"Request form data: {dict(request.form)}")
    logger.info(f"Request args: {dict(request.args)}")

    # Get USSD parameters
    session_id = request.form.get('sessionId', '')
    phone_number = request.form.get('phoneNumber', '')
    service_code = request.form.get('serviceCode', '')
    text = request.form.get('text', '')

    logger.info(f"Session ID: {session_id}")
    logger.info(f"Phone: {phone_number}")
    logger.info(f"Service Code: {service_code}")
    logger.info(f"Text: '{text}'")

    # Process USSD flow
    try:
        if text == "":
            # First interaction
            response = "CON Karibu kwa Revolut & WDO!\n1. Tuma Maoni\n2. Piga Kura\n3. Angalia Ripoti"

        elif text == "1":
            # User chose to submit feedback
            response = "CON Chagua aina ya maoni:\n1. Elimu\n2. Maji\n3. Afya\n4. Barabara\n5. Usalama"

        elif text.startswith("1*"):
            # User is in feedback flow
            parts = text.split("*")
            if len(parts) == 2:
                # User selected feedback category
                categories = {
                    "1": "Elimu",
                    "2": "Maji",
                    "3": "Afya",
                    "4": "Barabara",
                    "5": "Usalama"
                }
                category = categories.get(parts[1], "Maji")
                response = f"CON Andika maoni yako kuhusu {category}:"
            else:
                # User submitted feedback text
                feedback_text = "*".join(parts[2:]) if len(parts) > 2 else "Hakuna maoni"
                # Here you would save to database
                logger.info(f"Feedback received: {feedback_text}")
                response = "END Asante! Maoni yako yamerekodiwa. Utapata jibu hivi karibuni."

        elif text == "2":
            # User chose to vote in polls
            response = "CON Uchaguzi wa sasa:\n1. Je, unaridhika na huduma za elimu?\n2. Barabara zinafaa kukarabatiwa?"

        elif text.startswith("2*"):
            # User is voting
            parts = text.split("*")
            if len(parts) == 2:
                poll_id = parts[1]
                response = "CON Chagua jibu lako:\n1. Ndio\n2. Hapana\n3. Sijui"
            else:
                # Vote submitted
                vote = parts[2] if len(parts) > 2 else "1"
                logger.info(f"Vote received: {vote}")
                response = "END Asante kwa kupiga kura! Kura yako imehesabiwa."

        elif text == "3":
            # User wants to see reports
            response = "END Ripoti za hali ya huduma za umma zitakuwa hapa hivi karibuni."

        else:
            # Invalid input
            response = "END Chaguo halipo. Jaribu tena."

    except Exception as e:
        logger.error(f"USSD processing error: {e}")
        response = "END Kuna hitilafu. Jaribu tena baadaye."

    logger.info(f"USSD Response: {response}")
    logger.info("=== END USSD REQUEST ===")

    return Response(response, mimetype="text/plain")

# Test endpoint to verify your server is reachable
@main.route('/test', methods=['GET', 'POST'])
def test_endpoint():
    """Test endpoint to verify server connectivity"""
    return jsonify({
        'status': 'success',
        'message': 'Server is reachable',
        'method': request.method,
        'data': dict(request.form) if request.method == 'POST' else dict(request.args)
    })

# Health check endpoint
@main.route('/health')
def health_check():
    """Health check for monitoring"""
    return jsonify({'status': 'healthy', 'service': 'revolut-wdo'})

@main.route('/polls/create')
@login_required
@role_required('cso')  # Only CSOs can create polls
def create_poll_page():
    """Render poll creation page"""
    return render_template('polls/create.html')

@main.route('/polls/manage')
@login_required
@role_required('cso')  # Only CSOs can manage polls
def manage_polls_page():
    """Render poll management dashboard"""
    return render_template('polls/list.html')

@main.route('/polls/public')
def public_polls():
    """Public page for citizens to view and vote on polls"""
    return render_template('polls/public.html')

@main.route('/issues')
def issues():
    return render_template('issues/list.html')

@main.route('/issues/create')
def create_issue():
    return render_template('issues/create.html')

@main.route('/issues/<int:issue_id>')
def issue_details(issue_id):
    return render_template('issues/details.html', issue_id=issue_id)


@main.route('/set_language/<language>')
def set_language(language=None):
    if language in current_app.config['LANGUAGES']:
        session['language'] = language

        # Update user preference if logged in
        if current_user.is_authenticated:
            current_user.language = language
            db.session.commit()

    return redirect(request.referrer or url_for('main.index'))
