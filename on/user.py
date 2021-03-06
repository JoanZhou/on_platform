# -*- coding: utf-8 -*-
from django.db import models
from django.core.validators import URLValidator
import uuid
import django.utils.timezone as timezone
import decimal
import requests
from django.conf import settings
import os
from .QR_invite import user_qrcode, save_qrcode
from logging import getLogger

# from on.activities.running.models import RunningGoal


logger = getLogger("address")


class UserManager(models.Manager):
    # 提现
    def clear_balance(self, user_id):
        user = self.get(user_id=user_id)
        user.balance = decimal.Decimal(0)
        user.save()

    # 使用余额
    def use_balance(self, user_id, pay_delay):
        user = self.get(user_id=user_id)
        user.balance += decimal.Decimal(pay_delay)
        user.save()

    # 新进账的钱, 要同时增加累计收益与余额
    def update_balance(self, user_id, pay_delta):
        user = self.get(user_id=user_id)
        # 累计收益
        user.add_money += decimal.Decimal(pay_delta)
        # 所有收益
        user.all_profit += decimal.Decimal(pay_delta)
        # 今日收益
        user.today_profit += decimal.Decimal(pay_delta)
        user.save()

    # 增加用户的额外收益
    def updata_extra(self, user_id, pay_delta):
        user = self.get(user_id=user_id)
        user.extra_money += decimal.Decimal(pay_delta)
        user.save()

    # 更新用户的押金，是由微信支付后得到的
    def update_deposit(self, user_id, pay_delta):
        user = self.get(user_id=user_id)
        user.deposit += decimal.Decimal(pay_delta)
        if user.deposit < 0:
            user.deposit = 0
        user.save()

    # 当用户结束活动之后，将获取到的金额存储到余额中
    def save_balance(self, user_id, price, bonus,extra_earn):
        user = self.get(user_id=user_id)
        user.balance += decimal.Decimal(price)
        # 活动结束之后，将用户的累计收益改为0
        print("开始修改累计收益{}".format(price))
        user.add_money -= bonus
        print("将用户的累计收益改为0")
        user.extra_money -= extra_earn
        print("将用户的额外收益改成0")
        print("修改累计收益成功{}".format(user.add_money))
        user.save()

    # 活动结束之后处理用户的其他收益
    def read_handle(self, user_id, bonus):
        user = self.get(user_id=user_id)
        user.balance += decimal.Decimal(bonus)
        user.add_money -= decimal.Decimal(bonus)
        user.save()

    # sleep活动处理
    def sleep_handle(self,user_id,bonus,guaranty,extra_earn):
        try:
            user = self.get(user_id=user_id)
            #将用户的收益写进余额
            user.balance += decimal.Decimal(bonus)+decimal.Decimal(guaranty)+decimal.Decimal(extra_earn)
            #再将用户的累计收益出去余额
            user.add_money -= decimal.Decimal(bonus)
            user.extra_money -= extra_earn
            user.save()
        except Exception as e:
            print(e)
            pass

    # 额外收益处理

    def get_next_id(self):
        return self.count()

    # 微信用户openid是否存在
    def check_user(self, openid):
        users = self.filter(wechat_id=openid)
        if users:
            return users[0]
        else:
            return None

    # 创建一个新的用户
    def create_user(self, openid, nickname, imgurl, sex):
        # 获取新的 user_id
        user_id = 100100 + self.get_next_id()
        # 获取imgurl,并将其存入static中user的avatar里
        response = requests.get(imgurl)
        # 文件存储的实际路径
        filePath = os.path.join(settings.AVATAR_DIR, str(user_id) + ".jpg")
        # 引用所使用的路径
        refPath = os.path.join(settings.AVATAR_ROOT, str(user_id) + ".jpg")
        # 写入文件内容
        with open(filePath, 'wb') as f:
            f.write(response.content)
        # 创建用户的基本表
        user = self.create(user_id=user_id,
                           sex=sex,
                           wechat_id=openid,
                           nickname=user_id,
                           headimgurl=refPath)
        # 创建用户历史记录数据表
        UserRecord.objects.create_record(user=user)
        try:
            save_qrcode(user.user_id)
        except Exception as e:
            print("生成用户的二维码失败", e)

        # 创建用户邀请数量表
        # Invitenum.objects.create(user_id=user_id,invite_num=0,earn_more=0)
        return user

    # 通过openid获取用户
    def get_user_by_openid(self, openid):
        user = self.filter(wechat_id=openid)
        if user:
            return user[0]
        else:
            return None

    # 获取用户的收货地址
    def get_address(self, user_id):
        # get_or_create方法会根据其参数，从数据库中查询符合条件的记录，如果没有符合条件的记录，则会依据参数创建一条新纪录。
        address, is_create = self.get_or_create(user_id=user_id)
        if not is_create:
            return address
        else:
            return None

    # 修改用户的收货地址
    def update_address(self, user, field_dict):
        # 将手机号单独取出来
        try:
            number = int(field_dict['phone'])
        except Exception:
            number = None
        # 将手机号从字典数据中弹出,此时那个字典里面没有手机号
        field_dict.pop('phone')
        # **是将字典里面的数据变成键=值的状态
        self.filter(user=user).update(phone=number, **field_dict)
        user_address = self.filter(user=user)[0]
        # 只要修改收货地址，即更新尚未发货的订单的收货地址
        # UserOrder.objects.filter(user_id=user.user_id).filter(delivery_time=None).update(owner_name=user_address.name,
        #                                                                                  address=user_address.address,
        #                                                                                  owner_phone=user_address.phone)

    # 检查用户的收货地址是否完整，用于决定是否要发送提醒
    def address_is_complete(self, user):
        address_obj = self.filter(user=user)
        if not address_obj:
            return False
        else:
            address_obj = address_obj.first()
            if not address_obj.phone or not address_obj.name or not address_obj.address:
                return False
            return True


