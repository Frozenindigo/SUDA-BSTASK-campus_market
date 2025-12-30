from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.buyer import bp
from app.models import Product, Bounty, User, Review, Order, Favorite, Cart, Message, BrowsingHistory
from app.forms import BountyForm, ReviewForm, OrderForm, ProfileForm, MessageForm, PriceOfferForm
from datetime import datetime
import random
import string

@bp.route('/')
def index():
    """
    买家端首页 - 支持搜索、筛选和分页
    """
    # 1. 获取筛选参数
    query = request.args.get('q', '')
    category = request.args.get('category', '')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    sort_by = request.args.get('sort_by', 'latest')  # latest, price_asc, price_desc
    page = request.args.get('page', 1, type=int)
    per_page = 12  # 每页显示12个商品
    
    # 2. 构建查询
    products_query = Product.query.filter_by(status=1)
    
    # 搜索筛选
    if query:
        products_query = products_query.filter(Product.title.contains(query))
    
    # 分类筛选
    if category:
        products_query = products_query.filter_by(category=category)
    
    # 价格区间筛选
    if min_price is not None:
        products_query = products_query.filter(Product.price >= min_price)
    if max_price is not None:
        products_query = products_query.filter(Product.price <= max_price)
    
    # 排序
    if sort_by == 'price_asc':
        products_query = products_query.order_by(Product.price.asc())
    elif sort_by == 'price_desc':
        products_query = products_query.order_by(Product.price.desc())
    else:  # latest
        products_query = products_query.order_by(Product.timestamp.desc())
    
    # 分页
    products_pagination = products_query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    products = products_pagination.items
    
    # 3. 悬赏墙逻辑
    bounties = Bounty.query.filter_by(status=0).order_by(Bounty.created_at.desc()).limit(6).all()
    
    # 4. 数据统计
    user_count = User.query.count()
    product_count = Product.query.count()
    bounty_count = Bounty.query.count()
    
    # 5. 获取价格范围（用于筛选器）
    price_range = db.session.query(
        db.func.min(Product.price).label('min'),
        db.func.max(Product.price).label('max')
    ).filter_by(status=1).first()

    return render_template('index.html', 
                           products=products,
                           pagination=products_pagination,
                           query=query,
                           category=category,
                           min_price=min_price,
                           max_price=max_price,
                           sort_by=sort_by,
                           price_range=price_range,
                           bounties=bounties,
                           user_count=user_count,
                           product_count=product_count,
                           bounty_count=bounty_count)

@bp.route('/product/<int:product_id>')
def product_detail(product_id):
    """
    商品详情页
    """
    product = Product.query.get_or_404(product_id)
    
    # 记录浏览历史（仅登录用户）
    if current_user.is_authenticated:
        # 检查是否已有浏览记录
        existing_history = BrowsingHistory.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()
        
        if existing_history:
            # 更新浏览时间
            existing_history.viewed_at = datetime.utcnow()
        else:
            # 创建新的浏览记录
            history = BrowsingHistory(
                user_id=current_user.id,
                product_id=product_id
            )
            db.session.add(history)
        
        db.session.commit()
    
    # 获取该商品的所有评价
    reviews = product.reviews.order_by(Review.timestamp.desc()).all()
    
    # 检查是否已收藏
    is_favorited = False
    if current_user.is_authenticated:
        is_favorited = Favorite.query.filter_by(
            user_id=current_user.id, 
            product_id=product_id
        ).first() is not None
    
    # 检查是否已评价
    has_reviewed = False
    if current_user.is_authenticated:
        has_reviewed = Review.query.filter_by(
            buyer_id=current_user.id,
            product_id=product_id
        ).first() is not None
    
    # 获取与卖家的聊天记录
    messages = []
    if current_user.is_authenticated and current_user.id != product.seller_id:
        messages = Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.receiver_id == product.seller_id)) |
            ((Message.sender_id == product.seller_id) & (Message.receiver_id == current_user.id)),
            Message.product_id == product_id
        ).order_by(Message.created_at.asc()).all()
        
        # 标记消息为已读
        for msg in messages:
            if msg.receiver_id == current_user.id and not msg.is_read:
                msg.is_read = True
        db.session.commit()
    
    return render_template('product_detail.html', 
                         product=product, 
                         reviews=reviews,
                         is_favorited=is_favorited,
                         has_reviewed=has_reviewed,
                         messages=messages)

