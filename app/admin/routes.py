from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.admin import bp
from app.models import User, Product, Bounty

# 简单的权限检查装饰器逻辑（也可以写成装饰器，这里直接写在函数里简单点）
def check_admin():
    if not current_user.is_authenticated or current_user.role != 'admin':
        flash('您没有管理员权限！', 'danger')
        return False
    return True

@bp.route('/dashboard')
@login_required
def dashboard():
    if not check_admin():
        return redirect(url_for('buyer.index'))
    
    # --- 1. 数据统计 (Data Visualization) ---
    user_count = User.query.count()
    product_count = Product.query.count()
    # 计算总交易额 (状态为3已售出的商品总价)
    total_sales = db.session.query(db.func.sum(Product.price)).filter_by(status=3).scalar() or 0
    
    # 待审核/在售商品
    products = Product.query.order_by(Product.timestamp.desc()).limit(20).all()
    
    # 悬赏单统计
    bounty_count = Bounty.query.count()

    return render_template('admin_dashboard.html', 
                           user_count=user_count, 
                           product_count=product_count, 
                           total_sales=total_sales,
                           bounty_count=bounty_count,
                           products=products)

@bp.route('/delete_product/<int:id>')
@login_required
def delete_product(id):
    if not check_admin():
        return redirect(url_for('buyer.index'))
    
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash(f'商品 "{product.title}" 已被强制下架/删除', 'success')
    return redirect(url_for('admin.dashboard'))

@bp.route('/ban_user/<int:id>')
@login_required
def ban_user(id):
    """封禁用户逻辑 (这里演示删除，实际业务通常是设置 status=0)"""
    if not check_admin():
        return redirect(url_for('buyer.index'))
        
    user = User.query.get_or_404(id)
    if user.role == 'admin':
        flash('不能封禁管理员！', 'warning')
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f'用户 {user.username} 已被封禁', 'success')
        
    return redirect(url_for('admin.dashboard'))