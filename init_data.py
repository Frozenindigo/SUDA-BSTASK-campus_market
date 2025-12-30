# init_data.py
from app import create_app, db
from app.models import User, Product, Bounty, Order, Favorite, Cart, Message, BrowsingHistory
import random

app = create_app()

with app.app_context():
    db.create_all()
    
    # 1. 创建用户
    if not User.query.filter_by(username='seller').first():
        u1 = User(username='seller', role='seller', avatar='https://api.dicebear.com/7.x/avataaars/svg?seed=Annie')
        u1.set_password('123456')
        u2 = User(username='buyer', role='buyer', avatar='https://api.dicebear.com/7.x/avataaars/svg?seed=Bob')
        u2.set_password('123456')
        u3 = User(username='alice', role='seller', avatar='https://api.dicebear.com/7.x/avataaars/svg?seed=Alice')
        u3.set_password('123456')
        u4 = User(username='charlie', role='buyer', avatar='https://api.dicebear.com/7.x/avataaars/svg?seed=Charlie')
        u4.set_password('123456')
        u5 = User(username='admin', role='admin', email='admin@suda.edu.cn',
             avatar='https://api.dicebear.com/7.x/avataaars/svg?seed=Admin')
        u5.set_password('admin888')
        db.session.add_all([u1, u2, u3, u4, u5])
        db.session.commit()
        print("✅ 用户创建成功: seller/123456, buyer/123456, alice/123456, charlie/123456, admin/admin888")
    # 2. 创建商品数据 - 使用更匹配的图片
    products_data = [
        # 二手闲置
        {
            'title': '二手自行车 - 9成新',
            'price': 199.0,
            'category': 'second',
            'image': 'https://images.unsplash.com/photo-1485965120184-e220f721d03e?w=400',
            'desc': '捷安特山地车，骑了半年，车况良好，有意私聊。'
        },
        {
            'title': 'iPhone 12 - 128G 蓝色',
            'price': 3200.0,
            'category': 'second',
            'image': 'https://images.unsplash.com/photo-1592286927505-2fd0805e1bc2?w=400',
            'desc': '自用一年，无磕碰，电池健康度88%，配原装充电器。'
        },
        {
            'title': '大学教材 - 高等数学',
            'price': 15.0,
            'category': 'second',
            'image': 'https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=400',
            'desc': '高数上下册，笔记齐全，考研必备！'
        },
        {
            'title': 'MacBook Pro 2019',
            'price': 5800.0,
            'category': 'second',
            'image': 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400',
            'desc': '13寸，i5处理器，8G内存，256G固态，无划痕。'
        },
        {
            'title': '宿舍小冰箱',
            'price': 180.0,
            'category': 'second',
            'image': 'https://images.unsplash.com/photo-1584568694244-14fbdf83bd30?w=400',
            'desc': '容量50L，制冷效果好，毕业甩卖。'
        },
        {
            'title': '罗技G502鼠标',
            'price': 299.0,
            'category': 'second',
            'image': 'https://images.unsplash.com/photo-1527814050087-3793815479db?w=400',
            'desc': '电竞鼠标，手感一流，配重可调。'
        },
        {
            'title': '米家台灯',
            'price': 79.0,
            'category': 'second',
            'image': 'https://images.unsplash.com/photo-1513506003901-1e6a229e2d15?w=400',
            'desc': '护眼台灯，色温可调，宿舍学习必备。'
        },
        {
            'title': '索尼WH-1000XM4耳机',
            'price': 1580.0,
            'category': 'second',
            'image': 'https://images.unsplash.com/photo-1546435770-a3e426bf472b?w=400',
            'desc': '降噪耳机之王，用了半年，包装配件齐全。'
        },
        
        # 校园文创
        {
            'title': '手绘校园明信片套装',
            'price': 28.0,
            'category': 'creative',
            'image': 'https://images.unsplash.com/photo-1506929562872-bb421503ef21?w=400',
            'desc': '美院学姐手绘，12张装，记录校园美好时光。'
        },
        {
            'title': '定制帆布包 - 校训款',
            'price': 45.0,
            'category': 'creative',
            'image': 'https://images.unsplash.com/photo-1590874103328-eac38a683ce7?w=400',
            'desc': '纯棉帆布，印有校训，环保又时尚。'
        },
        {
            'title': '手工编织围巾',
            'price': 68.0,
            'category': 'creative',
            'image': 'https://images.unsplash.com/photo-1520903920243-00d872a2d1c9?w=400',
            'desc': '纯羊毛，纯手工编织，温暖过冬。'
        },
        {
            'title': '校园风景摄影集',
            'price': 35.0,
            'category': 'creative',
            'image': 'https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=400',
            'desc': '摄影社作品集，记录四季校园，限量100本。'
        },
        
        # 助农特产
        {
            'title': '农家土鸡蛋 30枚',
            'price': 38.0,
            'category': 'agri',
            'image': 'https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=400',
            'desc': '老家散养土鸡蛋，新鲜直达，营养丰富。'
        },
        {
            'title': '苏州东山白玉枇杷',
            'price': 58.0,
            'category': 'agri',
            'image': 'https://images.unsplash.com/photo-1580239089973-54c6e9f81a6a?w=400',
            'desc': '应季水果，甜度高，果肉饱满，包邮到校。'
        },
        {
            'title': '阳澄湖大闸蟹',
            'price': 168.0,
            'category': 'agri',
            'image': 'https://images.unsplash.com/photo-1580217592430-e756dc66e5d0?w=400',
            'desc': '3.5两公蟹，膏肥黄满，顺丰包邮。'
        },
        {
            'title': '农家自制蜂蜜',
            'price': 88.0,
            'category': 'agri',
            'image': 'https://images.unsplash.com/photo-1587049352846-4a222e784eaf?w=400',
            'desc': '百花蜜，纯天然无添加，500g装。'
        },
        
        # 更多二手物品
        {
            'title': '小米手环6',
            'price': 129.0,
            'category': 'second',
            'image': 'https://images.unsplash.com/photo-1575311373937-040b8e1fd5b6?w=400',
            'desc': '健康监测，运动记录，闲置转让。'
        },
        {
            'title': '瑜伽垫套装',
            'price': 45.0,
            'category': 'second',
            'image': 'https://images.unsplash.com/photo-1601925260368-ae2f83cf8b7f?w=400',
            'desc': '含瑜伽垫、弹力带、瑜伽球，9成新。'
        },
        {
            'title': '吉他 - 雅马哈F310',
            'price': 580.0,
            'category': 'second',
            'image': 'https://images.unsplash.com/photo-1510915361894-db8b60106cb1?w=400',
            'desc': '入门神器，音色纯正，送教程和picks。'
        },
        {
            'title': '滑板 - 双翘板',
            'price': 168.0,
            'category': 'second',
            'image': 'https://images.unsplash.com/photo-1547447134-cd3f5c716030?w=400',
            'desc': '加拿大枫木板面，ABEC-7轴承，顺滑流畅。'
        },
        {
            'title': 'Kindle Paperwhite',
            'price': 480.0,
            'category': 'second',
            'image': 'https://images.unsplash.com/photo-1592496431122-2349e0fbc666?w=400',
            'desc': '阅读神器，8G存储，护眼背光。'
        },
        {
            'title': '运动鞋 - 耐克Air Max',
            'price': 399.0,
            'category': 'second',
            'image': 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400',
            'desc': '42码，穿过3次，几乎全新。'
        },
        {
            'title': 'iPad 2021 - 64G',
            'price': 2100.0,
            'category': 'second',
            'image': 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400',
            'desc': '学习利器，配Apple Pencil一代。'
        },
        {
            'title': '单反相机 - 佳能800D',
            'price': 3800.0,
            'category': 'second',
            'image': 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=400',
            'desc': '套机含18-55镜头，快门不到5000次。'
        }
    ]
    
    seller = User.query.filter_by(role='seller').first()
    alice = User.query.filter_by(username='alice').first()
    
    for i, product_data in enumerate(products_data):
        # 随机分配给seller或alice
        owner = seller if i % 3 != 0 else alice
        
        existing = Product.query.filter_by(title=product_data['title'], seller_id=owner.id).first()
        if not existing:
            p = Product(
                title=product_data['title'],
                price=product_data['price'],
                category=product_data['category'],
                seller_id=owner.id,
                image_url=product_data['image'],
                attributes={'desc': product_data['desc']}
            )
            db.session.add(p)
    
    # 3. 创建悬赏数据
    buyer = User.query.filter_by(role='buyer').first()
    bounties = [
        {'title': '急求二手电动车', 'budget': 500, 'desc': '要求电池耐用，能跑20公里以上'},
        {'title': '寻找考研数学辅导老师', 'budget': 300, 'desc': '需要数学系学长学姐，一周2-3次'},
        {'title': '求购机械键盘', 'budget': 200, 'desc': '青轴或茶轴，品牌不限'}
    ]
    
    for bounty_data in bounties:
        existing = Bounty.query.filter_by(title=bounty_data['title']).first()
        if not existing:
            b = Bounty(
                title=bounty_data['title'],
                budget=bounty_data['budget'],
                desc=bounty_data['desc'],
                user_id=buyer.id
            )
            db.session.add(b)
    
    db.session.commit()
    print("✅ 演示数据填充完毕！")
    print("📊 商品数量:", Product.query.count())
    print("👥 用户数量:", User.query.count())
    print("💰 悬赏数量:", Bounty.query.count())
