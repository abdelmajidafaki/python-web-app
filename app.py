from flask import Flask
from config import Config  

from extensions import db, bcrypt, login_manager
from adminroutes import admin_routes

from authroutes import auth_routes  
from employeeroutes import employee_routes  



webapp = Flask(__name__)
webapp.config.from_object(Config)


db.init_app(webapp)
bcrypt.init_app(webapp)
login_manager.init_app(webapp)



webapp.register_blueprint(auth_routes)
webapp.register_blueprint(employee_routes,url_prefix='/employee')
webapp.register_blueprint(admin_routes, url_prefix='/admin')




if __name__ == '__main__':
    
    webapp.run(debug=True)
