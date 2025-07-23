from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .. import db
from ..models import Feedback
from ..utils.nlp import analyze_sentiment

feedback_bp = Blueprint('feedback', __name__)

@feedback_bp.route('/feedback', methods=['POST'])
@jwt_required()
def submit_feedback():
    user = get_jwt_identity()
    data = request.json
    sentiment = analyze_sentiment(data['text'])
    fb = Feedback(user_id=user['id'], text=data['text'], sentiment_score=sentiment)
    db.session.add(fb)
    db.session.commit()
    return jsonify({'message': 'Feedback submitted', 'sentiment': sentiment})
