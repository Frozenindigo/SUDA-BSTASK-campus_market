
from flask import Blueprint

# 1. 创建 bp
bp = Blueprint('seller', __name__)

# 2. 导入 routes
from app.seller import routes
