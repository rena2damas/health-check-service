import os

import flasgger
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from flask import Blueprint, Flask, redirect, url_for
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy

from src.cli.test import test_command
from src.settings.config import config_by_name

# SQLite database
db = SQLAlchemy()

# initialize Flask Restful
api = Api()


def create_app(config_name='default'):
    """Create a new app."""

    # define the WSGI application object
    app = Flask(__name__)

    # load object-based default configuration
    env = os.getenv('FLASK_ENV', config_name)
    app.config.from_object(config_by_name[env])

    setup_app(app)

    return app


def setup_app(app):
    # initialize root blueprint
    api_bp = Blueprint('api', __name__, url_prefix=app.config['APPLICATION_CONTEXT'])

    # link api to blueprint
    api.init_app(api_bp)

    # register api blueprint
    app.register_blueprint(api_bp)

    # Redirect root path to context root
    app.add_url_rule('/', 'index', lambda: redirect(url_for('flasgger.apidocs')))

    import src.resources.health_checks

    # configure swagger
    flasgger.Swagger(
        app=app,
        config=app.config['SWAGGER'],
        template=app.config['OPENAPI_SPEC'],
        merge=True
    )

    # register cli commands
    app.cli.add_command(test_command)
