# -*- encoding: utf-8 -*-
"""
FMZB Hub - Users Module
Consolidated users blueprint with authentication, profile management, and dashboard
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import re
import os
import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv

load_dotenv()

users_bp = Blueprint('users', __name__, url_prefix='/users')

# ===== DATABASE HELPERS =====

def get_db():
    """Get database connection to BIT 4444 Group Project"""
    try:
        conn = pymysql.connect(
            host=os.getenv('DB_HOST', 'mysql'),
            port=int(os.getenv('DB_PORT', 3309)),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', 'change-me'),
            database=os.getenv('DB_NAME', 'BIT 4444 Group Project'),
            charset='utf8mb4',
            cursorclass=DictCursor,
            autocommit=True
        )
        return conn
    except Exception as e:
        print(f"[ERROR] DB connection failed: {e}")
        return None

# ===== DECORATORS =====

def login_required(f):
    """Require login for protected routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('users.login'))
        return f(*args, **kwargs)
    return decorated_function

# ===== VALIDATORS =====

def is_valid_email(email):
    """Validate email format"""
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) is not None

def is_strong_password(password):
    """Validate password strength: 8+ chars, 1 upper, 1 lower, 1 digit, 1 special"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r'[A-Z]', password):
        return False, "Must contain uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Must contain lowercase letter"
    if not re.search(r'\d', password):
        return False, "Must contain digit"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Must contain special character"
    return True, "Valid"

# ===== ROUTES =====

@users_bp.route('/register', methods=['GET', 'POST'])
def register():
    """UC1: Registration"""
    if request.method == 'GET':
        return render_template('users/register.html')
    
    try:
        email = request.form.get('email', '').strip().lower()
        user_type = request.form.get('user_type', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip() or None
        website = request.form.get('website', '').strip() or None
        business_name = request.form.get('business_name', '').strip() or None
        
        # Validation
        if not email or not is_valid_email(email):
            flash('Invalid email address.', 'danger')
            return redirect(url_for('users.register'))
        
        if user_type not in ['customer', 'merchant']:
            flash('Invalid role.', 'danger')
            return redirect(url_for('users.register'))
        
        if not first_name or not last_name:
            flash('First and last name required.', 'danger')
            return redirect(url_for('users.register'))
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('users.register'))
        
        is_valid, msg = is_strong_password(password)
        if not is_valid:
            flash(msg, 'danger')
            return redirect(url_for('users.register'))
        
        # Check if email exists
        conn = get_db()
        if not conn:
            flash('Database error.', 'danger')
            return redirect(url_for('users.register'))
        
        cursor = conn.cursor()
        cursor.execute("SELECT Email FROM UserProfile WHERE Email = %s", (email,))
        if cursor.fetchone():
            conn.close()
            flash('Email already registered.', 'danger')
            return redirect(url_for('users.register'))
        
        # Create user
        hashed = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO UserProfile 
            (Email, UserType, ContactFirstName, ContactLastName, UPassword, Phone, Website, BusinessName, Status, TimeOfCreation)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'active', NOW())
        """, (email, user_type, first_name, last_name, hashed, phone, website, business_name))
        
        # Log activity
        cursor.execute("""
            INSERT INTO UserActivityLog (Email, ActivityType, ActivityDate)
            VALUES (%s, 'Registered', NOW())
        """, (email,))
        
        conn.close()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('users.login'))
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('users.register'))

@users_bp.route('/login', methods=['GET', 'POST'])
def login():
    """UC2: Login"""
    if request.method == 'GET':
        return render_template('users/login.html')
    
    try:
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        conn = get_db()
        if not conn:
            flash('Database error.', 'danger')
            return redirect(url_for('users.login'))
        
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM UserProfile WHERE Email = %s", (email,))
        user = cursor.fetchone()
        
        if not user or not check_password_hash(user['UPassword'], password):
            conn.close()
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('users.login'))
        
        if user['Status'] != 'active':
            conn.close()
            flash('Account disabled.', 'warning')
            return redirect(url_for('users.login'))
        
        # Create session
        session['user_email'] = email
        session['user_name'] = f"{user['ContactFirstName']} {user['ContactLastName']}"
        session['user_type'] = user['UserType']
        session.permanent = True
        
        # Update last login
        cursor.execute("UPDATE UserProfile SET LastLogin = NOW() WHERE Email = %s", (email,))
        
        # Log activity
        cursor.execute("INSERT INTO UserActivityLog (Email, ActivityType, ActivityDate) VALUES (%s, 'Logged In', NOW())", (email,))
        
        conn.close()
        flash(f'Welcome, {user["ContactFirstName"]}!', 'success')
        return redirect(url_for('users.dashboard'))
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('users.login'))

