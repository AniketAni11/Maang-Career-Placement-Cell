import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import sqlite3

def send_email(receiver_email, company_name, venue, interview_date):
    # Email content
    message = MIMEMultipart()
    message['From'] = 'michtoh4723@gmail.com'
    message['To'] = receiver_email
    message['Subject'] = "Notification: Company Application Reminder"

    body = f"Dear Student,\n\nThis is a reminder that you have an interview scheduled for {company_name}.\n\n"
    body += f"The interview will be held at {venue} on {interview_date}.\n\n"
    body += "We appreciate your interest in joining the team and the effort you put into submitting your application with us.\n"
    body += "Our hiring team is looking forward to meeting you.\n\n"
    body += "Best regards,\nThe Placement Cell"
    
    message.attach(MIMEText(body, 'plain'))

    try:
        # Establish SMTP connection
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587
        sender_email = 'michtoh4723@gmail.com'
        sender_password = 'bwox vqtv vhqh mfsa'  # Update with your Gmail app password or account password

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)

        # Send email
        server.sendmail(sender_email, receiver_email, message.as_string())
        print(f"Email sent successfully to {receiver_email} for {company_name}")

    except Exception as e:
        print(f"Error sending email: {str(e)}")

    finally:
        server.quit()

def send_notification():
    try:
        conn = sqlite3.connect('Database/placement_system.db')
        cursor = conn.cursor()

        cursor.execute("SELECT applied_company, company_date, Email FROM student_list")
        student_data = cursor.fetchall()

        for applied_companies, company_dates, email in student_data:
            companies = applied_companies.split(',') if applied_companies else []
            dates = company_dates.split(',') if company_dates else []
            for company, date in zip(companies, dates):
                cursor.execute("SELECT Venue, Date FROM companies WHERE Company_Name = ?", (company,))
                company_row = cursor.fetchone()
                if company_row:
                    venue = company_row[0]
                    interview_date = company_row[1]
                    check_and_send_email(date, email, company, venue, interview_date)
                else:
                    print(f"No data found for company: {company}")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        conn.close()

def check_and_send_email(date, receiver_email, company_name, venue, interview_date):
    tomorrow = datetime.now() + timedelta(days=1)
    date = date.strip()
    print(f"Date: '{date}', Name: '{company_name}', Venue: '{venue}', Interview Date: '{interview_date}'")
    if date and company_name and venue and interview_date:  # Check if date, name, venue, and interview_date are not None
        if datetime.strptime(date, "%Y-%m-%d").date() == tomorrow.date():
            print(f"Sending email reminder to {receiver_email} for {company_name} at {venue} on {interview_date}")
            send_email(receiver_email, company_name, venue, interview_date)
        else:
            print(f"No email reminder needed for {receiver_email} and {company_name}")
    else:
        print(f"Error: Missing data for {receiver_email}")


if __name__ == "__main__":
    send_notification()

