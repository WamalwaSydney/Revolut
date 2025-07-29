from flask import Blueprint, render_template, request, jsonify,Response
from flask_login import login_required, current_user
from app.auth import role_required
from app import db
import logging

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