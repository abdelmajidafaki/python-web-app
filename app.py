from flask import Flask, render_template, request, flash, redirect, url_for,abort
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, date,timezone
from sqlalchemy.orm import aliased
from collections import defaultdict
from functools import wraps
import secrets
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth
load_dotenv()
from flask_cors import CORS



webapp = Flask(__name__)
bcrypt = Bcrypt(webapp)
webapp.secret_key = 'test'
webapp.config['SESSION_TYPE'] = 'filesystem'
webapp.config['SESSION_COOKIE_HTTPONLY'] = True
webapp.config['SESSION_COOKIE_SECURE'] = True
webapp.config["SQLALCHEMY_DATABASE_URI"] = "mysql://root:@localhost/python_project"

'''
oauth = OAuth(webapp)
TELEGRAM_BOT_TOKEN ='6812826346:AAEYnoM8hbvhrlY8pxPngUD38W5GK14hNM4'
TELEGRAM_BOT_API_URL = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}'
'''
db = SQLAlchemy(webapp)

login_manager = LoginManager()
login_manager.init_app(webapp)
CORS(webapp, resources={r"/*": {"origins": "*"}})

#models
class users(db.Model, UserMixin):
    __tablename__ = 'users'
    userid = db.Column(db.Integer, primary_key=True)
    fulname = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    Pasword = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='inprogress')
    
    usertype = db.Column(db.String(20), default='not defined')
    Utoken = db.Column(db.String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe())
    
    def get_id(self):
        return str(self.userid)

class Task(db.Model):
    __tablename__ = 'tasks'
    task_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date)
    close_date = db.Column(db.Date)
    description = db.Column(db.Text, nullable=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.userid'), nullable=False)
    status = db.Column(db.String(20), default='In Progress')
    admin = db.relationship("users", foreign_keys=[admin_id], backref=db.backref("admin_tasks", lazy=True))
    token = db.Column(db.String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe())
class TaskAssignment(db.Model):
    __tablename__ = 'task_assignments'
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.task_id'), primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('users.userid'), primary_key=True)
    task = db.relationship("Task", backref=db.backref("assignments", cascade="all, delete-orphan"))
    employee = db.relationship("users", backref=db.backref("assigned_tasks", cascade="all, delete-orphan"))

class Task_Progression(db.Model):
    __tablename__ = 'task_progression'

    prog_id = db.Column(db.Integer, primary_key=True)
    progname = db.Column(db.String(255), nullable=False)
    start_at = db.Column(db.Date, nullable=False)
    end_at = db.Column(db.Date, nullable=True)
    statut = db.Column(db.String(255), nullable=True, default='inprogress')
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.task_id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('users.userid'), nullable=False)

    task = db.relationship('Task', backref=db.backref('task_progressions', lazy=True))
    employee = db.relationship('users', backref=db.backref('task_progressions', lazy=True))

    def __repr__(self):
        return f"<TaskProgression prog_id={self.prog_id}, progname={self.progname}, task_id={self.task_id}, employee_id={self.employee_id}, statut={self.statut}>"
class PersonalTask(db.Model):
    __tablename__ = 'PersonalTasks'

    PTDID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    TaskName = db.Column(db.String(255), nullable=False)
    DoAt = db.Column(db.Date)
    CompletedAt = db.Column(db.Date)
    Description = db.Column(db.Text, nullable=True)
    State = db.Column(db.String(255), nullable=False, default='in progress')
    employee_id = db.Column(db.Integer, db.ForeignKey('users.userid'), nullable=True)
    token = db.Column(db.String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe())
class PersonalTaskProgression(db.Model):
    __tablename__ = 'personal_task_progression'

    prog_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Ptask_id = db.Column(db.Integer, db.ForeignKey('PersonalTasks.PTDID'), nullable=False)
    progname=db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(255), nullable=False)
    
    start_at = db.Column(db.Date, nullable=False)
    completed_at = db.Column(db.Date, nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('users.userid'), nullable=True)

   


