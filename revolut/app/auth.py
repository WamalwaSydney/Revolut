from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Role
from functools import wraps
from datetime import datetime
import re

auth_bp = Blueprint('auth', __name__)

def role_required(role_name):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.is_json:
                    return jsonify({"error": "Authentication required"}), 401
                return redirect(url_for('auth.login'))

            if not current_user.has_role(role_name):
                if request.is_json:
                    return jsonify({"error": "Insufficient permissions"}), 403
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_email(email):
    """Validate email format"""
    pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    return True, "Password is valid"

def validate_phone(phone):
    """Validate phone number format"""
    if not phone:
        return True, "Phone number is optional"

    # Remove non-digits
    digits_only = re.sub(r'\D', '', phone)

    # Check if it's a valid Kenyan number
    if digits_only.startswith('254') and len(digits_only) == 12:
        return True, "Phone number is valid"
    elif digits_only.startswith('0') and len(digits_only) == 10:
        return True, "Phone number is valid"
    elif digits_only.startswith('7') and len(digits_only) == 9:
        return True, "Phone number is valid"
    else:
        return False, "Invalid phone number format"

# Web routes for login/register pages
@auth_bp.route('/login', methods=['GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    roles = Role.query.filter(Role.name.in_(['citizen', 'cso', 'official'])).all()
    return render_template('auth/register.html', roles=roles)

# Handle both form and JSON registration
@auth_bp.route('/register', methods=['POST'])
def handle_register():
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
            # Convert checkbox to boolean for form data
            data['terms'] = 'terms' in request.form

        # Validate required fields
        required_fields = ['username', 'email', 'password', 'role']
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            if request.is_json:
                return jsonify({"error": error_msg}), 400
            flash(error_msg, 'error')
            return redirect(url_for('auth.register'))

        # Validate terms acceptance
        if not data.get('terms'):
            error_msg = "You must agree to the Terms of Service and Privacy Policy"
            if request.is_json:
                return jsonify({"error": error_msg}), 400
            flash(error_msg, 'error')
            return redirect(url_for('auth.register'))

        # Validate email format
        if not validate_email(data['email']):
            error_msg = "Invalid email format"
            if request.is_json:
                return jsonify({"error": error_msg}), 400
            flash(error_msg, 'error')
            return redirect(url_for('auth.register'))

        # Validate password
        password_valid, password_message = validate_password(data['password'])
        if not password_valid:
            if request.is_json:
                return jsonify({"error": password_message}), 400
            flash(password_message, 'error')
            return redirect(url_for('auth.register'))

        # Validate confirm password (if provided)
        if data.get('confirmPassword') and data['password'] != data['confirmPassword']:
            error_msg = "Passwords do not match"
            if request.is_json:
                return jsonify({"error": error_msg}), 400
            flash(error_msg, 'error')
            return redirect(url_for('auth.register'))

        # Validate phone number (if provided)
        if data.get('phone'):
            phone_valid, phone_message = validate_phone(data['phone'])
            if not phone_valid:
                if request.is_json:
                    return jsonify({"error": phone_message}), 400
                flash(phone_message, 'error')
                return redirect(url_for('auth.register'))

        # Check if user exists
        existing_user = User.query.filter(
            (User.username == data['username']) | (User.email == data['email'])
        ).first()

        if existing_user:
            if existing_user.username == data['username']:
                error_msg = "Username already exists"
            else:
                error_msg = "Email already exists"

            if request.is_json:
                return jsonify({"error": error_msg}), 400
            flash(error_msg, 'error')
            return redirect(url_for('auth.register'))

        # Validate role
        role = Role.query.filter_by(name=data['role']).first()
        if not role:
            error_msg = "Invalid role selected"
            if request.is_json:
                return jsonify({"error": error_msg}), 400
            flash(error_msg, 'error')
            return redirect(url_for('auth.register'))

        # Create user
        user = User(
            username=data['username'].strip(),
            email=data['email'].strip().lower(),
            phone=data.get('phone', '').strip() if data.get('phone') else None,
            created_at=datetime.utcnow(),
            active=True
        )

        # Set password
        user.set_password(data['password'])

        # Assign role
        user.roles.append(role)

        # Save to database
        db.session.add(user)
        db.session.commit()

        # Return success response
        success_msg = "Account created successfully! Please log in."
        if request.is_json:
            return jsonify({"message": success_msg, "success": True}), 201

        flash(success_msg, 'success')
        return redirect(url_for('auth.login'))

    except Exception as e:
        # Rollback in case of error
        db.session.rollback()
        print(f"Registration error: {str(e)}")

        error_msg = "An unexpected error occurred. Please try again."
        if request.is_json:
            return jsonify({"error": error_msg}), 500

        flash(error_msg, 'error')
        return redirect(url_for('auth.register'))

# Handle both form and JSON login
@auth_bp.route('/login', methods=['POST'])
def handle_login():
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
            data['remember'] = 'remember' in request.form

        # Validate required fields
        if not data.get('username') or not data.get('password'):
            error_msg = "Username and password are required"
            if request.is_json:
                return jsonify({"error": error_msg}), 400
            flash(error_msg, 'error')
            return redirect(url_for('auth.login'))

        # Find user (allow login with username or email)
        user = User.query.filter(
            (User.username == data['username']) | (User.email == data['username'])
        ).first()

        print(f"Login attempt for: {data['username']}")
        print(f"User found: {user is not None}")
        if user:
            print(f"Password check: {user.check_password(data['password'])}")
            print(f"User active: {user.active}")

        if not user or not user.check_password(data['password']):
            error_msg = "Invalid username or password"
            if request.is_json:
                return jsonify({"error": error_msg}), 401
            flash(error_msg, 'error')
            return redirect(url_for('auth.login'))

        if not user.active:
            error_msg = "Account is deactivated"
            if request.is_json:
                return jsonify({"error": error_msg}), 401
            flash(error_msg, 'error')
            return redirect(url_for('auth.login'))

        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Log user in
        login_user(user, remember=data.get('remember', False))

        if request.is_json:
            return jsonify({
                "message": "Logged in successfully",
                "success": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "roles": user.get_role_names()
                }
            }), 200

        flash('Logged in successfully!', 'success')
        return redirect(url_for('main.dashboard'))

    except Exception as e:
        print(f"Login error: {str(e)}")
        error_msg = "An unexpected error occurred. Please try again."

        if request.is_json:
            return jsonify({"error": error_msg}), 500

        flash(error_msg, 'error')
        return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    if request.is_json:
        return jsonify({"message": "Logged out successfully"})
    else:
        flash('You have been logged out successfully', 'info')
        return redirect(url_for('main.index'))

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html')

@auth_bp.route('/settings')
@login_required
def settings():
    return render_template('auth/settings.html')

# API endpoints
@auth_bp.route('/api/check-username', methods=['POST'])
def check_username():
    try:
        data = request.get_json()
        username = data.get('username', '').strip()

        if not username:
            return jsonify({"error": "Username is required"}), 400

        exists = User.query.filter_by(username=username).first() is not None

        return jsonify({
            "available": not exists,
            "message": "Username is available" if not exists else "Username already exists"
        })

    except Exception as e:
        return jsonify({"error": "Error checking username"}), 500

@auth_bp.route('/api/check-email', methods=['POST'])
def check_email():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()

        if not email:
            return jsonify({"error": "Email is required"}), 400

        if not validate_email(email):
            return jsonify({"error": "Invalid email format"}), 400

        exists = User.query.filter_by(email=email).first() is not None

        return jsonify({
            "available": not exists,
            "message": "Email is available" if not exists else "Email already exists"
        })

    except Exception as e:
        return jsonify({"error": "Error checking email"}), 500