from flask import Flask, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from io import BytesIO
import segno

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///students.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admission_number = db.Column(db.String(20), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    department = db.Column(db.String(50))
    year_of_study = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    internet_usage_minutes = db.Column(db.Integer, default=0)
    hotspot_access = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class HotspotSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    end_time = db.Column(db.DateTime)
    data_used_mb = db.Column(db.Integer, default=0)

class HotspotRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    request_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    approved_by = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=True)
    approval_time = db.Column(db.DateTime, nullable=True)

class HotspotConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ssid = db.Column(db.String(50), default="SchoolHotspot")
    password = db.Column(db.String(50), default="school123")
    is_active = db.Column(db.Boolean, default=True)

def initialize_database():
    with app.app_context():
        try:
            # Drop all existing tables
            db.drop_all()
            
            # Create all tables with current schema
            db.create_all()
            
            # Create admin account
            admin = Student(
                admission_number="ADM001",
                full_name="Admin User",
                email="admin@school.edu",
                department="Administration",
                year_of_study=0,
                hotspot_access=True
            )
            admin.set_password("admin123")
            db.session.add(admin)
            
            # Create sample student
            student = Student(
                admission_number="STD001",
                full_name="John Doe",
                email="student@school.edu",
                department="Computer Science",
                year_of_study=2,
                hotspot_access=False
            )
            student.set_password("password123")
            db.session.add(student)
            
            # Create default hotspot config
            config = HotspotConfig()
            db.session.add(config)
            
            db.session.commit()
            print("Database initialized successfully")
        except Exception as e:
            db.session.rollback()
            print(f"Error initializing database: {str(e)}")
            raise

