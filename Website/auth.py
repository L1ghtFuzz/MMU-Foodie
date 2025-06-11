# Website/auth.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User  # Make sure User model is imported
from werkzeug.security import generate_password_hash, check_password_hash
from . import db  # Import db
from flask_login import login_user, login_required, logout_user, current_user


auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['identifier']
        password = request.form['password']

        # Query user by username or email
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if user and check_password_hash(user.password, password):
            login_user(user, remember=True)
            flash('Logged in successfully!', category='success')
            return redirect(url_for('views.home'))
        else:
            flash('Invalid credentials', category='error')
            # Stay on the login page to allow user to retry
            return redirect(url_for('auth.login'))

    # Pass current_user to template for conditional rendering (e.g., login/logout links)
    return render_template('login.html', user=current_user)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', category='info')
    return redirect(url_for('auth.login'))


@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('firstName')
        # --- FIX: Added username capture and validation ---
        username = request.form.get('username')
        # -------------------------------------------------
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        # Check for existing email or username
        user_by_email = User.query.filter_by(email=email).first()
        user_by_username = User.query.filter_by(username=username).first()

        if user_by_email:
            flash('Email already exists.', category='error')
        elif user_by_username:
            flash('Username already exists.', category='error')
        elif len(email) < 4:
            flash('Email must be greater than 3 characters.', category='error')
        elif not username or len(username) < 3: # Basic username validation
            flash('Username must be at least 3 characters.', category='error')
        elif len(first_name) < 2:
            flash('First name must be greater than 1 character.', category='error')
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
        elif len(password1) < 7:
            flash('Password must be at least 7 characters.', category='error')
        else:
            # Consistent hashing method: pbkdf2:sha256
            new_user = User(
                email=email,
                username=username, # --- FIX: Pass username to User model ---
                first_name=first_name,
                password=generate_password_hash(password1, method='pbkdf2:sha256')
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash('Account created!', category='success')
            return redirect(url_for('views.home'))

    return render_template("sign_up.html", user=current_user)


@auth.route('/change-password', methods=['GET', 'POST'])
# WARNING: This route, as currently implemented, is a MAJOR SECURITY VULNERABILITY!
# It allows anyone to change any user's password if they know the email/username,
# without any authentication (e.g., old password, email verification, security token).
# DO NOT USE IN PRODUCTION WITHOUT A SECURE RESET FLOW!
#
# For a secure password reset, you would typically:
# 1. Send a unique, time-limited token to the user's registered email.
# 2. Verify that token when the user clicks the link to set a new password.
# 3. This 'change_password' route would then be a "set new password via token" route.
#
# If this route is intended for a LOGGED-IN user to change their password,
# it MUST require the current password and be protected with @login_required.
# (See previous guidance for that implementation)
def change_password():
    if request.method == 'POST':
        identifier = request.form.get('identifier')  # can be email or username
        new_password = request.form.get('new_password')

        user = User.query.filter((User.email == identifier) | (User.username == identifier)).first()
        if not user:
            flash("No user found with that email or username.", category='error')
        else:
            # --- FIX: Use consistent hashing method: pbkdf2:sha256 ---
            user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
            # ---------------------------------------------------------
            db.session.commit()
            flash("Password updated successfully (WARNING: THIS IS INSECURE FOR RESET).", category='success')
            return redirect(url_for('auth.login'))

    # Pass current_user to template for conditional rendering
    return render_template("change_password.html", user=current_user)