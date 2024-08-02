from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from extensions import db
from modals import users, Task, TaskAssignment, Task_Progression, PersonalTask, PersonalTaskProgression
from datetime import datetime, date, timezone
import secrets
from collections import defaultdict
from sqlalchemy.orm import aliased
from functools import wraps

admin_routes = Blueprint('admin_routes', __name__)

def admin_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.usertype != "Admin":
            flash("You do not have permission to access this page.", 'danger')
            return redirect(url_for('auth_routes.loginpage'))
        return func(*args, **kwargs)
    return decorated_function

def get_user_or_redirect(user_id):
    user = users.query.filter_by(userid=user_id).first()
    if not user or user.usertype != "Admin":
        flash("You are not logged in or do not have permission to access this page.", 'danger')
        return redirect(url_for('auth_routes.loginpage'))
    return user

def get_task_status(task):
    today = date.today()
    if task.start_date > today:
        return "Upcoming"
    elif task.start_date <= today and (task.close_date is None or task.close_date >= today) and task.status == 'In Progress':
        return "Open"
    elif task.status == 'COMPLETED':
        return "Closed"
    else:
        return "Closed"

def calculate_days_to_close(task, today):
    if task.close_date and task.status == "In Progress":
        return (task.close_date - today).days
    return None

def sort_tasks(tasks):
    def to_datetime(d):
        return datetime.combine(d, datetime.min.time()) if isinstance(d, date) else d or datetime.max

    def sort_key(task_info):
        task, _, _, _, status = task_info
        start_date = to_datetime(task.start_date)
        close_date = to_datetime(task.close_date)
        if status == 'Open':
            return (0, close_date)
        elif status == 'Upcoming':
            return (1, start_date)
        else:
            return (2, datetime.max)

    tasks.sort(key=sort_key)
    return tasks

@admin_routes.route("/usersdashboard", methods=['GET', 'POST'])
@login_required
@admin_required
def usersdashboard():
    user = get_user_or_redirect(current_user.userid)
    all_users = users.query.all()
    return render_template("admin/homepage.html", fullname=user.fulname, all_users=all_users)

@admin_routes.route('/update_status/<int:userid>', methods=['POST'])
@login_required
@admin_required
def update_status(userid):
    user = users.query.filter_by(userid=userid).first()
    if not user:
        flash("User not found.", 'danger')
        return redirect(url_for('admin_routes.usersdashboard'))

    if 'action' in request.form:
        action = request.form['action']
        if action in ['activate', 'deactivate']:
            user.status = 'active' if action == 'activate' else 'inactive'
            flash(f"User status updated successfully ({action})", 'success')
        db.session.commit()

    elif 'usertype' in request.form:
        usertype = request.form['usertype']
        if usertype in ['Admin', 'employee']:
            user.usertype = usertype
            flash(f"User type updated successfully ({usertype})", 'success')
        db.session.commit()

    return redirect(url_for('admin_routes.usersdashboard'))

@admin_routes.route("/tasks/taskdetail/<token>", methods=['GET', 'POST'])
@login_required
@admin_required
def taskdetail(token):
    task = Task.query.filter_by(token=token).first()
    if not task:
        flash("Task not found.", 'danger')
        return redirect(url_for('admin_routes.tasks'))

    if request.method == 'POST':
        if 'opentask' in request.form:
            task.status = 'In Progress'
        elif 'closetask' in request.form:
            task.status = 'task Closed By Admin'
        db.session.commit()
        flash(f'Task is {task.status.lower()}', 'success')
        return redirect(url_for('admin_routes.tasks'))

    status = get_task_status(task)
    task_assignment = TaskAssignment.query.filter_by(task_id=task.task_id).first()
    task_progressions = Task_Progression.query.filter_by(task_id=task.task_id).all()

    return render_template("admin/taskdetail.html", task=task, task_assignment=task_assignment, task_progressions=task_progressions, status=status)
@admin_routes.route("/tasks", methods=['GET', 'POST'])
@login_required
@admin_required
def tasks():
    today = date.today()
    
    if request.method == 'POST':
        task_id = request.form.get('task_id')
        task = Task.query.get(task_id)
        if task:
            if 'opentask' in request.form:
                task.status = 'In Progress'
            elif 'closetask' in request.form:
                task.status = 'task Closed By Admin'
            db.session.commit()
            flash(f'Task is {task.status.lower()}', 'success')
        return redirect(url_for('admin_routes.tasks'))

    admin_alias = aliased(users)
    tasksq = db.session.query(Task, admin_alias.fulname.label('admin_name'), users.fulname.label('employee_name')) \
        .join(admin_alias, Task.admin_id == admin_alias.userid) \
        .outerjoin(TaskAssignment, Task.task_id == TaskAssignment.task_id) \
        .outerjoin(users, TaskAssignment.employee_id == users.userid) \
        .all()

    tasks = []
    for task, admin_name, employee_name in tasksq:
        status = get_task_status(task)
        daystoclose = calculate_days_to_close(task, today)
        task_tuple = (task, admin_name, ', '.join([employee_name] if employee_name else []), status, daystoclose)
        tasks.append(task_tuple)

    tasks = sort_tasks(tasks)

    return render_template("admin/tasks.html", tasks=tasks)



