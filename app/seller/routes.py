from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from . import bp 
from app.models import Product, Bounty, Order, Message
from app.forms import ProductForm
from datetime import datetime
import random

@bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if current_user.role != 'seller':
        flash('您不是卖家，无法访问后台', 'warning')
        return redirect(url_for('buyer.index'))
        
    form = ProductForm()
    if form.validate_on_submit():
        img = form.image_url.data or f"https://picsum.photos/seed/{random.randint(1,1000)}/300/300"
        product = Product(
            title=form.title.data,
            price=form.price.data,
            category=form.category.data,
            image_url=img,
            seller_id=current_user.id,
            attributes={'desc': form.desc.data}
        )
        db.session.add(product)
        db.session.commit()
        flash('商品发布成功！', 'success')
        return redirect(url_for('seller.dashboard'))
    
    my_products = Product.query.filter_by(seller_id=current_user.id).order_by(Product.timestamp.desc()).all()
    # 统计销售额
    total_sales = sum([p.price for p in my_products if p.status == 3])
    
    # 待处理订单数
    pending_orders = Order.query.filter_by(seller_id=current_user.id, status=1).count()
    
    # 未读消息数
    unread_messages = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
    
    return render_template('seller_dashboard.html', 
                         form=form, 
                         products=my_products, 
                         sales=total_sales,
                         pending_orders=pending_orders,
                         unread_messages=unread_messages)

@bp.route('/respond_bounty/<int:bounty_id>')
@login_required
def respond_bounty(bounty_id):
    bounty = Bounty.query.get_or_404(bounty_id)
    if bounty.status == 1:
        flash('该悬赏已被解决', 'warning')
        return redirect(url_for('buyer.index'))

    product = Product(
        title=f"【应赏】{bounty.title}",
        price=bounty.budget,
        category='second',
        seller_id=current_user.id,
        status=2,
        image_url="https://via.placeholder.com/300?text=Reserved",
        attributes={'origin_bounty_id': bounty.id, 'desc': f'响应买家求购：{bounty.desc}'}
    )
    
    bounty.status = 1
    db.session.add(product)
    db.session.commit()
    
    flash(f'接单成功！已为您自动生成交易订单。', 'success')
    return redirect(url_for('seller.dashboard'))

@bp.route('/orders')
@login_required
def orders():
    """卖家订单管理"""
    if current_user.role != 'seller':
        flash('您不是卖家', 'warning')
        return redirect(url_for('buyer.index'))
    
    orders = Order.query.filter_by(seller_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('seller_orders.html', orders=orders)

@bp.route('/ship_order/<int:order_id>')
@login_required
def ship_order(order_id):
    """发货"""
    order = Order.query.get_or_404(order_id)
    
    if order.seller_id != current_user.id:
        flash('无权操作', 'danger')
        return redirect(url_for('seller.orders'))
    
    if order.status != 1:
        flash('订单状态不正确', 'warning')
        return redirect(url_for('seller.orders'))
    
    order.status = 2  # 待收货
    order.shipped_at = datetime.utcnow()
    order.product.status = 2  # 已下单
    
    db.session.commit()
    flash('发货成功！', 'success')
    return redirect(url_for('seller.orders'))

@bp.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    """编辑商品"""
    product = Product.query.get_or_404(product_id)
    
    if product.seller_id != current_user.id:
        flash('无权编辑', 'danger')
        return redirect(url_for('seller.dashboard'))
    
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        product.title = form.title.data
        product.price = form.price.data
        product.category = form.category.data
        if form.image_url.data:
            product.image_url = form.image_url.data
        product.attributes = {'desc': form.desc.data}
        
        db.session.commit()
        flash('商品更新成功！', 'success')
        return redirect(url_for('seller.dashboard'))
    
    # 填充表单数据
    form.desc.data = product.attributes.get('desc', '')
    return render_template('edit_product.html', form=form, product=product)

@bp.route('/update_price/<int:product_id>', methods=['POST'])
@login_required
def update_price(product_id):
    """卖家修改商品价格"""
    product = Product.query.get_or_404(product_id)
    
    if product.seller_id != current_user.id:
        return jsonify({'success': False, 'message': '无权操作'})
    
    if product.status != 1:
        return jsonify({'success': False, 'message': '商品不在售卖状态，无法改价'})
    
    new_price = request.json.get('price')
    if not new_price or float(new_price) <= 0:
        return jsonify({'success': False, 'message': '请输入有效的价格'})
    
    old_price = product.price
    product.price = float(new_price)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'价格已从 ¥{old_price} 更新为 ¥{new_price}',
        'old_price': old_price,
        'new_price': new_price
    })

