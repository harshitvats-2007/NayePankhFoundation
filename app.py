"""
NayePankh Foundation - Multi-Page Flask Web Application
A youth-led nonprofit organization dedicated to uplifting underprivileged communities.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, Response, session
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import re
from datetime import datetime
import json
import os
import sqlite3
import io
import csv
import uuid

app = Flask(__name__)
app.secret_key = 'nayepankh_foundation_2024'
DB_FILE = 'nayepankh.db'

# ─── Security Setup ─────────────────────────────────────────────────────────

# Rate Limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Admin Credentials (in production use env vars or DB)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = generate_password_hash("admin123")

# Email validation regex
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('logged_in') is not True:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ─── Database Setup ─────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with app.app_context():
        conn = get_db()
        cursor = conn.cursor()
        
        # Volunteers Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS volunteers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                city TEXT,
                interest TEXT,
                message TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Contacts Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                subject TEXT,
                message TEXT NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Newsletter Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS newsletter (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Donations Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS donations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                certificate_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                amount REAL NOT NULL,
                cause TEXT,
                message TEXT,
                donated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()

# Initialize DB
init_db()

# ─── Mock Data for Blog ─────────────────────────────────────────────────────
BLOG_POSTS = [
    {
        'id': 1,
        'slug': '5000-children-and-counting',
        'title': '5,000 Children and Counting: The Shiksha for All Impact Report',
        'content': '''<p>Our education program has now reached 5,000 underprivileged children across 30+ cities.</p>
        <p>This journey started with a small group of volunteers teaching in makeshift classrooms. Today, we have structured learning centers equipped with digital tools and a comprehensive curriculum.</p>
        <h3>What We Achieved</h3>
        <ul>
            <li>5,000+ students enrolled</li>
            <li>95% attendance rate maintained</li>
            <li>30+ cities covered</li>
        </ul>
        <p>We are incredibly proud of our volunteer teachers who have made this possible.</p>''',
        'image': 'education_program.png',
        'date': 'May 28, 2026',
        'category': 'Education',
        'author': 'Education Team'
    },
    {
        'id': 2,
        'slug': 'breaking-taboos-menstrual-hygiene',
        'title': 'Breaking Taboos: How Our Menstrual Hygiene Campaign is Changing Rural India',
        'content': '''<p>From distributing 15,000+ sanitary kits to conducting village-level awareness sessions, our Swasthya Initiative is empowering women and girls.</p>
        <p>Menstruation remains a taboo topic in many rural parts of India. We set out to change this narrative by combining education with access to sanitary products.</p>
        <p>Our volunteers conduct safe-space workshops where women can ask questions without hesitation.</p>''',
        'image': 'health_hygiene.png',
        'date': 'May 15, 2026',
        'category': 'Health',
        'author': 'Health Team'
    },
    {
        'id': 3,
        'slug': 'paws-and-care-25000-animals',
        'title': 'Paws & Care: 25,000 Animals Fed and the Stories Behind the Numbers',
        'content': '''<p>Every stray animal we feed has a story. Meet some of the furry friends whose lives have been transformed by our animal welfare program.</p>
        <p>Through our dedicated volunteer network, we have set up permanent feeding stations across 15 cities, ensuring that street dogs and cats get at least one nutritious meal a day.</p>''',
        'image': 'animal_welfare.png',
        'date': 'May 2, 2026',
        'category': 'Animals',
        'author': 'Animal Welfare Team'
    },
    {
        'id': 4,
        'slug': 'annapurna-drive-1-lakh-meals',
        'title': 'Annapurna Drive: Serving 1 Lakh Meals and the Volunteers Who Made It Happen',
        'content': '''<p>Behind every meal served is a volunteer's dedication. A deep dive into our food distribution program and the communities it serves.</p>
        <p>Hunger is a solvable problem if we work together. By partnering with local kitchens and redirecting excess food, we've successfully provided over 1,00,000 meals to those in need.</p>''',
        'image': 'food_distribution.png',
        'date': 'April 20, 2026',
        'category': 'Nutrition',
        'author': 'Nutrition Team'
    },
    {
        'id': 5,
        'slug': 'volunteer-spotlight-college-students',
        'title': 'Volunteer Spotlight: Meet the College Students Leading Change in Their Cities',
        'content': '''<p>Inspiring stories from our volunteer chapter leaders across India — how they balance academics with social impact.</p>
        <p>We are a youth-led organization, and our strength lies in the passion of young people. In this post, we highlight three exceptional college students who manage entire city chapters.</p>''',
        'image': 'volunteers_helping.png',
        'date': 'April 8, 2026',
        'category': 'Community',
        'author': 'Community Team'
    },
    {
        'id': 6,
        'slug': 'nayepankh-turns-5',
        'title': 'NayePankh Turns 5: Reflections, Gratitude, and the Road Ahead',
        'content': '''<p>As we celebrate five years of impact, our founders share their reflections on the journey and the ambitious goals for the future.</p>
        <p>It feels like just yesterday we were a handful of high schoolers trying to help out during the pandemic. Now, we're a national movement. Thank you to everyone who believed in us.</p>''',
        'image': 'team_group.png',
        'date': 'March 25, 2026',
        'category': 'Milestone',
        'author': 'Founders'
    }
]

# ─── Routes ─────────────────────────────────────────────────────────────────

@app.route('/')
def home():
    return render_template('index.html', year=datetime.now().year)

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['logged_in'] = True
            return redirect(request.args.get('next') or url_for('admin_dashboard'))
        return render_template('login.html', error='Invalid credentials', year=datetime.now().year)
    return render_template('login.html', year=datetime.now().year)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('home'))

@app.route('/about')
def about():
    return render_template('about.html', year=datetime.now().year)

@app.route('/programs')
def programs():
    return render_template('programs.html', year=datetime.now().year)

@app.route('/gallery')
def gallery():
    return render_template('gallery.html', year=datetime.now().year)

@app.route('/donate')
def donate():
    return render_template('donate.html', year=datetime.now().year)

@app.route('/volunteer')
def volunteer():
    return render_template('volunteer.html', year=datetime.now().year)

@app.route('/contact')
def contact():
    return render_template('contact.html', year=datetime.now().year)

@app.route('/blog')
def blog():
    return render_template('blog.html', posts=BLOG_POSTS, year=datetime.now().year)

@app.route('/blog/<slug>')
def blog_detail(slug):
    post = next((p for p in BLOG_POSTS if p['slug'] == slug), None)
    if not post:
        return render_template('404.html', year=datetime.now().year), 404
    # Simple related posts logic (just take 3 other posts)
    related = [p for p in BLOG_POSTS if p['slug'] != slug][:3]
    return render_template('blog_detail.html', post=post, related=related, year=datetime.now().year)

@app.route('/success/<type>')
def success(type):
    valid_types = ['donation', 'volunteer', 'contact', 'newsletter']
    if type not in valid_types:
        return redirect(url_for('home'))
    return render_template('success.html', type=type, request_args=request.args, year=datetime.now().year)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', year=datetime.now().year), 404

# ─── Admin Dashboard Routes ─────────────────────────────────────────────────

@app.route('/admin')
@login_required
def admin_dashboard():
    # In a real app, you would have authentication here
    conn = get_db()
    cursor = conn.cursor()
    
    volunteers = cursor.execute('SELECT * FROM volunteers ORDER BY registered_at DESC').fetchall()
    donations = cursor.execute('SELECT * FROM donations ORDER BY donated_at DESC').fetchall()
    contacts = cursor.execute('SELECT * FROM contacts ORDER BY submitted_at DESC').fetchall()
    newsletter = cursor.execute('SELECT * FROM newsletter ORDER BY subscribed_at DESC').fetchall()
    
    stats = {
        'total_volunteers': len(volunteers),
        'total_donations': sum(d['amount'] for d in donations) if donations else 0,
        'total_contacts': len(contacts),
        'total_subscribers': len(newsletter)
    }
    
    conn.close()
    return render_template('admin.html', 
                          volunteers=volunteers, 
                          donations=donations, 
                          contacts=contacts, 
                          newsletter=newsletter, 
                          stats=stats,
                          year=datetime.now().year)

@app.route('/admin/export/<table>')
@login_required
def export_csv(table):
    allowed_tables = ['volunteers', 'donations', 'contacts', 'newsletter']
    if table not in allowed_tables:
        return "Invalid table", 400
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    
    if not rows:
        return "No data to export", 404
        
    # Get column names
    headers = [description[0] for description in cursor.description]
    
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(headers)
    cw.writerows(rows)
    
    output = si.getvalue()
    conn.close()
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={table}_export.csv"}
    )

# ─── API Endpoints ──────────────────────────────────────────────────────────

@app.route('/api/volunteer', methods=['POST'])
@limiter.limit("5 per minute")
def register_volunteer():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data received'}), 400
        
    email = data.get('email', '')
    if not EMAIL_REGEX.match(email):
        return jsonify({'success': False, 'message': 'Invalid email address'}), 400
        
    if len(data.get('message', '')) > 1000:
        return jsonify({'success': False, 'message': 'Message too long (max 1000 characters)'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO volunteers (name, email, phone, city, interest, message)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data.get('name', ''),
            data.get('email', ''),
            data.get('phone', ''),
            data.get('city', ''),
            data.get('interest', ''),
            data.get('message', '')
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': 'Database error'}), 500
    finally:
        conn.close()
        
    return jsonify({'success': True, 'message': 'Thank you for volunteering! We will contact you soon.'})

@app.route('/api/contact', methods=['POST'])
@limiter.limit("5 per minute")
def submit_contact():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data received'}), 400
        
    email = data.get('email', '')
    if not EMAIL_REGEX.match(email):
        return jsonify({'success': False, 'message': 'Invalid email address'}), 400
        
    if len(data.get('message', '')) > 2000:
        return jsonify({'success': False, 'message': 'Message too long (max 2000 characters)'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO contacts (name, email, subject, message)
            VALUES (?, ?, ?, ?)
        ''', (
            data.get('name', ''),
            data.get('email', ''),
            data.get('subject', ''),
            data.get('message', '')
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': 'Database error'}), 500
    finally:
        conn.close()
        
    return jsonify({'success': True, 'message': 'Message received! We will get back to you shortly.'})

@app.route('/api/newsletter', methods=['POST'])
@limiter.limit("10 per minute")
def subscribe_newsletter():
    data = request.get_json()
    email = data.get('email', '')
    if not email:
        return jsonify({'success': False, 'message': 'Email is required'}), 400
        
    if not EMAIL_REGEX.match(email):
        return jsonify({'success': False, 'message': 'Invalid email address'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO newsletter (email) VALUES (?)', (email,))
        conn.commit()
    except sqlite3.IntegrityError:
        # Email already exists
        pass
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': 'Database error'}), 500
    finally:
        conn.close()
        
    return jsonify({'success': True, 'message': 'Successfully subscribed to our newsletter!'})

@app.route('/api/donate', methods=['POST'])
@limiter.limit("5 per minute")
def process_donation():
    data = request.get_json()
    
    email = data.get('email', '')
    if email and not EMAIL_REGEX.match(email):
        return jsonify({'success': False, 'message': 'Invalid email address'}), 400
    
    # Generate a unique certificate ID for 80G
    # Format: NP-80G-YYYY-XXXX
    cert_id = f"NP-80G-{datetime.now().year}-{str(uuid.uuid4())[:8].upper()}"
    
    amount = float(data.get('amount', 0))
    name = data.get('name', 'Anonymous')
    cause = data.get('cause', 'General')
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO donations (certificate_id, name, email, amount, cause, message)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            cert_id,
            name,
            data.get('email', ''),
            amount,
            cause,
            data.get('message', '')
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': 'Database error'}), 500
    finally:
        conn.close()
        
    return jsonify({
        'success': True, 
        'message': f'Thank you for your generous donation of ₹{amount}!',
        'certificate_id': cert_id
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
