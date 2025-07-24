# Updated main.py

from flask import Blueprint, render_template, session, redirect, url_for, request
from flask_login import current_user
from app.models import Feedback, Poll

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Home page"""
    if current_user.is_authenticated:
        # Redirect authenticated users based on their role
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role in ['government', 'analyst']:
            return redirect(url_for('dashboard.government'))
        else:  # citizen or other roles
            return redirect(url_for('dashboard.citizen'))

    # For anonymous users, show public homepage
    try:
        # Get some public feedback and polls for the homepage
        feedback_list = Feedback.query.filter_by(is_anonymous=False).order_by(
            Feedback.created_at.desc()
        ).limit(5).all()

        polls = Poll.query.filter(
            Poll.is_active == True,
            Poll.is_public == True
        ).limit(2).all()
    except:
        # In case of database errors, show empty lists
        feedback_list = []
        polls = []

    return render_template('public/index.html', feedback_list=feedback_list, polls=polls)

@main.route('/about')
def about():
    """About page"""
    return render_template('public/about.html')

@main.route('/contact')
def contact():
    """Contact page"""
    return render_template('public/contact.html')

@main.route('/language/<lang>')
def set_language(lang):
    """Set language preference"""
    session['language'] = lang
    return redirect(request.referrer or url_for('main.index'))