'''
# Initialize OAuth
oauth = OAuth(webapp)
telegram = oauth.register(
    'telegram',
    client_id='21484942',
    client_secret='5fc20f9deee8f563f3d8a11ae4970cef',
    authorize_url='https://oauth.telegram.org/authorize',
    authorize_params=None,
    access_token_url='https://oauth.telegram.org/token',
    access_token_params=None,
    refresh_token_url=None,
    redirect_uri='/http://127.0.0.1:5000/login/telegram/authorized',
    client_kwargs={'scope': 'user:email'},
)
'''



#authntication
@login_manager.user_loader
def load_user(user_id):
    return users.query.get(int(user_id))

@webapp.route("/", methods=['GET', 'POST'])
def indexpage():
    return redirect(url_for('loginpage'))

@webapp.route("/register", methods=['GET', 'POST'])
def registerpage():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        cpassword = request.form['cpassword']
        if fullname and email:
            if password == cpassword:
                
                new_user = users(fulname=fullname, email=email, Pasword=cpassword)
                db.session.add(new_user)
                db.session.commit()
                flash("Registration successful!", 'success')
            else:
                flash("Passwords do not match. Please try again.", 'danger')
        else:
            flash("You must fill all inputs.", 'danger')
        return render_template("registerpage.html")
    return render_template("registerpage.html")

@webapp.route("/logout", methods=['GET'])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", 'info')
    return redirect(url_for('loginpage'))