@bp.route('/send_message/<int:product_id>', methods=['POST'])
@login_required
def send_message(product_id):
    """发送消息给卖家"""
    product = Product.query.get_or_404(product_id)
    
    if product.seller_id == current_user.id:
        return jsonify({'success': False, 'message': '不能给自己发消息'})
    
    content = request.json.get('content', '').strip()
    if not content:
        return jsonify({'success': False, 'message': '消息内容不能为空'})
    
    message = Message(
        product_id=product_id,
        sender_id=current_user.id,
        receiver_id=product.seller_id,
        content=content,
        message_type='text'
    )
    
    db.session.add(message)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '消息已发送',
        'data': {
            'id': message.id,
            'content': message.content,
            'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'sender_name': current_user.username
        }
    })

@bp.route('/send_price_offer/<int:product_id>', methods=['POST'])
@login_required
def send_price_offer(product_id):
    """发送议价请求"""
    product = Product.query.get_or_404(product_id)
    
    if product.seller_id == current_user.id:
        return jsonify({'success': False, 'message': '不能给自己议价'})
    
    offer_price = request.json.get('offer_price')
    content = request.json.get('content', '')
    
    if not offer_price or float(offer_price) <= 0:
        return jsonify({'success': False, 'message': '请输入有效的议价金额'})
    
    message = Message(
        product_id=product_id,
        sender_id=current_user.id,
        receiver_id=product.seller_id,
        content=content or f'我想以 ¥{offer_price} 的价格购买',
        message_type='price_offer',
        offer_price=float(offer_price)
    )
    
    db.session.add(message)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '议价请求已发送',
        'data': {
            'id': message.id,
            'offer_price': message.offer_price,
            'content': message.content,
            'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
    })

@bp.route('/post_bounty', methods=['GET', 'POST'])
@login_required
def post_bounty():
    """
    发布悬赏
    """
    form = BountyForm()
    if form.validate_on_submit():
        bounty = Bounty(
            title=form.title.data, 
            budget=form.budget.data, 
            desc=form.desc.data,
            user_id=current_user.id
        )
        db.session.add(bounty)
        db.session.commit()
        flash('✨ 悬赏发布成功！全校都能看到你的心愿了。', 'success')
        return redirect(url_for('buyer.index'))
    
    return render_template('post_bounty.html', form=form)

@bp.route('/buy/<int:product_id>', methods=['GET', 'POST'])
@login_required
def buy_product(product_id):
    """
    购买商品 - 创建订单
    """
    product = Product.query.get_or_404(product_id)
    
    if product.status != 1:
        flash('⚠️ 手慢了！该商品已被抢走或下架。', 'warning')
        return redirect(url_for('buyer.product_detail', product_id=product_id))
    
    if product.seller_id == current_user.id:
        flash('🚫 您不能购买自己发布的商品。', 'info')
        return redirect(url_for('buyer.product_detail', product_id=product_id))
    
    form = OrderForm()
    if form.validate_on_submit():
        # 生成订单号
        order_no = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        
        # 创建订单
        order = Order(
            order_no=order_no,
            buyer_id=current_user.id,
            seller_id=product.seller_id,
            product_id=product.id,
            price=product.price,
            address=form.address.data,
            contact=form.contact.data,
            status=1  # 待发货（模拟已付款）
        )
        
        # 更新商品状态
        product.status = 2  # 已下单
        
        db.session.add(order)
        db.session.commit()
        
        flash(f'✅ 订单创建成功！订单号：{order_no}', 'success')
        return redirect(url_for('buyer.my_orders'))
    
    return render_template('buy_product.html', product=product, form=form)

@bp.route('/favorite/<int:product_id>', methods=['POST'])
@login_required
def toggle_favorite(product_id):
    """收藏/取消收藏商品"""
    product = Product.query.get_or_404(product_id)
    favorite = Favorite.query.filter_by(
        user_id=current_user.id,
        product_id=product_id
    ).first()
    
    if favorite:
        db.session.delete(favorite)
        action = '取消收藏'
    else:
        favorite = Favorite(user_id=current_user.id, product_id=product_id)
        db.session.add(favorite)
        action = '收藏'
    
    db.session.commit()
    return jsonify({'success': True, 'action': action})

