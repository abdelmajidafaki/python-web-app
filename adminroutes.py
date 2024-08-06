from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from extensions import db
from modals import users, Task, TaskAssignment, Task_Progression, PersonalTask, PersonalTaskProgression,Teams,TeamsMember,Project,ProjectTeam
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
        task, _, _, _, status, _ = task_info  # Adjust to 6 elements
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
    project = Project.query.get(task.project_id) if task.project_id else None
    return render_template("admin/tasks/taskdetail.html", task=task, task_assignment=task_assignment, task_progressions=task_progressions, status=status,project=project)

@admin_routes.route("/tasks", methods=['GET', 'POST'])
@login_required
@admin_required
def tasks():
    today = date.today()
    projects = db.session.query(Project.project_name).distinct().all()
    project_names = [p[0] for p in projects]
    
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

    tasksq = Task.query.all()
    tasks = []

    for task in tasksq:
        admin_name = task.admin.fulname
        project_name = task.project.project_name if task.project else None
        employee_names = [assignment.employee.fulname for assignment in task.assignments]

        status = get_task_status(task)
        daystoclose = calculate_days_to_close(task, today)
        task_tuple = (task, admin_name, ', '.join(employee_names), status, daystoclose, project_name)
        tasks.append(task_tuple)

    tasks = sort_tasks(tasks)

    return render_template("admin/tasks/tasks.html", tasks=tasks, projects=project_names)



@admin_routes.route("/tasks//Create_new_task", methods=['GET', 'POST'])
@login_required
@admin_required
def addnewtask():
    if request.method == 'POST':
        task_name = request.form['task_name']
        start_date_str = request.form['start_date']
        description = request.form.get('description')
        project_id = request.form.get('project_id')
        if not project_id:
            project_id = None

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid start date format.', 'danger')
            return render_template(
                "admin/tasks/addtasks.html",
                employees=[{'userid': e.userid, 'fulname': e.fulname} for e in users.query.filter_by(usertype='employee').all()],
                projects=Project.query.all()
            )

        if start_date < date.today():
            flash('Start date cannot be in the past.', 'danger')
            return render_template(
                "admin/tasks/addtasks.html",
                employees=[{'userid': e.userid, 'fulname': e.fulname} for e in users.query.filter_by(usertype='employee').all()],
                projects=Project.query.all()
            )

        close_date = request.form.get('close_date')
        if close_date:
            close_date = datetime.strptime(close_date, '%Y-%m-%d').date()
        else:
            close_date = None

        selected_employee_ids = request.form.getlist('employees[]')
        new_task = Task(
            task_name=task_name,
            start_date=start_date,
            close_date=close_date,
            admin_id=current_user.userid,
            description=description,
            token=secrets.token_urlsafe(),
            project_id=project_id
        )
        db.session.add(new_task)
        db.session.commit()

        for employee_id in selected_employee_ids:
            assignment = TaskAssignment(task_id=new_task.task_id, employee_id=employee_id)
            db.session.add(assignment)

        db.session.commit()
        flash('New task added successfully!', 'success')
        return redirect(url_for('admin_routes.tasks'))

    employees = [{'userid': e.userid, 'fulname': e.fulname} for e in users.query.filter_by(usertype='employee').all()]
    projects = Project.query.all()
    
    project_teams = {}
    for project in projects:
        teams = Teams.query.join(ProjectTeam).filter(ProjectTeam.project_id == project.project_id).all()
        team_members = []
        for team in teams:
            team_members.extend([{'userid': member.userid, 'fulname': member.fulname} for member in team.members])
        project_teams[project.project_id] = team_members

    return render_template("admin/tasks/addtasks.html", employees=employees, projects=projects, project_teams=project_teams)


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
    projects = Project.query.all()
    employees = users.query.filter_by(usertype='employee').all()

    # Convert employees to a JSON-serializable format
    employees_list = [{'userid': emp.userid, 'fullname': emp.fulname} for emp in employees]

    # Prepare project teams
    project_teams = {}
    for project in projects:
        teams = Teams.query.join(ProjectTeam).filter(ProjectTeam.project_id == project.project_id).all()
        team_members = []
        for team in teams:
            team_members.extend([{'userid': member.userid, 'fullname': member.fulname} for member in team.members])
        project_teams[project.project_id] = team_members

    if not task:
        flash('Task not found or you do not have permission to update it.', 'danger')
        return redirect(url_for('admin_routes.tasks'))

    if request.method == 'POST':
        task_name = request.form['task_name']
        start_date_str = request.form['start_date']
        project_id = request.form.get('project_id')
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid start date format.', 'danger')
            return render_template("admin/tasks/update_task.html", task=task, project_teams=project_teams, employees=employees_list, projects=projects)
        if task.start_date!=start_date:
            if start_date < date.today():
                flash('Start date cannot be in the past.', 'danger')
                return render_template("admin/tasks/update_task.html", task=task, project_teams=project_teams, employees=employees_list, projects=projects)

        close_date = request.form.get('close_date')
        if close_date:
            close_date = datetime.strptime(close_date, '%Y-%m-%d').date()
        else:
            close_date = None

        selected_employee_ids = request.form.getlist('employees[]')
        task.task_name = task_name
        task.start_date = start_date
        task.close_date = close_date
        task.project_id = project_id

        TaskAssignment.query.filter_by(task_id=task.task_id).delete()
        for employee_id in selected_employee_ids:
            assignment = TaskAssignment(task_id=task.task_id, employee_id=employee_id)
            db.session.add(assignment)

        db.session.commit()
        flash('Task updated successfully!', 'success')
        return redirect(url_for('admin_routes.tasks'))

    return render_template("admin/tasks/update_task.html", task=task, employees=employees_list, project_teams=project_teams, projects=projects)


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

