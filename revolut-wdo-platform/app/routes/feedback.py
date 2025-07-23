from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.models import Feedback, FeedbackResponse, FeedbackCategory, Priority, FeedbackStatus
from app.utils.analytics import SentimentAnalyzer
from app import db
from datetime import datetime

feedback = Blueprint('feedback', __name__)

@feedback.route('/submit', methods=['GET', 'POST'])
def submit():
    """Submit new feedback - accessible to both logged in and anonymous users"""
    if request.method == 'POST':
        data = request.form
        
        # Validate required fields
        if not data.get('title') or not data.get('content') or not data.get('category') or not data.get('county'):
            flash('Please fill in all required fields', 'error')
            return render_template('feedback/submit.html')
        
        # Analyze sentiment
        sentiment_score, sentiment_label = SentimentAnalyzer.analyze_sentiment(data['content'])
        
        # Create feedback
        feedback_obj = Feedback(
            title=data['title'],
            content=data['content'],
            category=FeedbackCategory(data['category']),
            priority=Priority(data.get('priority', 'medium')),
            county=data['county'],
            constituency=data.get('constituency'),
            ward=data.get('ward'),
            latitude=float(data['latitude']) if data.get('latitude') else None,
            longitude=float(data['longitude']) if data.get('longitude') else None,
            sentiment_score=sentiment_score,
            sentiment_label=sentiment_label,
            submission_method='web',
            language=data.get('language', 'en'),
            is_anonymous=bool(data.get('is_anonymous')),
            user_id=current_user.id if current_user.is_authenticated else None
        )
        
        db.session.add(feedback_obj)
        db.session.commit()
        
        flash('Your feedback has been submitted successfully!', 'success')
        return redirect(url_for('feedback.view', id=feedback_obj.id))
    
    return render_template('feedback/submit.html')

@feedback.route('/view/<int:id>')
def view(id):
    """View specific feedback and responses"""
    feedback_obj = Feedback.query.get_or_404(id)
    responses = FeedbackResponse.query.filter_by(feedback_id=id).order_by(FeedbackResponse.created_at.desc()).all()
    
    return render_template('feedback/view.html', feedback=feedback_obj, responses=responses)

@feedback.route('/list')
def list_feedback():
    """List all public feedback with filtering"""
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category')
    county = request.args.get('county')
    status = request.args.get('status')
    
    query = Feedback.query
    
    if category:
        query = query.filter(Feedback.category == FeedbackCategory(category))
    if county:
        query = query.filter(Feedback.county == county)
    if status:
        query = query.filter(Feedback.status == status)
    
    feedback_list = query.order_by(Feedback.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('feedback/list.html', feedback_list=feedback_list)

@feedback.route('/respond/<int:id>', methods=['POST'])
@login_required
def respond(id):
    """Add response to feedback"""
    feedback_obj = Feedback.query.get_or_404(id)
    content = request.form.get('content')
    
    if not content:
        flash('Response content is required', 'error')
        return redirect(url_for('feedback.view', id=id))
    
    response = FeedbackResponse(
        content=content,
        feedback_id=id,
        user_id=current_user.id,
        is_official=current_user.is_government()
    )
    
    db.session.add(response)
    
    # Update feedback status if official response
    if current_user.is_government():
        feedback_obj.status = 'reviewed'
    
    db.session.commit()
    
    flash('Response added successfully', 'success')
    return redirect(url_for('feedback.view', id=id))

@feedback.route('/my-feedback')
@login_required
def my_feedback():
    """View user's submitted feedback"""
    page = request.args.get('page', 1, type=int)
    
    feedback_list = Feedback.query.filter_by(user_id=current_user.id).order_by(
        Feedback.created_at.desc()
    ).paginate(page=page, per_page=20, error_out=False)
    
    return render_template('feedback/my_feedback.html', feedback_list=feedback_list)
