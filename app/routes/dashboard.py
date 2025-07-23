from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Feedback

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    feedback_data = Feedback.query.all()
    result = [{
        'text': f.text,
        'sentiment': f.sentiment_score,
        'timestamp': f.timestamp
    } for f in feedback_data]
    return jsonify(result)
