from app import db
from app.models import UserFeedback, Alert
from datetime import datetime, timedelta
from collections import Counter

def check_for_trending_issues():
    # Check feedback from last 24 hours
    time_threshold = datetime.utcnow() - timedelta(hours=24)
    recent_feedback = UserFeedback.query.filter(
        UserFeedback.created_at >= time_threshold,
        UserFeedback.is_processed == True
    ).all()

    # Count tags
    tag_counter = Counter()
    for feedback in recent_feedback:
        if feedback.tags:
            tag_counter.update(feedback.tags)

    # Check for tags that appear more than threshold (e.g., 10 times)
    trending_tags = [tag for tag, count in tag_counter.items() if count >= 10]

    for tag in trending_tags:
        # Check if alert already exists
        existing_alert = Alert.query.filter_by(topic=tag).first()
        if not existing_alert:
            # Get affected locations
            locations = [f.location for f in recent_feedback
                        if tag in f.tags and f.location]
            alert = Alert(
                topic=tag,
                severity='medium',
                affected_locations=list(set(locations)))
            db.session.add(alert)

    db.session.commit()