# HTML Generation Functions
def generate_html(title, content, messages=None, is_logged_in=False):
    css = """
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 0;
            background-color: #f4f4f4;
            color: #333;
        }
        .container {
            width: 80%;
            margin: auto;
            overflow: hidden;
            padding: 20px;
        }
        header {
            background: #35424a;
            color: white;
            padding: 20px 0;
            min-height: 70px;
            border-bottom: #e8491d 3px solid;
        }
        header a {
            color: #ffffff;
            text-decoration: none;
            text-transform: uppercase;
            font-size: 16px;
        }
        header ul {
            padding: 0;
            list-style: none;
        }
        header li {
            display: inline;
            padding: 0 20px 0 20px;
        }
        .alert {
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
        }
        .alert-success {
            background-color: #d4edda;
            color: #155724;
        }
        .alert-danger {
            background-color: #f8d7da;
            color: #721c24;
        }
        .alert-info {
            background-color: #d1ecf1;
            color: #0c5460;
        }
        form {
            background: #ffffff;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        form label {
            display: block;
            margin: 10px 0 5px;
        }
        form input[type="text"],
        form input[type="password"],
        form input[type="email"],
        form input[type="number"],
        form select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        form button {
            display: inline-block;
            background: #e8491d;
            color: #fff;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        form button:hover {
            background: #35424a;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        table, th, td {
            border: 1px solid #ddd;
        }
        th, td {
            padding: 12px;
            text-align: left;
        }
        th {
            background-color: #35424a;
            color: white;
        }
        tr:nth-child(even) {
            background-color: #f2f2f2;
        }
        .internet-frame {
            width: 100%;
            height: 600px;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin: 20px 0;
        }
        .nav-links {
            margin: 20px 0;
        }
        .nav-links a {
            margin-right: 15px;
            color: #e8491d;
            text-decoration: none;
        }
        .nav-links a:hover {
            text-decoration: underline;
        }
        .button {
            display: inline-block;
            background: #e8491d;
            color: white;
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 5px;
            margin-top: 20px;
        }
        .button:hover {
            background: #35424a;
        }
        .student-info {
            background: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .personal-info, .internet-usage {
            background: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .qr-code {
            text-align: center;
            margin: 20px 0;
        }
        .qr-code img {
            max-width: 200px;
            height: auto;
        }
    </style>
    """
    
    nav_links = """
    <li><a href="/">Home</a></li>
    """ + ("""
    <li><a href="/dashboard">Dashboard</a></li>
    <li><a href="/profile">Profile</a></li>
    <li><a href="/hotspot">Hotspot</a></li>
    <li><a href="/request_hotspot">Request Hotspot</a></li>
    <li><a href="/connect_hotspot">Connect Instructions</a></li>
    <li><a href="/logout">Logout</a></li>
    """ if is_logged_in else """
    <li><a href="/login">Login</a></li>
    """)
    
    message_html = ""
    if messages:
        for category, message in messages:
            message_html += f'<div class="alert alert-{category}">{message}</div>'
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        {css}
    </head>
    <body>
        <header>
            <div class="container">
                <h1>Student Hotspot Access Portal</h1>
                <nav>
                    <ul>
                        {nav_links}
                    </ul>
                </nav>
            </div>
        </header>
        
        <div class="container">
            {message_html}
            {content}
        </div>
    </body>
    </html>
    """

# Routes
@app.route('/')
def landing_page():
    content = """
    <h2>Welcome to Student Hotspot Portal</h2>
    <p>Please login to access the hotspot and your student details</p>
    <a href="/login" class="button">Login</a>
    """
    messages = []
    if '_flashes' in session:
        messages = session['_flashes']
    return generate_html("Welcome", content, messages)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        admission_number = request.form['admission_number']
        password = request.form['password']
        
        student = Student.query.filter_by(admission_number=admission_number).first()
        
        if student and student.check_password(password):
            session['student_id'] = student.id
            session['admission_number'] = student.admission_number
            student.last_login = datetime.datetime.utcnow()
            db.session.commit()
            
            new_session = HotspotSession(student_id=student.id)
            db.session.add(new_session)
            db.session.commit()
            session['hotspot_session_id'] = new_session.id
            
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid admission number or password', 'danger')
    
    content = """
    <h2>Student Login</h2>
    <form method="POST">
        <label for="admission_number">Admission Number:</label>
        <input type="text" id="admission_number" name="admission_number" required>
        
        <label for="password">Password:</label>
        <input type="password" id="password" name="password" required>
        
        <button type="submit">Login</button>
    </form>
    """
    messages = []
    if '_flashes' in session:
        messages = session['_flashes']
    return generate_html("Login", content, messages)

@app.route('/logout')
def logout():
    if 'hotspot_session_id' in session:
        hotspot_session = HotspotSession.query.get(session['hotspot_session_id'])
        if hotspot_session:
            hotspot_session.end_time = datetime.datetime.utcnow()
            duration = (hotspot_session.end_time - hotspot_session.start_time).total_seconds() / 60
            student = Student.query.get(session['student_id'])
            student.internet_usage_minutes += int(duration)
            db.session.commit()
    
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('landing_page'))

@app.route('/dashboard')
def dashboard():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    
    student = Student.query.get(session['student_id'])
    
    last_login = student.last_login.strftime('%Y-%m-%d %H:%M:%S') if student.last_login else 'Never'
    
    content = f"""
    <h2>Welcome, {student.full_name}</h2>
    <div class="student-info">
        <p><strong>Admission Number:</strong> {student.admission_number}</p>
        <p><strong>Department:</strong> {student.department}</p>
        <p><strong>Year of Study:</strong> {student.year_of_study}</p>
        <p><strong>Last Login:</strong> {last_login}</p>
        <p><strong>Hotspot Access:</strong> {'Approved' if student.hotspot_access else 'Not Approved'}</p>
    </div>
    
    <div class="nav-links">
        <h3>Quick Links</h3>
        <a href="/profile">View Profile</a>
        <a href="/request_hotspot">Request Hotspot Access</a>
        <a href="/connect_hotspot">Connection Instructions</a>
        <a href="/hotspot">Access Hotspot</a>
        <a href="/logout">Logout</a>
    </div>
    """
    messages = []
    if '_flashes' in session:
        messages = session['_flashes']
    return generate_html("Dashboard", content, messages, is_logged_in=True)

@app.route('/profile')
def profile():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    
    student = Student.query.get(session['student_id'])
    sessions = HotspotSession.query.filter_by(student_id=student.id)\
                                 .order_by(HotspotSession.start_time.desc())\
                                 .limit(10)\
                                 .all()
    
    sessions_html = ""
    for sess in sessions:
        if sess.end_time:
            duration_min = (sess.end_time - sess.start_time).seconds // 60
            duration = f'Duration: {duration_min} minutes'
        else:
            duration = 'Active session'
        
        end_time = sess.end_time.strftime('%Y-%m-%d %H:%M:%S') if sess.end_time else 'Active'
        sessions_html += f"""
        <tr>
            <td>{sess.start_time.strftime('%Y-%m-%d %H:%M:%S')}</td>
            <td>{end_time}</td>
            <td>{duration}</td>
        </tr>
        """
    
    content = f"""
    <h2>Student Profile</h2>
    <div class="personal-info">
        <h3>Personal Information</h3>
        <p><strong>Admission Number:</strong> {student.admission_number}</p>
        <p><strong>Full Name:</strong> {student.full_name}</p>
        <p><strong>Email:</strong> {student.email}</p>
        <p><strong>Department:</strong> {student.department}</p>
        <p><strong>Year of Study:</strong> {student.year_of_study}</p>
        <p><strong>Hotspot Access:</strong> {'Approved' if student.hotspot_access else 'Not Approved'}</p>
    </div>
    
    <div class="internet-usage">
        <h3>Hotspot Usage</h3>
        <p><strong>Total Minutes Used:</strong> {student.internet_usage_minutes}</p>
        
        <h4>Recent Sessions</h4>
        <table>
            <thead>
                <tr>
                    <th>Start Time</th>
                    <th>End Time</th>
                    <th>Duration</th>
                </tr>
            </thead>
            <tbody>
                {sessions_html}
            </tbody>
        </table>
    </div>
    
    <div class="nav-links">
        <a href="/dashboard">Back to Dashboard</a>
    </div>
    """
    messages = []
    if '_flashes' in session:
        messages = session['_flashes']
    return generate_html("Profile", content, messages, is_logged_in=True)

@app.route('/request_hotspot', methods=['GET', 'POST'])
def request_hotspot():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    student = Student.query.get(session['student_id'])
    
    if student.hotspot_access:
        flash('You already have hotspot access', 'info')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        existing_request = HotspotRequest.query.filter_by(
            student_id=student.id,
            status='pending'
        ).first()
        
        if existing_request:
            flash('You already have a pending hotspot request', 'warning')
        else:
            new_request = HotspotRequest(student_id=student.id)
            db.session.add(new_request)
            db.session.commit()
            flash('Hotspot access request submitted for admin approval', 'success')
        
        return redirect(url_for('dashboard'))

    current_request = HotspotRequest.query.filter_by(
        student_id=student.id
    ).order_by(HotspotRequest.request_time.desc()).first()

    status_message = "No active hotspot access"
    if current_request:
        if current_request.status == 'approved':
            status_message = f"Hotspot Access Approved (on {current_request.approval_time.strftime('%Y-%m-%d')})"
        elif current_request.status == 'pending':
            status_message = "Hotspot Access Pending Approval"
        else:
            status_message = "Last request was rejected"

    content = f"""
    <h2>Hotspot Access Request</h2>
    <div class="student-info">
        <p><strong>Current Status:</strong> {status_message}</p>
        <p>Your admission number: {student.admission_number}</p>
    </div>
    
    <form method="POST">
        <p>Click below to request hotspot access</p>
        <button type="submit">Request Hotspot Access</button>
    </form>
    
    <div class="nav-links">
        <a href="/dashboard">Back to Dashboard</a>
    </div>
    """
    return generate_html("Hotspot Access", content, is_logged_in=True)

@app.route('/connect_hotspot')
def connect_hotspot():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    
    student = Student.query.get(session['student_id'])
    if not student.hotspot_access:
        flash('You need approved hotspot access', 'danger')
        return redirect(url_for('request_hotspot'))
    
    config = HotspotConfig.query.first()
    if not config:
        config = HotspotConfig()
        db.session.add(config)
        db.session.commit()
    
    content = f"""
    <h2>Connect to School Hotspot</h2>
    <div class="student-info">
        <h3>Connection Instructions</h3>
        <ol>
            <li>Go to your device's WiFi settings</li>
            <li>Look for network: <strong>{config.ssid}</strong></li>
            <li>Connect using password: <strong>{config.password}</strong></li>
            <li>Open any browser and you'll be redirected to login</li>
        </ol>
        
        <div class="qr-code">
            <h4>Quick Connect QR Code</h4>
            <img src="/qrcode" alt="Hotspot QR Code">
            <p>Scan this code with your phone camera to connect automatically</p>
        </div>
    </div>
    """
    return generate_html("Hotspot Connection", content, is_logged_in=True)

@app.route('/qrcode')
def generate_qrcode():
    config = HotspotConfig.query.first()
    if not config:
        config = HotspotConfig()
        db.session.add(config)
        db.session.commit()
    
    wifi_config = f"WIFI:T:WPA;S:{config.ssid};P:{config.password};;"
    qrcode = segno.make(wifi_config, micro=False)
    buffer = BytesIO()
    qrcode.save(buffer, kind="png", scale=6)
    buffer.seek(0)
    
    return send_file(buffer, mimetype='image/png')

@app.route('/hotspot')
def hotspot_access():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    student = Student.query.get(session['student_id'])
    if not student.hotspot_access:
        flash('You need approved hotspot access to use this feature', 'danger')
        return redirect(url_for('request_hotspot'))

    # Start new hotspot session if not already active
    if 'hotspot_session_id' not in session:
        new_session = HotspotSession(student_id=student.id)
        db.session.add(new_session)
        db.session.commit()
        session['hotspot_session_id'] = new_session.id

    content = f"""
    <h2>Hotspot Access Portal</h2>
    <div class="student-info">
        <p>Welcome, {student.full_name}</p>
        <p>You are now connected to the school hotspot</p>
    </div>
    
    <div class="internet-frame">
        <iframe src="https://example.com" width="100%" height="100%" frameborder="0"></iframe>
    </div>
    
    <div class="nav-links">
        <a href="/logout">Disconnect and Logout</a>
    </div>
    """
    return generate_html("Hotspot Access", content, is_logged_in=True)

@app.route('/admin/hotspot_requests')
def hotspot_requests():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    pending_requests = db.session.query(
        HotspotRequest, Student
    ).join(
        Student, HotspotRequest.student_id == Student.id
    ).filter(
        HotspotRequest.status == 'pending'
    ).all()

    requests_html = ""
    for request, student in pending_requests:
        requests_html += f"""
        <tr>
            <td>{student.admission_number}</td>
            <td>{student.full_name}</td>
            <td>{student.department}</td>
            <td>{request.request_time.strftime('%Y-%m-%d %H:%M')}</td>
            <td>
                <a href="/admin/approve_hotspot/{request.id}">Approve</a> | 
                <a href="/admin/reject_hotspot/{request.id}">Reject</a>
            </td>
        </tr>
        """

    content = f"""
    <h2>Pending Hotspot Requests</h2>
    <table>
        <thead>
            <tr>
                <th>Admission No.</th>
                <th>Student Name</th>
                <th>Department</th>
                <th>Request Time</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {requests_html}
        </tbody>
    </table>
    <div class="nav-links">
        <a href="/admin">Back to Admin Dashboard</a>
    </div>
    """
    return generate_html("Hotspot Requests", content, is_logged_in=True)

@app.route('/admin/approve_hotspot/<int:request_id>')
def approve_hotspot(request_id):
    if 'student_id' not in session:
        return redirect(url_for('login'))

    request = HotspotRequest.query.get(request_id)
    if request:
        request.status = 'approved'
        request.approved_by = session['student_id']
        request.approval_time = datetime.datetime.utcnow()
        
        # Grant hotspot access to student
        student = Student.query.get(request.student_id)
        student.hotspot_access = True
        
        db.session.commit()
        flash('Hotspot access approved', 'success')
    return redirect(url_for('hotspot_requests'))

@app.route('/admin/reject_hotspot/<int:request_id>')
def reject_hotspot(request_id):
    if 'student_id' not in session:
        return redirect(url_for('login'))

    request = HotspotRequest.query.get(request_id)
    if request:
        request.status = 'rejected'
        db.session.commit()
        flash('Hotspot access rejected', 'warning')
    return redirect(url_for('hotspot_requests'))

@app.route('/admin')
def admin_home():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    
    return generate_html("Admin Dashboard", """
    <h2>Admin Dashboard</h2>
    <div class="nav-links">
        <a href="/admin/students">Manage Students</a>
        <a href="/admin/add_student">Add New Student</a>
        <a href="/admin/hotspot_requests">Manage Hotspot Requests</a>
        <a href="/dashboard">Back to Dashboard</a>
    </div>
    """, is_logged_in=True)

@app.route('/admin/students')
def admin_students():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    
    students = Student.query.all()
    students_html = ""
    
    for student in students:
        students_html += f"""
        <tr>
            <td>{student.admission_number}</td>
            <td>{student.full_name}</td>
            <td>{student.email}</td>
            <td>{student.department}</td>
            <td>{student.year_of_study}</td>
            <td>{student.internet_usage_minutes} mins</td>
            <td>{'Yes' if student.hotspot_access else 'No'}</td>
            <td>
                <a href="/admin/edit_student/{student.id}">Edit</a> | 
                <a href="/admin/delete_student/{student.id}">Delete</a>
            </td>
        </tr>
        """
    
    content = f"""
    <h2>Student Management</h2>
    <div class="nav-links">
        <a href="/admin/add_student">Add New Student</a>
        <a href="/admin">Back to Admin Dashboard</a>
    </div>
    
    <table>
        <thead>
            <tr>
                <th>Admission No.</th>
                <th>Full Name</th>
                <th>Email</th>
                <th>Department</th>
                <th>Year</th>
                <th>Usage (mins)</th>
                <th>Hotspot Access</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {students_html}
        </tbody>
    </table>
    """
    return generate_html("Manage Students", content, is_logged_in=True)

@app.route('/admin/add_student', methods=['GET', 'POST'])
def add_student():
    if 'student_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        admission_number = request.form['admission_number']
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        department = request.form['department']
        year_of_study = request.form['year_of_study']
        hotspot_access = 'hotspot_access' in request.form
        
        student = Student(
            admission_number=admission_number,
            full_name=full_name,
            email=email,
            department=department,
            year_of_study=year_of_study,
            hotspot_access=hotspot_access
        )
        student.set_password(password)
        
        db.session.add(student)
        db.session.commit()
        
        flash('Student added successfully', 'success')
        return redirect(url_for('admin_students'))
    
    content = """
    <h2>Add New Student</h2>
    <form method="POST">
        <label for="admission_number">Admission Number:</label>
        <input type="text" id="admission_number" name="admission_number" required>
        
        <label for="full_name">Full Name:</label>
        <input type="text" id="full_name" name="full_name" required>
        
        <label for="email">Email:</label>
        <input type="email" id="email" name="email" required>
        
        <label for="password">Password:</label>
        <input type="password" id="password" name="password" required>
        
        <label for="department">Department:</label>
        <input type="text" id="department" name="department" required>
        
        <label for="year_of_study">Year of Study:</label>
        <input type="number" id="year_of_study" name="year_of_study" min="1" max="6" required>
        
        <label>
            <input type="checkbox" name="hotspot_access" value="true">
            Grant Hotspot Access Immediately
        </label>
        
        <button type="submit">Add Student</button>
    </form>
    <div class="nav-links">
        <a href="/admin/students">Back to Student List</a>
    </div>
    """
    return generate_html("Add Student", content, is_logged_in=True)

if __name__ == '__main__':
    initialize_database()
    app.run(debug=True)