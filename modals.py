from extensions import db
import secrets
from flask_login import UserMixin


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

