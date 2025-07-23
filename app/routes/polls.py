from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from .. import db
from ..models import Poll

polls_bp = Blueprint('polls', __name__)

@polls_bp.route('/polls', methods=['POST'])
@jwt_required()
def create_poll():
    data = request.json
    poll = Poll(question=data['question'], options=data['options'])
    db.session.add(poll)
    db.session.commit()
    return jsonify({'message': 'Poll created'})

@polls_bp.route('/polls', methods=['GET'])
def get_polls():
    polls = Poll.query.all()
    output = [{'question': p.question, 'options': p.options} for p in polls]
    return jsonify(output)
