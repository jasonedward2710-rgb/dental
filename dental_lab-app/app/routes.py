from flask import render_template, flash, redirect, url_for, request
from app import app, db
from app.forms import LoginForm, RegistrationForm, JobForm, PracticeForm, DoctorForm, EditJobForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, Job, Practice, Doctor
from werkzeug.urls import url_parse
from datetime import datetime, timedelta
import logging

USER_PRACTICE_MAP = {
    # Admins (no restriction)
    'infinitydd': None,
    'infinitylab1#': None,

    # Practice-specific users
    'ballito@familydentalcare.co.za': 'Ballito',
    'dbnnorthfdc@familydentalcare.co.za': 'Durban North',
    'lalucia@familydentalcare.co.za': 'La Lucia',
    'linkhills@familydentalcare.co.za': 'Linkhills',
    'dentist@familydentalcare.co.za': 'Queensburgh',
    'onnicol@familydentalcare.co.za': 'Sandton',
    'somerset@familydentalcare.co.za': 'Somerset',
    'tablebay@familydentalcare.co.za': 'Table Bay',
    'tongaat@familydentalcare.co.za': 'Tongaat',
    'hiltonfdc1': 'Hilton'
}


# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/')
@app.route('/index')
@login_required
def index():
    from sqlalchemy import or_
    search_query = request.args.get('search_query', '')
    practice_filter = request.args.get('practice_filter', '')
    doctor_filter = request.args.get('doctor_filter', '')
    due_date_filter = request.args.get('due_date_filter', '')

    jobs_query = Job.query

    # 🔍 1. SEARCH filter (always allow all statuses)
    if search_query:
        jobs_query = jobs_query.filter(
            or_(
                Job.patient_name.ilike(f"%{search_query}%"),
                Job.lab_slip_number.ilike(f"%{search_query}%"),
                Job.invoice_number.ilike(f"%{search_query}%")
            )
        )

    # 👤 2. Practice filter: restrict non-admins
    if not current_user.is_admin:
        user_practice = USER_PRACTICE_MAP.get(current_user.username)
        if user_practice:
            jobs_query = jobs_query.filter_by(practice_name=user_practice)
    else:
        if practice_filter:
            jobs_query = jobs_query.filter_by(practice_name=practice_filter)

    # 👨‍⚕️ 3. Doctor filter
    if doctor_filter:
        jobs_query = jobs_query.filter_by(doctor_name=doctor_filter)

    # 📅 4. Due date filter or default
    if due_date_filter:
        try:
            due_date = datetime.strptime(due_date_filter, '%Y-%m-%d').date()
            jobs_query = jobs_query.filter(Job.due_date == due_date)
        except ValueError:
            pass
    elif not search_query:
        # Default view: next 3 days
        today = datetime.today().date()
        three_days_later = today + timedelta(days=3)
        jobs_query = jobs_query.filter(Job.due_date.between(today, three_days_later))

        # 🚫 Apply job status filter *only in default view, not when searching*
        jobs_query = jobs_query.filter(Job.job_status.in_(['In Production', 'Ready For Delivery', 'In Transit To Practice']))

    # ✅ 5. Execute query
    jobs = jobs_query.order_by(Job.due_date.asc()).all()
    practices = Practice.query.all()
    doctors = Doctor.query.all()

    return render_template('index.html',
        title='Home',
        jobs=jobs,
        practices=practices,
        doctors=doctors,
        search_query=search_query,
        practice_filter=practice_filter,
        doctor_filter=doctor_filter,
        due_date_filter=due_date_filter
    )



@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if not current_user.is_admin:
        flash('Only administrators can register new users.')
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, is_admin=form.is_admin.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('index'))
    return render_template('register.html', title='Register', form=form)

@app.route('/add_job', methods=['GET', 'POST'])
@login_required
def add_job():
    form = JobForm()
    if form.validate_on_submit():
        job = Job(
            job_type=form.job_type.data,
            practice_name=Practice.query.get(form.practice_name.data).name,
            doctor_name=Doctor.query.get(form.doctor_name.data).name,
            patient_name=form.patient_name.data,
            lab_slip_number=form.lab_slip_number.data,
            job_status=form.job_status.data,
            due_date=form.due_date.data,
            shade=form.shade.data,
            invoice_number=form.invoice_number.data,
            delivery_info=form.delivery_info.data,
            comments=form.comments.data,
            created_date=datetime.utcnow(),
            updated_date=datetime.utcnow()
        )
        db.session.add(job)
        db.session.commit()
        flash('Job added successfully.')
        return redirect(url_for('index'))
    return render_template('add_edit_job.html', title='Add Job', form=form)

@app.route('/edit_job/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_job(id):
    if not current_user.is_admin:
        flash('Only administrators can add edit jobs.')
        return redirect(url_for('index'))
    job = Job.query.get_or_404(id)
    form = EditJobForm(obj=job)
    if form.validate_on_submit():
        job.job_type = form.job_type.data
        job.practice_name = form.practice_name.data
        job.doctor_name = form.doctor_name.data
        job.patient_name = form.patient_name.data
        job.lab_slip_number = form.lab_slip_number.data
        job.job_status = form.job_status.data
        job.due_date = form.due_date.data
        job.shade = form.shade.data
        job.invoice_number = form.invoice_number.data
        job.delivery_info = form.delivery_info.data
        job.comments = form.comments.data
        job.updated_date = datetime.utcnow()
        db.session.commit()
        flash('Job updated successfully.')
        return redirect(url_for('index'))
    return render_template('edit_job.html', title='Edit Job', form=form, job=job)

@app.route('/job/<int:id>')
@login_required
def job(id):
    job = Job.query.get_or_404(id)
    return render_template('job.html', title='Job Details', job=job)

@app.route('/add_practices', methods=['GET', 'POST'])
@login_required
def add_practices():
    if not current_user.is_admin:
        flash('Only administrators can add practices.')
        return redirect(url_for('index'))
    form = PracticeForm()
    if form.validate_on_submit():
        practices = [Practice(name=name.strip()) for name in form.practice_names.data.split(',')]
        db.session.bulk_save_objects(practices)
        db.session.commit()
        flash('Practices added successfully!')
        return redirect(url_for('index'))
    return render_template('add_practices.html', title='Add Practices', form=form)

@app.route('/add_doctors', methods=['GET', 'POST'])
@login_required
def add_doctors():
    if not current_user.is_admin:
        flash('Only administrators can add doctors.')
        return redirect(url_for('index'))
    form = DoctorForm()
    if form.validate_on_submit():
        doctors = [Doctor(name=name.strip(), practice_id=form.practice_id.data) for name in form.doctor_names.data.split(',')]
        db.session.bulk_save_objects(doctors)
        db.session.commit()
        flash('Doctors added successfully!')
        return redirect(url_for('index'))
    return render_template('add_doctors.html', title='Add Doctors', form=form)

@app.route('/delete_job/<int:id>', methods=['POST'])
@login_required
def delete_job(id):
    if not current_user.is_admin:
        flash('Admin access required to delete jobs.')
        return redirect(url_for('index'))

    job = Job.query.get_or_404(id)
    db.session.delete(job)
    db.session.commit()
    return redirect(url_for('index'))