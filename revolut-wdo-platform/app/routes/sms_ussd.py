from flask import Blueprint, request, jsonify
from app.models import Feedback, FeedbackCategory, User
from app.utils.sms_handler import SMSHandler
from app.utils.analytics import SentimentAnalyzer
from app import db
import re

sms_ussd = Blueprint('sms_ussd', __name__)

sms_handler = SMSHandler()

@sms_ussd.route('/ussd', methods=['POST'])
def ussd_callback():
    """Handle USSD requests"""
    session_id = request.form.get('sessionId')
    service_code = request.form.get('serviceCode')
    phone_number = request.form.get('phoneNumber')
    text = request.form.get('text', '')
    
    response = sms_handler.process_ussd_request(session_id, service_code, phone_number, text)
    
    return response, 200, {'Content-Type': 'text/plain'}

@sms_ussd.route('/sms', methods=['POST'])
def sms_callback():
    """Handle incoming SMS messages"""
    phone_number = request.form.get('from')
    message = request.form.get('text', '')
    
    try:
        # Parse feedback from SMS
        parsed = sms_handler.parse_feedback_sms(message)
        
        if parsed['is_valid']:
            # Find or create user
            user = User.query.filter_by(phone=phone_number).first()
            
            # Analyze sentiment
            sentiment_score, sentiment_label = SentimentAnalyzer.analyze_sentiment(parsed['content'])
            
            # Create feedback
            feedback = Feedback(
                title=f"SMS Feedback - {parsed['category'].title()}",
                content=parsed['content'],
                category=FeedbackCategory(parsed['category']),
                county=parsed['county'],
                sentiment_score=sentiment_score,
                sentiment_label=sentiment_label,
                submission_method='sms',
                user_id=user.id if user else None
            )
            
            db.session.add(feedback)
            db.session.commit()
            
            # Send confirmation SMS
            confirmation = f"Thank you! Your feedback has been received. Reference: #{feedback.id}"
            sms_handler.send_sms(phone_number, confirmation)
            
        else:
            # Send error message
            error_msg = "Invalid format. Use: FEEDBACK <category> <county> <message>"
            sms_handler.send_sms(phone_number, error_msg)
    
    except Exception as e:
        # Send error message
        error_msg = "Sorry, there was an error processing your feedback. Please try again."
        sms_handler.send_sms(phone_number, error_msg)
    
    return jsonify({'status': 'processed'})

@sms_ussd.route('/delivery-report', methods=['POST'])
def delivery_report():
    """Handle SMS delivery reports"""
    # Log delivery status for monitoring
    message_id = request.form.get('id')
    status = request.form.get('status')
    
    # You can implement delivery tracking here
    
    return jsonify({'status': 'received'})
