# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

# Import core packages
import os

# Import Flask 
from flask import Flask

# Inject Flask magic
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Session config
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400

# Import routing to render the pages
from app import views

# Register users blueprint
from app.users import users_bp
app.register_blueprint(users_bp)
