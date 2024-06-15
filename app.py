from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, current_user, login_required, logout_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
from flask import jsonify
from flask import render_template
from flask_paginate import Pagination, get_page_parameter
from flask import Flask, render_template, request, redirect, flash
from math import ceil
from flask_paginate import Pagination, get_page_args
from flask import send_from_directory
from sendemailstudent import send_notification

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = '6e38ac95e3ce49a1cd424af5f204f05b6cd81c721c3a2b6f'
app.config['UPLOAD_FOLDER'] = 'uploads'

login_manager = LoginManager(app)


class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username


@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('Database/placement_system.db')
    cursor = conn.cursor()
    cursor.execute("SELECT Username FROM users WHERE id=?", (user_id,))
    username = cursor.fetchone()[0]
    conn.close()
    return User(user_id, username)


@app.route('/')
def index():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user_type = request.form['userType']

    conn = sqlite3.connect('Database/placement_system.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE Username=?", (username,))
    user = cursor.fetchone()
    if user and check_password_hash(user[2], password) and user[3] == user_type:
        user_obj = User(user[0], username)
        login_user(user_obj)
        if user_type == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user_type == 'student':
            return redirect(url_for('student_dashboard'))
    else:
        return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    return render_template('Admin_Home.html')


@app.route('/student/dashboard')
@login_required
def student_dashboard():
    current_username = current_user.username
    conn = sqlite3.connect('Database/placement_system.db')
    cursor = conn.cursor()
    cursor.execute("SELECT Name, PRN, Email FROM student_list WHERE Username=?", (current_username,))
    student_info = cursor.fetchone()
    return render_template('Student_Home.html', student_info=student_info)

@app.route('/admin/company_list')
@login_required
def company_list():
    conn = sqlite3.connect('Database/placement_system.db')
    cursor = conn.cursor()
    cursor.execute("SELECT company_name, industry, location, role, salary, deadline FROM companies")
    companies = cursor.fetchall()
    conn.close()
    return render_template('Company_list.html', companies=companies)



@app.route('/download_pdf/<company_name>')
def download_pdf(company_name):
    # Construct the path to the PDF file
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{company_name}.pdf')
    
    # Check if the file exists
    if os.path.isfile(pdf_path):
        # If the file exists, send it to the client
        return send_from_directory(app.config['UPLOAD_FOLDER'], f'{company_name}.pdf', as_attachment=True)
    else:
        # If the file does not exist, return a 404 error
        return "PDF not found", 404



@app.route('/apply_company', methods=['POST'])
@login_required
def apply_company():
    if request.method == 'POST':
        company_name = request.json.get('company_name')
        current_username = current_user.username
        
        # Check if the user has already applied for the company
        conn = sqlite3.connect('Database/placement_system.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_applications WHERE Username = ? AND Company_Name = ?", (current_username, company_name))
        result = cursor.fetchone()
        if result:
            conn.close()
            return jsonify({'error': 'You have already applied for this company'}), 400

        # Retrieve date from companies table
        cursor.execute("SELECT Date FROM companies WHERE company_name = ?", (company_name,))
        result = cursor.fetchone()
        if result:
            company_date = result[0]
        else:
            conn.close()
            return jsonify({'error': 'Company not found'}), 404
        
        # Update user_applications table with applied company
        cursor.execute("INSERT INTO user_applications (Username, Company_Name) VALUES (?, ?)", (current_username, company_name))
        
        # Update student_list table with applied company and date
        cursor.execute("UPDATE student_list SET applied_company = COALESCE(applied_company || ', ' || ?, ?), company_date = COALESCE(company_date || ', ' || ?, ?) WHERE Username = ?", (company_name, company_name, company_date, company_date, current_username))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Applied successfully'}), 200
    else:
        return jsonify({'error': 'Method not allowed'}), 405




@app.route('/admin/student_list')
@login_required
def student_list():
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 10  # Number of students per page
    conn = sqlite3.connect('Database/placement_system.db')
    cursor = conn.cursor()
    
    # Fetch total number of students
    cursor.execute("SELECT COUNT(*) FROM student_list")
    total_students = cursor.fetchone()[0]

    # Calculate total number of pages
    total_pages = ceil(total_students / per_page)
    
    # Ensure that page is within valid range
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    # Calculate offset
    offset = (page - 1) * per_page + 1
    
    # Fetch students for the current page
    cursor.execute("SELECT * FROM student_list LIMIT ? OFFSET ?", (per_page, offset - 1))
    students = cursor.fetchall()
    
    conn.close()
    
    pagination = Pagination(page=page, total=total_students, per_page=per_page, css_framework='bootstrap4')
    
    return render_template('student_list.html', students=students, pagination=pagination)



@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Handle form submission to update user profile
        name = request.form['name']
        department = request.form['department']
        email = request.form['email']
        birthdate = request.form['birthdate']
        Contact_number = request.form['contact']
        interest = request.form['interest']
        address = request.form['address']
        PRN = request.form['prn']
        # Similarly, fetch other form fields
        
        # Update the user's profile in the database
        conn = sqlite3.connect('Database/placement_system.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE student_list SET Name=?, Department=?, Email=?, Birthdate=?, Contact_Number = ?, Interest = ?, Address = ?, PRN = ?  WHERE Username=?", (name, department, email, birthdate, Contact_number, interest, address, PRN, current_user.username))
        conn.commit()
        conn.close()
        
        # Redirect back to the profile page after saving changes
        return redirect(url_for('student_dashboard'))

    # Fetch user's profile details
    conn = sqlite3.connect('Database/placement_system.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM student_list WHERE Username=?", (current_user.username,))
    user_profile = cursor.fetchone()
    conn.close()

    return render_template('edit_profile.html', user_profile=user_profile)

@app.route('/student/applied_jobs')
@login_required
def applied_jobs():
    conn = sqlite3.connect('Database/placement_system.db')
    cursor = conn.cursor()
    cursor.execute("SELECT applied_company FROM student_list WHERE Username=?", (current_user.username,))
    result = cursor.fetchone()
    applied_companies = [(idx, company_name) for idx, company_name in enumerate(result[0].split(','))] if result else []
    conn.close()
    return render_template('applied_jobs.html', applied_companies=applied_companies)


@app.route('/student/schedule')
@login_required
def student_schedule():
    conn = sqlite3.connect('Database/placement_system.db')
    cursor = conn.cursor()
    cursor.execute("SELECT applied_company, company_date FROM student_list WHERE Username = ?", (current_user.username,))
    schedule_data = cursor.fetchall()
    conn.close()
    return render_template('Student_Schedule.html', schedule_data=schedule_data)


@app.route('/about')
def about_page():
    return render_template('About.html')

@app.route('/contact')
def contact_us_page():
    return render_template('Contact_Us.html')

@app.route('/admin_about')
def admin_about_page():
    return render_template('Admin_about_us.html')

@app.route('/admin_contact')
def admin_contact_us_page():
    return render_template('Admin_Contact_Us.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    name = request.form['name']
    prn = request.form['prn']
    email = request.form['email']
    password = generate_password_hash(request.form['password'])
    contact_number = request.form['contact']
    department = request.form['department']
    birthdate = request.form['birthdate']
    gender = request.form['gender']
    course = request.form['course']
    address = request.form['address']
    cgpa = request.form['cgpa']
    resume = request.files['resume']
    interest = request.form['interest']
    academic_year = request.form['academic_year']

    resume_filename = secure_filename(resume.filename)
    resume.save(os.path.join(app.config['UPLOAD_FOLDER'], resume_filename))

    conn = sqlite3.connect('Database/placement_system.db')
    cursor = conn.cursor()

    cursor.execute("INSERT INTO users (Username, Password, User_Type) VALUES (?, ?, ?)",
                   (username, password, 'student'))
    conn.commit()

    cursor.execute(
        "INSERT INTO student_list (Username, Name, PRN, Email, Contact_Number, Department, Birthdate, Gender, Course, Address, CGPA, Resume, Interest, academic_year) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (username, name, prn, email, contact_number, department, birthdate, gender, course, address, cgpa,
         resume_filename, interest, academic_year))
    conn.commit()

    conn.close()

    return redirect(url_for('index'))

@app.route('/admin_update_company')
def admin_update_company():
    page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')

    conn = sqlite3.connect('Database/placement_system.db')
    cursor = conn.cursor()

    # Fetch total number of companies
    cursor.execute("SELECT COUNT(*) FROM companies")
    total_companies = cursor.fetchone()[0]

    # Fetch companies for the current page
    cursor.execute("SELECT * FROM companies LIMIT ? OFFSET ?", (per_page, offset))
    companies = cursor.fetchall()

    conn.close()

    pagination = Pagination(page=page, total=total_companies, per_page=per_page, offset=offset, css_framework='bootstrap4')

    return render_template('Admin_Update_Company.html', companies=companies, pagination=pagination)

@app.route('/send_email', methods=['POST'])
@login_required
def send_email():
    # Call the send_notification function from sendemailstudent.py
    send_notification()
    flash('Email notifications sent successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_company', methods=['GET', 'POST'])
def admin_add_company():
    if request.method == 'POST':
        company_name = request.form['company_name']
        industry = request.form['industry']
        location = request.form['location']
        date = request.form['date']
        venue = request.form['venue']
        salary = request.form.get('salary')
        role = request.form.get('role')
        deadline = request.form.get('deadline')
        vacancies = request.form.get('vacancies')  # Add this line to capture vacancies
        
        company_detail_pdf = request.files['company_detail_pdf']
        if company_detail_pdf:
            filename = secure_filename(company_detail_pdf.filename)
            company_detail_pdf.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            filename = None

        # Insert the new company into the database
        conn = sqlite3.connect('Database/placement_system.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO companies (company_name, industry, location, Date, Venue, salary, role, deadline, vacancies, company_detail_pdf) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (company_name, industry, location, date, venue, salary, role, deadline, vacancies, filename))
        conn.commit()
        conn.close()

        flash('Company added successfully!', 'success')
        return redirect(url_for('admin_update_company'))

    return render_template('Admin_Add_Company.html')


if __name__ == '__main__':
    app.run(debug=True)