@bp.route('/my_favorites')
@login_required
def my_favorites():
    """我的收藏"""
    favorites = Favorite.query.filter_by(user_id=current_user.id).order_by(Favorite.created_at.desc()).all()
    products = [f.product for f in favorites if f.product.status == 1]
    return render_template('my_favorites.html', products=products)

@bp.route('/browsing_history')
@login_required
def browsing_history():
    """浏览历史"""
    # 获取最近浏览的商品（去重，按最后浏览时间排序）
    history_records = db.session.query(BrowsingHistory).filter_by(
        user_id=current_user.id
    ).order_by(BrowsingHistory.viewed_at.desc()).all()
    
    # 去重：保留每个商品最新的浏览记录
    seen_products = set()
    unique_history = []
    for record in history_records:
        if record.product_id not in seen_products and record.product.status == 1:
            seen_products.add(record.product_id)
            unique_history.append(record)
    
    return render_template('browsing_history.html', history_records=unique_history)

@bp.route('/clear_history', methods=['POST'])
@login_required
def clear_history():
    """清空浏览历史"""
    BrowsingHistory.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('浏览历史已清空', 'success')
    return redirect(url_for('buyer.browsing_history'))

@bp.route('/my_orders')
@login_required
def my_orders():
    """我的订单"""
    orders = Order.query.filter_by(buyer_id=current_user.id).order_by(Order.created_at.desc()).all()
    # 为每个订单检查是否已评价
    for order in orders:
        # 悬赏订单没有product_id，跳过评价检查
        if order.is_bounty_order or order.product_id is None:
            order.has_reviewed = False
        else:
            order.has_reviewed = Review.query.filter_by(
                buyer_id=current_user.id,
                product_id=order.product_id
            ).first() is not None
    return render_template('my_orders.html', orders=orders)