@admin_routes.route('/teams', methods=['GET'])
@login_required
@admin_required
def teams():
   
    all_teams = Teams.query.all()
    all_users = users.query.all()  
    all_projects = Project.query.all()
    team_data = {}
    for team in all_teams:

        team_members = TeamsMember.query.filter_by(team_id=team.team_id).all()
        member_ids = [member.userid for member in team_members]
        members = users.query.filter(users.userid.in_(member_ids)).all()
        supervisor = users.query.get(team.supervisor_id) if team.supervisor_id else None
        associated_projects = [project for project in all_projects if ProjectTeam.query.filter_by(team_id=team.team_id, project_id=project.project_id).first()]
        team_data[team] = {
            'members': members,
            'supervisor': supervisor,
            'projects': associated_projects
        }
    return render_template('admin/teams/teams.html', team_data=team_data)

@admin_routes.route('/teams/Create_new_team', methods=['POST','GET'])
def add_team():
    if request.method == 'POST':
        team_name = request.form['team_name']
        team_members = request.form.getlist('team_members')
        supervisor_id = request.form.get('supervisor_id')
        new_team = Teams(team_name=team_name, supervisor_id=supervisor_id ,TETOKEN=secrets.token_urlsafe())
        db.session.add(new_team)
        db.session.commit() 
        for member_id in team_members:
            team_member = TeamsMember(team_id=new_team.team_id, userid=member_id)
            db.session.add(team_member)
        db.session.commit()
        flash('Team added successfully!', 'success')
        return redirect(url_for('admin_routes.teams'))
    
    employees = users.query.filter_by(usertype='employee')
    return render_template('admin/teams/addteam.html', employees=employees)

@admin_routes.route('/teams/update/<string:TETOKEN>', methods=['GET', 'POST'])
@login_required
@admin_required
def update_team(TETOKEN):
    team = Teams.query.filter_by(TETOKEN=TETOKEN).first_or_404()
    if request.method == 'POST':
        team_name = request.form['team_name']
        team_members = request.form.getlist('team_members')
        supervisor_id = request.form.get('supervisor_id')
        team.team_name = team_name
        team.supervisor_id = supervisor_id
        TeamsMember.query.filter_by(team_id=team.team_id).delete()
        for member_id in team_members:
            team_member = TeamsMember(team_id=team.team_id, userid=member_id)
            db.session.add(team_member)
        db.session.commit()
        flash('Team updated successfully!', 'success')
        return redirect(url_for('admin_routes.teams'))
    team_member_ids = [tm.userid for tm in TeamsMember.query.filter_by(team_id=team.team_id).all()]
    employees = users.query.filter_by(usertype='employee').all()
    return render_template('admin/teams/updateteam.html', team=team, employees=employees, team_member_ids=team_member_ids)




