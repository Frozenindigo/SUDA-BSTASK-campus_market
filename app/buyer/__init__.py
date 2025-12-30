from flask import Blueprint

bp = Blueprint('buyer', __name__)

from app.buyer import routes