@webapp.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@webapp.route("/login", methods=['GET', 'POST'])
def loginpage():
    if current_user.is_authenticated:
        if current_user.usertype == "Admin":
            return redirect(url_for('homepage'))  
        elif current_user.usertype == "employee":
            return redirect(url_for('employee'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.Pasword, password):
            if user.status == "active":
                login_user(user)
                flash("Login successful!", 'success')
                if user.usertype == "Admin":
                    return redirect(url_for('homepage'))
                elif user.usertype == "employee":
                    return redirect(url_for('employee'))
            elif user.status == "inactive":
                flash("Your account is inactive. Please contact administration to activate your account.", 'danger')
            else:
                flash("Your account should be activated.", 'danger')
        else:
            flash("Invalid email or password. Please try again.", 'danger')

    if current_user.is_authenticated and request.method == 'GET':
        return redirect(url_for('homepage'))
    return render_template("loginpage.html")


#---------------------------------------------------------------------------telegraaam---------------------------------------------------------
'''
@webapp.route('/login/telegram')
def telegram_login():
    redirect_uri = url_for('telegram_authorized', _external=True)
    return oauth.telegram.authorize_redirect(redirect_uri)

@webapp.route('/login/telegram/authorized')
def telegram_authorized():
    if 'error' in request.args:
        flash('Telegram login failed', 'danger')
        return redirect(url_for('loginpage'))

    telegram_id = request.args.get('id')
    first_name = request.args.get('first_name')
    username = request.args.get('username')
    auth_date = request.args.get('auth_date')
    hash = request.args.get('hash')

    # Verify the Telegram hash
    if not verify_telegram_hash(request.args, hash):
        flash('Invalid Telegram login', 'danger')
        return redirect(url_for('loginpage'))

    user = users.query.filter_by(telegram_id=telegram_id).first()
    if not user:
        user = users(
            fullname=first_name,
            email=username,
            telegram_id=telegram_id
        )
        db.session.add(user)
        db.session.commit()

    login_user(user)
    flash("Login successful via Telegram!", 'success')
    return redirect(url_for('homepage'))

def verify_telegram_hash(params, hash):
    secret = os.getenv('TELEGRAM_BOT_TOKEN')  # Use your bot token or another secret key
    hash_string = ''.join(f'{k}={v}\n' for k, v in sorted(params.items()) if k != 'hash')
    hash_string += secret
    return hash == hashlib.sha256(hash_string.encode('utf-8')).hexdigest()#
'''
#-------------------------------------------------------------------------------------------------------------------------------------------------------------------    

def employee_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.usertype != "employee":
            flash("You do not have permission to access this page.", 'danger')
            return redirect(url_for('loginpage'))
        return func(*args, **kwargs)
    return decorated_function




#------------------------------------------------------------employeside--------------------------------------------------------------------------------------------
@webapp.route("/employee", methods=['GET', 'POST'])
@login_required
@employee_required
def employee():
    user_id = current_user.userid
    user = users.query.get(user_id)

    if user:
        assigned_tasks = db.session.query(Task) \
            .join(TaskAssignment, Task.task_id == TaskAssignment.task_id) \
            .filter(TaskAssignment.employee_id == user_id) \
            .all()

        today = date.today()

        tasks = []

        for task in assigned_tasks:
            if task.start_date > today:
                status = "Upcoming"
                daystoclose = None
            elif task.start_date <= today and (task.close_date is None or task.close_date >= today) and task.status == 'In Progress':
                status = "Open"
                if task.close_date:
                    daystoclose = (task.close_date - today).days
                else:
                    daystoclose = None
            elif task.status == 'COMPLETED':
                status = "Closed"
                daystoclose = None
            else:
                status = "Closed"
                daystoclose = None

            admin_name = task.admin.fulname 
            tasks.append((task, admin_name, status, daystoclose))

        def to_datetime(d):
            if isinstance(d, datetime):
                return d
            elif isinstance(d, date):
                return datetime.combine(d, datetime.min.time())
            else:
                return datetime.max
        def sort_key(task_info):
            task, _, status, daystoclose = task_info
            start_date = to_datetime(task.start_date)
            close_date = to_datetime(task.close_date)

            if status == 'Open':
                return (0, close_date)
            elif status == 'Upcoming':
                return (1, start_date)
            else:
                return (2, datetime.max)
        tasks.sort(key=sort_key)

        return render_template("employee/employeepage.html", user=user, tasks=tasks)
    else:
        flash("User not found. Please log in again.", 'danger')
        return redirect(url_for('loginpage'))



@webapp.route("/employee/taskdetails/<token>/<etoken>", methods=['GET', 'POST'])
@login_required
@employee_required

def taskdetails(token, etoken):
    user_id = current_user.userid
    user = users.query.get(user_id)
    task = Task.query.filter_by(token=token).first()
    employee=users.query.filter_by(Utoken=etoken).first()
    task_assignment = TaskAssignment.query.filter_by(task_id=task.task_id, employee_id=employee.userid).first()
    
    
    task_progressions = Task_Progression.query.filter_by(task_id=task.task_id, employee_id=employee.userid).all()
    if task:
        if request.method == 'POST':
            if 'mark_task_done' in request.form:
                
                task.status = 'COMPLETED'  
                db.session.commit()
                flash('Task marked as done.', 'success')
                return redirect(url_for('taskdetails',token=token, etoken=etoken))
            progression_id = request.form.get('progression_id')
            progression = Task_Progression.query.get(progression_id)

            if progression:
                progression.end_at = date.today()
                progression.statut = 'Completed'

                db.session.commit()
                flash('Progression marked as completed.', 'success')
                return redirect(url_for('taskdetails',token=token, etoken=etoken ))
                
            if progression:
                progression.statut = 'Completed'
                db.session.commit()
                flash('Progression marked as completed successfully.', 'success')
                return redirect(url_for('taskdetails',token=token, etoken=etoken))
            else:
                flash('Progression not found.', 'danger')   

        today = date.today()
        if task.start_date > today:
                status = "Upcoming"
        elif task.start_date <= today and (task.close_date is None or task.close_date >= today) and task.status == 'In Progress':
                status = "Open"
        elif  task.status == 'COMPLETED':
                status = "Closed"
        else:
                status = "Closed"
            
        return render_template("employee/taskdetails.html", user=user, task=task, task_assignment=task_assignment, task_progressions=task_progressions, status=status)
    else:
        flash("Task not found.", 'danger')
    return redirect(url_for('employee'))

@webapp.route('/employee/taskdetails/addprogression/<token>/<etoken>', methods=['GET', 'POST'])
@login_required
@employee_required
def addprogression(token, etoken):
    user_id = current_user.userid
    user = users.query.get(user_id)
    employee=users.query.filter_by(Utoken=etoken).first()
    task = Task.query.filter_by(token=token).first()
    task_assignment = TaskAssignment.query.filter_by(task_id=task.task_id, employee_id=employee.userid).first()

    if task_assignment:
        if request.method == 'POST':
            
            progname = request.form.get('progname')
            start_at = request.form.get('start_at')
            if not start_at or start_at == '0000-00-00':
                start_at = date.today() 

    
            if isinstance(start_at, str):
                try:
                    start_at = date.fromisoformat(start_at) 
                except ValueError:
                    start_at = date.today()
            new_progression = Task_Progression(progname=progname,
                                            start_at=start_at,
                                            task_id=task.task_id,
                                            employee_id =employee.userid)
            
            
            db.session.add(new_progression)
            db.session.commit()
            print(f"start_at: {start_at }")
            flash('Task progression added successfully.', 'success')
            return redirect(url_for('employee')) 
        else:
            
            return render_template('employee/taskprog.html', task_id=task.task_id, employee_id=user_id)
    else:
        flash('You are not authorized to add progression for this task.', 'danger')
        return redirect(url_for('taskdetails'))
    
#-------------------------------------------------------------------------------personal task-----------------------------------------------------------------------------------
@webapp.route('/employee/addpersonaltask', methods=['GET', 'POST'])
@login_required
@employee_required
def addpertask():

    user = current_user
    if request.method == 'POST':
        task_name = request.form.get('taskName')
        do_at = request.form.get('doAt')
        completed_at = request.form.get('completedAt')
        state = request.form.get('state')
        description= request.form.get('description')           
        employee_id=user.userid
        if do_at :
            do_at=do_at
        else: do_at= date.today()
     
        new_task = PersonalTask(
            TaskName=task_name,
            DoAt=do_at ,
            CompletedAt=completed_at if completed_at else None,
            State=state,employee_id=employee_id,
            Description=description if description else None,
            token=secrets.token_urlsafe()
        )

        db.session.add(new_task)
        db.session.commit()
      
        return redirect(url_for('personaltasks'))
    
    return render_template('employee/addpertask.html')


@webapp.route('/employee/delete_pertask/<string:token>')
@login_required
@employee_required
def delete_pertask(token):
    task = PersonalTask.query.filter_by(token=token).first_or_404()
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('personaltasks'))


