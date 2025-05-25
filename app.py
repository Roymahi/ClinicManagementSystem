from flask import flash
from flask import Flask, render_template, redirect, url_for, flash, request
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///clinic.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# For production, enable CSRF protection (e.g., Flask-WTF)

db = SQLAlchemy(app)

def utc_today():
    return datetime.utcnow().date()

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
        username = request.form.get('username')
        password = request.form.get('password')
        if username == USERNAME and password == PASSWORD:
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid credentials'
    return render_template('login.html', error=error)

@app.route('/dashboard')
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
def delete_visit(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    db.session.delete(appointment)
    db.session.commit()
    flash("Appointment deleted successfully.", "success")
    return redirect(url_for('dashboard'))
    

@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if request.method == 'POST':
        name = request.form.get('Patient-Name')
        age_str = request.form.get('Patient-Age')
        gender = request.form.get('Gender')
        phone = request.form.get('Patient-PhoneNo')
        desc = request.form.get('Patient-desc')
        date_str = request.form.get('date')

        try:
            age = int(age_str) if age_str else None
        except ValueError:
            age = None

        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else utc_today()
        except ValueError:
            date = utc_today()

        new_patient = Patient(name=name, age=age, gender=gender, phone=phone, disease=desc, date=date)
        db.session.add(new_patient)
        db.session.commit()

        print(f"Patient Added: {name}, {age}, {phone}")
        return redirect(url_for('dashboard'))
    return render_template('add_patient.html')

@app.route('/add_doctor', methods=['GET', 'POST'])
def add_doctor():
    if request.method == 'POST':
        name = request.form.get('Doctor-Name')
        specialization = request.form.get('Doctor-Specialization')
        phone = request.form.get('Doctor-Phone')
        email = request.form.get('Doctor-Email')
        experience_str = request.form.get('Doctor-Experience')

        try:
            experience = int(experience_str) if experience_str else None
        except ValueError:
            experience = None

        new_doctor = Doctor(name=name, specialization=specialization, phone=phone, email=email, experience=experience)
        db.session.add(new_doctor)
        db.session.commit()

        print(f"Doctor Added: {name}, {specialization}, {phone}")
        return redirect(url_for('dashboard'))
    return render_template('add_doctor.html')

@app.route('/add_appointment', methods=['GET', 'POST'])
def add_appointment():
    if request.method == 'POST':
        patient_name = request.form.get('Patient-Name')
        doctor_name = request.form.get('Doctor-Name')
        date_str = request.form.get('Appointment-Date')
        time = request.form.get('Appointment-Time')
        reason = request.form.get('Reason')
        status = request.form.get('Status') or 'scheduled'

        try:
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else utc_today()
        except ValueError:
            appointment_date = utc_today()

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

        print(f"Appointment Added: {patient_name} with {doctor_name} on {appointment_date} at {time}")
        return redirect(url_for('dashboard'))
    return render_template('add_appointment.html')

@app.route('/update_patient/<int:patient_id>', methods=['GET', 'POST'])
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
def patients_by_date():
    selected_date = request.args.get('date')
    patients = get_patients_by_date(selected_date)
    return render_template('patients_by_date.html', patients=patients, selected_date=selected_date)

@app.route('/update_visit/<int:appointment_id>', methods=['GET', 'POST'])
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
def total_visit():
    completed_visits = Appointment.query.filter_by(status='completed').count()
    return render_template('total_visit.html', completed_visits=completed_visits)

@app.route('/mark_visit_completed/<int:appointment_id>', methods=['POST'])
def mark_visit_completed(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.status = 'completed'
    db.session.commit()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
