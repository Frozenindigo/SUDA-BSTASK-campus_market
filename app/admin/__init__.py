from flask import Blueprint

bp = Blueprint('admin', __name__)

# 必须引入 routes，否则视图函数不会注册
from app.admin import routes