@webapp.route('/employee/toggle_pertask/<string:token>/<string:action>')
@login_required
@employee_required
def toggle_pertask(token, action):
    
    task = PersonalTask.query.filter_by(token=token).first_or_404()
    
    
    if action == 'complete':
        task.State = 'completed'
        task.CompletedAt = date.today()
        flash('Task marked as completed.', 'success')
    elif action == 'rollback':
        task.State = 'in progress'
        task.CompletedAt = None
        flash('Task mark rolled back', 'warning')  

    
    db.session.commit()

    
    return redirect(url_for('personaltasks'))


@webapp.route('/employee/edit_pertask/<string:token>', methods=['GET', 'POST'])
@login_required
@employee_required
def edit_pertask(token):
    task = PersonalTask.query.filter_by(token=token).first_or_404()
    
    if request.method == 'POST':
        task.TaskName = request.form.get('taskName')
        task.Description= request.form.get('description') 
        task.DoAt = request.form.get('doAt')
        task.CompletedAt = request.form.get('completedAt')
        db.session.commit()
        return redirect(url_for('personaltasks'))
    
    return render_template('employee/editpertask.html', task=task)


@webapp.route('/employee/personaltasks')
@login_required
@employee_required
def personaltasks():
    user = current_user
    

    tasks = PersonalTask.query.filter(PersonalTask.employee_id == user.userid).all()
    return render_template('employee/personalstask.html', tasks=tasks)

@webapp.route('/employee/personaltasks/personaltaskdetail/<Ptoken>', methods=['GET', 'POST'])
@login_required
@employee_required
def personaltaskdetail(Ptoken):
    
    task = PersonalTask.query.filter_by(token=Ptoken).first()
    task_progressions = PersonalTaskProgression.query.filter_by(Ptask_id=task.PTDID).all()

    if request.method == 'POST':
        if 'mark_task_done' in request.form:
            
            task.State = 'completed'
            task.CompletedAt= date.today()
            db.session.commit()
            flash('Task marked as completed.', 'success')
            return redirect(url_for('personaltaskdetail', Ptoken=Ptoken))
        if 'Task_not_done' in request.form:
            
            task.State = 'in progress'
            task.CompletedAt= None
            db.session.commit()
            flash('Task mark is rolled back.', 'success')
            return redirect(url_for('personaltaskdetail', Ptoken=Ptoken))

        if 'progression_id' in request.form:
            
            progression_id = request.form.get('progression_id')
            progression = PersonalTaskProgression.query.get(progression_id)

            if progression:
                progression.completed_at = date.today()
                progression.status = 'Completed'
                db.session.commit()
                flash('Progression marked as completed.', 'success')
                return redirect(url_for('personaltaskdetail', Ptoken=Ptoken))
            else:
                flash('Progression not found.', 'danger')
    
    return render_template('employee/personal_taskdetail.html', task=task, task_progressions=task_progressions)

