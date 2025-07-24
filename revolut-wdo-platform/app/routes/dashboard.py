from flask import Blueprint, render_template, request, jsonify,redirect,url_for
from flask_login import login_required, current_user
from app.models import Feedback, Poll, User
from app.utils.analytics import AnalyticsDashboard, SentimentAnalyzer
from app import db
from datetime import datetime, timedelta
import json

dashboard = Blueprint('dashboard', __name__)

@dashboard.route('/citizen')
@login_required
def citizen():
    """Citizen dashboard"""
    if current_user.role not in ['citizen', 'admin']:
        return redirect(url_for('dashboard.government'))

    # User's feedback stats
    user_feedback = Feedback.query.filter_by(user_id=current_user.id).count()
    pending_feedback = Feedback.query.filter_by(
        user_id=current_user.id, status='pending'
    ).count()

    # Recent feedback
    recent_feedback = Feedback.query.filter_by(user_id=current_user.id).order_by(
        Feedback.created_at.desc()
    ).limit(5).all()

    # Available polls
    available_polls = Poll.query.filter(
        Poll.is_active == True,
        Poll.is_public == True
    ).limit(3).all()

    return render_template('dashboard/citizen.html',
                         user_feedback=user_feedback,
                         pending_feedback=pending_feedback,
                         recent_feedback=recent_feedback,
                         available_polls=available_polls)

@dashboard.route('/government')
@login_required
def government():
    """Government dashboard with analytics"""
    if not current_user.is_government():
        return redirect(url_for('dashboard.citizen'))

    # Get analytics data
    stats = AnalyticsDashboard.get_feedback_stats(30)
    trending = AnalyticsDashboard.get_trending_issues(7)
    user_stats = AnalyticsDashboard.get_user_engagement_stats()

    # Recent feedback requiring attention
    priority_feedback = Feedback.query.filter(
        Feedback.status == 'pending',
        Feedback.priority.in_(['high', 'urgent'])
    ).order_by(Feedback.created_at.desc()).limit(10).all()

    return render_template('dashboard/government.html',
                         stats=stats,
                         trending=trending,
                         user_stats=user_stats,
                         priority_feedback=priority_feedback)

@dashboard.route('/analytics')
@login_required
def analytics():
    """Advanced analytics dashboard"""
    if not current_user.is_government():
        return redirect(url_for('dashboard.citizen'))

    # Get filter parameters
    days = request.args.get('days', 30, type=int)
    county = request.args.get('county')
    category = request.args.get('category')

    # Build query
    query = Feedback.query.filter(
        Feedback.created_at >= datetime.utcnow() - timedelta(days=days)
    )

    if county:
        query = query.filter(Feedback.county == county)
    if category:
        query = query.filter(Feedback.category == category)

    feedback_data = query.all()

    # Analyze data
    analytics_data = {
        'total_feedback': len(feedback_data),
        'sentiment_distribution': {},
        'category_distribution': {},
        'county_distribution': {},
        'trend_data': []
    }

    # Process analytics
    for feedback in feedback_data:
        # Sentiment
        sentiment = feedback.sentiment_label or 'neutral'
        analytics_data['sentiment_distribution'][sentiment] = \
            analytics_data['sentiment_distribution'].get(sentiment, 0) + 1

        # Category
        category = feedback.category.value
        analytics_data['category_distribution'][category] = \
            analytics_data['category_distribution'].get(category, 0) + 1

        # County
        county = feedback.county
        analytics_data['county_distribution'][county] = \
            analytics_data['county_distribution'].get(county, 0) + 1

    return render_template('dashboard/analytics.html', analytics_data=analytics_data)

@dashboard.route('/api/chart-data')
@login_required
def chart_data():
    """API endpoint for chart data"""
    chart_type = request.args.get('type')
    days = request.args.get('days', 30, type=int)

    if chart_type == 'sentiment_trend':
        # Get sentiment trend over time
        start_date = datetime.utcnow() - timedelta(days=days)

        # Group by date and sentiment
        results = db.session.query(
            db.func.date(Feedback.created_at).label('date'),
            Feedback.sentiment_label,
            db.func.count(Feedback.id).label('count')
        ).filter(
            Feedback.created_at >= start_date
        ).group_by(
            db.func.date(Feedback.created_at),
            Feedback.sentiment_label
        ).all()

        # Format for charts
        chart_data = {}
        for result in results:
            date_str = result.date.strftime('%Y-%m-%d')
            sentiment = result.sentiment_label or 'neutral'

            if date_str not in chart_data:
                chart_data[date_str] = {'positive': 0, 'negative': 0, 'neutral': 0}

            chart_data[date_str][sentiment] = result.count

        return jsonify(chart_data)

    elif chart_type == 'category_distribution':
        # Get category distribution
        results = db.session.query(
            Feedback.category,
            db.func.count(Feedback.id).label('count')
        ).filter(
            Feedback.created_at >= datetime.utcnow() - timedelta(days=days)
        ).group_by(Feedback.category).all()

        return jsonify({result.category.value: result.count for result in results})

    return jsonify({'error': 'Invalid chart type'})
