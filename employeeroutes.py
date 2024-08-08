from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from extensions import db
from functools import wraps
from modals import users, Task, TaskAssignment, Task_Progression, PersonalTask, PersonalTaskProgression,Project,ProjectTeam
import secrets
from datetime import datetime, date

employee_routes = Blueprint('employee_routes', __name__)

def employee_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.usertype != "employee":
            flash("You do not have permission to access this page.", 'danger')
            return redirect(url_for('auth_routes.loginpage'))
        return func(*args, **kwargs)
    return decorated_function

def get_task_status(task):
    today = date.today()
    status = ""
    if task.start_date > today:
        status = "Upcoming"
    elif task.start_date <= today and (task.close_date is None or task.close_date >= today) and task.status == 'In Progress':
        status = "Open"
    elif task.status == 'COMPLETED':
        status = "Closed"
    else:
        status = "Closed"

    daystoclose = (task.close_date - today).days if task.close_date else None
    
    
    return status, daystoclose

def process_date(date_str):
    if not date_str or date_str == '0000-00-00':
        return date.today()
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        return date.today()

@employee_routes.route("/Assignedtasks", methods=['GET', 'POST'])
@login_required
@employee_required
def Assignedtasks():
    user_id = current_user.userid
    user = users.query.get(user_id)

    if user:
        assigned_tasks = db.session.query(Task) \
            .join(TaskAssignment, Task.task_id == TaskAssignment.task_id) \
            .filter(TaskAssignment.employee_id == user_id) \
            .all()

        tasks = [(task, task.admin.fulname, *get_task_status(task)) for task in assigned_tasks]

        def to_datetime(d):
            if isinstance(d, datetime):
                return d
            elif isinstance(d, date):
                return datetime.combine(d, datetime.min.time())
            return datetime.max
        
        def sort_key(task_info):
            task, _, status, daystoclose = task_info
            start_date = to_datetime(task.start_date)
            close_date = to_datetime(task.close_date)
            if status == 'Open':
                return (0, close_date)
            elif status == 'Upcoming':
                return (1, start_date)
            return (2, datetime.max)
        
        tasks.sort(key=sort_key)

        return render_template("employee/employeepage.html", user=user, tasks=tasks)
    else:
        flash("User not found. Please log in again.", 'danger')
        return redirect(url_for('auth_routes.loginpage'))




@employee_routes.route("/Assignedtasks/taskdetails/<token>/<etoken>", methods=['GET', 'POST'])
@login_required
@employee_required
def taskdetails(token, etoken):
    user_id = current_user.userid
    user = users.query.get(user_id)
    task = Task.query.filter_by(token=token).first()
    employee = users.query.filter_by(Utoken=etoken).first()
    task_assignment = TaskAssignment.query.filter_by(task_id=task.task_id, employee_id=employee.userid).first()
    
    task_progressions = Task_Progression.query.filter_by(task_id=task.task_id).all()
    
    if task:
        if request.method == 'POST':
            if 'mark_task_done' in request.form:
                task.status = 'COMPLETED'
                db.session.commit()
                flash('Task marked as done.', 'success')
                return redirect(url_for('employee_routes.taskdetails', token=token, etoken=etoken))
            
            progression_id = request.form.get('progression_id')
            progression = Task_Progression.query.get(progression_id)

            if progression:
                progression.end_at = date.today()
                progression.statut = 'Completed'
                db.session.commit()
                flash('Progression marked as completed.', 'success')
                return redirect(url_for('employee_routes.taskdetails', token=token, etoken=etoken))
            else:
                flash('Progression not found.', 'danger')   

        status, _ = get_task_status(task)
        
        return render_template("employee/taskdetails.html", user=user, task=task, task_assignment=task_assignment, task_progressions=task_progressions, status=status)
    else:
        flash("Task not found.", 'danger')
    return redirect(url_for('employee_routes.Assignedtasks'))

@employee_routes.route('/Assignedtasks/taskdetails/addprogression/<token>/<etoken>', methods=['GET', 'POST'])
@login_required
@employee_required
def addprogression(token, etoken):
    user_id = current_user.userid
    user = users.query.get(user_id)
    employee = users.query.filter_by(Utoken=etoken).first()
    task = Task.query.filter_by(token=token).first()
    task_assignment = TaskAssignment.query.filter_by(task_id=task.task_id, employee_id=employee.userid).first()

    if task_assignment:
        if request.method == 'POST':
            progname = request.form.get('progname')
            start_at = process_date(request.form.get('start_at'))
            
            new_progression = Task_Progression(
                progname=progname,
                start_at=start_at,
                task_id=task.task_id,
                employee_id=employee.userid
            )
            
            db.session.add(new_progression)
            db.session.commit()
            flash('Task progression added successfully.', 'success')
            return redirect(url_for('employee_routes.Assignedtasks'))
        
        return render_template('employee/taskprog.html', task_id=task.task_id, employee_id=user_id)
    else:
        flash('You are not authorized to add progression for this task.', 'danger')
        return redirect(url_for('employee_routes.taskdetails', token=token, etoken=etoken))

