from .extensions import db, flask_admin, cors, migrate, login_manager

def register_extensions(app):
    """Register Flask extensions."""

    db.init_app(app)
    migrate.init_app(app, db)
    flask_admin.init_app(app)
    # cors.init_app(app)
    cors.init_app(app, resources={r"/*": {"origins": "*"}})

    login_manager.init_app(app)
    # bcrypt.init_app(app)
    # cache.init_app(app)
    # csrf_protect.init_app(app)
    # login_manager.init_app(app)
    # debug_toolbar.init_app(app)
    # migrate.init_app(app, db)
    # flask_static_digest.init_app(app)
