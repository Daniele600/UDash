import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

from flask import Flask, render_template
from dash import Dash

from . import default_settings, register_extensions
from .layouts import base_layout
from . import custom_router

# from .extensions import admin, db, login_manager
from .extensions import db, flask_admin

#The models, import for flask admin
from .models import Dashboard, Project, MenuPage, User
#The models' views, for flask admin
from .views import DashboardView, ProjectView, UserView, MenuPageView, ExtFileAdmin
from .app_settings import FILES_UPLOAD_PATH

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
#path = os.path.join(os.path.dirname(__file__), FILES_UPLOAD_PATH)
flask_admin.add_view(ExtFileAdmin(files_upload_path, f"/{FILES_UPLOAD_PATH}/", name="Static Files"))


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

with server.app_context():
    app.layout = base_layout()
    cust_rout = custom_router.CustomRouter(app, "dash_main_container")
