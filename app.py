from  flask import Flask,render_template,request,flash,session,redirect,url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime,date    
from sqlalchemy.orm import aliased




webapp=Flask(__name__)
bcrypt = Bcrypt(webapp)
webapp.secret_key = 'test'
webapp.config['SESSION_TYPE'] = 'filesystem'
webapp.config["SQLALCHEMY_DATABASE_URI"] = "mysql://root:@localhost/python_project"
db = SQLAlchemy(webapp)


class users(db.Model):
    __tablename__ = 'users'
    userid = db.Column(db.Integer, primary_key=True)
    fulname = db.Column(db.String(255), nullable=False)  
    email = db.Column(db.String(255), nullable=False)
    Pasword = db.Column(db.String(255), nullable=False)
    status=db.Column(db.String(20), default='inprogress')
    usertype=db.Column(db.String(20),  default='not defined')

class Task(db.Model):
    __tablename__ = 'tasks'
    
    task_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date)
    close_date = db.Column(db.Date)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.userid'), nullable=False)
    status = db.Column(db.String(20), default='In Progress')
    admin = db.relationship("users", foreign_keys=[admin_id], backref=db.backref("admin_tasks", lazy=True)) 


class TaskAssignment(db.Model):
    __tablename__ = 'task_assignments'
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.task_id'), primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('users.userid'), primary_key=True)
    task = db.relationship("Task", backref=db.backref("assignments", cascade="all, delete-orphan"))
    employee = db.relationship("users", backref=db.backref("assigned_tasks", cascade="all, delete-orphan"))

@webapp.route("/", methods=['GET', 'POST'])
def indexpage():
    return redirect(url_for('homepage'))

@webapp.route("/register", methods=['GET', 'POST'])
def registerpage():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        cpassword=request.form['cpassword']
        if fullname and email :
            if password==cpassword:
                Bcrypt_ps = bcrypt.generate_password_hash(password).decode('utf-8')
                new_user = users(fulname=fullname, email=email, Pasword=Bcrypt_ps)
                db.session.add(new_user)
                db.session.commit()
                flash("Registration successful!", 'success')
            else:
                flash("Passwords do not match. Please try again.", 'primary')    
        else:
            flash("You must fill all inputs.", 'primary')   
        return render_template("registerpage.html")
    return render_template("registerpage.html")



@webapp.route("/login", methods=['GET', 'POST'])
def loginpage():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users.query.filter_by(email=email).first()
        if user:
            if bcrypt.check_password_hash(user.Pasword, password):    
                if user.status=="active":
                    if user.usertype=="Admin":
                        flash("Login successful!", 'success')
                        session['user'] = user.userid
                        return redirect(url_for('homepage'))
                    elif user.usertype=="Employee":
                        return redirect(url_for('Employeepage'))
                elif user.status=="inactive":
                    flash("Your account is inactive. Please contact administration to activate your account.", 'danger')
                else:    
                    flash("the account should be activated", 'danger')
            else:
                flash("Invalid email or password. Please try again.", 'danger')
        else:
                flash("Invalid email or password. Please try again.", 'danger')          
    if 'user' in session:
        return redirect(url_for('homepage'))
    return render_template("loginpage.html") 

@webapp.route('/update_status/<int:userid>', methods=['POST'])
def update_status(userid):
    if 'user' in session: 
        user = users.query.filter_by(userid=userid).first()
        if not user:
            flash("User not found.", 'danger')
        else:
            if 'action' in request.form:
                action = request.form['action']
                if action == 'activate':
                    user.status = 'active'
                elif action == 'deactivate':
                    user.status = 'inactive'
                db.session.commit()
                flash(f"User status updated successfully ({action})", 'success')
            elif 'usertype' in request.form:
                usertype = request.form['usertype']
                if usertype == 'Admin':
                    user.usertype = 'Admin'
                elif usertype == 'employee':
                    user.usertype = 'employee'
                db.session.commit()
                flash(f"User type updated successfully ({usertype})", 'success')
        return redirect(url_for('homepage'))
    else:
        flash("You need to login first.", 'danger')
        return redirect(url_for('login'))