# 记录用户的信息表，不需要冗余数据

class UserInfo(models.Model):
    """ Extending Django User Model Using a One-To-One Link
        Profile Model, based on WeChat User API
        http://admin.wechat.com/wiki/index.php?title=User_Profile
    """
    user_id = models.IntegerField(primary_key=True, default=0)
    # sex 0/not set,1/female,2/male
    sex = models.IntegerField(default=0)
    # Unique user ID for the official account, e.g.: "o6_bmjrPTlm6_2sgVt7hMZOPfL2M"
    wechat_id = models.CharField(max_length=255, unique=True)
    # User nickname, e.g.: "Band"
    nickname = models.CharField(max_length=255)
    # Profile photo URL. The last number in the URL shows the size of the square image, which can be 0 (640*640), 46, 64, 96 and 132. This parameter is null if the user hasn't set a profile photo
    # e.g.: "http://wx.qlogo.cn/mmopen/g3MonUZtNHkdmzicIlibx6iaFqAc56vxLSUfpb6n5WKSYVY0ChQKkiaJSgQ1dZuTOgvLLrhJbERQQ4eMsv84eavHiaiceqxibJxCfHe/0"
    headimgurl = models.CharField(max_length=300, validators=[URLValidator()])

    # ================== For On Platform ==================
    # 活动押金
    deposit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # 活动积分
    points = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # 余额
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # 图币
    virtual_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # 所有收益
    all_profit = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    # 今日收益
    today_profit = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    # 额外收益
    extra_money = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    # 累计收益
    add_money = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    objects = UserManager()
    # def __str__(self):
    #     return self.nickname


