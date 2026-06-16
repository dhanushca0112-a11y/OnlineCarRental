# 🚗 DriveIndia - Car Rental Management System

A full-stack car rental web application with Customer + Admin panels.

## 🚀 Quick Start

```bash
# 1. Navigate to project folder
cd carrental

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py
```

Open: **http://localhost:5000**

---

## 🔑 Login Credentials

### Admin Panel
- URL: http://localhost:5000/admin/login
- Email: `admin@driveindia.com`
- Password: `Admin@123`

### Customer
- Register at: http://localhost:5000/register
- Or use any email/password you register with

---

## 📋 Features

### Customer Panel
- ✅ Register / Login
- ✅ Browse 6 Indian cars (Thar, Nexon, Swift, Creta, Innova, Seltos)
- ✅ Search & filter (category, fuel, price, seats, availability)
- ✅ Car detail with Leaflet.js map + route distance
- ✅ Multi-step booking (dates, locations, price calc)
- ✅ UPI payment demo with QR code
- ✅ Booking status tracker
- ✅ Download invoice (print-ready)
- ✅ Wishlist (heart toggle)
- ✅ My Bookings with cancel
- ✅ Ratings & Reviews
- ✅ Profile page
- ✅ Dark / Light mode

### Admin Panel
- ✅ Secure admin login
- ✅ Dashboard with revenue charts (Chart.js)
- ✅ Fleet management (Add / Edit / Delete cars)
- ✅ Toggle car availability
- ✅ View & manage all bookings
- ✅ Payment verification (Confirm / Reject)
- ✅ Customer management
- ✅ Pending payment alerts

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python Flask |
| Database | SQLite (via SQLAlchemy) |
| Frontend | HTML5 + CSS3 + Vanilla JS |
| Maps | Leaflet.js + OpenStreetMap |
| Charts | Chart.js |
| Icons | Font Awesome 6 |
| Fonts | Syne + DM Sans (Google Fonts) |

---

## 📁 Project Structure

```
carrental/
├── app.py              # Main Flask app + all routes
├── requirements.txt    # Dependencies
├── instance/
│   └── carrental.db    # SQLite database (auto-created)
├── static/
│   └── css/
│       └── main.css    # Shared styles
└── templates/
    ├── base.html           # Customer base layout
    ├── index.html          # Hero homepage
    ├── cars.html           # Browse cars with filters
    ├── car_detail.html     # Car detail + booking + map
    ├── payment.html        # UPI/Card payment
    ├── booking_status.html # Booking tracker
    ├── my_bookings.html    # Customer booking history
    ├── invoice.html        # Printable invoice
    ├── wishlist.html       # Saved cars
    ├── profile.html        # User profile
    ├── login.html          # Customer login
    ├── register.html       # Registration
    ├── admin_base.html     # Admin sidebar layout
    ├── admin_login.html    # Admin login
    ├── admin_dashboard.html # Dashboard + charts
    ├── admin_cars.html     # Fleet management
    ├── admin_car_form.html # Add/Edit car form
    ├── admin_bookings.html # All bookings
    ├── admin_payments.html # Payment verification
    └── admin_users.html    # Customer list
```

---

## 🛡️ Security Features

- Password hashing (Werkzeug)
- Session-based authentication
- Admin route protection decorator
- Customer route protection decorator
- CSRF protection via Flask session secret

---

## 🎨 UI Highlights

- Premium dark/light glassmorphism design
- Smooth hover animations
- Responsive mobile + desktop
- Animated counter stats
- Interactive Leaflet maps with routing
- Chart.js revenue & status charts
- UPI QR code payment demo
- Progress tracker for bookings

---

## 💡 Pre-loaded Cars

1. **Mahindra Thar** - SUV, Diesel, ₹3,500/day
2. **Tata Nexon** - SUV, Petrol, ₹2,200/day  
3. **Maruti Swift** - Hatchback, Petrol, ₹1,200/day
4. **Hyundai Creta** - SUV, Diesel, ₹2,800/day
5. **Toyota Innova Crysta** - MPV, Diesel, ₹4,200/day
6. **Kia Seltos** - SUV, Petrol, ₹2,600/day
