"""
Entrypoint for initial import of the package in any context
Creates routes/blueprints without creating the app
Home to factories for creating the app and its plugins
"""
from tassaron_flask_template import Flask
from dotenv import load_dotenv
import os
import datetime


def create_app():
    mutated_env_file = False
    def create_ensure_env_var_func():
        default_values = {
            "FLASK_APP": "tassaron_flask_template.run:app",
            "FLASK_ENV": "development",
            "SECRET_KEY": os.urandom(24),
        }
        mutation = False
        if os.path.exists(".env"):
            mutation = True
        def ensure_env_var(token):
            nonlocal mutated_env_file
            if token not in os.environ:
                mutated_env_file = mutation
                with open(".env", "a") as f:
                    f.write(f"\n{str(token)}={default_values[token]}")

        return ensure_env_var

    # FLASK_ENV must be set in the environment before the Flask instance is created
    ensure_env_var = create_ensure_env_var_func()
    ensure_env_var("FLASK_APP")
    ensure_env_var("FLASK_ENV")
    ensure_env_var("SECRET_KEY")
    load_dotenv(".env")

    app = Flask("tassaron_flask_template")
    app.logger.info("Created Flask instance")
    if mutated_env_file:
        app.logger.warning(".env file was modified programmatically")
    app.config.update(
        SECRET_KEY=os.environ["SECRET_KEY"],
        SERVER_NAME=os.environ.get("SERVER_NAME", None),
        ADMIN_URL=os.environ.get("ADMIN_URL", "/admin"),
        UPLOADS_DEFAULT_DEST="app/static/uploads",
        MAX_CONTENT_LENGTH=int(os.environ.get("FILESIZE_LIMIT_MB", 2)) * 1024 * 1024,
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URI", "sqlite+pysqlite:///db/database.db"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        WTF_CSRF_ENABLED=True,
        WTF_CSRF_TIME_LIMIT=1800,
        SESSION_COOKIE_SECURE=True,
        REMEMBER_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_HTTPONLY=True,
        SITE_NAME=os.environ.get("SITE_NAME", "Your Website Name Here"),
        FOOTER_YEAR=os.environ.get("FOOTER_YEAR", str(datetime.datetime.now().year)),
        MODULES_CONFIG=os.environ.get("MODULES_CONFIG", "modules.json"),
    )

    if app.env == "production":
        # Configure email
        try:
            app.config["EMAIL_API_KEY"] = os.environ["EMAIL_API_KEY"]
            app.config["EMAIL_API_URL"] = os.environ["EMAIL_API_URL"]
            app.config["EMAIL_SENDER_NAME"] = os.environ["EMAIL_SENDER_NAME"]
            app.config["EMAIL_SENDER_ADDRESS"] = os.environ["EMAIL_SENDER_ADDRESS"]
        except KeyError as e:
            raise KeyError(f"{e} is missing from .env")
    else:
        app.logger.warning("Email is disabled because FLASK_ENV != production")

    from .routes import main_routes
    app.register_blueprint(main_routes)
    return app


def init_app(app, modules=None):
    from .plugins import db, migrate, bcrypt, login_manager
    for plugin in (db, bcrypt, login_manager):
        plugin.init_app(app)
    migrate.init_app(app, db)
    login_manager.login_view = "account.login"
    login_manager.login_message_category = "info"
    app.register_modules(modules)

    if app.env == "production":
        # Enable Monitoring Dashboard only in production
        import flask_monitoringdashboard as monitor

        monitor.config.init_from(file=os.environ.get("MONITOR_CONFIG", "monitor.cfg"))
        try:
            monitor.config.username = os.environ["MONITOR_USERNAME"]
            monitor.config.password = os.environ["MONITOR_PASSWORD"]
        except KeyError:
            raise KeyError(
                "MONITOR_USERNAME and MONITOR_PASSWORD must be added to .env"
            )
        monitor.config.security_token = os.urandom(24)
        monitor.bind(app)

    from .models import User

    @login_manager.user_loader
    def get_user(user_id):
        return User.query.get(int(user_id))

    login_manager.anonymous_user = lambda: User(
        email=None, password=None, is_admin=False
    )

    from flask_uploads import configure_uploads
    from .images import Images

    configure_uploads(app, Images)

    def inject_vars():
        import flask_login

        nonlocal app
        return {
            "logged_in": flask_login.current_user.is_authenticated,
            "site_name": app.config["SITE_NAME"],
            "footer_year": app.config["FOOTER_YEAR"],
        }

    app.context_processor(inject_vars)

    return app