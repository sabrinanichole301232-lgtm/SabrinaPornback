from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import json
import uuid
from datetime import datetime, timedelta
import hashlib
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# File to store listings data
DATA_FILE = 'listings.json'

def init_data_file():
    """Initialize the data file if it doesn't exist"""
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump([], f)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def verify_payment(gift_card_number, card_name, amount):
    """Simulate payment verification - returns True/False and message"""
    # This is a simulated payment verification
    # In production, you would integrate with actual payment gateway
    
    # Basic validation
    if not gift_card_number or not card_name or not amount:
        return False, "All payment fields are required"
    
    # Simulate gift card format validation
    if len(gift_card_number) < 8:
        return False, "Invalid gift card number format"
    
    # Simulate amount validation
    try:
        amount_float = float(amount)
        if amount_float <= 0:
            return False, "Amount must be positive"
    except ValueError:
        return False, "Invalid amount format"
    
    # For demo purposes, always return success
    # In production, this would call actual payment API
    return True, "Payment verification successful"

@app.route('/api/listings', methods=['GET'])
def get_listings():
    """Get all listings (public endpoint - shows only approved listings by default)"""
    init_data_file()
    with open(DATA_FILE, 'r') as f:
        listings = json.load(f)
    
    # For public view, only show approved listings
    approved_only = request.args.get('approved_only', 'true').lower() == 'true'
    
    if approved_only:
        listings = [l for l in listings if l.get('status') == 'Approved']
    
    return jsonify(listings)

@app.route('/api/listings/all', methods=['GET'])
def get_all_listings():
    """Get all listings (admin only)"""
    auth = request.headers.get('Authorization')
    
    # Simple password check
    if not auth or auth != f"Bearer {hashlib.sha256(app.config['ADMIN_PASSWORD'].encode()).hexdigest()}":
        return jsonify({'error': 'Unauthorized'}), 401
    
    init_data_file()
    with open(DATA_FILE, 'r') as f:
        listings = json.load(f)
    
    return jsonify(listings)

@app.route('/api/listings', methods=['POST'])
def create_listing():
    """Create a new listing"""
    try:
        # Get form data
        data = request.form.to_dict()
        file = request.files.get('image')
        
        # Validate required fields
        required_fields = ['full_name', 'email', 'title', 'description', 
                          'gift_card_number', 'card_name', 'amount']
        
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Verify payment
        payment_valid, payment_message = verify_payment(
            data['gift_card_number'],
            data['card_name'],
            data['amount']
        )
        
        if not payment_valid:
            return jsonify({'error': payment_message}), 400
        
        # Handle file upload
        image_url = None
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            image_url = f"/uploads/{filename}"
        
        # Create listing object
        listing = {
            'id': str(uuid.uuid4()),
            'full_name': data['full_name'],
            'email': data['email'],
            'title': data['title'],
            'description': data['description'],
            'image_url': image_url,
            'payment_details': {
                'gift_card_number': data['gift_card_number'][-4:],  # Only store last 4 digits
                'card_name': data['card_name'],
                'amount': data['amount'],
                'verified': payment_valid
            },
            'status': 'Pending',
            'created_at': datetime.now().isoformat(),
            'verification_date': (datetime.now() + timedelta(days=1)).isoformat()
        }
        
        # Save to file
        init_data_file()
        with open(DATA_FILE, 'r') as f:
            listings = json.load(f)
        
        listings.append(listing)
        
        with open(DATA_FILE, 'w') as f:
            json.dump(listings, f, indent=2)
        
        return jsonify({
            'message': 'Listing created successfully. It will be reviewed within 24 hours.',
            'listing': listing
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/listings/<listing_id>', methods=['PUT'])
def update_listing(listing_id):
    """Update listing status (admin only)"""
    auth = request.headers.get('Authorization')
    
    # Simple password check
    admin_hash = hashlib.sha256(app.config['ADMIN_PASSWORD'].encode()).hexdigest()
    if not auth or auth != f"Bearer {admin_hash}":
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    action = data.get('action')  # approve, reject, delete
    
    init_data_file()
    with open(DATA_FILE, 'r') as f:
        listings = json.load(f)
    
    # Find the listing
    listing_index = None
    for i, listing in enumerate(listings):
        if listing['id'] == listing_id:
            listing_index = i
            break
    
    if listing_index is None:
        return jsonify({'error': 'Listing not found'}), 404
    
    if action == 'delete':
        # Delete the listing
        listing = listings.pop(listing_index)
        
        # Delete associated image if exists
        if listing.get('image_url'):
            image_path = listing['image_url'].replace('/uploads/', '')
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], image_path)
            if os.path.exists(full_path):
                os.remove(full_path)
        
        message = 'Listing deleted successfully'
    else:
        # Update status
        if action == 'approve':
            listings[listing_index]['status'] = 'Approved'
            message = 'Listing approved successfully'
        elif action == 'reject':
            listings[listing_index]['status'] = 'Rejected'
            message = 'Listing rejected successfully'
        else:
            return jsonify({'error': 'Invalid action'}), 400
    
    # Save changes
    with open(DATA_FILE, 'w') as f:
        json.dump(listings, f, indent=2)
    
    return jsonify({'message': message})

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Admin login endpoint"""
    data = request.json
    password = data.get('password')
    
    if password == app.config['ADMIN_PASSWORD']:
        # Generate simple token (in production, use JWT)
        token = hashlib.sha256(f"{password}{datetime.now().isoformat()}".encode()).hexdigest()
        return jsonify({
            'success': True,
            'token': hashlib.sha256(password.encode()).hexdigest(),
            'message': 'Login successful'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Invalid password'
        }), 401

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get listing statistics"""
    init_data_file()
    with open(DATA_FILE, 'r') as f:
        listings = json.load(f)
    
    stats = {
        'total': len(listings),
        'pending': len([l for l in listings if l.get('status') == 'Pending']),
        'approved': len([l for l in listings if l.get('status') == 'Approved']),
        'rejected': len([l for l in listings if l.get('status') == 'Rejected'])
    }
    
    return jsonify(stats)

if __name__ == '__main__':
    init_data_file()
    app.run(debug=True, port=5000)