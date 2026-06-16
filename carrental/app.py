"""
DCA Car Rentals - Complete Flask Application
Full-stack Car Rental Management System with Customer + Admin panels
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta
from functools import wraps
import os
import json
import io
import base64

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dca_secret_2026_secure_key'

import json as _json
@app.template_filter('fromjson')
def fromjson_filter(s):
    try:
        return _json.loads(s)
    except Exception:
        return []

@app.context_processor
def inject_globals():
    from datetime import date
    pending = 0
    if 'user_id' in session and session.get('is_admin'):
        pending = Booking.query.filter_by(payment_status='paid', status='payment_pending').count()
    return dict(today=date.today().isoformat(), pending_payments_count=pending)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///carrental.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

db = SQLAlchemy(app)

# ─────────────────────────────────────────────
# DATABASE MODELS
# ─────────────────────────────────────────────

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(15))
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bookings = db.relationship('Booking', backref='user', lazy=True)
    reviews = db.relationship('Review', backref='user', lazy=True)
    wishlist = db.relationship('Wishlist', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Car(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    model_year = db.Column(db.Integer)
    category = db.Column(db.String(50))  # SUV, Sedan, Hatchback, MPV
    seats = db.Column(db.Integer, default=5)
    fuel_type = db.Column(db.String(20))  # Petrol, Diesel, Electric, CNG
    transmission = db.Column(db.String(20))  # Manual, Automatic
    price_per_day = db.Column(db.Float, nullable=False)
    price_per_km = db.Column(db.Float, default=12.0)
    is_available = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.String(300))
    description = db.Column(db.Text)
    features = db.Column(db.Text)  # JSON string
    color = db.Column(db.String(30))
    mileage = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bookings = db.relationship('Booking', backref='car', lazy=True)
    reviews = db.relationship('Review', backref='car', lazy=True)
    wishlist = db.relationship('Wishlist', backref='car', lazy=True)

    def avg_rating(self):
        if self.reviews:
            return round(sum(r.rating for r in self.reviews) / len(self.reviews), 1)
        return 0

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'brand': self.brand,
            'category': self.category,
            'seats': self.seats,
            'fuel_type': self.fuel_type,
            'transmission': self.transmission,
            'price_per_day': self.price_per_day,
            'is_available': self.is_available,
            'image_url': self.image_url,
            'avg_rating': self.avg_rating(),
            'review_count': len(self.reviews),
            'color': self.color,
            'mileage': self.mileage,
            'model_year': self.model_year
        }


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    car_id = db.Column(db.Integer, db.ForeignKey('car.id'), nullable=False)
    pickup_date = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.Date, nullable=False)
    pickup_location = db.Column(db.String(200), nullable=False)
    drop_location = db.Column(db.String(200), nullable=False)
    pickup_lat = db.Column(db.Float)
    pickup_lng = db.Column(db.Float)
    drop_lat = db.Column(db.Float)
    drop_lng = db.Column(db.Float)
    distance_km = db.Column(db.Float, default=0)
    days = db.Column(db.Integer, nullable=False)
    # Pricing breakdown
    base_day_amount = db.Column(db.Float, default=0)   # days × price_per_day
    base_km_amount  = db.Column(db.Float, default=0)   # km × price_per_km
    driver_amount   = db.Column(db.Float, default=0)   # driver charge if with-driver
    safety_amount   = db.Column(db.Float, default=0)   # female night-safety add-on
    total_amount = db.Column(db.Float, nullable=False)
    gst_amount = db.Column(db.Float, default=0)
    final_amount = db.Column(db.Float, nullable=False)
    # New feature fields
    drive_type = db.Column(db.String(20), default='self')   # 'self' | 'driver'
    gender = db.Column(db.String(10), default='male')       # 'male' | 'female'
    id_proof_type = db.Column(db.String(50))                # ID proof selected during verification
    pickup_time = db.Column(db.String(10))                  # HH:MM – for night-safety check
    night_safety = db.Column(db.Boolean, default=False)     # True if female + after 22:00
    safety_features = db.Column(db.Text)                    # JSON list of chosen safety add-ons
    status = db.Column(db.String(20), default='pending')
    payment_status = db.Column(db.String(20), default='unpaid')
    payment_method = db.Column(db.String(30))
    upi_transaction_id = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    car_id = db.Column(db.Integer, db.ForeignKey('car.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    car_id = db.Column(db.Integer, db.ForeignKey('car.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────────
# AUTH DECORATORS
# ─────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('admin_login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
# CUSTOMER ROUTES
# ─────────────────────────────────────────────

@app.route('/')
def index():
    cars = Car.query.filter_by(is_available=True).limit(6).all()
    featured_cars = [c.to_dict() for c in cars]
    stats = {
        'total_cars': Car.query.count(),
        'total_bookings': Booking.query.count(),
        'happy_customers': User.query.filter_by(is_admin=False).count(),
        'cities': 25
    }
    return render_template('index.html', featured_cars=featured_cars, stats=stats)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')

        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': 'Email already registered'})

        user = User(name=name, email=email, phone=phone)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        session['user_id'] = user.id
        session['user_name'] = user.name
        session['is_admin'] = False
        return jsonify({'success': True, 'message': 'Registration successful!'})

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() or request.form
        email = data.get('email')
        password = data.get('password')

        user = User.query.filter_by(email=email, is_admin=False).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['is_admin'] = False
            return jsonify({'success': True, 'redirect': url_for('cars')})

        return jsonify({'success': False, 'message': 'Invalid email or password'})

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/cars')
def cars():
    all_cars = Car.query.all()
    cars_data = [c.to_dict() for c in all_cars]
    wishlist_ids = []
    if 'user_id' in session:
        wl = Wishlist.query.filter_by(user_id=session['user_id']).all()
        wishlist_ids = [w.car_id for w in wl]
    return render_template('cars.html', cars=cars_data, wishlist_ids=wishlist_ids)


@app.route('/api/cars')
def api_cars():
    query = Car.query
    category = request.args.get('category')
    fuel = request.args.get('fuel')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    seats = request.args.get('seats', type=int)
    search = request.args.get('search', '')
    available_only = request.args.get('available', 'false') == 'true'

    if category and category != 'all':
        query = query.filter_by(category=category)
    if fuel and fuel != 'all':
        query = query.filter_by(fuel_type=fuel)
    if min_price:
        query = query.filter(Car.price_per_day >= min_price)
    if max_price:
        query = query.filter(Car.price_per_day <= max_price)
    if seats:
        query = query.filter(Car.seats >= seats)
    if search:
        query = query.filter(Car.name.ilike(f'%{search}%'))
    if available_only:
        query = query.filter_by(is_available=True)

    cars = query.all()
    return jsonify([c.to_dict() for c in cars])


@app.route('/car/<int:car_id>')
def car_detail(car_id):
    car = Car.query.get_or_404(car_id)
    reviews = Review.query.filter_by(car_id=car_id).order_by(Review.created_at.desc()).all()
    reviews_data = [{
        'user_name': User.query.get(r.user_id).name,
        'rating': r.rating,
        'comment': r.comment,
        'date': r.created_at.strftime('%d %b %Y')
    } for r in reviews]
    in_wishlist = False
    if 'user_id' in session:
        in_wishlist = Wishlist.query.filter_by(user_id=session['user_id'], car_id=car_id).first() is not None
    return render_template('car_detail.html', car=car, reviews=reviews_data, in_wishlist=in_wishlist)


@app.route('/book/<int:car_id>', methods=['GET', 'POST'])
@login_required
def book_car(car_id):
    car = Car.query.get_or_404(car_id)
    if not car.is_available:
        flash('This car is currently not available.', 'warning')
        return redirect(url_for('cars'))

    if request.method == 'POST':
        data = request.get_json()
        pickup_date = datetime.strptime(data['pickup_date'], '%Y-%m-%d').date()
        return_date = datetime.strptime(data['return_date'], '%Y-%m-%d').date()
        days = (return_date - pickup_date).days
        if days < 1:
            return jsonify({'success': False, 'message': 'Return date must be after pickup date'})

        drive_type   = data.get('drive_type', 'self')   # 'self' or 'driver'
        gender       = data.get('gender', 'male')
        id_proof_type = data.get('id_proof_type', '')   # Government ID proof type
        pickup_time  = data.get('pickup_time', '09:00')
        distance_km  = float(data.get('distance_km', 0))
        safety_feats = data.get('safety_features', [])  # list of chosen add-on labels

        # --- Pricing ---
        base_day_amount = car.price_per_day * days
        base_km_amount  = car.price_per_km * distance_km  # per-km on top of per-day

        # Driver surcharge: ₹800/day
        DRIVER_PER_DAY  = 800
        driver_amount   = DRIVER_PER_DAY * days if drive_type == 'driver' else 0

        # Female night-safety add-on (after 22:00): ₹200 flat
        SAFETY_CHARGE   = 200
        hour = int(pickup_time.split(':')[0]) if ':' in pickup_time else 9
        night_safety    = (gender == 'female' and hour >= 22)
        safety_amount   = SAFETY_CHARGE if night_safety else 0

        subtotal = base_day_amount + base_km_amount + driver_amount + safety_amount
        gst      = round(subtotal * 0.18, 2)
        final    = round(subtotal + gst, 2)

        import random
        booking_id = f"DCA{datetime.now().strftime('%Y%m%d')}{random.randint(1000, 9999)}"

        booking = Booking(
            booking_id=booking_id,
            user_id=session['user_id'],
            car_id=car_id,
            pickup_date=pickup_date,
            return_date=return_date,
            pickup_location=data['pickup_location'],
            drop_location=data['drop_location'],
            pickup_lat=data.get('pickup_lat'),
            pickup_lng=data.get('pickup_lng'),
            drop_lat=data.get('drop_lat'),
            drop_lng=data.get('drop_lng'),
            distance_km=distance_km,
            days=days,
            base_day_amount=base_day_amount,
            base_km_amount=base_km_amount,
            driver_amount=driver_amount,
            safety_amount=safety_amount,
            total_amount=subtotal,
            gst_amount=gst,
            final_amount=final,
            drive_type=drive_type,
            gender=gender,
            id_proof_type=id_proof_type,
            pickup_time=pickup_time,
            night_safety=night_safety,
            safety_features=json.dumps(safety_feats),
            status='payment_pending'
        )
        db.session.add(booking)
        db.session.commit()
        return jsonify({'success': True, 'booking_id': booking.id,
                        'redirect': url_for('payment', booking_id=booking.id)})

    return render_template('book_car.html', car=car)


@app.route('/payment/<int:booking_id>')
@login_required
def payment(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != session['user_id']:
        return redirect(url_for('index'))
    car = Car.query.get(booking.car_id)
    return render_template('payment.html', booking=booking, car=car)


@app.route('/api/confirm-payment', methods=['POST'])
@login_required
def confirm_payment():
    data = request.get_json()
    booking = Booking.query.get(data['booking_id'])
    if not booking or booking.user_id != session['user_id']:
        return jsonify({'success': False})

    booking.payment_method = data.get('method', 'UPI')
    booking.upi_transaction_id = data.get('transaction_id', '')
    booking.payment_status = 'paid'
    booking.status = 'payment_pending'
    db.session.commit()
    return jsonify({'success': True, 'redirect': url_for('booking_status', booking_id=booking.id)})


@app.route('/booking-status/<int:booking_id>')
@login_required
def booking_status(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != session['user_id']:
        return redirect(url_for('index'))
    car = Car.query.get(booking.car_id)
    return render_template('booking_status.html', booking=booking, car=car)


@app.route('/my-bookings')
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=session['user_id']).order_by(Booking.created_at.desc()).all()
    bookings_data = []
    for b in bookings:
        car = Car.query.get(b.car_id)
        bookings_data.append({'booking': b, 'car': car})
    return render_template('my_bookings.html', bookings_data=bookings_data)


@app.route('/api/cancel-booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != session['user_id']:
        return jsonify({'success': False})
    if booking.status in ['confirmed', 'completed']:
        return jsonify({'success': False, 'message': 'Cannot cancel confirmed booking'})
    booking.status = 'cancelled'
    db.session.commit()
    return jsonify({'success': True})


@app.route('/wishlist/toggle/<int:car_id>', methods=['POST'])
@login_required
def toggle_wishlist(car_id):
    existing = Wishlist.query.filter_by(user_id=session['user_id'], car_id=car_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'success': True, 'action': 'removed'})
    else:
        wl = Wishlist(user_id=session['user_id'], car_id=car_id)
        db.session.add(wl)
        db.session.commit()
        return jsonify({'success': True, 'action': 'added'})


@app.route('/wishlist')
@login_required
def wishlist():
    items = Wishlist.query.filter_by(user_id=session['user_id']).all()
    cars = [Car.query.get(w.car_id).to_dict() for w in items if Car.query.get(w.car_id)]
    return render_template('wishlist.html', cars=cars)


@app.route('/api/review', methods=['POST'])
@login_required
def add_review():
    data = request.get_json()
    # Check if already reviewed
    existing = Review.query.filter_by(user_id=session['user_id'], car_id=data['car_id']).first()
    if existing:
        existing.rating = data['rating']
        existing.comment = data['comment']
    else:
        review = Review(user_id=session['user_id'], car_id=data['car_id'],
                        rating=data['rating'], comment=data['comment'])
        db.session.add(review)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/invoice/<int:booking_id>')
@login_required
def download_invoice(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != session['user_id'] and not session.get('is_admin'):
        return redirect(url_for('index'))
    car = Car.query.get(booking.car_id)
    user = User.query.get(booking.user_id)
    return render_template('invoice.html', booking=booking, car=car, user=user)


@app.route('/profile')
@login_required
def profile():
    user = User.query.get(session['user_id'])
    bookings_count = Booking.query.filter_by(user_id=user.id).count()
    reviews_count = Review.query.filter_by(user_id=user.id).count()
    return render_template('profile.html', user=user, bookings_count=bookings_count, reviews_count=reviews_count)


# ─────────────────────────────────────────────
# STATIC INFO PAGES
# ─────────────────────────────────────────────

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/api/contact', methods=['POST'])
def contact_submit():
    """Handle contact form submission"""
    data = request.get_json()
    # In production, send email. For now, store/acknowledge.
    return jsonify({'success': True, 'message': 'Message received! Dhanush will reply within 24 hours.'})


# ─────────────────────────────────────────────
# ADMIN ROUTES
# ─────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        data = request.get_json() or request.form
        email = data.get('email')
        password = data.get('password')
        user = User.query.filter_by(email=email, is_admin=True).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['is_admin'] = True
            return jsonify({'success': True, 'redirect': url_for('admin_dashboard')})
        return jsonify({'success': False, 'message': 'Invalid admin credentials'})
    return render_template('admin_login.html')


@app.route('/admin')
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    # Stats
    total_users = User.query.filter_by(is_admin=False).count()
    total_cars = Car.query.count()
    total_bookings = Booking.query.count()
    confirmed_bookings = Booking.query.filter_by(status='confirmed').count()
    pending_payments = Booking.query.filter_by(payment_status='paid', status='payment_pending').count()
    total_revenue = db.session.query(db.func.sum(Booking.final_amount)).filter(
        Booking.status.in_(['confirmed', 'completed'])
    ).scalar() or 0

    # Monthly revenue (last 6 months)
    monthly_data = []
    for i in range(5, -1, -1):
        month_start = date.today().replace(day=1) - timedelta(days=30*i)
        month_end = (month_start.replace(month=month_start.month % 12 + 1, day=1)
                     if month_start.month < 12 else month_start.replace(year=month_start.year+1, month=1, day=1))
        rev = db.session.query(db.func.sum(Booking.final_amount)).filter(
            Booking.created_at >= month_start,
            Booking.created_at < month_end,
            Booking.status.in_(['confirmed', 'completed'])
        ).scalar() or 0
        monthly_data.append({'month': month_start.strftime('%b'), 'revenue': float(rev)})

    # Recent bookings
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(8).all()
    recent_data = []
    for b in recent_bookings:
        user = User.query.get(b.user_id)
        car = Car.query.get(b.car_id)
        recent_data.append({'booking': b, 'user': user, 'car': car})

    return render_template('admin_dashboard.html',
        total_users=total_users, total_cars=total_cars,
        total_bookings=total_bookings, confirmed_bookings=confirmed_bookings,
        pending_payments=pending_payments, total_revenue=total_revenue,
        monthly_data=json.dumps(monthly_data), recent_data=recent_data)


@app.route('/admin/cars')
@admin_required
def admin_cars():
    cars = Car.query.all()
    return render_template('admin_cars.html', cars=cars)


@app.route('/admin/car/add', methods=['GET', 'POST'])
@admin_required
def admin_add_car():
    if request.method == 'POST':
        data = request.form
        features_list = request.form.getlist('features')

        car = Car(
            name=data['name'],
            brand=data['brand'],
            model_year=int(data.get('model_year', 2023)),
            category=data['category'],
            seats=int(data['seats']),
            fuel_type=data['fuel_type'],
            transmission=data['transmission'],
            price_per_day=float(data['price_per_day']),
            price_per_km=float(data.get('price_per_km', 12)),
            image_url=data.get('image_url', ''),
            description=data.get('description', ''),
            features=json.dumps(features_list),
            color=data.get('color', ''),
            mileage=data.get('mileage', ''),
            is_available=data.get('is_available') == 'on'
        )
        db.session.add(car)
        db.session.commit()
        flash('Car added successfully!', 'success')
        return redirect(url_for('admin_cars'))

    return render_template('admin_car_form.html', car=None)


@app.route('/admin/car/edit/<int:car_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_car(car_id):
    car = Car.query.get_or_404(car_id)
    if request.method == 'POST':
        data = request.form
        car.name = data['name']
        car.brand = data['brand']
        car.model_year = int(data.get('model_year', 2023))
        car.category = data['category']
        car.seats = int(data['seats'])
        car.fuel_type = data['fuel_type']
        car.transmission = data['transmission']
        car.price_per_day = float(data['price_per_day'])
        car.price_per_km = float(data.get('price_per_km', 12))
        car.image_url = data.get('image_url', car.image_url)
        car.description = data.get('description', '')
        car.color = data.get('color', '')
        car.mileage = data.get('mileage', '')
        car.is_available = data.get('is_available') == 'on'
        db.session.commit()
        flash('Car updated successfully!', 'success')
        return redirect(url_for('admin_cars'))

    return render_template('admin_car_form.html', car=car)


@app.route('/admin/car/delete/<int:car_id>', methods=['POST'])
@admin_required
def admin_delete_car(car_id):
    car = Car.query.get_or_404(car_id)
    db.session.delete(car)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/admin/car/toggle/<int:car_id>', methods=['POST'])
@admin_required
def admin_toggle_car(car_id):
    car = Car.query.get_or_404(car_id)
    car.is_available = not car.is_available
    db.session.commit()
    return jsonify({'success': True, 'is_available': car.is_available})


@app.route('/admin/bookings')
@admin_required
def admin_bookings():
    status_filter = request.args.get('status', 'all')
    query = Booking.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    bookings = query.order_by(Booking.created_at.desc()).all()
    bookings_data = []
    for b in bookings:
        user = User.query.get(b.user_id)
        car = Car.query.get(b.car_id)
        bookings_data.append({'booking': b, 'user': user, 'car': car})
    return render_template('admin_bookings.html', bookings_data=bookings_data, status_filter=status_filter)


@app.route('/admin/payment/confirm/<int:booking_id>', methods=['POST'])
@admin_required
def admin_confirm_payment(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    booking.payment_status = 'confirmed'
    booking.status = 'confirmed'
    db.session.commit()
    return jsonify({'success': True})


@app.route('/admin/payment/reject/<int:booking_id>', methods=['POST'])
@admin_required
def admin_reject_payment(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    booking.payment_status = 'rejected'
    booking.status = 'rejected'
    db.session.commit()
    return jsonify({'success': True})


@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.filter_by(is_admin=False).order_by(User.created_at.desc()).all()
    users_data = []
    for u in users:
        bookings = Booking.query.filter_by(user_id=u.id).count()
        users_data.append({'user': u, 'bookings': bookings})
    return render_template('admin_users.html', users_data=users_data)


@app.route('/admin/payments')
@admin_required
def admin_payments():
    pending = Booking.query.filter_by(payment_status='paid', status='payment_pending').order_by(Booking.created_at.desc()).all()
    all_payments = Booking.query.filter(Booking.payment_status != 'unpaid').order_by(Booking.created_at.desc()).all()
    pending_data = [{'booking': b, 'user': User.query.get(b.user_id), 'car': Car.query.get(b.car_id)} for b in pending]
    all_data = [{'booking': b, 'user': User.query.get(b.user_id), 'car': Car.query.get(b.car_id)} for b in all_payments]
    return render_template('admin_payments.html', pending_data=pending_data, all_data=all_data)


# ─────────────────────────────────────────────
# DATABASE INITIALIZATION
# ─────────────────────────────────────────────

def init_db():
    with app.app_context():
        db.create_all()

        # Create admin user
        if not User.query.filter_by(is_admin=True).first():
            admin = User(name='Admin', email='admin@dcacarrentals.com', phone='9999999999', is_admin=True)
            admin.set_password('Admin@123')
            db.session.add(admin)

        # Seed Indian cars
        if Car.query.count() == 0:
            indian_cars = [
                {
                    'name': 'Mahindra Thar', 'brand': 'Mahindra', 'model_year': 2023,
                    'category': 'SUV', 'seats': 4, 'fuel_type': 'Diesel',
                    'transmission': 'Manual', 'price_per_day': 3500, 'price_per_km': 18,
                    'image_url': 'https://imgd.aeplcdn.com/664x374/n/cw/ec/40087/thar-exterior-right-front-three-quarter-2.jpeg?isig=0&q=80',
                    'color': 'Napoli Black', 'mileage': '15.2 kmpl',
                    'description': 'The iconic Mahindra Thar is a legendary off-road SUV. Perfect for adventure seekers who want to explore rugged terrain with style and confidence.',
                    'features': json.dumps(['4WD', 'Off-road Mode', 'Touchscreen', 'Convertible Roof', 'Hill Descent Control'])
                },
                {
                    'name': 'Tata Nexon', 'brand': 'Tata', 'model_year': 2026,
                    'category': 'SUV', 'seats': 5, 'fuel_type': 'Petrol',
                    'transmission': 'Automatic', 'price_per_day': 2200, 'price_per_km': 12,
                    'image_url': 'https://imgd.aeplcdn.com/664x374/n/cw/ec/141115/nexon-exterior-right-front-three-quarter-4.jpeg?isig=0&q=80',
                    'color': 'Flame Red', 'mileage': '17.4 kmpl',
                    'description': 'The Tata Nexon is India\'s safest compact SUV with a 5-star Global NCAP rating. Modern, feature-packed and perfect for city and highway drives.',
                    'features': json.dumps(['5-Star Safety', 'Sunroof', 'TPMS', 'Cruise Control', 'Apple CarPlay'])
                },
                {
                    'name': 'Maruti Swift', 'brand': 'Maruti Suzuki', 'model_year': 2026,
                    'category': 'Hatchback', 'seats': 5, 'fuel_type': 'Petrol',
                    'transmission': 'Manual', 'price_per_day': 1200, 'price_per_km': 8,
                    'image_url': 'https://imgd.aeplcdn.com/664x374/n/cw/ec/159087/swift-exterior-right-front-three-quarter-3.jpeg?isig=0&q=80',
                    'color': 'Speedy Blue', 'mileage': '23.2 kmpl',
                    'description': 'India\'s most loved hatchback. The Maruti Swift offers exceptional fuel efficiency, spirited performance and a fun driving experience for everyday use.',
                    'features': json.dumps(['SmartPlay Pro', 'Auto AC', 'Rear Parking Camera', 'ESP', 'Hill Hold'])
                },
                {
                    'name': 'Hyundai Creta', 'brand': 'Hyundai', 'model_year': 2026,
                    'category': 'SUV', 'seats': 5, 'fuel_type': 'Diesel',
                    'transmission': 'Automatic', 'price_per_day': 2800, 'price_per_km': 14,
                    'image_url': 'https://imgd.aeplcdn.com/664x374/n/cw/ec/106815/creta-exterior-right-front-three-quarter-2.jpeg?isig=0&q=80',
                    'color': 'Abyss Black Pearl', 'mileage': '18.4 kmpl',
                    'description': 'The Hyundai Creta is India\'s best-selling SUV. With its premium features, comfortable cabin and powerful performance, it\'s perfect for long journeys.',
                    'features': json.dumps(['Panoramic Sunroof', 'Ventilated Seats', 'ADAS', '360-degree Camera', 'Bose Sound'])
                },
                {
                    'name': 'Toyota Innova Crysta', 'brand': 'Toyota', 'model_year': 2023,
                    'category': 'MPV', 'seats': 7, 'fuel_type': 'Diesel',
                    'transmission': 'Automatic', 'price_per_day': 4200, 'price_per_km': 20,
                    'image_url': 'https://imgd.aeplcdn.com/664x374/n/cw/ec/45701/crysta-exterior-right-front-three-quarter-3.jpeg?isig=0&q=80',
                    'color': 'Super White', 'mileage': '11.6 kmpl',
                    'description': 'The Toyota Innova Crysta is India\'s premium MPV and the most trusted family vehicle. Spacious 7-seater with exceptional comfort for long-distance travel.',
                    'features': json.dumps(['Captain Seats', 'Dual AC', 'Auto Sliding Door', 'Toyota Safety Sense', 'Ambient Lighting'])
                },
                {
                    'name': 'Kia Seltos', 'brand': 'Kia', 'model_year': 2026,
                    'category': 'SUV', 'seats': 5, 'fuel_type': 'Petrol',
                    'transmission': 'Automatic', 'price_per_day': 2600, 'price_per_km': 13,
                    'image_url': 'https://imgd.aeplcdn.com/664x374/n/cw/ec/141115/seltos-exterior-right-front-three-quarter-4.jpeg?isig=0&q=80',
                    'color': 'Imperial Blue', 'mileage': '16.5 kmpl',
                    'description': 'The Kia Seltos combines bold styling with advanced technology. A premium SUV experience at a competitive price with segment-first features.',
                    'features': json.dumps(['10.25" Touchscreen', 'HUD', 'ADAS Level 2', 'Bose Premium Sound', 'OTA Updates'])
                },
            ]

            for car_data in indian_cars:
                car = Car(
                    name=car_data['name'], brand=car_data['brand'],
                    model_year=car_data['model_year'], category=car_data['category'],
                    seats=car_data['seats'], fuel_type=car_data['fuel_type'],
                    transmission=car_data['transmission'], price_per_day=car_data['price_per_day'],
                    price_per_km=car_data['price_per_km'], image_url=car_data['image_url'],
                    color=car_data['color'], mileage=car_data['mileage'],
                    description=car_data['description'], features=car_data['features'],
                    is_available=True
                )
                db.session.add(car)

        db.session.commit()
        print("✅ Database initialized successfully!")
        print("📧 Admin Login: admin@dcacarrentals.com / Admin@123")


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
