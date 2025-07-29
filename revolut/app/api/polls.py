# app/api/polls.py - COMPLETELY FIXED Poll Management System
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
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

def fix_poll_options_format(poll):
    """Fix poll options format to ensure they have proper IDs"""
    if not isinstance(poll.options, list):
        poll.options = []
        return

    fixed_options = []
    for i, option in enumerate(poll.options):
        if isinstance(option, dict):
            # Ensure the option has an ID
            if 'id' not in option:
                option['id'] = i + 1
            # Ensure it has a votes count
            if 'votes' not in option:
                option['votes'] = 0
            # Ensure it has text
            if 'text' not in option:
                option['text'] = f"Option {i + 1}"
            fixed_options.append(option)
        elif isinstance(option, str):
            # Convert string option to dict format
            fixed_options.append({
                'id': i + 1,
                'text': option,
                'votes': 0
            })

    poll.options = fixed_options
    return poll

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

        # Create poll options with proper IDs and vote counts
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
                current_app.logger.info(f"Poll notification requested for poll {poll.id}")
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
    """Submit a vote for a poll - COMPLETELY FIXED VERSION"""
    try:
        data = request.get_json()
        poll = Poll.query.get_or_404(poll_id)

        # Debug logging
        current_app.logger.info(f"Vote request for poll {poll_id}: {data}")
        current_app.logger.info(f"Current poll options: {poll.options}")

        # Check if poll is still active
        if poll.expires_at and poll.expires_at < datetime.utcnow():
            return jsonify({"error": "Poll has expired"}), 400

        # Validate vote
        option_id = data.get('option_id')
        if option_id is None:
            return jsonify({"error": "Option ID is required"}), 400

        try:
            option_id = int(option_id)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid option ID format"}), 400

        # Fix poll options format if needed
        poll = fix_poll_options_format(poll)
        current_app.logger.info(f"Fixed poll options: {poll.options}")

        # Find the option and increment vote count
        option_found = False
        updated_options = []

        for option in poll.options:
            # Ensure option is a dictionary
            if not isinstance(option, dict):
                current_app.logger.warning(f"Skipping invalid option in poll {poll_id}: {option}")
                continue

            # Create a copy of the option
            updated_option = option.copy()

            # Check if this is the voted option
            if updated_option.get('id') == option_id:
                updated_option['votes'] = updated_option.get('votes', 0) + 1
                option_found = True
                current_app.logger.info(f"Vote recorded for option {option_id} in poll {poll_id}")

            updated_options.append(updated_option)

        if not option_found:
            return jsonify({"error": f"Option {option_id} not found in poll"}), 400

        # Update the poll with new options
        poll.options = updated_options

        # Use flag_modified to ensure SQLAlchemy detects the change
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(poll, "options")

        db.session.commit()
        current_app.logger.info(f"Poll {poll_id} updated successfully")

        # Calculate total votes and percentages
        total_votes = sum(opt.get('votes', 0) for opt in poll.options if isinstance(opt, dict))

        # Add percentages to options for response
        options_with_percentage = []
        for option in poll.options:
            if not isinstance(option, dict):
                continue

            votes = option.get('votes', 0)
            percentage = (votes / total_votes * 100) if total_votes > 0 else 0
            options_with_percentage.append({
                'id': option.get('id'),
                'text': option.get('text', ''),
                'votes': votes,
                'percentage': round(percentage, 1)
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
        return jsonify({"error": f"Failed to record vote: {str(e)}"}), 500

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
            # Fix poll options format
            poll = fix_poll_options_format(poll)

            # Calculate total votes
            total_votes = sum(opt.get('votes', 0) for opt in poll.options if isinstance(opt, dict))

            # Add percentage to each option
            options_with_percentage = []
            for option in poll.options:
                if not isinstance(option, dict):
                    continue

                votes = option.get('votes', 0)
                percentage = (votes / total_votes * 100) if total_votes > 0 else 0
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

        # Fix poll options format
        poll = fix_poll_options_format(poll)

        total_votes = sum(opt.get('votes', 0) for opt in poll.options if isinstance(opt, dict))

        # Add percentage to each option
        options_with_stats = []
        for option in poll.options:
            if not isinstance(option, dict):
                continue

            votes = option.get('votes', 0)
            percentage = (votes / total_votes * 100) if total_votes > 0 else 0
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
            # Fix poll options format
            poll = fix_poll_options_format(poll)

            total_votes = sum(opt.get('votes', 0) for opt in poll.options if isinstance(opt, dict))

            # Calculate statistics
            options_with_stats = []
            for option in poll.options:
                if not isinstance(option, dict):
                    continue

                votes = option.get('votes', 0)
                percentage = (votes / total_votes * 100) if total_votes > 0 else 0
                options_with_stats.append({
                    **option,
                    "percentage": round(percentage, 1)
                })

            is_active = poll.expires_at > datetime.utcnow() if poll.expires_at else True

            results.append({
                "id": poll.id,
                "question": poll.question,
                "options": options_with_stats,
                "total_votes": total_votes,
                "expires_at": poll.expires_at.isoformat() if poll.expires_at else None,
                "created_at": poll.created_at.isoformat(),
                "is_active": is_active,
                "status": "Active" if is_active else "Expired"
            })

        return jsonify({
            "polls": results,
            "total_count": len(results),
            "active_count": len([p for p in results if p['is_active']])
        })

    except Exception as e:
        current_app.logger.error(f"Error fetching poll results: {str(e)}")
        return jsonify({"error": "Failed to fetch poll results"}), 500

# Database migration script to fix existing polls
@polls_bp.route('/fix-existing-polls', methods=['POST'])
@login_required
@role_required('admin')  # Only admins can run this
def fix_existing_polls():
    """Fix existing polls that don't have proper option IDs"""
    try:
        all_polls = Poll.query.all()
        fixed_count = 0

        for poll in all_polls:
            original_options = poll.options
            poll = fix_poll_options_format(poll)

            # Check if anything changed
            if poll.options != original_options:
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(poll, "options")
                fixed_count += 1
                current_app.logger.info(f"Fixed poll {poll.id}: {poll.options}")

        if fixed_count > 0:
            db.session.commit()

        return jsonify({
            "status": "success",
            "message": f"Fixed {fixed_count} polls",
            "total_polls": len(all_polls),
            "fixed_polls": fixed_count
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error fixing polls: {str(e)}")
        return jsonify({"error": f"Failed to fix polls: {str(e)}"}), 500