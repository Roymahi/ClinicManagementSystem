from flask import flash
from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func
import re

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///clinic.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'  # Added for session management

db = SQLAlchemy(app)

def utc_today():
    return datetime.utcnow().date()

# Input validation functions
def validate_name(name):
    if not name or len(name.strip()) < 2:
        return False
    return re.match(r'^[a-zA-Z\s]+$', name.strip())

def validate_phone(phone):
    if not phone:
        return False
    # Remove spaces and check if it's 10 digits
    clean_phone = re.sub(r'\s+', '', phone)
    return re.match(r'^\d{10}$', clean_phone)

def validate_email(email):
    if not email:
        return True  # Email is optional
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email)

def validate_age(age_str):
    try:
        age = int(age_str)
        return 0 < age <= 120
    except (ValueError, TypeError):
        return False

def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Patient Model
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    phone = db.Column(db.String(20))
    disease = db.Column(db.String(200))
    date = db.Column(db.Date, default=utc_today)

# Doctor Model
class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    specialization = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100))
    experience = db.Column(db.Integer)
    date_added = db.Column(db.Date, default=utc_today)

# Appointment Model
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    doctor_name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.String(200))
    status = db.Column(db.String(20), default='scheduled')  # scheduled/completed/cancelled etc.

# User Auth (simple, for demo only)
USERNAME = 'admin'
PASSWORD = 'admin@123'

def get_doctor_of_month():
    current_month = datetime.utcnow().month
    current_year = datetime.utcnow().year

    result = db.session.query(
        Appointment.doctor_name,
        func.count(Appointment.id).label('appointment_count')
    ).filter(
        func.extract('month', Appointment.date) == current_month,
        func.extract('year', Appointment.date) == current_year
    ).group_by(Appointment.doctor_name).order_by(func.count(Appointment.id).desc()).first()

    if result:
        doctor_name = result[0]
        doctor = Doctor.query.filter_by(name=doctor_name).first()
        return doctor
    return None

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            error = 'Please enter both username and password'
        elif username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid credentials'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    total_patients = Patient.query.count()
    total_appointments = Appointment.query.count()
    total_visits = Appointment.query.count()  # You may want to differentiate visits vs appointments
    total_doctors = Doctor.query.count()
    doctor_of_month = get_doctor_of_month()

    patients = Patient.query.all()
    appointments = Appointment.query.all()

    return render_template('dashboard.html',
                           total_patients=total_patients,
                           total_appointments=total_appointments,
                           total_visits=total_visits,
                           total_doctors=total_doctors,
                           doctor_of_month=doctor_of_month,
                           patients=patients,
                           appointments=appointments,
                           selected_date=None)
    