@employee_routes.route('/addpersonaltask', methods=['GET', 'POST'])
@login_required
@employee_required
def addpertask():
    if request.method == 'POST':
        task_name = request.form.get('taskName')
        do_at = process_date(request.form.get('doAt'))
        completed_at = request.form.get('completedAt')
        state = request.form.get('state')
        description = request.form.get('description')           
        employee_id = current_user.userid
     
        new_task = PersonalTask(
            TaskName=task_name,
            DoAt=do_at,
            CompletedAt=completed_at if completed_at else None,
            State=state,
            employee_id=employee_id,
            Description=description if description else None,
            token=secrets.token_urlsafe()
        )

        db.session.add(new_task)
        db.session.commit()
        return redirect(url_for('employee_routes.personaltasks'))
    
    return render_template('employee/addpertask.html')

@employee_routes.route('/Assignedtasks/delete_pertask/<string:token>')
@login_required
@employee_required
def delete_pertask(token):
    task = PersonalTask.query.filter_by(token=token).first_or_404()
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('employee_routes.personaltasks'))

@employee_routes.route('/toggle_pertask/<string:token>/<string:action>')
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
    return redirect(url_for('employee_routes.personaltasks'))

@employee_routes.route('/edit_pertask/<string:token>', methods=['GET', 'POST'])
@login_required
@employee_required
def edit_pertask(token):
    task = PersonalTask.query.filter_by(token=token).first_or_404()
    
    if request.method == 'POST':
        task.TaskName = request.form.get('taskName')
        task.Description = request.form.get('description') 
        task.DoAt = process_date(request.form.get('doAt'))
        task.CompletedAt = request.form.get('completedAt')
        db.session.commit()
        return redirect(url_for('employee_routes.personaltasks'))
    
    return render_template('employee/editpertask.html', task=task)

@employee_routes.route('/personaltasks')
@login_required
@employee_required
def personaltasks():
    tasks = PersonalTask.query.filter(PersonalTask.employee_id == current_user.userid).all()
    return render_template('employee/personalstask.html', tasks=tasks)

@employee_routes.route('/personaltasks/personaltaskdetail/<Ptoken>', methods=['GET', 'POST'])
@login_required
@employee_required
def personaltaskdetail(Ptoken):
    task = PersonalTask.query.filter_by(token=Ptoken).first()
    task_progressions = PersonalTaskProgression.query.filter_by(Ptask_id=task.PTDID).all()

    if request.method == 'POST':
        if 'mark_task_done' in request.form:
            task.State = 'completed'
            task.CompletedAt = date.today()
            db.session.commit()
            flash('Task marked as completed.', 'success')
            return redirect(url_for('employee_routes.personaltaskdetail', Ptoken=Ptoken))
        if 'Task_not_done' in request.form:
            task.State = 'in progress'
            task.CompletedAt = None
            db.session.commit()
            flash('Task mark rolled back.', 'success')
            return redirect(url_for('employee_routes.personaltaskdetail', Ptoken=Ptoken))

        if 'progression_id' in request.form:
            progression_id = request.form.get('progression_id')
            progression = PersonalTaskProgression.query.get(progression_id)

            if progression:
                progression.completed_at = date.today()
                progression.status = 'Completed'
                db.session.commit()
                flash('Progression marked as completed.', 'success')
                return redirect(url_for('employee_routes.personaltaskdetail', Ptoken=Ptoken))
            else:
                flash('Progression not found.', 'danger')
    
    return render_template('employee/personal_taskdetail.html', task=task, task_progressions=task_progressions)

@employee_routes.route('/personaltasks/personaltaskdetail/addpersonalprogression/<Ptoken>', methods=['GET', 'POST'])
@login_required
@employee_required
def addpersonalprogression(Ptoken):
    task = PersonalTask.query.filter_by(token=Ptoken).first()

    if not task:
        flash('Personal Task not found.', 'danger')
        return redirect(url_for('employee_routes.personaltasks'))

    if request.method == 'POST':
        progname = request.form.get('progname')
        start_at = process_date(request.form.get('start_at'))
        
        if not progname:
            flash('Progress name is required.', 'danger')
            return redirect(url_for('employee_routes.addpersonalprogression', Ptoken=Ptoken))
        
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
        return redirect(url_for('employee_routes.personaltaskdetail', Ptoken=Ptoken))
    
    return render_template('employee/add_personal_progression.html', task=task)
