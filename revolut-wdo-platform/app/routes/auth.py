from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User
from app import db, login_manager
from .forms import LoginForm, RegistrationForm, ResetPasswordForm

auth = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def _redirect_by_role(user):
    """Helper function to redirect users based on their role"""
    # Convert role to lowercase for comparison to handle case differences
    user_role = user.role.lower() if user.role else 'citizen'

    print(f"Redirecting user: {user.username}, Role: {user.role} (normalized: {user_role})")

    if user_role == 'admin':
        print("Redirecting to admin dashboard")
        return redirect(url_for('admin.dashboard'))
    elif user_role in ['government', 'analyst']:
        print("Redirecting to government dashboard")
        return redirect(url_for('dashboard.government'))
    else:  # citizen or any other role
        print("Redirecting to citizen dashboard")
        return redirect(url_for('dashboard.citizen'))

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Unified login for all user roles"""
    print(f"=== LOGIN ATTEMPT ===")
    print(f"Method: {request.method}")
    print(f"User authenticated: {current_user.is_authenticated}")

    if current_user.is_authenticated:
        print(f"Already logged in: {current_user.username}, Role: {current_user.role}")
        return _redirect_by_role(current_user)

    form = LoginForm()

    if form.validate_on_submit():
        email_or_username = form.email.data.strip()
        password = form.password.data

        print(f"Form data - Email/Username: '{email_or_username}', Password length: {len(password)}")

        # Find user by email or username
        user = User.query.filter(
            (User.email == email_or_username) | (User.username == email_or_username)
        ).first()

        if user:
            print(f"✅ User found:")
            print(f"  - ID: {user.id}")
            print(f"  - Username: {user.username}")
            print(f"  - Email: {user.email}")
            print(f"  - Role: {user.role}")
            print(f"  - Active: {getattr(user, 'is_active', 'No is_active field')}")

            # Test password
            try:
                password_valid = user.check_password(password)
                print(f"  - Password check result: {password_valid}")

                # Alternative password check if the first fails
                if not password_valid and hasattr(user, 'password_hash'):
                    password_valid = check_password_hash(user.password_hash, password)
                    print(f"  - Alternative password check: {password_valid}")

            except Exception as e:
                print(f"  - Password check error: {e}")
                password_valid = False

            if password_valid:
                # Check if user is active
                if hasattr(user, 'is_active') and not user.is_active:
                    print("❌ User account is deactivated")
                    flash('Your account has been deactivated. Please contact support.', 'error')
                    return render_template('auth/login.html', form=form)

                print(f"✅ Logging in user: {user.username}")

                try:
                    login_user(user, remember=form.remember.data)

                    # Verify login worked
                    print(f"Current user after login: {current_user.username if current_user.is_authenticated else 'NOT AUTHENTICATED'}")
                    print(f"Current user role: {current_user.role if current_user.is_authenticated else 'N/A'}")

                    flash(f'Welcome back, {user.username}!', 'success')

                    # Handle next parameter
                    next_page = request.args.get('next')
                    if next_page:
                        print(f"Redirecting to next page: {next_page}")
                        return redirect(next_page)

                    # Redirect based on role
                    print(f"Calling _redirect_by_role for user with role: {user.role}")
                    return _redirect_by_role(user)

                except Exception as e:
                    print(f"❌ Login error: {e}")
                    flash('Login failed. Please try again.', 'error')
            else:
                print("❌ Invalid password")
        else:
            print(f"❌ No user found with email/username: '{email_or_username}'")
            # Let's also check what users exist
            try:
                all_users = User.query.limit(5).all()
                print("Available users (first 5):")
                for u in all_users:
                    print(f"  - {u.username} ({u.email}) - Role: {u.role}")
            except Exception as e:
                print(f"Error querying users: {e}")

        flash('Invalid email/username or password', 'error')
    else:
        if request.method == 'POST':
            print(f"❌ Form validation failed: {form.errors}")

    print("=== END LOGIN ATTEMPT ===")
    return render_template('auth/login.html', form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    """User registration - defaults to citizen role"""
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)

    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            # Check if user already exists
            existing_user = User.query.filter(
                (User.email == form.email.data) | (User.username == form.username.data)
            ).first()

            if existing_user:
                if existing_user.email == form.email.data:
                    flash('Email already registered. Please use a different email.', 'error')
                else:
                    flash('Username already taken. Please choose a different username.', 'error')
                return render_template('auth/register.html', form=form)

            # Create new user with citizen role by default
            user = User(
                username=form.username.data,
                email=form.email.data,
                phone=getattr(form, 'phone', None) and form.phone.data,
                county=getattr(form, 'county', None) and form.county.data,
                role='citizen',  # Default role
                is_active=True
            )
            user.set_password(form.password.data)

            db.session.add(user)
            db.session.commit()

            print(f"New user registered: {user.username} ({user.email}) - Role: {user.role}")
            flash('Your account has been created! You can now log in.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            print(f"Registration error: {e}")
            flash('Registration failed. Please try again.', 'error')

    return render_template('auth/register.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    """User logout"""
    username = current_user.username if current_user.is_authenticated else 'Unknown'
    logout_user()
    flash(f'Goodbye {username}! You have been logged out.', 'success')
    return redirect(url_for('main.index'))

@auth.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Password reset request"""
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # In a real application, you would send an email here
            # For now, just show a message
            flash('If an account with that email exists, you will receive password reset instructions.', 'info')
        else:
            flash('If an account with that email exists, you will receive password reset instructions.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', form=form)

@auth.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('auth/profile.html', user=current_user)

@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    from .forms import ChangePasswordForm

    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Your password has been updated!', 'success')
            return redirect(url_for('auth.profile'))
        else:
            flash('Current password is incorrect.', 'error')

    return render_template('auth/change_password.html', form=form)

# Error handlers
@auth.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@auth.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# Helper function to create admin user programmatically
def create_admin_user(username='admin', email='admin@revolutwdo.org', password='admin123'):
    """Create admin user - can be called from Flask shell or startup script"""
    try:
        # Check if admin already exists
        existing_admin = User.query.filter_by(email=email).first()

        if existing_admin:
            print(f"Admin user already exists: {existing_admin.username}")
            return existing_admin

        # Create new admin user
        admin_user = User(
            username=username,
            email=email,
            role='admin',
            is_active=True
        )
        admin_user.set_password(password)

        db.session.add(admin_user)
        db.session.commit()

        print(f"Admin user created successfully: {username} ({email})")
        return admin_user

    except Exception as e:
        db.session.rollback()
        print(f"Error creating admin user: {e}")
        return None