# 交易的管理模型，管理所有的收款，退款与提现
class UserPayManager(models.Manager):
    # 交易记录已经存在
    def exist_trade(self, transaction_id):
        if self.filter(transaction_id=transaction_id):
            return True
        else:
            return False

    # 获取利益
    def earn_profit(self, goal_id, bonus):
        self.create(goal_id=goal_id,
                    bonus=bonus)

    # 失去押金
    def loose_pay(self, goal_id, bonus):
        self.create(goal_id=goal_id,
                    bonus=-bonus)

    # 增加用户交易记录，为退款等做准备
    def create_trade(self, goal_id, trade_data):
        self.create(goal_id=goal_id,
                    device_info=trade_data['device_info'],
                    openid=trade_data['openid'],
                    trade_type=trade_data['trade_type'],
                    trade_state=trade_data['result_code'],
                    bank_type=trade_data['bank_type'],
                    total_fee=trade_data['total_fee'],
                    cash_fee=trade_data['cash_fee'],
                    fee_type=trade_data['fee_type'],
                    transaction_id=trade_data['transaction_id'],
                    out_trade_id=trade_data['out_trade_no'],
                    time_end=trade_data['time_end'])

    # 增加用户提现记录
    def create_withdraw(self, openid, amount, trade_data, user_id):
        self.create(openid=openid,
                    payment_no=trade_data['payment_no'],
                    partner_trade_no=trade_data['partner_trade_no'],
                    amount=amount,
                    user_id=user_id)

    # 获取用户退款记录
    def create_refund(self, openid, goal_id):
        # 获取用户特定目标对应的押金订单
        trade = UserTrade.objects.filter(openid=openid, goal_id=goal_id)
        print("Trade:{0}".format(trade))
        user = UserInfo.objects.get_user_by_openid(openid)
        print("User:{0}".format(user.user_id))
        # 获取退款金额
        amount = 0
        # 为避免交叉引用
        from on.models import Goal
        sub_models = get_son_models(Goal)
        for sub_model_key in sub_models:
            sub_model = sub_models[sub_model_key]
            goal = sub_model.objects.filter(user_id=user.user_id).filter(goal_id=goal_id)
            if goal:
                goal = goal.first()
                amount = int(float(goal.guaranty + goal.down_payment) * 100)
                break
        if settings.DEBUG:
            trade = trade.first()
            refund_trade = self.create(transaction_id=trade.transaction_id,
                                       openid=trade.openid,
                                       total_fee=trade.cash_fee,
                                       refund_fee=amount,
                                       goal_id=goal_id)
            return refund_trade, goal.status
        else:
            if trade and amount > 0:
                trade = trade.first()
                refund_trade = self.create(transaction_id=trade.transaction_id,
                                           openid=trade.openid,
                                           total_fee=trade.cash_fee,
                                           refund_fee=amount,
                                           goal_id=goal_id)
                return refund_trade, goal.status
            else:
                return None, goal.status


# 记录所有的收款记录
class UserTrade(models.Model):
    trade_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # 微信支付的终端设备号
    device_info = models.CharField(max_length=255)
    # 用户在商户下的唯一标识
    openid = models.CharField(max_length=255)
    # 活动ID
    goal_id = models.UUIDField(null=False, default=uuid.uuid4)
    # 交易类型 : JSAPI，NATIVE，APP，MICROPAY
    trade_type = models.CharField(max_length=255)
    # 交易状态 : SUCCESS / Others
    trade_state = models.CharField(null=False, max_length=255)
    # 银行标识
    bank_type = models.CharField(null=True, max_length=255)
    # 以分为单位的订单金额
    total_fee = models.IntegerField(null=False)
    # 根据优惠券计算出的实际支付金额
    cash_fee = models.IntegerField(null=False)
    # 货币类型
    fee_type = models.CharField(null=True, max_length=255)
    # 微信支付订单号
    transaction_id = models.CharField(null=False, max_length=255)
    # 商户订单号
    out_trade_id = models.CharField(null=False, max_length=255)
    # 支付完成的时间
    time_end = models.CharField(null=False, max_length=255)

    objects = UserPayManager()


# TODO增加用户的id字段
# 用户提现记录
class UserWithdraw(models.Model):
    trade_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # 用户在商户下的唯一标识
    openid = models.CharField(null=False, max_length=255)
    # 以分为单位的订单金额
    amount = models.IntegerField(null=False, default=0)
    # 商户订单号
    partner_trade_no = models.CharField(null=True, max_length=255)
    # 微信支付订单号
    payment_no = models.CharField(null=True, max_length=255)
    # 提现时间
    finish_time = models.DateTimeField(null=False, default=timezone.now)
    # 用户的user_id
    user_id = models.IntegerField(default=0)
    objects = UserPayManager()


class newUserWithdraw(models.Model):
    withdraw_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.IntegerField(null=False)
    openid = models.CharField(null=False, max_length=255)
    amount = models.DecimalField(default=0, max_digits=12, decimal_places=2)
    partner_trade_no = models.CharField(null=True, max_length=255)
    # 微信支付订单号
    payment_no = models.CharField(null=True, max_length=255)
    create_time = models.DateTimeField(null=False, default=timezone.now)

    class Meta:
        db_table = "on_newwithdraw"


# 活动结束用户退款记录
class UserRefund(models.Model):
    # refund_id 将作为退款订单中的 out_refund_no
    refund_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # transaction_id 将作为退款记录关联的订单号
    transaction_id = models.CharField(null=False, max_length=255)
    # 订单总金额，即当时申请订单的总金额数
    total_fee = models.IntegerField(null=False, default=1)
    # 退款总金额，即最终退还给用户的押金数
    refund_fee = models.IntegerField(null=False, default=1)
    # 退款关联goal_id
    goal_id = models.UUIDField(null=False, default=uuid.uuid4())
    # openid
    openid = models.CharField(null=True, max_length=255)

    objects = UserPayManager()


