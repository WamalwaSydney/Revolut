from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .. import db
from ..models import Feedback

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/moderate', methods=['POST'])
@jwt_required()
def moderate_content():
    user = get_jwt_identity()
    if user['role'] != 'admin':
        return jsonify({'message': 'Admin access required'}), 403
    data = request.json
    fb = Feedback.query.get(data['id'])
    if fb:
        db.session.delete(fb)
        db.session.commit()
        return jsonify({'message': 'Feedback removed'})
    return jsonify({'message': 'Feedback not found'}), 404
