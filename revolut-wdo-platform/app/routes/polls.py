from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.models import Poll, PollOption, PollResponse
from app import db
from datetime import datetime

polls = Blueprint('polls', __name__)

@polls.route('/')
def list_polls():
    """List all active polls"""
    active_polls = Poll.query.filter(
        Poll.is_active == True,
        Poll.is_public == True
    ).order_by(Poll.created_at.desc()).all()
    
    return render_template('polls/list.html', polls=active_polls)

@polls.route('/view/<int:id>')
def view_poll(id):
    """View poll details and vote"""
    poll = Poll.query.get_or_404(id)
    
    # Check if user has already voted
    user_response = None
    if current_user.is_authenticated:
        user_response = PollResponse.query.filter_by(
            poll_id=id, user_id=current_user.id
        ).first()
    
    return render_template('polls/view.html', poll=poll, user_response=user_response)

@polls.route('/vote/<int:id>', methods=['POST'])
def vote(id):
    """Submit vote for a poll"""
    poll = Poll.query.get_or_404(id)
    option_id = request.form.get('option_id', type=int)
    
    if not option_id:
        flash('Please select an option', 'error')
        return redirect(url_for('polls.view_poll', id=id))
    
    option = PollOption.query.get_or_404(option_id)
    
    # Check if poll is still active
    if not poll.is_active:
        flash('This poll is no longer active', 'error')
        return redirect(url_for('polls.view_poll', id=id))
    
    # Check if user has already voted
    if current_user.is_authenticated:
        existing_response = PollResponse.query.filter_by(
            poll_id=id, user_id=current_user.id
        ).first()
        
        if existing_response:
            flash('You have already voted in this poll', 'warning')
            return redirect(url_for('polls.view_poll', id=id))
    
    # Create response
    response = PollResponse(
        poll_id=id,
        option_id=option_id,
        user_id=current_user.id if current_user.is_authenticated else None
    )
    
    # Update vote count
    option.vote_count += 1
    
    db.session.add(response)
    db.session.commit()
    
    flash('Your vote has been recorded!', 'success')
    return redirect(url_for('polls.results', id=id))

@polls.route('/results/<int:id>')
def results(id):
    """View poll results"""
    poll = Poll.query.get_or_404(id)
    return render_template('polls/results.html', poll=poll)

@polls.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new poll (government users only)"""
    if not current_user.is_government():
        flash('Only government users can create polls', 'error')
        return redirect(url_for('polls.list_polls'))
    
    if request.method == 'POST':
        data = request.form
        
        # Validate required fields
        if not data.get('title') or not data.get('question'):
            flash('Title and question are required', 'error')
            return render_template('polls/create.html')
        
        # Create poll
        poll = Poll(
            title=data['title'],
            description=data.get('description'),
            question=data['question'],
            county=data.get('county'),
            created_by=current_user.id
        )
        
        db.session.add(poll)
        db.session.flush()  # Get poll ID
        
        # Add options
        options = request.form.getlist('options[]')
        for option_text in options:
            if option_text.strip():
                option = PollOption(text=option_text.strip(), poll_id=poll.id)
                db.session.add(option)
        
        db.session.commit()
        
        flash('Poll created successfully!', 'success')
        return redirect(url_for('polls.view_poll', id=poll.id))
    
    return render_template('polls/create.html')