# 用户结算表，与微信支付无关，仅仅记录每个用户因为哪个活动增加了余额或减少了钱数
class UserSettlement(models.Model):
    # 自增主键
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    # 用户关联的goal_id
    goal_id = models.UUIDField(default=uuid.uuid4, editable=False)
    # 若用户是瓜分钱或返还钱，则bonus为正；否则为负
    bonus = models.FloatField(null=False, default=0)
    # 瓜分时间
    generate_time = models.DateTimeField(null=False, default=timezone.now)

    objects = UserPayManager()


class UserRelation(models.Model):
    # 这个是关系id，每一个用户对应一个关系，id值是唯一的
    relation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # 用户的ID
    user_id = models.UUIDField(null=False)
    # 好友的ID
    friend_id = models.UUIDField(null=False)
    # 群组ID 没啥用
    group_id = models.IntegerField(null=True)
    # 建立关系的时间
    create_time = models.DateTimeField(auto_created=True)
    # 备注, 由于备注存在双向关系
    remark = models.CharField(null=True, max_length=255)

class UserInviteManager(models.Manager):
    """当用户要请的人参加活动的时候距离被他邀请的人相聚三天的时候，算是邀请人邀请成功"""
    def get_user_invite(self,openid):
        time_now = timezone.now().date()
        print(time_now)
        user = self.filter(invite=openid)

        if user:
            user = user[0]
            print(user.user_id, "是哪个用户邀请的人")
            invite_time = user.create_time.date()
            if time_now-invite_time == 2:
                return user.user_id
            else:
                return False
        return False

class UserInvite(models.Model):
    # 这个是关系id，每一个用户对应一个关系，id值是唯一的
    relation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    #
    user_id = models.IntegerField(default=0)
    # 被邀请人的openid
    invite = models.CharField(null=False, max_length=225)
    # 建立关系的时间
    create_time = models.DateTimeField(auto_created=True)
    # 是否参与愚人节活动
    fools_day = models.IntegerField(null=False, default=0)
    objects = UserInviteManager()
    class Meta:
        db_table = "on_userinvite"


# 建立一个临时的用户邀请数量记录表，记录每个用户邀请了多少人
class InvitenumManager(models.Manager):
    # 更新邀请人的数量
    def undate_num(self, user_id):
        user = self.get(user_id=user_id)
        user.invite_num += 1
        user.save()

    # 更新用户的收益
    def earning(self, user_id):
        user = self.get(user_id=user_id)
        user.earn_more += 0.5
        user.save()

    # 统计用户邀请数量
    def count_num(self, user_id):
        user = self.get(user_id=user_id)
        num = user.invite_num
        return num


class Invitenum(models.Model):
    # 主键
    id = models.IntegerField(primary_key=True, default=0)
    # 用户
    user_id = models.IntegerField(default=0)
    # 邀请用户的数量
    invite_num = models.IntegerField(default=0)
    # 增加用户收益
    earn_more = models.FloatField(default=0)
    objects = InvitenumManager()

    class Meta:
        db_table = "on_invitenum"


class UserRecordManager(models.Manager):
    # 更新参加活动的次数与总系数
    def update_join(self, user, coeff):
        record = self.get(user=user)
        record.join_times += 1
        record.all_coefficient += float(coeff)
        record.save()

    # 更新完成的总天数
    def update_finish_day(self, user):
        record = self.get(user=user)
        record.finish_days += 1
        record.save()

    # 更新完成的次数
    def finish_goal(self, user):
        record = self.get(user=user)
        record.finish_times += 1
        record.save()

    # 新建用户user的记录表
    def create_record(self, user):
        self.create(user=user)

    # #用户结算之后，将用户的打卡天数重置为0
    # def clear_record(self,user_id):
    #     record = self.get(user_id=user_id)
    #     record.


class UserRecord(models.Model):
    # 记录对应的用户
    user = models.ForeignKey(UserInfo, on_delete=models.PROTECT, related_name="record")
    # 完成的次数
    finish_times = models.IntegerField(null=True, default=0)
    # 参加的次数
    join_times = models.IntegerField(null=True, default=0)
    # 完成的天数
    finish_days = models.IntegerField(null=True, default=0)
    # 总系数
    all_coefficient = models.FloatField(null=True, default=0)

    objects = UserRecordManager()


