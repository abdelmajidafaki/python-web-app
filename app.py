from  flask import Flask,render_template
webapp=Flask(__name__)
from flask_bootstrap import Bootstrap5
@webapp.route("/")
def regesterpage():
    return render_template("registerpage.html")
if __name__ == '__main__':
    webapp.run(debug=True)