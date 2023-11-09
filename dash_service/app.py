import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

from flask import Flask, render_template, request, redirect
from dash import Dash

from . import default_settings, register_extensions
from .layouts import base_layout
from . import custom_router

from .extensions import db, flask_admin, login_manager

#The models, import for flask admin
from .models import Dashboard, Project, MenuPage, User
#The models' views, for flask admin
from .views import DashboardView, ProjectView, UserView, MenuPageView, ExtFileAdmin
from .app_settings import FILES_UPLOAD_PATH
from .db_access import db_access
import flask_login
from flask_admin.menu import MenuLink

import os




# Monitors the transactions and integrates with Flask
sentry_sdk.init(
    integrations=[FlaskIntegration()],
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0,
)

server = Flask(__package__)
server.config.from_object(default_settings)
# register extensions (method is in __init.py)
register_extensions(server)



# Flask-Admin
flask_admin.add_view(ProjectView(Project, db.session))
flask_admin.add_view(DashboardView(Dashboard, db.session))
flask_admin.add_view(MenuPageView(MenuPage, db.session))
flask_admin.add_view(UserView(User, db.session))
# production storage will be an Azure blob storage
#check if files upload path exists, create if not
files_upload_path = os.path.join(os.path.dirname(__file__), FILES_UPLOAD_PATH)
if not os.path.isdir(files_upload_path):
    os.makedirs(files_upload_path)
flask_admin.add_view(ExtFileAdmin(files_upload_path, f"/{FILES_UPLOAD_PATH}/", name="File upload"))

class LogoutMenuLink(MenuLink):
    def is_accessible(self):
        return flask_login.current_user.is_authenticated
flask_admin.add_link(LogoutMenuLink(name="Logout", category="", url="/logout"))














app = Dash(
    server=server,
    # use_pages=True,
    use_pages=False,
    title=default_settings.TITLE,
    external_scripts=default_settings.EXTERNAL_SCRIPTS,
    external_stylesheets=default_settings.EXTERNAL_STYLESHEETS,
    suppress_callback_exceptions=True,
)

with server.app_context():
    db.create_all()
    # Check if there is at least one user
    first_user = User.query.first()
    # if not add the admin

    if first_user is None:
        first_admin = User(
            name="Admin",
            email="admin@admin.com",
            password="admin",
            is_admin=True,
        )

        db.session.add(first_admin)
        db.session.commit()

# Does not work, fix this
# @server.errorhandler(404)
# def page_not_found(error):
#     return render_template("404.html", title="Page not found", body="Page not found"), 404



'''
Flask login
'''
#routes for login/logout
@server.route("/login/")
def page_login():
    req_args = request.args.to_dict(flat=False)
    message = ""
    if "msg" in req_args:
        if "err_cred" in req_args["msg"]:
            message = "Login error"
        elif "err_nocred" in req_args["msg"]:
            message = "Email or password cannot be empty"
        elif "err_nouser" in req_args["msg"]:
            message = "User not found"

    return render_template("login.html", message=message)

@server.route("/do_login/", methods=["POST", "GET"])
def do_login():
    form_args = request.form.to_dict(flat=False)
    arg_email = ""
    arg_pwd = ""
    if "email" in form_args:
        arg_email = form_args["email"][0]
    if "pwd" in form_args:
        arg_pwd = form_args["pwd"][0]

    if arg_email.strip() == "" or arg_pwd.strip() == "":
        return redirect("/login/?msg=err_nocred")

    user:User = User.query.filter(User.email == arg_email).first()

    if user is None:
        return redirect("/login/?msg=err_nouser")
    if user.verify_password(arg_pwd):
        flask_login.login_user(user)
        return redirect("/admin/")

    return redirect("/login/?msg=err_cred")


@server.route("/logout/")
def do_logout():
    flask_login.logout_user()

    return redirect("/login/")




@login_manager.user_loader
def load_user(user_id):
    return db_access().get_user_by_id(user_id)




with server.app_context():
    app.layout = base_layout()
    cust_rout = custom_router.CustomRouter(app, "dash_main_container")