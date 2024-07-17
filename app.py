from  flask import Flask,render_template,request,flash,session,redirect,url_for
from flask_sqlalchemy import SQLAlchemy
webapp=Flask(__name__)
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
@webapp.route("/register", methods=['GET', 'POST'])
def registerpage():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        cpassword=request.form['cpassword']
        if fullname and email :
            if password==cpassword:
                new_user = users(fulname=fullname, email=email, Pasword=password)
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
        user = users.query.filter_by(email=email, Pasword=password).first()
        if user:
            flash("Login successful!", 'success')
            session['user'] = user.userid
            return redirect(url_for('homepage'))
        else:
            flash("Invalid email or password. Please try again.", 'danger')
    return render_template("loginpage.html")
@webapp.route("/homepage", methods=['GET', 'POST'])
def homepage():
    if 'user' in session:
        user_id = session['user']  
        user = users.query.filter_by(userid=user_id).first()  
        if user:
            fullname = user.fulname 
            return render_template("homepage.html", fullname=fullname)
    else:
        flash("You are not logged in. Please log in to access this page.", 'danger')
        return redirect(url_for('loginpage'))
    return render_template("homepage.html")
if __name__ == '__main__':
    webapp.run(debug=True)  