class UserTicketManager(models.Manager):
    # 创建卡券
    def create_ticket(self, goal_id, ticket_type, number):
        ticket = self.create(goal_id=goal_id,
                             ticket_type=ticket_type,
                             number=number)
        return ticket

    # 主动使用, 或被动使用
    def use_ticket(self, goal_id, ticket_type, use_time=timezone.now()):
        # 有主键约束
        try:
            exist_ticket = self.get(goal_id=goal_id, ticket_type=ticket_type)
            # goal = RunningGoal.objects.get(goal_id=goal_id)
            # if goal.is_day_now():
            #     return
            # else:
            if exist_ticket and exist_ticket.number > 0:
                # 更新数据库里票券的数量
                exist_ticket.number = exist_ticket.number - 1
                exist_ticket.save()
                # 在使用记录中增加一条, 注意这里如果是帮助用户使用，那么应该是在 **昨天** 使用。
                UserTicketUseage.objects.insert_record(goal_id, ticket_type, use_time)
                return True
            else:
                # 没有足够的票
                return False
        except Exception:
            return False

    # 查询还有多少延时券
    def get_delay_tickets(self, goal_id):
        exist_delay = self.get_or_create(goal_id=goal_id, ticket_type="D")[0]
        return exist_delay.number

    # 查询还有多少免签券
    def get_nosigned_tickets(self, goal_id):
        exist_nosigned = self.get_or_create(goal_id=goal_id, ticket_type="NS")[0]
        return exist_nosigned.number


"""
用户卡券对应表，不同的目标有不同的券
"""


class UserTicket(models.Model):
    goal_id = models.UUIDField(null=False, default=uuid.uuid4)
    TICKET_CHOICES = (
        # D = Delay
        (u'D', u'延时'),
        # NS = NoSigned
        (u'NS', u'免签')
    )
    ticket_type = models.CharField(max_length=32, choices=TICKET_CHOICES)
    number = models.IntegerField(default=0)
    objects = UserTicketManager()

    @property
    def tic_type(self):
        return self.get_ticket_type_display()

    class Meta:
        unique_together = ("goal_id", "ticket_type")


class UserTicketUseageManager(models.Manager):
    def insert_record(self, goal_id, ticket_type, time):
        self.create(goal_id=goal_id, ticket_type=ticket_type, useage_time=time)


"""
用户卡券使用记录表，主要用于查看第二天用户是否要进行延时
"""


class UserTicketUseage(models.Model):
    goal_id = models.UUIDField(null=False, default=uuid.uuid4)
    TICKET_CHOICES = (
        # D = Delay
        (u'D', u'延时'),
        # NS = NoSigned
        (u'NS', u'免签')
    )
    ticket_type = models.CharField(max_length=32, choices=TICKET_CHOICES)
    useage_time = models.DateTimeField(null=False, default=timezone.now)
    objects = UserTicketUseageManager()


"""
收货地址登记表
"""


class UserAddress(models.Model):
    user = models.OneToOneField(UserInfo, primary_key=True, null=False)
    phone = models.CharField(null=True, max_length=13)
    address = models.CharField(null=True, max_length=255)
    name = models.CharField(null=True, max_length=32)
    area = models.CharField(null=True, max_length=255)
    objects = UserManager()


STATUS_CHOICES = (
    (u'N', u'已下单'),
    (u'S', u'已发货'),
    (u'E', u'已收件')
)


class UserOrderManager(models.Manager):
    # 为阅读活动创立一个订单，如果返回None则说明信息填写不完整，不为空则说明信息填写完整
    def create_reading_goal_order(self, user_id, order_name, order_money, order_image, goal_id):
        user = UserInfo.objects.get(user_id=user_id)
        address_list = UserAddress.objects.filter(user=user)
        if not address_list:
            address_obj = UserAddress.objects.get_address(user_id=user_id)
        else:
            address_obj = address_list.first()
        activity_type = 2
        # 这里无需判断收货地址是否齐全
        order = self.create(owner_name="",
                            owner_phone="",
                            user_id=user_id,
                            address="",
                            order_money=order_money,
                            order_name=order_name,
                            order_image=order_image,
                            order_count=1,
                            area="",
                            goal_id=goal_id,
                            activity_type=activity_type)
        return order


"""
订单登记表
"""


