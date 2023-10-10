import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

from flask import Flask

from . import default_settings, register_extensions

from dash import Dash

#Monitors the transactions and integrates with Flask
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
# admin.add_view(ProjectView(Project, db.session))
# admin.add_view(DashboardView(Dashboard, db.session))
# admin.add_view(DataExplorerView(DataExplorer, db.session))
# admin.add_view(MenuPageView(MenuPage, db.session))
# admin.add_view(UserView(User, db.session))


app = Dash(
    server=server,
    # use_pages=True,
    use_pages=False,
    title=default_settings.TITLE,
    external_scripts=default_settings.EXTERNAL_SCRIPTS,
    external_stylesheets=default_settings.EXTERNAL_STYLESHEETS,
    suppress_callback_exceptions=True,
)
