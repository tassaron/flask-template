"""
Entrypoint for initial import of the package in any context
Creates routes/blueprints without creating the app
Home to factories for creating the app and its plugins
"""
from flask import Flask
from dotenv import load_dotenv
import os
import datetime
import logging
from .routes import main_routes


load_dotenv(".env")
LOG = logging.getLogger(__package__)
logging.basicConfig(filename=os.environ.get("LOG_FILE", "debug.log"))
LOG.setLevel(logging.getLevelName(os.environ.get("LOG_LEVEL", "WARNING")))


def create_app():
    def create_ensure_env_var_func():
        default_values = {
            "FLASK_APP": "tassaron_flask_template.run:app",
            "FLASK_ENV": "development",
            "SECRET_KEY": os.urandom(24),
            "DOMAIN_NAME": "localhost",
        }
        def ensure_env_var(token):
            nonlocal default_values
            if token not in os.environ:
                LOG.warning(f"Creating new {str(token)}")
                with open(".env", "a") as f:
                    f.write(
                        f"\n{str(token)}={default_values[token]}"
                    )
        return ensure_env_var
    
    # FLASK_ENV must be set in the environment before the Flask instance is created
    LOG.info("Loading environment variables")
    ensure_env_var = create_ensure_env_var_func()
    ensure_env_var("FLASK_APP")
    ensure_env_var("FLASK_ENV")
    ensure_env_var("SECRET_KEY")
    ensure_env_var("DOMAIN_NAME")
    load_dotenv(".env")

    LOG.info("Creating Flask instance")
    app = Flask("tassaron_flask_template")
    app.config.update(
        SECRET_KEY=os.environ["SECRET_KEY"],
        DOMAIN_NAME=os.environ["DOMAIN_NAME"],
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
        # Flask only respects FLASK_ENV if it's set in the environment before instance creation
        # but for consistency and ease of access, we store it in app.config too
        FLASK_ENV=os.environ["FLASK_ENV"],
    )

    if app.config["FLASK_ENV"] == "production":
        # Configure email
        try:
            app.config["EMAIL_API_KEY"] = os.environ["EMAIL_API_KEY"]
            app.config["EMAIL_API_URL"] = os.environ["EMAIL_API_URL"]
            app.config["EMAIL_SENDER_NAME"] = os.environ["EMAIL_SENDER_NAME"]
            app.config["EMAIL_SENDER_ADDRESS"] = os.environ["EMAIL_SENDER_ADDRESS"]
        except KeyError as e:
            raise KeyError(f"{e} is missing from .env")
    else:
        LOG.warning("Email is disabled because FLASK_ENV != production")
    if app.config["DEBUG"] == True:
        LOG.critical("DEBUGGER IS ACTIVE because FLASK_ENV == development")

    app.register_blueprint(main_routes)
    return app


def create_plugins():
    LOG.info("Creating plugins")
    from flask_login import LoginManager
    from flask_sqlalchemy import SQLAlchemy
    from flask_bcrypt import Bcrypt
    from flask_migrate import Migrate

    return SQLAlchemy(), Migrate(), Bcrypt(), LoginManager()
