from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.models import User, Feedback, Poll, FeedbackResponse
from app import db
from datetime import datetime

admin = Blueprint('admin', __name__)

@admin.before_request
@login_required
def require_admin():
    """Ensure only admins can access admin routes"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))

@admin.route('/')
def dashboard():
    """Admin dashboard with system overview"""
    # System stats
    total_users = User.query.count()
    total_feedback = Feedback.query.count()
    total_polls = Poll.query.count()
    pending_feedback = Feedback.query.filter_by(status='pending').count()
    
    # Recent activity
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_feedback = Feedback.query.order_by(Feedback.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_feedback=total_feedback,
                         total_polls=total_polls,
                         pending_feedback=pending_feedback,
                         recent_users=recent_users,
                         recent_feedback=recent_feedback)

@admin.route('/users')
def users():
    """Manage users"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    role = request.args.get('role', '')
    
    query = User.query
    
    if search:
        query = query.filter(
            User.username.contains(search) |
            User.email.contains(search)
        )
    
    if role:
        query = query.filter(User.role == role)
    
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/users.html', users=users)

@admin.route('/users/<int:id>/toggle-status', methods=['POST'])
def toggle_user_status(id):
    """Toggle user active status"""
    user = User.query.get_or_404(id)
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.username} has been {status}', 'success')
    
    return redirect(url_for('admin.users'))

@admin.route('/users/<int:id>/change-role', methods=['POST'])
def change_user_role(id):
    """Change user role"""
    user = User.query.get_or_404(id)
    new_role = request.form.get('role')
    
    if new_role in ['citizen', 'analyst', 'government', 'admin']:
        user.role = new_role
        db.session.commit()
        flash(f'User {user.username} role changed to {new_role}', 'success')
    else:
        flash('Invalid role specified', 'error')
    
    return redirect(url_for('admin.users'))

@admin.route('/feedback/moderate')
def moderate_feedback():
    """Moderate feedback content"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'pending')
    
    feedback_list = Feedback.query.filter_by(status=status).order_by(
        Feedback.created_at.desc()
    ).paginate(page=page, per_page=20, error_out=False)
    
    return render_template('admin/moderate_feedback.html', feedback_list=feedback_list)

@admin.route('/feedback/<int:id>/update-status', methods=['POST'])
def update_feedback_status(id):
    """Update feedback status"""
    feedback = Feedback.query.get_or_404(id)
    new_status = request.form.get('status')
    
    if new_status in ['pending', 'reviewed', 'in_progress', 'resolved', 'rejected']:
        feedback.status = new_status
        feedback.updated_at = datetime.utcnow()
        db.session.commit()
        flash(f'Feedback status updated to {new_status}', 'success')
    else:
        flash('Invalid status specified', 'error')
    
    return redirect(url_for('admin.moderate_feedback'))

@admin.route('/feedback/<int:id>/delete', methods=['POST'])
def delete_feedback(id):
    """Delete feedback entry"""
    feedback = Feedback.query.get_or_404(id)
    
    # Delete associated responses first
    FeedbackResponse.query.filter_by(feedback_id=id).delete()
    
    # Delete feedback
    db.session.delete(feedback)
    db.session.commit()
    
    flash('Feedback and all responses have been deleted', 'success')
    return redirect(url_for('admin.moderate_feedback'))

@admin.route('/polls')
def manage_polls():
    """Manage polls"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'active')
    
    query = Poll.query
    
    if status == 'active':
        query = query.filter(Poll.is_active == True)
    elif status == 'inactive':
        query = query.filter(Poll.is_active == False)
    
    polls = query.order_by(Poll.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/manage_polls.html', polls=polls)

@admin.route('/polls/<int:id>/toggle-status', methods=['POST'])
def toggle_poll_status(id):
    """Toggle poll active status"""
    poll = Poll.query.get_or_404(id)
    poll.is_active = not poll.is_active
    poll.updated_at = datetime.utcnow()
    db.session.commit()
    
    status = 'activated' if poll.is_active else 'deactivated'
    flash(f'Poll "{poll.title}" has been {status}', 'success')
    
    return redirect(url_for('admin.manage_polls'))

@admin.route('/polls/<int:id>/delete', methods=['POST'])
def delete_poll(id):
    """Delete poll and all related data"""
    poll = Poll.query.get_or_404(id)
    
    # Delete associated options and responses
    PollOption.query.filter_by(poll_id=id).delete()
    PollResponse.query.filter_by(poll_id=id).delete()
    
    # Delete poll
    db.session.delete(poll)
    db.session.commit()
    
    flash('Poll and all related data have been deleted', 'success')
    return redirect(url_for('admin.manage_polls'))

@admin.route('/system-config', methods=['GET', 'POST'])
def system_config():
    """Manage system configuration"""
    if request.method == 'POST':
        # Update config values (in a real app, this would update a config DB or environment)
        # For demo purposes, we'll just flash messages
        flash('System configuration updated successfully', 'success')
        return redirect(url_for('admin.system_config'))
    
    # In a real implementation, you would load current config from DB
    config = {
        'enable_sms': True,
        'enable_ussd': True,
        'default_language': 'en',
        'max_feedback_length': 500,
        'feedback_moderation': 'auto',
        'notification_email': 'admin@revolutwdo.org'
    }
    
    return render_template('admin/system_config.html', config=config)

@admin.route('/analytics/config', methods=['GET', 'POST'])
def analytics_config():
    """Configure analytics settings"""
    if request.method == 'POST':
        # Update analytics config
        flash('Analytics configuration updated successfully', 'success')
        return redirect(url_for('admin.analytics_config'))
    
    # Mock configuration data
    config = {
        'enable_sentiment': True,
        'enable_realtime': True,
        'trending_threshold': 10,
        'priority_keywords': ['urgent', 'emergency', 'help']
    }
    
    return render_template('admin/analytics_config.html', config=config)

@admin.route('/reports')
def generate_reports():
    """Generate and download reports"""
    report_type = request.args.get('type', 'feedback')
    timeframe = request.args.get('timeframe', 'month')
    
    # In a real implementation, this would generate a PDF/Excel report
    # For demo, we'll just show a placeholder
    
    filename = f"{report_type}_report_{timeframe}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    
    flash(f'Report "{filename}" generated successfully. Download will start shortly.', 'success')
    return redirect(url_for('admin.dashboard'))