@webapp.route("/homepage", methods=['GET', 'POST'])
def homepage():
    if 'user' in session:
        user_id = session['user']  
        user = users.query.filter_by(userid=user_id).first()  
        if user:
            fullname = user.fulname 
            all_users = users.query.all()
            return render_template("homepage.html", fullname=fullname,all_users=all_users)
    flash("You are not logged in. Please log in to access this page.", 'danger')
    return redirect(url_for('loginpage'))


@webapp.route("/tasks", methods=['GET', 'POST'])
def tasks():
    tasks = []
    if 'user' in session:
        user_id = session['user']  
        user = users.query.filter_by(userid=user_id).first()
        if user:
            admin_alias = aliased(users)
            tasks_query = db.session.query(Task,admin_alias.fulname.label('admin_name'),users.fulname.label('employee_name')).\
                                        join(admin_alias, Task.admin_id == admin_alias.userid).\
                                        outerjoin(TaskAssignment, Task.task_id == TaskAssignment.task_id).\
                                        outerjoin(users, TaskAssignment.employee_id == users.userid).all()

            current_task_id = None
            current_task = None
            admin_name = None
            employee_names = []

            for task, admin_name, employee_name in tasks_query:
                if current_task_id is None:
                    current_task_id = task.task_id
                    current_task = task
                    admin_name = admin_name

                if task.task_id != current_task_id:
                    tasks.append((current_task, admin_name, employee_names))
                    current_task_id = task.task_id
                    current_task = task
                    employee_names = []

                if employee_name:
                    employee_names.append(employee_name)

            if current_task is not None:
                tasks.append((current_task, admin_name, employee_names))

            return render_template("tasks.html", tasks=tasks)
    flash("You are not logged in. Please log in to access this page.", 'danger')
    return redirect(url_for('loginpage'))

@webapp.route("/tasks/addnewtask", methods=['GET', 'POST'])
def addnewtask():
    if 'user' in session:
        user_id = session['user']  
        user = users.query.filter_by(userid=user_id).first()
        employees = users.query.filter_by(usertype='employee').all()  
        if user:
            if request.method == 'POST':
                task_name = request.form['task_name']
                startdate = request.form['start_date']
                try:
                    start_date = datetime.strptime(startdate, '%Y-%m-%d').date()
                except ValueError:
                    flash('Invalid start date format.', 'danger')
                    return render_template("addtasks.html", employees=employees)
                

                today = date.today()
                if start_date < today:
                    flash('Start date cannot be in the past.', 'danger')
                    return render_template("addtasks.html", employees=employees)
                
                close_date = request.form.get('close_date', None)
                if close_date:
                    close_date = datetime.strptime(close_date, '%Y-%m-%d').date()
                else:
                    close_date = None


                selected_employee_ids = request.form.getlist('employees[]')
                new_task = Task(task_name=task_name, start_date=start_date, close_date=close_date, admin_id=user_id)
                db.session.add(new_task)
                db.session.commit() 


                for employee_id in selected_employee_ids:
                    assignment = TaskAssignment(task_id=new_task.task_id, employee_id=employee_id)
                    db.session.add(assignment)

                db.session.commit()
                flash('New task added successfully!', 'success')
            return render_template("addtasks.html", employees=employees)
    flash("You are not logged in. Please log in to access this page.", 'danger')
    return redirect(url_for('loginpage'))


@webapp.route("/tasks/delete/<int:task_id>", methods=['POST'])
def delete_task(task_id):
    if request.method == 'POST': 
        if 'user' in session:
            
            task = Task.query.get(task_id)
            if task:
                TaskAssignment.query.filter_by(task_id=task_id).delete()
                db.session.delete(task)
                db.session.commit()
                flash('Task deleted successfully!', 'success')
            else:
                flash('Task not found.', 'danger')
            return redirect(url_for('tasks')) 
        else:
            flash("You are not logged in. Please log in to access this page.", 'danger')
            return redirect(url_for('loginpage'))




@webapp.route("/logout", methods=['GET'])
def logout():
    session.pop('user', None)  
    flash("You have been logged out.", 'info')
    return redirect(url_for('loginpage'))


if __name__ == '__main__':  
    webapp.run(debug=True)