@app.route('/visit/delete/<int:appointment_id>', methods=['POST'])
@login_required
def delete_visit(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    db.session.delete(appointment)
    db.session.commit()
    flash("Appointment deleted successfully.", "success")
    return redirect(url_for('dashboard'))
    

@app.route('/add_patient', methods=['GET', 'POST'])
@login_required
def add_patient():
    if request.method == 'POST':
        name = request.form.get('Patient-Name', '').strip()
        age_str = request.form.get('Patient-Age', '').strip()
        gender = request.form.get('Gender', '').strip()
        phone = request.form.get('Patient-PhoneNo', '').strip()
        desc = request.form.get('Patient-desc', '').strip()
        date_str = request.form.get('date', '').strip()

        # Validation
        errors = []
        if not validate_name(name):
            errors.append('Please enter a valid name (letters only)')
        if not validate_age(age_str):
            errors.append('Please enter a valid age (1-120)')
        if gender not in ['Male', 'Female', 'Other']:
            errors.append('Please select a valid gender')
        if not validate_phone(phone):
            errors.append('Please enter a valid 10-digit phone number')
        if not desc:
            errors.append('Please enter patient description/disease')

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('add_patient.html')

        try:
            age = int(age_str)
        except ValueError:
            age = None

        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else utc_today()
        except ValueError:
            date = utc_today()

        new_patient = Patient(name=name, age=age, gender=gender, phone=phone, disease=desc, date=date)
        db.session.add(new_patient)
        db.session.commit()

        flash(f"Patient {name} added successfully!", 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_patient.html')

@app.route('/add_doctor', methods=['GET', 'POST'])
@login_required
def add_doctor():
    if request.method == 'POST':
        name = request.form.get('Doctor-Name', '').strip()
        specialization = request.form.get('Doctor-Specialization', '').strip()
        phone = request.form.get('Doctor-Phone', '').strip()
        email = request.form.get('Doctor-Email', '').strip()
        experience_str = request.form.get('Doctor-Experience', '').strip()

        # Validation
        errors = []
        if not validate_name(name):
            errors.append('Please enter a valid doctor name')
        if not specialization:
            errors.append('Please enter specialization')
        if not validate_phone(phone):
            errors.append('Please enter a valid 10-digit phone number')
        if not validate_email(email):
            errors.append('Please enter a valid email address')
        if experience_str and not experience_str.isdigit():
            errors.append('Please enter valid experience in years')

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('add_doctor.html')

        try:
            experience = int(experience_str) if experience_str else None
        except ValueError:
            experience = None

        new_doctor = Doctor(name=name, specialization=specialization, phone=phone, email=email, experience=experience)
        db.session.add(new_doctor)
        db.session.commit()

        flash(f"Doctor {name} added successfully!", 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_doctor.html')

@app.route('/add_appointment', methods=['GET', 'POST'])
@login_required
def add_appointment():
    doctors = Doctor.query.all()
    patients = Patient.query.all()
    
    if request.method == 'POST':
        patient_name = request.form.get('Patient-Name', '').strip()
        doctor_name = request.form.get('Doctor-Name', '').strip()
        date_str = request.form.get('Appointment-Date', '').strip()
        time = request.form.get('Appointment-Time', '').strip()
        reason = request.form.get('Reason', '').strip()
        status = request.form.get('Status', 'scheduled').strip()

        # Validation
        errors = []
        if not patient_name:
            errors.append('Please enter patient name')
        if not doctor_name:
            errors.append('Please enter doctor name')
        if not date_str:
            errors.append('Please select appointment date')
        if not time:
            errors.append('Please enter appointment time')
        if not reason:
            errors.append('Please enter reason for appointment')

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('add_appointment.html', doctors=doctors, patients=patients)

        try:
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            if appointment_date < datetime.now().date():
                flash('Appointment date cannot be in the past', 'error')
                return render_template('add_appointment.html', doctors=doctors, patients=patients)
        except ValueError:
            flash('Please enter a valid date', 'error')
            return render_template('add_appointment.html', doctors=doctors, patients=patients)

        new_appointment = Appointment(
            patient_name=patient_name,
            doctor_name=doctor_name,
            date=appointment_date,
            time=time,
            reason=reason,
            status=status
        )
        db.session.add(new_appointment)
        db.session.commit()

        flash(f"Appointment scheduled for {patient_name} with Dr. {doctor_name}", 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_appointment.html', doctors=doctors, patients=patients)

@app.route('/update_patient/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def update_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if request.method == 'POST':
        patient.name = request.form.get('Patient-Name')
        try:
            patient.age = int(request.form.get('Patient-Age'))
        except (TypeError, ValueError):
            patient.age = None
        patient.gender = request.form.get('Gender')
        patient.phone = request.form.get('Patient-PhoneNo')
        patient.disease = request.form.get('Patient-desc')

        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('update_patient.html', patient=patient)

@app.route('/delete_patient/<int:patient_id>', methods=['POST'])
@login_required
def delete_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    db.session.delete(patient)
    db.session.commit()
    return redirect(url_for('dashboard'))

def get_patients_by_date(selected_date):
    if selected_date:
        try:
            target_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            target_date = None
        if target_date:
            return Patient.query.filter(Patient.date == target_date).all()
    return Patient.query.all()

@app.route('/patients_by_date')
@login_required
def patients_by_date():
    selected_date = request.args.get('date')
    patients = get_patients_by_date(selected_date)
    return render_template('patients_by_date.html', patients=patients, selected_date=selected_date)

@app.route('/update_visit/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
def update_visit(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    if request.method == 'POST':
        appointment.patient_name = request.form.get('Patient-Name')
        appointment.doctor_name = request.form.get('Doctor-Name')
        date_str = request.form.get('Appointment-Date')
        try:
            appointment.date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else appointment.date
        except ValueError:
            pass
        appointment.time = request.form.get('Appointment-Time')
        appointment.reason = request.form.get('Reason')
        appointment.status = request.form.get('Status') or appointment.status

        db.session.commit()
        return redirect(url_for('dashboard'))

    return render_template('update_visit.html', appointment=appointment)

@app.route('/total_visit')
@login_required
def total_visit():
    completed_visits = Appointment.query.filter_by(status='completed').count()
    return render_template('total_visit.html', completed_visits=completed_visits)

@app.route('/mark_visit_completed/<int:appointment_id>', methods=['POST'])
@login_required
def mark_visit_completed(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.status = 'completed'
    db.session.commit()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