@admin_routes.route('/teams/delete_team/<string:TETOKEN>', methods=['GET','POST'])
@login_required
@admin_required
def delete_team(TETOKEN):
    team = Teams.query.filter_by(TETOKEN=TETOKEN).first()
    if not team:
        flash('Team not found', 'danger')
        return redirect(url_for('admin_routes.teams'))
    TeamsMember.query.filter_by(team_id=team.team_id).delete()
    db.session.delete(team)  
    db.session.commit()

    flash('Team deleted successfully!', 'success')
    return redirect(url_for('admin_routes.teams'))


@admin_routes.route('/projects')
@login_required
@admin_required
def projects():
    projects = Project.query.all()
    return render_template('admin/projects/projects.html', projects=projects)


@admin_routes.route('/projects/create_project', methods=['GET', 'POST'])
@login_required
def create_project():
    if request.method == 'POST':
        project_name = request.form['project_name']
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        description = request.form.get('description')
        selected_teams = request.form.getlist('teams')  

        new_project = Project(
            project_name=project_name,
            start_date=start_date,
            end_date=end_date,
            description=description
        )
        
        db.session.add(new_project)
        db.session.flush() 

        
        for team_id in selected_teams:
            project_team = ProjectTeam(project_id=new_project.project_id, team_id=team_id)
            db.session.add(project_team)
        
        db.session.commit()
        
        flash('Project created successfully!', 'success')
        return redirect(url_for('admin_routes.projects'))
    
    teams = Teams.query.all()
    return render_template('admin/projects/addproject.html', teams=teams)
@admin_routes.route('/projects/update/<string:token>', methods=['GET', 'POST'])
def update_project(token):
    project = Project.query.filter_by(token=token).first_or_404()
    all_teams = Teams.query.all()  

    if request.method == 'POST':
        project.project_name = request.form['project_name']
        project.description = request.form['description']
        project.statut = request.form['statut']
        project.start_date = request.form['start_date']
        project.end_date = request.form['end_date']

        project.teams = [] 
        
        selected_team_ids = request.form.getlist('teams')
        selected_teams = Teams.query.filter(Teams.team_id.in_(selected_team_ids)).all()
        project.teams.extend(selected_teams) 
        
        db.session.commit()
        flash('Project updated successfully!', 'success')
        return redirect(url_for('admin_routes.projects'))
    
    project_teams_ids = [team.team_id for team in project.teams]

    return render_template('admin/projects/update_project.html', project=project, all_teams=all_teams, project_teams_ids=project_teams_ids)

@admin_routes.route('/projects/delete/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    flash('Project deleted successfully!', 'success')
    return redirect(url_for('admin_routes.projects'))


@admin_routes.route("/projects/project_details/<string:token>", methods=['GET'])
@login_required
@admin_required
def project_details(token):
    project = Project.query.filter_by(token=token).first()
    if not project:
        flash('Project not found.', 'danger')
        return redirect(url_for('admin_routes.projects'))
    
    tasks = Task.query.filter_by(project_id=project.project_id).all()
    teams = Teams.query.join(ProjectTeam).filter(ProjectTeam.project_id == project.project_id).all()
    
    team_details = []
    for team in teams:
        supervisor = users.query.filter_by(userid=team.supervisor_id).first()
        members = [{'userid': member.userid, 'fullname': member.fulname, 'Utoken': member.Utoken} for member in team.members]
        team_details.append({
            'team_name': team.team_name,
            'supervisor': supervisor,
            'members': members
        })
    
    return render_template('admin/projects/projectdetails.html', project=project, tasks=tasks, team_details=team_details)