class UserOrder(models.Model):
    order_id = models.UUIDField(primary_key=True, null=False, default=uuid.uuid4)
    # 收货人的姓名
    owner_name = models.CharField(null=True, max_length=64)
    # 收货人的电话
    owner_phone = models.CharField(null=True, max_length=13)
    # 用户ID
    user_id = models.IntegerField(null=False, default=100100)
    # 收货地址
    address = models.CharField(null=True, max_length=255)
    # 货物状态
    status = models.CharField(null=False, max_length=32, choices=STATUS_CHOICES, default='N')
    # 快递单号
    postal_code = models.CharField(null=True, max_length=255)
    # 快递单位
    postal_name = models.CharField(null=True, max_length=64)
    # 下单时间
    order_time = models.DateTimeField(null=False, default=timezone.now)
    # 发货时间
    delivery_time = models.DateTimeField(null=True)
    # 确认收货时间
    confirm_time = models.DateTimeField(null=True)
    # 订单对应的钱数
    order_money = models.FloatField(null=False, default=0)
    # 货物名称
    order_name = models.CharField(null=False, default="未填写", max_length=255)
    # 货物对应的图片
    order_image = models.CharField(null=False, default="/static/order/demo.png", max_length=255)
    # 物品数量
    order_count = models.IntegerField(null=False, default=1)
    # 备注信息，比如可以备注其关联的目标id等
    remarks = models.CharField(null=True, max_length=255)
    area = models.CharField(null=True, max_length=255)
    # 确认订单
    is_no_confirm = models.IntegerField(null=False, default=0)
    goal_id = models.UUIDField(null=True, default=uuid.uuid4)
    ACTIVITY_CHOICES = (
        (u'0', u'作息'),
        (u'1', u'跑步'),
        (u'2', u'购书阅读1期'),
        # (u'2', u'购书阅读2期')
    )
    # 活动类型
    activity_type = models.CharField(max_length=16, choices=ACTIVITY_CHOICES)

    objects = UserOrderManager()


# 获取某个模型的所有子模型
def get_son_models(model):
    all_sub_models = {}
    for sub_model in model.__subclasses__():
        all_sub_models[sub_model.__name__] = sub_model
    return all_sub_models


class FoolsDayManager(models.Manager):
    # 微信用户user是否存在
    def check_user(self, user_id):
        users = self.filter(user_id=user_id)
        if users:
            return users[0]
        else:
            return None

    # 用户增加积分
    def add_points(self, user_id):
        user = self.get(user_id=user_id)
        print("开始增加")
        user.add_point += 3
        print("增加成功")
        user.save()

    # 用户减少积分
    def reduce_points(self, user_id):
        user = self.get(user_id=user_id)
        print("开始减少")
        user.reduce_point -= 1
        print("减少成功")
        user.save()

    # 更新用户积分
    def update_point(self, user_id):
        user = self.get(user_id=user_id)
        user.point_all = user.add_point + user.reduce_point
        user.save()

    # 用户参加活动
    def join_act(self, user_id):
        user = self.get(user_id=user_id)
        user.is_no_join = 1
        user.save()

    # 判断用户是否参加了愚人节活动
    def join_in_fools(self, user_id):
        # 先判断用户是否激活了活动
        user = self.filter(user_id=user_id)
        if len(user) > 0:
            if user[0].is_no_join:
                return True
            else:
                return False
        else:
            return False


class FoolsDay(models.Model):
    # 用户的活动id
    goal_id = models.UUIDField(primary_key=True, null=False, default=uuid.uuid4)
    # 用户id
    user_id = models.IntegerField(default=0)
    # 用户的加积分
    add_point = models.IntegerField(null=False, default=0)
    # 用户减去的积分
    reduce_point = models.IntegerField(null=False, default=0)
    # 用户的总积分
    point_all = models.IntegerField(null=False, default=0)
    # 用户状态
    status = models.IntegerField(null=False, default=0)
    # 用户的参加状态
    is_no_join = models.IntegerField(null=False, default=0)
    objects = FoolsDayManager()

    class Meta:
        db_table = "on_foolsday"


class TutorialManager(models.Manager):
    pass


class Tutorial(models.Model):
    user_id = models.IntegerField(primary_key=True, default=0, null=False)
    times_in_homepage = models.IntegerField(default=0, null=True)
    times_in_running = models.IntegerField(default=0, null=True)
    times_in_read = models.IntegerField(default=0, null=True)
    times_in_sleep = models.IntegerField(default=0, null=True)
    objects = TutorialManager()

    class Meta:
        db_table = "on_tutorial"