@webapp.route('/employee/personaltasks/personaltaskdetail/addpersonalprogression/<Ptoken>', methods=['GET', 'POST'])
@login_required
@employee_required
def addpersonalprogression(Ptoken):

    task = PersonalTask.query.filter_by(token=Ptoken).first()

    if not task:
        flash('Personal Task not found.', 'danger')
        return redirect(url_for('personaltasks'))

    if request.method == 'POST':
        
        progname = request.form.get('progname')
        start_at = request.form.get('start_at')
        
        if not progname:
            flash('Progress name is required.', 'danger')
            return redirect(url_for('addpersonalprogression', Ptoken=Ptoken))
        
        if not start_at or start_at == '0000-00-00':
            start_at = date.today() 

        if isinstance(start_at, str):
            try:
                start_at = date.fromisoformat(start_at) 
            except ValueError:
                start_at = date.today()
        
       
        new_progression = PersonalTaskProgression(
            Ptask_id=task.PTDID,
            progname=progname,
            status='in progress',
            start_at=start_at,
            employee_id=current_user.userid
        )
        
        db.session.add(new_progression)
        db.session.commit()
        flash('Personal Task Progression added successfully.', 'success')
        return redirect(url_for('personaltaskdetail', Ptoken=Ptoken))
    
    return render_template('employee/add_personal_progression.html', task=task)
#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------admin side----------------------------------------------------------------------------------------
def admin_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.usertype != "Admin":
            flash("You do not have permission to access this page.", 'danger')
            return redirect(url_for('loginpage'))
        return func(*args, **kwargs)
    return decorated_function

@webapp.route("/homepage", methods=['GET', 'POST'])
@login_required
@admin_required
def homepage():
    user_id = current_user.userid
    user = users.query.filter_by(userid=user_id).first()
    
    if user:
        if user.usertype == "Admin":
            fullname = user.fulname
            all_users = users.query.all()
            return render_template("admin/homepage.html", fullname=fullname, all_users=all_users)
        elif user.usertype == "employee":
            return redirect(url_for('employee'))

    flash("You are not logged in. Please log in to access this page.", 'danger')
    return redirect(url_for('loginpage'))

@webapp.route('/update_status/<int:userid>', methods=['POST'])
@login_required
@admin_required
def update_status(userid):
    user = current_user
    if user.usertype == "Admin":
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
    elif user.usertype == "employee":
        return redirect(url_for('employee'))
    else:
        flash("You need to login first.", 'danger')
        return redirect(url_for('loginpage'))
    

@webapp.route("/tasks/taskdetail/<token>", methods=['GET', 'POST'])
@login_required
@admin_required
def taskdetail(token):
    user_id = current_user.userid
    user = users.query.get(user_id)
    task = Task.query.filter_by(token=token).first()
    
    task_assignment = TaskAssignment.query.filter_by(task_id=task.task_id).first()
    task_progressions = Task_Progression.query.filter_by(task_id=task.task_id).all()
    if task:  
        if request.method == 'POST':
            if 'opentask' in request.form:
                
                task.status = 'In Progress'  
                db.session.commit()
                flash('Task is open ', 'success')
                return redirect(url_for('tasks'))
            elif 'closetask' in request.form:
                
                task.status = 'task Closed By Admin'  
                db.session.commit()
                flash('Task is closed ', 'success')
                return redirect(url_for('tasks'))    
        today = date.today()
        if task.start_date > today:
                status = "Upcoming"
        elif task.start_date <= today and (task.close_date is None or task.close_date >= today) and task.status == 'In Progress':
                status = "Open"
        elif  task.status == 'COMPLETED':
                status = "Closed"
        else:
                status = "Closed"
            
        return render_template("admin/taskdetail.html", user=user, task=task, task_assignment=task_assignment, task_progressions=task_progressions, status=status)
    else:
        flash("Task not found.", 'danger')
    return redirect(url_for('admintasks'))