@admin_routes.route("/tasks/addnewtask", methods=['GET', 'POST'])
@login_required
@admin_required
def addnewtask():
    if request.method == 'POST':
        task_name = request.form['task_name']
        start_date_str = request.form['start_date']
        description = request.form.get('description')

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid start date format.', 'danger')
            return render_template("admin/addtasks.html", employees=users.query.filter_by(usertype='employee').all())

        if start_date < date.today():
            flash('Start date cannot be in the past.', 'danger')
            return render_template("admin/addtasks.html", employees=users.query.filter_by(usertype='employee').all())

        close_date = request.form.get('close_date')
        if close_date:
            close_date = datetime.strptime(close_date, '%Y-%m-%d').date()
        else:
            close_date = None

        selected_employee_ids = request.form.getlist('employees[]')
        new_task = Task(task_name=task_name, start_date=start_date, close_date=close_date,
                        admin_id=current_user.userid, description=description, token=secrets.token_urlsafe())
        db.session.add(new_task)
        db.session.commit()

        for employee_id in selected_employee_ids:
            assignment = TaskAssignment(task_id=new_task.task_id, employee_id=employee_id)
            db.session.add(assignment)

        db.session.commit()
        flash('New task added successfully!', 'success')
        return redirect(url_for('admin_routes.tasks'))

    employees = users.query.filter_by(usertype='employee').all()
    return render_template("admin/addtasks.html", employees=employees)

@admin_routes.route("/tasks/delete/<int:task_id>", methods=['POST'])
@login_required
@admin_required
def delete_task(task_id):
    task = Task.query.get(task_id)
    if task:
        db.session.query(Task_Progression).filter(Task_Progression.task_id == task_id).delete(synchronize_session='fetch')
        db.session.query(TaskAssignment).filter(TaskAssignment.task_id == task_id).delete(synchronize_session='fetch')
        db.session.query(Task).filter(Task.task_id == task_id).delete(synchronize_session='fetch')
        db.session.commit()
        flash('Task deleted successfully!', 'success')
    else:
        flash('Task not found.', 'danger')
    return redirect(url_for('admin_routes.tasks'))

@admin_routes.route("/tasks/update/<token>", methods=['GET', 'POST'])
@login_required
@admin_required
def update_task(token):
    task = Task.query.filter_by(token=token).first()
    if not task:
        flash('Task not found or you do not have permission to update it.', 'danger')
        return redirect(url_for('admin_routes.tasks'))

    if request.method == 'POST':
        task_name = request.form['task_name']
        start_date_str = request.form['start_date']

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid start date format.', 'danger')
            return render_template("admin/update_task.html", task=task, employees=users.query.filter_by(usertype='employee').all())

        if start_date < date.today():
            flash('Start date cannot be in the past.', 'danger')
            return render_template("admin/update_task.html", task=task, employees=users.query.filter_by(usertype='employee').all())

        close_date = request.form.get('close_date')
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
        return redirect(url_for('admin_routes.tasks'))

    employees = users.query.filter_by(usertype='employee').all()
    return render_template("admin/update_task.html", task=task, employees=employees)

@admin_routes.route("/userdetails/<Utoken>", methods=['GET'])
@login_required
@admin_required
def userdetails(Utoken):
    user = users.query.filter_by(Utoken=Utoken).first_or_404()
    personal_tasks = PersonalTask.query.filter_by(employee_id=user.userid).all()
    
    assigned_tasks = Task.query.join(TaskAssignment, Task.task_id == TaskAssignment.task_id) \
                               .filter(TaskAssignment.employee_id == user.userid).all()
    
    now = datetime.now(tz=timezone.utc).date()
    tasks = []

    if user.usertype == 'Admin':
        created_tasks = Task.query.filter(Task.admin_id == user.userid).all()
        for task in created_tasks:
            start_date = task.start_date if isinstance(task.start_date, datetime) else datetime.combine(task.start_date, datetime.min.time(), tzinfo=timezone.utc)
            close_date = task.close_date if isinstance(task.close_date, datetime) else datetime.combine(task.close_date, datetime.min.time(), tzinfo=timezone.utc) if task.close_date else None
            
            status = get_task_status(task)
            daystoclose = calculate_days_to_close(task, now)
            tasks.append((task, user.fulname, status, daystoclose))

    else:
        for task in assigned_tasks:
            start_date = task.start_date if isinstance(task.start_date, datetime) else datetime.combine(task.start_date, datetime.min.time(), tzinfo=timezone.utc)
            close_date = task.close_date if isinstance(task.close_date, datetime) else datetime.combine(task.close_date, datetime.min.time(), tzinfo=timezone.utc) if task.close_date else None
            
            status = get_task_status(task)
            daystoclose = calculate_days_to_close(task, now)
            tasks.append((task, task.admin.fulname, status, daystoclose))

    return render_template("admin/userdetails.html", user=user, personal_tasks=personal_tasks, tasks=tasks)

@admin_routes.route('/userdetails/employepertask/<string:token>')
@login_required
@admin_required
def employepertask(token):
    task = PersonalTask.query.filter_by(token=token).first_or_404()
    task_progressions = PersonalTaskProgression.query.filter_by(Ptask_id=task.PTDID).all()
    return render_template("admin/employeeperstask.html", task=task, task_progressions=task_progressions)