@bp.route('/cancel_order/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    """取消订单"""
    order = Order.query.get_or_404(order_id)
    
    if order.buyer_id != current_user.id:
        return jsonify({'success': False, 'message': '无权操作'})
    
    if order.status not in [0, 1]:  # 只能取消待付款和待发货的订单
        return jsonify({'success': False, 'message': '当前订单状态不能取消'})
    
    order.status = 4  # 已取消
    
    # 恢复商品状态
    if order.product.status == 2:  # 如果商品是已下单状态
        order.product.status = 1  # 恢复为在售
    
    db.session.commit()
    return jsonify({'success': True, 'message': '订单已取消'})

@bp.route('/review/<int:order_id>', methods=['GET', 'POST'])
@login_required
def review_order(order_id):
    """评价订单"""
    order = Order.query.get_or_404(order_id)
    
    if order.buyer_id != current_user.id:
        flash('无权访问', 'danger')
        return redirect(url_for('buyer.my_orders'))
    
    if order.status != 3:
        flash('订单未完成，无法评价', 'warning')
        return redirect(url_for('buyer.my_orders'))
    
    # 检查是否已评价
    existing_review = Review.query.filter_by(
        buyer_id=current_user.id,
        product_id=order.product_id
    ).first()
    
    if existing_review:
        flash('您已评价过该商品', 'info')
        return redirect(url_for('buyer.my_orders'))
    
    form = ReviewForm()
    if form.validate_on_submit():
        review = Review(
            buyer_id=current_user.id,
            seller_id=order.seller_id,
            product_id=order.product_id,
            rating=form.rating.data,
            content=form.content.data
        )
        
        # 更新卖家信誉分
        seller = order.seller
        if form.rating.data >= 4:
            seller.credit_score += 5
        elif form.rating.data <= 2:
            seller.credit_score = max(0, seller.credit_score - 5)
        
        db.session.add(review)
        db.session.commit()
        
        flash('评价提交成功！', 'success')
        return redirect(url_for('buyer.my_orders'))
    
    return render_template('review_order.html', order=order, form=form)

@bp.route('/confirm_receipt/<int:order_id>')
@login_required
def confirm_receipt(order_id):
    """确认收货"""
    order = Order.query.get_or_404(order_id)
    
    if order.buyer_id != current_user.id:
        flash('无权操作', 'danger')
        return redirect(url_for('buyer.my_orders'))
    
    if order.status != 2:
        flash('订单状态不正确', 'warning')
        return redirect(url_for('buyer.my_orders'))
    
    order.status = 3  # 已完成
    order.completed_at = datetime.utcnow()
    order.product.status = 3  # 已售出
    
    db.session.commit()
    flash('确认收货成功！', 'success')
    return redirect(url_for('buyer.my_orders'))

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """个人中心"""
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.username = form.username.data
        if form.email.data:
            current_user.email = form.email.data
        if form.avatar.data:
            current_user.avatar = form.avatar.data
        
        db.session.commit()
        flash('个人资料更新成功！', 'success')
        return redirect(url_for('buyer.profile'))
    
    # 统计数据
    my_orders_count = Order.query.filter_by(buyer_id=current_user.id).count()
    my_favorites_count = Favorite.query.filter_by(user_id=current_user.id).count()
    my_products_count = Product.query.filter_by(seller_id=current_user.id).count() if current_user.role == 'seller' else 0
    my_bounties_count = Bounty.query.filter_by(user_id=current_user.id).count()
    
    return render_template('profile.html', 
                         form=form,
                         orders_count=my_orders_count,
                         favorites_count=my_favorites_count,
                         products_count=my_products_count,
                         bounties_count=my_bounties_count)

@bp.route('/my_products')
@login_required
def my_products():
    """我的发布（买家查看自己发布的商品）"""
    products = Product.query.filter_by(seller_id=current_user.id).order_by(Product.timestamp.desc()).all()
    return render_template('my_products.html', products=products)

@bp.route('/cart')
@login_required
def cart():
    """购物车页面"""
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    # 过滤掉已下架或已售出的商品
    valid_items = [item for item in cart_items if item.product.status == 1]
    total_price = sum([item.product.price * item.quantity for item in valid_items])
    return render_template('cart.html', cart_items=valid_items, total_price=total_price)

@bp.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    """添加商品到购物车"""
    product = Product.query.get_or_404(product_id)
    
    if product.status != 1:
        return jsonify({'success': False, 'message': '商品已下架或已售出'})
    
    if product.seller_id == current_user.id:
        return jsonify({'success': False, 'message': '不能购买自己发布的商品'})
    
    # 检查是否已在购物车中
    cart_item = Cart.query.filter_by(
        user_id=current_user.id,
        product_id=product_id
    ).first()
    
    if cart_item:
        cart_item.quantity += 1
        cart_item.updated_at = datetime.utcnow()
    else:
        cart_item = Cart(
            user_id=current_user.id,
            product_id=product_id,
            quantity=1
        )
        db.session.add(cart_item)
    
    db.session.commit()
    return jsonify({'success': True, 'message': '已添加到购物车'})

@bp.route('/remove_from_cart/<int:cart_id>', methods=['POST'])
@login_required
def remove_from_cart(cart_id):
    """从购物车移除商品"""
    cart_item = Cart.query.get_or_404(cart_id)
    
    if cart_item.user_id != current_user.id:
        flash('无权操作', 'danger')
        return redirect(url_for('buyer.cart'))
    
    db.session.delete(cart_item)
    db.session.commit()
    flash('已从购物车移除', 'success')
    return redirect(url_for('buyer.cart'))

@bp.route('/update_cart/<int:cart_id>', methods=['POST'])
@login_required
def update_cart(cart_id):
    """更新购物车商品数量"""
    cart_item = Cart.query.get_or_404(cart_id)
    
    if cart_item.user_id != current_user.id:
        return jsonify({'success': False, 'message': '无权操作'})
    
    quantity = request.json.get('quantity', 1)
    if quantity < 1:
        quantity = 1
    
    cart_item.quantity = quantity
    cart_item.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'quantity': quantity,
        'subtotal': cart_item.product.price * quantity
    })