@webapp.route("/tasks", methods=['GET', 'POST'])
@login_required
@admin_required
def tasks():
    user = current_user

    if user.usertype == "Admin":
        if request.method == 'POST':
            task_id = request.form.get('task_id')
            task = Task.query.get(task_id)
            if task:
                if 'opentask' in request.form:
                    task.status = 'In Progress'
                    db.session.commit()
                    flash('Task is open', 'success')
                elif 'closetask' in request.form:
                    task.status = 'task Closed By Admin'
                    db.session.commit()
                    flash('Task is closed', 'success')
            return redirect(url_for('tasks'))

        admin_alias = aliased(users)
        tasksq = db.session.query(Task, admin_alias.fulname.label('admin_name'), users.fulname.label('employee_name')) \
            .join(admin_alias, Task.admin_id == admin_alias.userid) \
            .outerjoin(TaskAssignment, Task.task_id == TaskAssignment.task_id) \
            .outerjoin(users, TaskAssignment.employee_id == users.userid) \
            .all()

        task_dict = defaultdict(lambda: {'task': None, 'admin_name': '', 'employee_names': [], 'status': ''})
        for task, admin_name, employee_name in tasksq:
            if task not in task_dict:
                task_dict[task]['task'] = task
                task_dict[task]['admin_name'] = admin_name
            if employee_name:
                task_dict[task]['employee_names'].append(employee_name)
            task_dict[task]['status'] = calculate_task_status(task)

        tasks = [(v['task'], v['admin_name'], ', '.join(v['employee_names']), v['status']) for v in task_dict.values()]

        def to_datetime(d):
            return datetime.combine(d, datetime.min.time()) if isinstance(d, date) else d or datetime.max

        def sort_key(task_info):
            task, _, _, status = task_info
            start_date = to_datetime(task.start_date)
            close_date = to_datetime(task.close_date)
            if status == 'Open':
                return (0, close_date)
            elif status == 'Upcoming':
                return (1, start_date)
            else:
                return (2, datetime.max)

        tasks.sort(key=sort_key)

        return render_template("admin/tasks.html", tasks=tasks)
    
    elif user.usertype == "employee":
        return redirect(url_for('employee'))
    


def calculate_task_status(task):
    today = date.today()
    if task.start_date > today and task.status == 'In Progress':
        return "Upcoming"
    elif task.start_date <= today and (task.close_date is None or task.close_date >= today) and task.status == 'In Progress':
        return "Open"
    elif task.status == 'COMPLETED':
        return "Closed"
    else:
        return "Closed"

@webapp.route("/tasks/addnewtask", methods=['GET', 'POST'])
@login_required
@admin_required
def addnewtask():
    user = current_user
    if user.usertype == "Admin":
        employees = users.query.filter_by(usertype='employee').all()

        if request.method == 'POST':
            task_name = request.form['task_name']
            startdate = request.form['start_date']
            description = request.form.get('description')
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
            new_task = Task(task_name=task_name, start_date=start_date, close_date=close_date,
                            admin_id=user.userid, description=description,token=secrets.token_urlsafe())
            db.session.add(new_task)
            db.session.commit()

            for employee_id in selected_employee_ids:
                assignment = TaskAssignment(task_id=new_task.task_id, employee_id=employee_id)
                db.session.add(assignment)

            db.session.commit()
            flash('New task added successfully!', 'success')
            return render_template("admin/addtasks.html", employees=employees)

        return render_template("admin/addtasks.html", employees=employees)
    
    elif user.usertype == "employee":
        return redirect(url_for('employee'))



@webapp.route("/tasks/delete/<int:task_id>", methods=['POST'])
@login_required
@admin_required
def delete_task(task_id):
    user = current_user
    if user.usertype == "Admin":
        task = Task.query.get(task_id)
        if task:
            
                
                db.session.query(Task_Progression).filter(Task_Progression.task_id == task_id).delete(synchronize_session='fetch')

                db.session.query(TaskAssignment).filter(TaskAssignment.task_id == task_id).delete(synchronize_session='fetch')
                db.session.query(Task).filter(Task.task_id == task_id).delete(synchronize_session='fetch')
                db.session.commit()
                flash('Task deleted successfully!', 'success')
            
        else:
            flash('Task not found.', 'danger')
    else:
        flash("You do not have permission to delete this task.", 'danger')
    
    return redirect(url_for('tasks'))


