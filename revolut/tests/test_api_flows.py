import pytest
import json
from revolut.app import create_app, db
from revolut.app.models import User, Role, Poll, Issue

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })

    with app.app_context():
        db.create_all()
        # Create roles
        citizen_role = Role(name='citizen')
        cso_role = Role(name='cso')
        db.session.add_all([citizen_role, cso_role])
        db.session.commit()

        # Create test user with cso role
        cso_user = User(username='testcso', email='cso@example.com')
        cso_user.set_password('password123')
        cso_user.roles.append(cso_role)
        db.session.add(cso_user)
        db.session.commit()

    yield app

    with app.app_context():
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

def login(client, username, password):
    return client.post('/auth/login', json={
        'username': username,
        'password': password
    })

def test_create_poll_and_vote(client, app):
    # Login as CSO
    login_resp = login(client, 'testcso', 'password123')
    assert login_resp.status_code == 200 or login_resp.status_code == 302

    # Create poll
    poll_data = {
        "question": "Is the community satisfied with local services?",
        "options": ["Yes", "No", "Not sure"],
        "duration_days": 7
    }
    create_resp = client.post('/api/polls', json=poll_data)
    assert create_resp.status_code == 201
    poll_json = create_resp.get_json()
    poll_id = poll_json['poll']['id']

    # Vote on poll with valid option
    vote_resp = client.post(f'/api/polls/{poll_id}/vote', json={"option_id": 1})
    assert vote_resp.status_code == 200
    vote_json = vote_resp.get_json()
    assert vote_json['status'] == 'success'
    assert vote_json['selected_option'] == 1

    # Vote on poll with invalid option
    invalid_vote_resp = client.post(f'/api/polls/{poll_id}/vote', json={"option_id": 99})
    assert invalid_vote_resp.status_code == 400

def test_create_issue(client):
    issue_data = {
        "title": "Broken streetlight",
        "description": "The streetlight on 5th avenue is broken and needs repair.",
        "location": "Nairobi West",
        "category": "Infrastructure",
        "priority": "High",
        "contact": "254700000000"
    }
    create_resp = client.post('/api/issues', json=issue_data)
    assert create_resp.status_code == 200 or create_resp.status_code == 201
    create_json = create_resp.get_json()
    assert create_json['status'] == 'success'
    assert 'issue_id' in create_json

def test_submit_feedback(client, app):
    feedback_data = {
        "content": "Great service improvement in the area.",
        "location": "Nairobi West",
        "source": "web"
    }
    feedback_resp = client.post('/api/feedback', json=feedback_data)
    assert feedback_resp.status_code == 200 or feedback_resp.status_code == 201
    feedback_json = feedback_resp.get_json()
    assert feedback_json['status'] == 'success'
    assert 'feedback_id' in feedback_json