@bp.route('/cart/checkout', methods=['GET', 'POST'])
@login_required
def cart_checkout():
    """购物车结算"""
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    valid_items = [item for item in cart_items if item.product.status == 1]
    
    if not valid_items:
        flash('购物车为空', 'warning')
        return redirect(url_for('buyer.cart'))
    
    form = OrderForm()
    if form.validate_on_submit():
        # 为每个商品创建订单
        order_nos = []
        for item in valid_items:
            order_no = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
            order = Order(
                order_no=order_no,
                buyer_id=current_user.id,
                seller_id=item.product.seller_id,
                product_id=item.product_id,
                price=item.product.price * item.quantity,
                address=form.address.data,
                contact=form.contact.data,
                status=1  # 待发货
            )
            # 更新商品状态
            item.product.status = 2  # 已下单
            # 删除购物车项
            db.session.delete(item)
            db.session.add(order)
            order_nos.append(order_no)
        
        db.session.commit()
        flash(f'✅ 成功创建 {len(order_nos)} 个订单！', 'success')
        return redirect(url_for('buyer.my_orders'))
    
    total_price = sum([item.product.price * item.quantity for item in valid_items])
    return render_template('cart_checkout.html', cart_items=valid_items, total_price=total_price, form=form)

@bp.route('/cart/count')
@login_required
def cart_count():
    """获取购物车商品数量（用于AJAX）"""
    count = Cart.query.filter_by(user_id=current_user.id).count()
    return jsonify({'count': count})

@bp.route('/messages')
@login_required
def my_messages():
    """我的消息列表"""
    # 获取与我相关的所有对话（按商品分组）
    sent_messages = Message.query.filter_by(sender_id=current_user.id).all()
    received_messages = Message.query.filter_by(receiver_id=current_user.id).all()
    
    # 按商品和对话对象分组
    conversations = {}
    for msg in sent_messages + received_messages:
        # 跳过商品或用户已被删除的消息
        if msg.product is None:
            continue
        
        other_user = msg.sender if msg.sender_id != current_user.id else msg.receiver
        if other_user is None:
            continue
        
        key = (msg.product_id, msg.sender_id if msg.sender_id != current_user.id else msg.receiver_id)
        if key not in conversations:
            conversations[key] = {
                'product': msg.product,
                'other_user': other_user,
                'last_message': msg,
                'unread_count': 0
            }
        else:
            if msg.created_at > conversations[key]['last_message'].created_at:
                conversations[key]['last_message'] = msg
        
        if msg.receiver_id == current_user.id and not msg.is_read:
            conversations[key]['unread_count'] += 1
    
    # 转换为列表并按最后消息时间排序
    conversation_list = sorted(
        conversations.values(),
        key=lambda x: x['last_message'].created_at,
        reverse=True
    )
    
    return render_template('my_messages.html', conversations=conversation_list)

# ==================== 悬赏接单相关功能 ====================

@bp.route('/accept_bounty/<int:bounty_id>', methods=['POST'])
@login_required
def accept_bounty(bounty_id):
    """接单悬赏"""
    bounty = Bounty.query.get_or_404(bounty_id)
    
    # 检查悬赏状态
    if bounty.status != 0:
        return jsonify({'success': False, 'message': '该悬赏已被接单或已完成'})
    
    # 不能接自己发布的悬赏
    if bounty.user_id == current_user.id:
        return jsonify({'success': False, 'message': '不能接自己发布的悬赏'})
    
    # 更新悬赏状态为"沟通中"
    bounty.status = 1
    bounty.accepter_id = current_user.id
    bounty.accepted_at = datetime.utcnow()
    
    # 发送系统消息
    system_message = Message(
        bounty_id=bounty.id,
        sender_id=current_user.id,
        receiver_id=bounty.user_id,
        content=f'我已接单您的悬赏"{bounty.title}"，让我们沟通一下具体需求吧！',
        message_type='text'
    )
    
    db.session.add(system_message)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '接单成功！请与发布者沟通',
        'bounty_id': bounty.id
    })

@bp.route('/bounty_chat/<int:bounty_id>')
@login_required
def bounty_chat(bounty_id):
    """悬赏聊天页面"""
    bounty = Bounty.query.get_or_404(bounty_id)
    
    # 检查权限：只有发布者和接单者可以查看
    if bounty.user_id != current_user.id and bounty.accepter_id != current_user.id:
        flash('无权访问该悬赏对话', 'danger')
        return redirect(url_for('buyer.index'))
    
    # 获取聊天记录
    messages = Message.query.filter_by(bounty_id=bounty_id).order_by(Message.created_at.asc()).all()
    
    # 标记消息为已读
    for msg in messages:
        if msg.receiver_id == current_user.id and not msg.is_read:
            msg.is_read = True
    db.session.commit()
    
    # 判断当前用户角色
    is_author = (bounty.user_id == current_user.id)
    other_user = bounty.accepter if is_author else bounty.author
    
    return render_template('bounty_chat.html',
                         bounty=bounty,
                         messages=messages,
                         is_author=is_author,
                         other_user=other_user)

