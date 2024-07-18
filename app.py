from  flask import Flask,render_template,request,flash,session,redirect,url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

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
                    flash("Login successful!", 'success')
                    session['user'] = user.userid
                    return redirect(url_for('homepage'))
                else:
                    if user.status=="inactive":
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

@webapp.route("/update_status/<int:user_id>", methods=['POST'])
def update_status(user_id):
    if 'user' in session:
        user = users.query.filter_by(userid=user_id).first()
        if user:
            action = request.form['action']
            if action == 'activate':
                user.status = 'active'
            elif action == 'deactivate':    
                user.status = 'inactive'
            db.session.commit()
            flash(f"User status updated successfully ({action})", 'success')
            return redirect(url_for('homepage'))
    flash("Unable to update user status.", 'danger')
    return redirect(url_for('homepage'))

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

@webapp.route("/logout", methods=['GET'])
def logout():
    session.pop('user', None)  
    flash("You have been logged out.", 'info')
    return redirect(url_for('loginpage'))
if __name__ == '__main__':
    webapp.run(debug=True)  