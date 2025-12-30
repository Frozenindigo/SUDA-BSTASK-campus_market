from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, SelectField, TextAreaField, IntegerField, EmailField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])
    submit = SubmitField('登录')

class RegisterForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('密码', validators=[DataRequired()])
    role = SelectField('注册角色', choices=[('buyer', '普通买家'), ('seller', '认证卖家')])
    submit = SubmitField('注册')

class ProductForm(FlaskForm):
    title = StringField('商品标题', validators=[DataRequired()])
    price = FloatField('价格', validators=[DataRequired()])
    category = SelectField('商品分类', choices=[
        ('second', '二手闲置 (孤品)'), 
        ('creative', '校园文创 (设计)'), 
        ('agri', '助农特产 (食品)')
    ])
    # 模拟图片上传，实际项目用FileField，这里填URL演示方便
    image_url = StringField('图片链接 (可留空用默认图)')
    desc = TextAreaField('商品描述 / 产地 / 新旧程度')
    submit = SubmitField('立即发布')

class BountyForm(FlaskForm):
    title = StringField('求购物品名称', validators=[DataRequired()])
    budget = FloatField('你的预算', validators=[DataRequired()])
    desc = TextAreaField('详细需求描述')
    submit = SubmitField('发布悬赏')

class ReviewForm(FlaskForm):
    rating = IntegerField('评分', validators=[DataRequired(), NumberRange(min=1, max=5, message='评分必须在1-5之间')])
    content = TextAreaField('评价内容', validators=[DataRequired(), Length(min=5, max=500)])
    submit = SubmitField('提交评价')

class ProfileForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(min=2, max=20)])
    email = EmailField('邮箱', validators=[Optional()])
    avatar = StringField('头像链接', validators=[Optional()])
    submit = SubmitField('保存修改')

class OrderForm(FlaskForm):
    address = StringField('收货地址', validators=[DataRequired(), Length(min=5, max=200)])
    contact = StringField('联系方式', validators=[DataRequired(), Length(min=5, max=64)])
    submit = SubmitField('确认下单')
class MessageForm(FlaskForm):
    content = TextAreaField('消息内容', validators=[DataRequired(), Length(min=1, max=500)])
    submit = SubmitField('发送')

class PriceOfferForm(FlaskForm):
    offer_price = FloatField('议价金额', validators=[DataRequired(), NumberRange(min=0.01)])
    content = TextAreaField('留言说明', validators=[Optional(), Length(max=200)])
    submit = SubmitField('发送议价')
