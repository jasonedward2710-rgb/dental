from datetime import datetime
from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Practice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)

    def __repr__(self):
        return f'<Practice {self.name}>'

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    practice_id = db.Column(db.Integer, db.ForeignKey('practice.id'), nullable=False)
    practice = db.relationship('Practice', back_populates='doctors')

    def __repr__(self):
        return f'<Doctor {self.name}>'

Practice.doctors = db.relationship('Doctor', order_by=Doctor.id, back_populates='practice')

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_type = db.Column(db.String(64))
    practice_name = db.Column(db.String(64))
    doctor_name = db.Column(db.String(64))
    patient_name = db.Column(db.String(64))
    lab_slip_number = db.Column(db.String(64))
    job_status = db.Column(db.String(64))
    due_date = db.Column(db.Date)
    shade = db.Column(db.String(64))
    invoice_number = db.Column(db.String(64))
    delivery_info = db.Column(db.String(64))
    comments = db.Column(db.Text)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    updated_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'job_type': self.job_type,
            'practice_name': self.practice_name,
            'doctor_name': self.doctor_name,
            'patient_name': self.patient_name,
            'lab_slip_number': self.lab_slip_number,
            'job_status': self.job_status,
            'due_date': self.due_date.strftime('%d/%m/%Y') if self.due_date else None,
            'shade': self.shade,
            'invoice_number': self.invoice_number,
            'delivery_info': self.delivery_info,
            'comments': self.comments,
            'created_date': self.created_date.strftime('%d/%m/%Y') if self.created_date else None,
            'updated_date': self.updated_date.strftime('%d/%m/%Y') if self.updated_date else None
        }

    def __repr__(self):
        return '<Job {}>'.format(self.patient_name)
