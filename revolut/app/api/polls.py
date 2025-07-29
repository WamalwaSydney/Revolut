# app/api/polls.py - Complete Poll Management System
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from flask import current_app
from app.models import Poll, User, UserFeedback
from app.auth import role_required
from datetime import datetime, timedelta
import re

polls_bp = Blueprint('polls', __name__, url_prefix='/api/polls')

def validate_poll_data(data):
    """Validate poll creation data"""
    errors = []

    # Validate question
    question = data.get('question', '').strip()
    if not question:
        errors.append("Poll question is required")
    elif len(question) < 10:
        errors.append("Poll question must be at least 10 characters")
    elif len(question) > 500:
        errors.append("Poll question must be less than 500 characters")

    # Validate options
    options = data.get('options', [])
    if not options or len(options) < 2:
        errors.append("Poll must have at least 2 options")
    elif len(options) > 6:
        errors.append("Poll cannot have more than 6 options")

    # Validate each option
    for i, option in enumerate(options):
        if not isinstance(option, str) or not option.strip():
            errors.append(f"Option {i+1} cannot be empty")
        elif len(option.strip()) > 100:
            errors.append(f"Option {i+1} must be less than 100 characters")

    # Validate duration
    duration_days = data.get('duration_days', 7)
    try:
        duration_days = int(duration_days)
        if duration_days < 1 or duration_days > 30:
            errors.append("Poll duration must be between 1 and 30 days")
    except (ValueError, TypeError):
        errors.append("Invalid poll duration")

    return errors