@bp.route('/toggle_product_status/<int:product_id>', methods=['POST'])
@login_required
def toggle_product_status(product_id):
    """上架/下架商品"""
    product = Product.query.get_or_404(product_id)
    
    if product.seller_id != current_user.id:
        return jsonify({'success': False, 'message': '无权操作'})
    
    if product.status == 1:  # 在售 -> 下架
        product.status = 0  # 0表示下架
        action = '下架'
    elif product.status == 0:  # 下架 -> 在售
        product.status = 1
        action = '上架'
    else:
        return jsonify({'success': False, 'message': '当前商品状态无法切换'})
    
    db.session.commit()
    return jsonify({'success': True, 'message': f'商品已{action}', 'new_status': product.status})

@bp.route('/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    """删除商品"""
    product = Product.query.get_or_404(product_id)
    
    if product.seller_id != current_user.id:
        return jsonify({'success': False, 'message': '无权操作'})
    
    if product.status in [2, 3]:  # 已下单或已售出的商品不能删除
        return jsonify({'success': False, 'message': '该商品有订单记录，无法删除'})
    
    db.session.delete(product)
    db.session.commit()
    
    return jsonify({'success': True, 'message': '商品已删除'})

@bp.route('/messages')
@login_required
def my_messages():
    """卖家消息中心"""
    if current_user.role != 'seller':
        flash('您不是卖家', 'warning')
        return redirect(url_for('buyer.index'))
    
    # 获取收到的所有消息（按商品分组）
    received_messages = Message.query.filter_by(receiver_id=current_user.id).order_by(Message.created_at.desc()).all()
    
    # 按商品和买家分组
    conversations = {}
    for msg in received_messages:
        # 跳过商品或买家已被删除的消息
        if msg.product is None or msg.sender is None:
            continue
            
        key = (msg.product_id, msg.sender_id)
        if key not in conversations:
            conversations[key] = {
                'product': msg.product,
                'buyer': msg.sender,
                'messages': [],
                'unread_count': 0
            }
        conversations[key]['messages'].append(msg)
        if not msg.is_read:
            conversations[key]['unread_count'] += 1
    
    # 转换为列表
    conversation_list = sorted(
        conversations.values(),
        key=lambda x: x['messages'][0].created_at,
        reverse=True
    )
    
    return render_template('seller_messages.html', conversations=conversation_list)

@bp.route('/reply_message', methods=['POST'])
@login_required
def reply_message():
    """回复买家消息"""
    product_id = request.json.get('product_id')
    buyer_id = request.json.get('buyer_id')
    content = request.json.get('content', '').strip()
    
    if not all([product_id, buyer_id, content]):
        return jsonify({'success': False, 'message': '参数不完整'})
    
    product = Product.query.get_or_404(product_id)
    if product.seller_id != current_user.id:
        return jsonify({'success': False, 'message': '无权操作'})
    
    message = Message(
        product_id=product_id,
        sender_id=current_user.id,
        receiver_id=buyer_id,
        content=content,
        message_type='text'
    )
    
    db.session.add(message)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '回复已发送',
        'data': {
            'id': message.id,
            'content': message.content,
            'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
    })

@bp.route('/accept_offer/<int:message_id>', methods=['POST'])
@login_required
def accept_offer(message_id):
    """接受买家议价"""
    message = Message.query.get_or_404(message_id)
    
    if message.receiver_id != current_user.id:
        return jsonify({'success': False, 'message': '无权操作'})
    
    if message.message_type != 'price_offer':
        return jsonify({'success': False, 'message': '这不是一个议价消息'})
    
    product = message.product
    if product.seller_id != current_user.id:
        return jsonify({'success': False, 'message': '无权操作'})
    
    if product.status != 1:
        return jsonify({'success': False, 'message': '商品不在售卖状态'})
    
    # 更新商品价格
    old_price = product.price
    product.price = message.offer_price
    
    # 发送确认消息给买家
    reply = Message(
        product_id=product.id,
        sender_id=current_user.id,
        receiver_id=message.sender_id,
        content=f'我已接受您的议价 ¥{message.offer_price}，商品价格已更新！',
        message_type='text'
    )
    
    db.session.add(reply)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'已接受议价，价格从 ¥{old_price} 更新为 ¥{message.offer_price}',
        'old_price': old_price,
        'new_price': message.offer_price
    })