@users_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """UC3: Profile"""
    email = session.get('user_email')
    
    if request.method == 'GET':
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM UserProfile WHERE Email = %s", (email,))
        user = cursor.fetchone()
        conn.close()
        return render_template('users/profile.html', user=user)
    
    try:
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip() or None
        website = request.form.get('website', '').strip() or None
        business_name = request.form.get('business_name', '').strip() or None
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Update profile fields
        updates = []
        params = []
        
        if first_name:
            updates.append("ContactFirstName = %s")
            params.append(first_name)
        if last_name:
            updates.append("ContactLastName = %s")
            params.append(last_name)
        if phone is not None:
            updates.append("Phone = %s")
            params.append(phone)
        if website is not None:
            updates.append("Website = %s")
            params.append(website)
        if business_name is not None:
            updates.append("BusinessName = %s")
            params.append(business_name)
        
        # Handle password change
        if new_password:
            if new_password != confirm_password:
                conn.close()
                flash('Passwords do not match.', 'danger')
                cursor.execute("SELECT * FROM UserProfile WHERE Email = %s", (email,))
                user = cursor.fetchone()
                return render_template('users/profile.html', user=user)
            
            is_valid, msg = is_strong_password(new_password)
            if not is_valid:
                conn.close()
                flash(msg, 'danger')
                cursor.execute("SELECT * FROM UserProfile WHERE Email = %s", (email,))
                user = cursor.fetchone()
                return render_template('users/profile.html', user=user)
            
            updates.append("UPassword = %s")
            params.append(generate_password_hash(new_password))
        
        if updates:
            params.append(email)
            sql = f"UPDATE UserProfile SET {', '.join(updates)} WHERE Email = %s"
            cursor.execute(sql, params)
            
            # Log activity
            cursor.execute("INSERT INTO UserActivityLog (Email, ActivityType, ActivityDate) VALUES (%s, 'Profile Updated', NOW())", (email,))
            
            flash('Profile updated.', 'success')
        else:
            flash('No changes.', 'info')
        
        conn.close()
        return redirect(url_for('users.profile'))
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('users.profile'))

@users_bp.route('/deactivate', methods=['POST'])
@login_required
def deactivate():
    """UC4: Deactivate"""
    try:
        email = session.get('user_email')
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Soft delete
        cursor.execute("UPDATE UserProfile SET Status = 'disabled' WHERE Email = %s", (email,))
        
        # Log activity
        cursor.execute("INSERT INTO UserActivityLog (Email, ActivityType, ActivityDate) VALUES (%s, 'Deactivated', NOW())", (email,))
        
        conn.close()
        session.clear()
        
        flash('Account deactivated.', 'info')
        return redirect(url_for('users.login'))
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('users.profile'))

@users_bp.route('/dashboard')
@login_required
def dashboard():
    """UC5: Dashboard"""
    return render_template('users/dashboard.html')

@users_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout"""
    try:
        email = session.get('user_email')
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO UserActivityLog (Email, ActivityType, ActivityDate) VALUES (%s, 'Logged Out', NOW())", (email,))
        conn.close()
    except:
        pass
    
    session.clear()
    flash('Logged out.', 'success')
    return redirect(url_for('users.login'))

# ===== API ENDPOINTS =====

@users_bp.route('/api/metrics', methods=['GET'])
@login_required
def metrics():
    """Get KPI metrics"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as total FROM UserProfile")
        total = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as active FROM UserProfile WHERE Status = 'active'")
        active = cursor.fetchone()['active']
        
        cursor.execute("SELECT COUNT(*) as disabled FROM UserProfile WHERE Status = 'disabled'")
        disabled = cursor.fetchone()['disabled']
        
        conn.close()
        return jsonify({'total': total, 'active': active, 'disabled': disabled})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@users_bp.route('/api/charts/roles', methods=['GET'])
@login_required
def charts_roles():
    """Get chart data for FusionCharts"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT UserType, COUNT(*) as cnt FROM UserProfile GROUP BY UserType")
        rows = cursor.fetchall()
        conn.close()
        
        categories = [{'label': row['UserType'].capitalize()} for row in rows]
        dataset = [{'value': row['cnt']} for row in rows]
        
        return jsonify({'categories': categories, 'dataset': dataset})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@users_bp.route('/api/recent-users', methods=['GET'])
@login_required
def recent_users():
    """Get recent users for dashboard table"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Email, UserType, Status, TimeOfCreation, ContactFirstName, ContactLastName
            FROM UserProfile 
            ORDER BY TimeOfCreation DESC 
            LIMIT 10
        """)
        users = cursor.fetchall()
        conn.close()
        return jsonify(users)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@users_bp.route('/api/chat-analyze', methods=['POST'])
@login_required
def chat_analyze():
    """UC6: Chat-based analysis"""
    try:
        email = session.get('user_email')
        data = request.get_json()
        question = (data.get('question', '') or '').strip().lower()
        
        if not question:
            return jsonify({'error': 'No question'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Whitelisted queries
        queries = {
            'new customers': ('SELECT COUNT(*) as cnt FROM UserProfile WHERE UserType="customer" AND TimeOfCreation >= DATE_SUB(NOW(), INTERVAL 30 DAY)', 'New customers (30d)'),
            'active users': ('SELECT COUNT(*) as cnt FROM UserProfile WHERE Status="active"', 'Total active users'),
            'merchants': ('SELECT COUNT(*) as cnt FROM UserProfile WHERE UserType="merchant"', 'Total merchants'),
            'customers': ('SELECT COUNT(*) as cnt FROM UserProfile WHERE UserType="customer"', 'Total customers'),
            'disabled': ('SELECT COUNT(*) as cnt FROM UserProfile WHERE Status="disabled"', 'Disabled accounts'),
        }
        
        result = None
        label = 'Not found'
        
        for keyword, (sql, desc) in queries.items():
            if keyword in question:
                cursor.execute(sql)
                row = cursor.fetchone()
                result = row['cnt'] if row else 0
                label = desc
                break
        
        # Log activity
        cursor.execute("INSERT INTO UserActivityLog (Email, ActivityType, ActivityDescription, ActivityDate) VALUES (%s, 'Analysis', %s, NOW())", (email, question))
        
        conn.close()
        
        if result is not None:
            return jsonify({'answer': f'{label}: {result}', 'value': result, 'label': label})
        else:
            return jsonify({'answer': 'Query not understood. Try: "new customers", "active users", "merchants", "customers", "disabled"'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