@bp.route('/send_bounty_message/<int:bounty_id>', methods=['POST'])
@login_required
def send_bounty_message(bounty_id):
    """发送悬赏聊天消息"""
    bounty = Bounty.query.get_or_404(bounty_id)
    
    # 检查权限
    if bounty.user_id != current_user.id and bounty.accepter_id != current_user.id:
        return jsonify({'success': False, 'message': '无权发送消息'})
    
    content = request.json.get('content', '').strip()
    if not content:
        return jsonify({'success': False, 'message': '消息内容不能为空'})
    
    # 确定接收者
    receiver_id = bounty.user_id if current_user.id == bounty.accepter_id else bounty.accepter_id
    
    message = Message(
        bounty_id=bounty_id,
        sender_id=current_user.id,
        receiver_id=receiver_id,
        content=content,
        message_type='text'
    )
    
    db.session.add(message)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '消息已发送',
        'data': {
            'id': message.id,
            'content': message.content,
            'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'sender_name': current_user.username
        }
    })

@bp.route('/create_bounty_order/<int:bounty_id>', methods=['POST'])
@login_required
def create_bounty_order(bounty_id):
    """创建悬赏订单（从聊天页面）"""
    bounty = Bounty.query.get_or_404(bounty_id)
    
    # 只有悬赏发布者可以创建订单
    if bounty.user_id != current_user.id:
        return jsonify({'success': False, 'message': '只有发布者可以创建订单'})
    
    if bounty.status != 1:
        return jsonify({'success': False, 'message': '悬赏状态不正确'})
    
    # 获取表单数据
    data = request.json
    final_price = data.get('price', bounty.budget)
    address = data.get('address', '').strip()
    contact = data.get('contact', '').strip()
    
    if not address or not contact:
        return jsonify({'success': False, 'message': '请填写完整的收货信息'})
    
    # 生成订单号
    order_no = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    
    # 创建订单
    order = Order(
        order_no=order_no,
        buyer_id=bounty.user_id,  # 发布者是买家
        seller_id=bounty.accepter_id,  # 接单者是卖家
        product_id=None,  # 悬赏订单没有关联商品
        price=float(final_price),
        address=address,
        contact=contact,
        status=1,  # 待发货（模拟已付款）
        is_bounty_order=True
    )
    
    # 更新悬赏状态
    bounty.status = 2  # 已完成
    bounty.order_id = order.id
    
    db.session.add(order)
    db.session.commit()
    
    # 关联订单
    bounty.order_id = order.id
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'订单创建成功！订单号：{order_no}',
        'order_no': order_no
    })

@bp.route('/my_bounties')
@login_required
def my_bounties():
    """我的悬赏（发布的和接单的）"""
    # 我发布的悬赏
    posted_bounties = Bounty.query.filter_by(user_id=current_user.id).order_by(Bounty.created_at.desc()).all()
    
    # 我接单的悬赏
    accepted_bounties = Bounty.query.filter_by(accepter_id=current_user.id).order_by(Bounty.accepted_at.desc()).all()
    
    return render_template('my_bounties.html',
                         posted_bounties=posted_bounties,
                         accepted_bounties=accepted_bounties)

@bp.route('/cancel_bounty/<int:bounty_id>', methods=['POST'])
@login_required
def cancel_bounty(bounty_id):
    """取消悬赏"""
    bounty = Bounty.query.get_or_404(bounty_id)
    
    # 只有发布者可以取消
    if bounty.user_id != current_user.id:
        return jsonify({'success': False, 'message': '只有发布者可以取消悬赏'})
    
    # 只有待接单状态可以取消
    if bounty.status != 0:
        return jsonify({'success': False, 'message': '该悬赏无法取消'})
    
    bounty.status = 3  # 已取消
    db.session.commit()
    
    return jsonify({'success': True, 'message': '悬赏已取消'})