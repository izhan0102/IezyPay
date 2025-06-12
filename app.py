from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta
from functools import wraps

# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'izypaytransactionsystem')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///iezypay.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)  # Keep users logged in for a year

# Initialize SQLAlchemy and LoginManager
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Define database models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    pin_hash = db.Column(db.String(200))
    balance = db.Column(db.Float, default=2000.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    transactions = db.relationship('Transaction', backref='user', lazy=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'credit', 'debit', 'transfer'
    description = db.Column(db.String(200))
    recipient = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def pin_required(f):
    """Decorator to require PIN verification for protected routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            # Check if PIN is set
            if not current_user.pin_hash:
                return redirect(url_for('setup_pin'))
            
            # Check if PIN is already verified in this session
            pin_verified = session.get('pin_verified', False)
            
            if not pin_verified:
                # Only redirect if PIN not verified
                return redirect(url_for('verify_pin', next=request.path))
        
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    """Homepage route"""
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        pin = request.form.get('pin', '')  # Default to empty string if None
        
        # Validate PIN if provided
        if pin and (len(pin) != 4 or not pin.isdigit()):
            flash('PIN must be a 4-digit number', 'danger')
            return render_template('signup.html')
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered', 'danger')
            return render_template('signup.html')
        
        existing_phone = User.query.filter_by(phone=phone).first()
        if existing_phone:
            flash('Phone number already registered', 'danger')
            return render_template('signup.html')
        
        # Create new user
        user = User(
            name=name,
            email=email,
            phone=phone,
            password_hash=generate_password_hash(password),
            pin_hash=generate_password_hash(pin) if pin else None,
            balance=1000.0  # Starting balance
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login route"""
    if request.method == 'POST':
        email_or_phone = request.form.get('email_or_phone')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email_or_phone).first() or User.query.filter_by(phone=email_or_phone).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            flash('Please check your login details and try again', 'danger')
            return redirect(url_for('login'))
        
        login_user(user, remember=True)
        session.permanent = True
        
        if not user.pin_hash:
            return redirect(url_for('setup_pin'))
        
        return redirect(url_for('verify_pin', next=url_for('dashboard')))
    
    return render_template('login.html')

@app.route('/setup-pin', methods=['GET', 'POST'])
@login_required
def setup_pin():
    """PIN setup route"""
    if current_user.pin_hash:
        flash('You have already set up a PIN', 'info')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        pin = request.form.get('pin')
        confirm_pin = request.form.get('confirm_pin')
        
        if pin != confirm_pin:
            flash('PINs do not match', 'danger')
            return redirect(url_for('setup_pin'))
        
        if len(pin) != 4 or not pin.isdigit():
            flash('PIN must be a 4-digit number', 'danger')
            return redirect(url_for('setup_pin'))
        
        current_user.pin_hash = generate_password_hash(pin, method='sha256')
        db.session.commit()
        
        session['pin_verified'] = True
        flash('PIN set successfully', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('setup_pin.html')

@app.route('/verify-pin', methods=['GET', 'POST'])
@login_required
def verify_pin():
    """PIN verification route"""
    if not current_user.pin_hash:
        return redirect(url_for('setup_pin'))
    
    next_page = request.args.get('next', url_for('dashboard'))
    
    # If PIN is already verified, go directly to the next page
    if session.get('pin_verified', False):
        return redirect(next_page)
    
    # If this is a direct navigation from a link (not a refresh)
    # and the user is coming from another page in our app, skip PIN verification
    referrer = request.referrer
    if request.method == 'GET' and referrer and referrer.startswith(request.host_url) and 'verify-pin' not in referrer:
        # Check if the referrer is from our app but not from the verify-pin page itself
        session['pin_verified'] = True
        return redirect(next_page)
    
    if request.method == 'POST':
        pin = request.form.get('pin')
        
        if check_password_hash(current_user.pin_hash, pin):
            session['pin_verified'] = True
            session.modified = True  # Ensure the session is saved
            return redirect(next_page)
        else:
            flash('Incorrect PIN', 'danger')
    
    return render_template('verify_pin.html', next=next_page)

@app.route('/dashboard')
@login_required
@pin_required
def dashboard():
    """User dashboard route"""
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.timestamp.desc()).limit(5).all()
    return render_template('dashboard.html', transactions=transactions)

@app.route('/logout')
@login_required
def logout():
    """User logout route"""
    session.pop('pin_verified', None)
    logout_user()
    return redirect(url_for('index'))

@app.route('/send-money')
@login_required
@pin_required
def send_money():
    """Money sending interface route"""
    return render_template('send_money.html')

@app.route('/send-money/phone', methods=['POST'])
@login_required
@pin_required
def send_money_phone():
    """Send money by phone number route"""
    phone = request.form.get('phone')
    amount = float(request.form.get('amount'))
    note = request.form.get('note', '')
    
    # Check if it's an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if amount <= 0:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Amount must be greater than 0'})
        flash('Amount must be greater than 0', 'danger')
        return redirect(url_for('send_money'))
    
    if current_user.balance < amount:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Insufficient balance'})
        flash('Insufficient balance', 'danger')
        return redirect(url_for('send_money'))
    
    recipient = User.query.filter_by(phone=phone).first()
    
    if not recipient:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Recipient not found'})
        flash('Recipient not found', 'danger')
        return redirect(url_for('send_money'))
    
    if recipient.id == current_user.id:
        if is_ajax:
            return jsonify({'success': False, 'message': 'You cannot send money to yourself'})
        flash('You cannot send money to yourself', 'danger')
        return redirect(url_for('send_money'))
    
    # Create transaction for sender (debit)
    sender_transaction = Transaction(
        user_id=current_user.id,
        amount=amount,
        transaction_type='debit',
        description=f'Money sent to {recipient.name}' + (f' - {note}' if note else ''),
        recipient=recipient.name
    )
    
    # Create transaction for recipient (credit)
    recipient_transaction = Transaction(
        user_id=recipient.id,
        amount=amount,
        transaction_type='credit',
        description=f'Money received from {current_user.name}' + (f' - {note}' if note else ''),
        recipient=current_user.name
    )
    
    # Update balances
    current_user.balance -= amount
    recipient.balance += amount
    
    # Commit changes
    db.session.add(sender_transaction)
    db.session.add(recipient_transaction)
    db.session.commit()
    
    success_message = f'₹{amount} sent successfully to {recipient.name}'
    
    if is_ajax:
        return jsonify({
            'success': True, 
            'message': success_message,
            'new_balance': current_user.balance
        })
    
    flash(success_message, 'success')
    return redirect(url_for('dashboard', transaction_success='true', message=success_message))

@app.route('/send-money/qr', methods=['POST'])
@login_required
@pin_required
def send_money_qr():
    """Send money by QR code route"""
    recipient_id = request.form.get('recipient_id')
    amount = float(request.form.get('amount'))
    note = request.form.get('note', '')
    
    # Check if it's an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if amount <= 0:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Amount must be greater than 0'})
        flash('Amount must be greater than 0', 'danger')
        return redirect(url_for('send_money'))
    
    if current_user.balance < amount:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Insufficient balance'})
        flash('Insufficient balance', 'danger')
        return redirect(url_for('send_money'))
    
    recipient = User.query.get(recipient_id)
    
    if not recipient:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Recipient not found'})
        flash('Recipient not found', 'danger')
        return redirect(url_for('send_money'))
    
    if recipient.id == current_user.id:
        if is_ajax:
            return jsonify({'success': False, 'message': 'You cannot send money to yourself'})
        flash('You cannot send money to yourself', 'danger')
        return redirect(url_for('send_money'))
    
    # Create transaction for sender (debit)
    sender_transaction = Transaction(
        user_id=current_user.id,
        amount=amount,
        transaction_type='debit',
        description=f'Money sent to {recipient.name}' + (f' - {note}' if note else ''),
        recipient=recipient.name
    )
    
    # Create transaction for recipient (credit)
    recipient_transaction = Transaction(
        user_id=recipient.id,
        amount=amount,
        transaction_type='credit',
        description=f'Money received from {current_user.name}' + (f' - {note}' if note else ''),
        recipient=current_user.name
    )
    
    # Update balances
    current_user.balance -= amount
    recipient.balance += amount
    
    # Commit changes
    db.session.add(sender_transaction)
    db.session.add(recipient_transaction)
    db.session.commit()
    
    success_message = f'₹{amount} sent successfully to {recipient.name}'
    
    if is_ajax:
        return jsonify({
            'success': True, 
            'message': success_message,
            'new_balance': current_user.balance
        })
    
    flash(success_message, 'success')
    return redirect(url_for('dashboard', transaction_success='true', message=success_message))

@app.route('/receive-money')
@login_required
@pin_required
def receive_money():
    """Money receiving interface route"""
    return render_template('receive_money.html')

@app.route('/transactions')
@login_required
@pin_required
def transactions():
    """Transaction history route"""
    all_transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.timestamp.desc()).all()
    return render_template('transactions.html', transactions=all_transactions)

@app.route('/get-latest-transactions')
@login_required
@pin_required
def get_latest_transactions():
    """API endpoint to get latest transactions"""
    latest_transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.timestamp.desc()).limit(5).all()
    
    transactions_data = []
    for transaction in latest_transactions:
        transactions_data.append({
            'id': transaction.id,
            'amount': transaction.amount,
            'transaction_type': transaction.transaction_type,
            'description': transaction.description,
            'recipient': transaction.recipient,
            'timestamp': transaction.timestamp.strftime('%d %b %Y, %I:%M %p')
        })
    
    return jsonify({
        'success': True,
        'transactions': transactions_data,
        'balance': current_user.balance
    })

@app.route('/clear-session')
def clear_session():
    """Route to clear user session"""
    session.clear()
    flash('Session cleared. Please log in again.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    # Use environment variables for production deployment
    debug = os.environ.get('FLASK_DEBUG', 'True') == 'True'
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    app.run(debug=debug, host=host, port=port) 