@webapp.route("/tasks/update/<token>", methods=['GET', 'POST'])
@login_required
@admin_required
def update_task(token):
    user = current_user
    if user.usertype == "Admin":
        employees = users.query.filter_by(usertype='employee').all()
        task = Task.query.filter_by(token=token).first()

        if task:
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

                task.task_name = task_name
                task.start_date = start_date
                task.close_date = close_date
                TaskAssignment.query.filter_by(task_id=task.task_id).delete()
                for employee_id in selected_employee_ids:
                    assignment = TaskAssignment(task_id=task.task_id, employee_id=employee_id)
                    db.session.add(assignment)

                db.session.commit()
                flash('Task updated successfully!', 'success')
                return redirect(url_for('tasks'))

            return render_template("admin/update_task.html", task=task, employees=employees)

        flash('Task not found or you do not have permission to update it.', 'danger')
        return redirect(url_for('tasks'))

    flash("You are not logged in. Please log in to access this page.", 'danger')
    return redirect(url_for('loginpage'))

#---------------------------------------------------------admin----------------employe details -------------------------------------------------------------------------------------------------------


@webapp.route("/userdetails/<Utoken>", methods=['GET'])
@login_required
@admin_required
def userdetails(Utoken):
    user = users.query.filter_by(Utoken=Utoken).first()
    
    if not user:
        abort(404)  

    
    personal_tasks = PersonalTask.query.filter(PersonalTask.employee_id == user.userid).all()
    
    
    assigned_tasks = Task.query.join(TaskAssignment, Task.task_id == TaskAssignment.task_id) \
                               .filter(TaskAssignment.employee_id == user.userid).all()
    
    now = datetime.now(tz=timezone.utc)
    tasks = []

    if user.usertype == 'Admin':
        
        created_tasks = Task.query.filter(Task.admin_id == user.userid).all()
        for task in created_tasks:
            
            start_date = task.start_date if isinstance(task.start_date, datetime) else datetime.combine(task.start_date, datetime.min.time(), tzinfo=timezone.utc)
            close_date = task.close_date if isinstance(task.close_date, datetime) else datetime.combine(task.close_date, datetime.min.time(), tzinfo=timezone.utc) if task.close_date else None
            
            status = "Closed"
            daystoclose = None
            
            if start_date > now:
                status = "Upcoming"
            elif start_date <= now and (close_date is None or close_date >= now) and task.status == 'In Progress':
                status = "Open"
                if close_date:
                    daystoclose = (close_date - now).days
            elif task.status == 'COMPLETED':
                status = "Closed"
            
            admin_name = user.fulname
            tasks.append((task, admin_name, status, daystoclose))

    else: 
        for task in assigned_tasks:
            start_date = task.start_date if isinstance(task.start_date, datetime) else datetime.combine(task.start_date, datetime.min.time(), tzinfo=timezone.utc)
            close_date = task.close_date if isinstance(task.close_date, datetime) else datetime.combine(task.close_date, datetime.min.time(), tzinfo=timezone.utc) if task.close_date else None
            
            status = "Closed"
            daystoclose = None
            
            if start_date > now:
                status = "Upcoming"
            elif start_date <= now and (close_date is None or close_date >= now) and task.status == 'In Progress':
                status = "Open"
                if close_date:
                    daystoclose = (close_date - now).days
            elif task.status == 'COMPLETED':
                status = "Closed"
            
            admin_name = task.admin.fulname
            tasks.append((task, admin_name, status, daystoclose))

    return render_template("admin/userdetails.html", user=user, personal_tasks=personal_tasks, tasks=tasks)


@webapp.route('/userdetails/employepertask/<string:token>')
@login_required
@admin_required
def employepertask(token):
    task = PersonalTask.query.filter_by(token=token).first_or_404()
    
    task_progressions = PersonalTaskProgression.query.filter_by(Ptask_id=task.PTDID).all()
    
    return render_template(
        "admin/employeeperstask.html",
        task=task,
        task_progressions=task_progressions
    )




if __name__ == '__main__':
    
    webapp.run(debug=True)
