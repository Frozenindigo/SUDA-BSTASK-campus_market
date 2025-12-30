from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login
import json

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    email = db.Column(db.String(120), index=True)
    role = db.Column(db.String(20), default='buyer')
    avatar = db.Column(db.String(256), default='https://api.dicebear.com/7.x/notionists/svg?seed=Felix')
    
    # 信誉分
    credit_score = db.Column(db.Integer, default=100)
    
    # 🔥 修复点：明确指定外键
    reviews_received = db.relationship(
        'Review', 
        foreign_keys='Review.seller_id', 
        backref='seller', 
        lazy='dynamic'
    )
    
    # 订单关系
    orders_bought = db.relationship('Order', foreign_keys='Order.buyer_id', backref='buyer', lazy='dynamic')
    orders_sold = db.relationship('Order', foreign_keys='Order.seller_id', backref='seller', lazy='dynamic')
    
    # 收藏关系
    favorites = db.relationship('Favorite', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    # 购物车关系
    cart_items = db.relationship('Cart', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def average_rating(self):
        reviews = self.reviews_received.all()
        if not reviews: return 5.0
        return round(sum([r.rating for r in reviews]) / len(reviews), 1)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String(128))
    price = db.Column(db.Float)
    image_url = db.Column(db.String(256))
    category = db.Column(db.String(20))
    status = db.Column(db.Integer, default=1)
    _attributes = db.Column('attributes', db.Text, default='{}')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    seller = db.relationship('User', foreign_keys=[seller_id], backref='products')
    reviews = db.relationship('Review', backref='product', lazy='dynamic')
    favorites = db.relationship('Favorite', backref='product', lazy='dynamic', cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='product', lazy='dynamic')
    cart_items = db.relationship('Cart', backref='product', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def attributes(self):
        return json.loads(self._attributes)
    @attributes.setter
    def attributes(self, value):
        self._attributes = json.dumps(value)

class Bounty(db.Model):
    """悬赏模型 - 增强版"""
    __tablename__ = 'bounties'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # 发布悬赏的人
    title = db.Column(db.String(128))
    budget = db.Column(db.Float)
    desc = db.Column(db.Text)
    status = db.Column(db.Integer, default=0)  # 0:待接单 1:沟通中 2:已完成 3:已取消
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 接单相关字段
    accepter_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # 接单人
    accepted_at = db.Column(db.DateTime)  # 接单时间
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))  # 关联的订单
    
    author = db.relationship('User', foreign_keys=[user_id], backref='posted_bounties')
    accepter = db.relationship('User', foreign_keys=[accepter_id], backref='accepted_bounties')
    
    def status_text(self):
        status_map = {0: '待接单', 1: '沟通中', 2: '已完成', 3: '已取消'}
        return status_map.get(self.status, '未知')

class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    
    rating = db.Column(db.Integer)
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 这里的 relationship 保持不变，因为指定了 foreign_keys=[buyer_id]
    buyer = db.relationship('User', foreign_keys=[buyer_id], backref='reviews_written')

class Order(db.Model):
    """订单模型"""
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(32), unique=True, index=True)  # 订单号
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    
    price = db.Column(db.Float)  # 订单价格
    status = db.Column(db.Integer, default=0)  # 0:待付款 1:待发货 2:待收货 3:已完成 4:已取消
    address = db.Column(db.String(256))  # 收货地址
    contact = db.Column(db.String(64))  # 联系方式
    
    # 新增：标记是否为悬赏订单
    is_bounty_order = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime)  # 付款时间
    shipped_at = db.Column(db.DateTime)  # 发货时间
    completed_at = db.Column(db.DateTime)  # 完成时间
    
    def status_text(self):
        status_map = {0: '待付款', 1: '待发货', 2: '待收货', 3: '已完成', 4: '已取消'}
        return status_map.get(self.status, '未知')

class Favorite(db.Model):
    """收藏模型"""
    __tablename__ = 'favorites'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='unique_favorite'),)

class Cart(db.Model):
    """购物车模型"""
    __tablename__ = 'carts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    quantity = db.Column(db.Integer, default=1)  # 商品数量
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='unique_cart_item'),)

class Message(db.Model):
    """买家卖家沟通消息模型"""
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    bounty_id = db.Column(db.Integer, db.ForeignKey('bounties.id'))  # 新增：关联悬赏
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    content = db.Column(db.Text)
    message_type = db.Column(db.String(20), default='text')  # text, price_offer
    offer_price = db.Column(db.Float)  # 议价金额
    is_read = db.Column(db.Boolean, default=False)  # 是否已读
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    product = db.relationship('Product', backref='messages')
    bounty = db.relationship('Bounty', backref='messages')  # 新增：悬赏消息关系
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')

class BrowsingHistory(db.Model):
    """浏览历史模型"""
    __tablename__ = 'browsing_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='browsing_history')
    product = db.relationship('Product', backref='browsing_records')
    
    __table_args__ = (db.Index('idx_user_viewed', 'user_id', 'viewed_at'),)