class InviteIncomeManager(models.Manager):

    def invite_handle(self,activity_type,user_id):
        from on.models import SleepingGoal, RunningGoal, ReadingGoal
        try:
            invite = self.filter(user_id=user_id)
            user = UserInfo.objects.get(user_id=user_id)
            if invite:
                invite = invite[0]
                if activity_type == "0":
                    invite.sleep += 1
                    sleepGoal = SleepingGoal.objects.get(user_id=user_id)
                    sleepGoal.extra_earn += decimal.Decimal(2)
                    sleepGoal.save()
                elif activity_type == "1":
                    invite.run += 1
                    runGoal = RunningGoal.objects.get(user_id=user_id)
                    runGoal.extra_earn += decimal.Decimal(2)
                    runGoal.save()
                elif activity_type == "2":
                    invite.read +=1
                    #阅读表无法直接操作
                    readGoal = ReadingGoal.objects.get(user_id=user_id)
                    extra_earn = readGoal.extra_earn+decimal.Decimal(2)
                    ReadingGoal.objects.filter(user_id=user_id).update(extra_earn=extra_earn)
                user.extra_money += decimal.Decimal(2)
            else:
                if activity_type == "0":
                    self.create(user_id=user_id,sleep=1)
                    sleepGoal = SleepingGoal.objects.get(user_id=user_id)
                    sleepGoal.extra_earn += decimal.Decimal(2)
                    sleepGoal.save()
                elif activity_type == "1":
                    self.create(user_id=user_id, run=1)
                    runGoal = RunningGoal.objects.get(user_id=user_id)
                    runGoal.extra_earn += decimal.Decimal(2)
                    runGoal.save()
                elif activity_type == "2":
                    self.create(user_id=user_id, read=1)
                    readGoal = ReadingGoal.objects.get(user_id=user_id)
                    extra_earn = readGoal.extra_earn + decimal.Decimal(2)
                    ReadingGoal.objects.filter(user_id=user_id).update(extra_earn=extra_earn)
                user.extra_money += decimal.Decimal(2)
            user.save()
            invite.save()
            return True
        except Exception as e:
            print("用户的邀请收益发生错误",e)
            return False

class InviteIncome(models.Model):
    id = models.IntegerField(primary_key=True,default=0)
    user_id = models.IntegerField(default=0, null=False)
    run = models.IntegerField(null=False,default=0)
    read = models.IntegerField(null=False,default=0)
    sleep = models.IntegerField(null=False,default=0)
    objects = InviteIncomeManager()
    class Meta:
        db_table = "on_invite_income"

class BonusManager(models.Manager):

    def add_run(self,user_id,profit):
        try:
            user = self.filter(user_id=user_id)
            if user:
                user = user[0]
                user.run += profit
                user.save()
        except Exception as e:
            print(e)
            return True

    def add_read(self,user_id,profit):
        try:
            user = self.filter(user_id=user_id)
            if user:
                user = user[0]
                user.read += profit
                user.save()
        except Exception as e:
            print(e)
            return True
    def add_sleep(self,user_id,profit):
        try:
            user = self.filter(user_id=user_id)
            if user:
                user = user[0]
                user.sleep += profit
                user.save()
        except Exception as e:
            print(e)
            return True
    def add_ride(self,user_id,profit):
        try:
            user = self.filter(user_id=user_id)
            if user:
                user = user[0]
                user.ride += profit
                user.save()
        except Exception as e:
            print(e)
            return True
    def add_walk(self,user_id,profit):
        try:
            user = self.filter(user_id=user_id)
            if user:
                user = user[0]
                user.walk += profit
                user.save()
        except Exception as e:
            print(e)
            return True


class BonusRank(models.Model):
    user_id = models.IntegerField(primary_key=True,default=0)
    run = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    read = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sleep = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ride = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    walk = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    objects = BonusManager()
    class Meta:
        db_table = "on_bonusrank"







class LoginRecord(models.Model):
    id = models.CharField(primary_key=True,default=uuid.uuid4,max_length=60)
    user_id = models.IntegerField(primary_key=True,default=0)
    timeNow = models.DateTimeField()
    nickname = models.CharField(max_length=200,null=True)
    class Meta:
        db_table = "on_loginrecord"