@polls_bp.route('', methods=['POST'])
@login_required
@role_required('cso')  # Only CSOs and admins can create polls
def create_poll():
    """Create a new poll"""
    try:
        data = request.get_json()

        # Validate input data
        validation_errors = validate_poll_data(data)
        if validation_errors:
            return jsonify({"errors": validation_errors}), 400

        # Create poll options with vote counts
        options = []
        for i, option_text in enumerate(data['options']):
            options.append({
                "id": i + 1,
                "text": option_text.strip(),
                "votes": 0
            })

        # Calculate expiry date
        duration_days = int(data.get('duration_days', 7))
        expires_at = datetime.utcnow() + timedelta(days=duration_days)

        # Create poll
        poll = Poll(
            question=data['question'].strip(),
            options=options,
            created_by=current_user.id,
            expires_at=expires_at
        )

        db.session.add(poll)
        db.session.commit()

        # Send SMS notifications if requested
        if data.get('notify_citizens', False):
            try:
                from app.utils.sms import send_poll_notification
                notification_result = send_poll_notification(poll.id)
                current_app.logger.info(f"Poll notification sent: {notification_result}")
            except Exception as e:
                current_app.logger.error(f"Failed to send poll notifications: {str(e)}")

        # Log poll creation
        current_app.logger.info(f"Poll created by user {current_user.id}: {poll.id}")

        return jsonify({
            "status": "success",
            "message": "Poll created successfully",
            "poll": {
                "id": poll.id,
                "question": poll.question,
                "options": poll.options,
                "expires_at": poll.expires_at.isoformat(),
                "created_at": poll.created_at.isoformat()
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating poll: {str(e)}")
        return jsonify({"error": "Failed to create poll"}), 500

@polls_bp.route('/<int:poll_id>/vote', methods=['POST'])
def vote_on_poll(poll_id):
    """Submit a vote for a poll"""
    try:
        data = request.get_json()
        poll = Poll.query.get_or_404(poll_id)

        # Check if poll is still active
        if poll.expires_at < datetime.utcnow():
            return jsonify({"error": "Poll has expired"}), 400

        # Validate vote
        option_id = data.get('option_id')
        if option_id is None:
            return jsonify({"error": "Option ID is required"}), 400

        try:
            option_id = int(option_id)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid option ID"}), 400

        # Find the option and increment vote count
        option_found = False
        for option in poll.options:
            if option['id'] == option_id:
                option['votes'] += 1
                option_found = True
                break

        if not option_found:
            return jsonify({"error": "Invalid option selected"}), 400

        # Mark the poll as modified to trigger SQLAlchemy update
        db.session.merge(poll)
        db.session.commit()

        # Calculate total votes and percentages
        total_votes = sum(opt['votes'] for opt in poll.options)
        
        # Add percentages to options
        options_with_percentage = []
        for option in poll.options:
            percentage = (option['votes'] / total_votes * 100) if total_votes > 0 else 0
            options_with_percentage.append({
                **option,
                "percentage": round(percentage, 1)
            })

        return jsonify({
            "status": "success", 
            "message": "Vote recorded successfully",
            "updated_poll": {
                "id": poll.id,
                "total_votes": total_votes,
                "options": options_with_percentage
            },
            "selected_option": option_id
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error voting on poll {poll_id}: {str(e)}")
        return jsonify({"error": "Failed to record vote"}), 500

@polls_bp.route('', methods=['GET'])
def get_active_polls():
    """Get all active polls"""
    try:
        # Get active polls (not expired)
        active_polls = Poll.query.filter(
            Poll.expires_at > datetime.utcnow()
        ).order_by(Poll.created_at.desc()).all()

        polls_data = []
        for poll in active_polls:
            total_votes = sum(opt['votes'] for opt in poll.options)

            # Add percentage to each option
            options_with_percentage = []
            for option in poll.options:
                percentage = (option['votes'] / total_votes * 100) if total_votes > 0 else 0
                options_with_percentage.append({
                    **option,
                    "percentage": round(percentage, 1)
                })

            polls_data.append({
                "id": poll.id,
                "question": poll.question,
                "options": options_with_percentage,
                "total_votes": total_votes,
                "expires_at": poll.expires_at.isoformat(),
                "created_at": poll.created_at.isoformat(),
                "days_remaining": (poll.expires_at - datetime.utcnow()).days
            })

        return jsonify({
            "polls": polls_data,
            "count": len(polls_data)
        })

    except Exception as e:
        current_app.logger.error(f"Error fetching polls: {str(e)}")
        return jsonify({"error": "Failed to fetch polls"}), 500

@polls_bp.route('/<int:poll_id>', methods=['GET'])
def get_poll_details(poll_id):
    """Get detailed information about a specific poll"""
    try:
        poll = Poll.query.get_or_404(poll_id)

        total_votes = sum(opt['votes'] for opt in poll.options)

        # Add percentage to each option
        options_with_stats = []
        for option in poll.options:
            percentage = (option['votes'] / total_votes * 100) if total_votes > 0 else 0
            options_with_stats.append({
                **option,
                "percentage": round(percentage, 1)
            })

        # Get creator information
        creator = User.query.get(poll.created_by)

        return jsonify({
            "id": poll.id,
            "question": poll.question,
            "options": options_with_stats,
            "total_votes": total_votes,
            "expires_at": poll.expires_at.isoformat(),
            "created_at": poll.created_at.isoformat(),
            "is_active": poll.expires_at > datetime.utcnow(),
            "creator": {
                "username": creator.username if creator else "Unknown",
                "roles": creator.get_role_names() if creator else []
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error fetching poll {poll_id}: {str(e)}")
        return jsonify({"error": "Failed to fetch poll details"}), 500

@polls_bp.route('/results', methods=['GET'])
def get_poll_results():
    """Get results for all polls (admin/CSO access)"""
    try:
        # Get all polls (including expired ones)
        all_polls = Poll.query.order_by(Poll.created_at.desc()).all()

        results = []
        for poll in all_polls:
            total_votes = sum(opt['votes'] for opt in poll.options)

            # Calculate statistics
            options_with_stats = []
            for option in poll.options:
                percentage = (option['votes'] / total_votes * 100) if total_votes > 0 else 0
                options_with_stats.append({
                    **option,
                    "percentage": round(percentage, 1)
                })

            results.append({
                "id": poll.id,
                "question": poll.question,
                "options": options_with_stats,
                "total_votes": total_votes,
                "expires_at": poll.expires_at.isoformat(),
                "created_at": poll.created_at.isoformat(),
                "is_active": poll.expires_at > datetime.utcnow(),
                "status": "Active" if poll.expires_at > datetime.utcnow() else "Expired"
            })

        return jsonify({
            "polls": results,
            "total_count": len(results),
            "active_count": len([p for p in results if p['is_active']])
        })

    except Exception as e:
        current_app.logger.error(f"Error fetching poll results: {str(e)}")
        return jsonify({"error": "Failed to fetch poll results"}), 500

# # app/utils/sms.py - SMS Integration for Polls
# import africastalking
# from app import current_app, db
# from app.models import User, Poll
# import logging

# logger = logging.getLogger(__name__)

# def initialize_sms():
#     """Initialize Africa's Talking SMS service"""
#     try:
#         username = current_app.config.get('AFRICASTALKING_USERNAME')
#         api_key = current_app.config.get('AFRICASTALKING_API_KEY')

#         if not username or not api_key:
#             logger.error("Africa's Talking credentials not configured")
#             return None

#         africastalking.initialize(username=username, api_key=api_key)
#         return africastalking.SMS
#     except Exception as e:
#         logger.error(f"Failed to initialize SMS service: {str(e)}")
#         return None

# def send_poll_notification(poll_id):
#     """Send SMS notification about new poll to citizens"""
#     try:
#         sms_service = initialize_sms()
#         if not sms_service:
#             return {"error": "SMS service not available"}

#         # Get poll details
#         poll = Poll.query.get(poll_id)
#         if not poll:
#             return {"error": "Poll not found"}

#         # Create SMS message
#         message = f"🗳️ NEW POLL: {poll.question}\n\n"

#         # Add options (limit for SMS length)
#         for i, option in enumerate(poll.options[:4]):  # Limit to 4 options for SMS
#             message += f"{i+1}. {option['text']}\n"

#         if len(poll.options) > 4:
#             message += f"...and {len(poll.options) - 4} more options\n"

#         message += f"\nDial *{current_app.config.get('SMS_SHORTCODE', '40404')}# to vote!"
#         message += f"\nExpires: {poll.expires_at.strftime('%d/%m/%Y')}"

#         # Get citizen phone numbers (you might want to add subscription preferences)
#         citizens = User.query.join(User.roles).filter_by(name='citizen').all()
#         recipients = [user.phone for user in citizens if user.phone]

#         if not recipients:
#             return {"error": "No citizen phone numbers found"}

#         # Send SMS in batches (Africa's Talking limit)
#         batch_size = 100
#         total_sent = 0
#         errors = []

#         for i in range(0, len(recipients), batch_size):
#             batch = recipients[i:i + batch_size]
#             try:
#                 response = sms_service.send(message, batch)

#                 # Log response
#                 if 'SMSMessageData' in response:
#                     sent_count = len([r for r in response['SMSMessageData']['Recipients']
#                                     if r['status'] == 'Success'])
#                     total_sent += sent_count

#                     # Log any failures
#                     failures = [r for r in response['SMSMessageData']['Recipients']
#                               if r['status'] != 'Success']
#                     if failures:
#                         errors.extend(failures)

#             except Exception as e:
#                 logger.error(f"Failed to send SMS batch: {str(e)}")
#                 errors.append(f"Batch error: {str(e)}")

#         result = {
#             "total_recipients": len(recipients),
#             "successfully_sent": total_sent,
#             "errors": errors
#         }

#         logger.info(f"Poll notification sent: {result}")
#         return result

#     except Exception as e:
#         logger.error(f"Error sending poll notification: {str(e)}")
#         return {"error": str(e)}

# def send_sms(phone_number, message):
#     """Send individual SMS message"""
#     try:
#         sms_service = initialize_sms()
#         if not sms_service:
#             return False

#         response = sms_service.send(message, [phone_number])

#         if 'SMSMessageData' in response:
#             recipient = response['SMSMessageData']['Recipients'][0]
#             return recipient['status'] == 'Success'

#         return False

#     except Exception as e:
#         logger.error(f"Failed to send SMS to {phone_number}: {str(e)}")
#         return False

# # Enhanced USSD Poll Integration
# # Add to your main routes file (paste-4.txt)

# def handle_ussd_polls(text, session_id, phone_number):
#     """Handle USSD poll interactions"""
#     try:
#         # Get active polls
#         active_polls = Poll.query.filter(
#             Poll.expires_at > datetime.utcnow()
#         ).order_by(Poll.created_at.desc()).limit(5).all()

#         if not active_polls:
#             return "END Hakuna uchaguzi wa sasa. Jaribu baadaye."

#         parts = text.split("*")

#         if len(parts) == 2:  # User selected "2" (polls)
#             response = "CON Chagua uchaguzi:\n"
#             for i, poll in enumerate(active_polls):
#                 # Truncate long questions for USSD
#                 question = poll.question[:40] + "..." if len(poll.question) > 40 else poll.question
#                 response += f"{i+1}. {question}\n"
#             return response

#         elif len(parts) == 3:  # User selected a poll
#             try:
#                 poll_index = int(parts[2]) - 1
#                 if 0 <= poll_index < len(active_polls):
#                     poll = active_polls[poll_index]
#                     response = f"CON {poll.question}\n\nChagua jibu:\n"
#                     for option in poll.options:
#                         response += f"{option['id']}. {option['text']}\n"
#                     return response
#                 else:
#                     return "END Chaguo halipo. Jaribu tena."
#             except ValueError:
#                 return "END Chaguo halipo. Jaribu tena."

#         elif len(parts) == 4:  # User voted
#             try:
#                 poll_index = int(parts[2]) - 1
#                 option_id = int(parts[3])

#                 if 0 <= poll_index < len(active_polls):
#                     poll = active_polls[poll_index]

#                     # Find and update the option
#                     option_found = False
#                     for option in poll.options:
#                         if option['id'] == option_id:
#                             option['votes'] += 1
#                             option_found = True
#                             break

#                     if option_found:
#                         db.session.merge(poll)
#                         db.session.commit()

#                         # Send confirmation SMS
#                         confirmation_msg = f"Asante kwa kupiga kura!\nUchaguzi: {poll.question}\nJibu lako limerekodiwa."
#                         send_sms(phone_number, confirmation_msg)

#                         return "END Asante kwa kupiga kura! Kura yako imehesabiwa. Utapokea ujumbe wa uthibitisho."
#                     else:
#                         return "END Chaguo halipo. Jaribu tena."
#                 else:
#                     return "END Uchaguzi haupo. Jaribu tena."

#             except ValueError:
#                 return "END Chaguo halipo. Jaribu tena."

#         return "END Kuna hitilafu. Jaribu tena."

#     except Exception as e:
#         logger.error(f"USSD poll error: {str(e)}")
#         return "END Kuna hitilafu. Jaribu tena baadaye."