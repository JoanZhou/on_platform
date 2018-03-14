# -*- coding: utf-8 -*-
import uuid
from django.db import models
from on.user import UserInfo, UserTicket, UserTicketUseage, UserSettlement, UserRefund
import django.utils.timezone as timezone, datetime
from datetime import timedelta
import math
import decimal
import logging
from on.wechatconfig import payClient
from django.conf import settings

ACTIVITY_CHOICES = (
    (u'0', u'作息'),
    (u'1', u'跑步'),
    (u'2', u'购书阅读')
)

STATUS_CHOICES = (
    (u'ACTIVE', u'进行中'),
    (u'FAILED', u'失败'),
    (u'SUCCESS', u'成功'),
    (u'PENDING', u'等待支付')
)
GOAL_CHOICES = (
    (0, '自由模式'),
    (1, '日常模式')
)

logger = logging.getLogger("app")
debuglogger = logging.getLogger("django")


class ActivityManager(models.Manager):
    def get_active_activity(self, activity_type):
        app = self.filter(activity_type=activity_type)
        if app:
            return app[0]
        else:
            return None

    # 主要用于创建目标时对活动奖金池与系数的更新
    def add_bonus_coeff(self, activity_type, bonus, coefficient):
        activity = self.get(activity_type=activity_type)
        bonus = activity.bonus_all + decimal.Decimal(bonus)
        coeff = activity.coefficient + decimal.Decimal(coefficient)
        activity.bonus_all = bonus
        activity.coefficient = coeff
        activity.active_participants += 1
        activity.save()

    # 更新奖金池与系数值
    def update_bonus(self, activity_type, bonus_delta):
        activity = self.get(activity_type=activity_type)
        activity.bonus_all += bonus_delta
        activity.save()

    # 在用户结束任务后要更新活动的系数值
    def update_coeff(self, activity_type, coeff_delta):
        activity = self.get(activity_type=activity_type)
        activity.coefficient += coeff_delta
        activity.save()

    # 更新参数人数
    def update_person(self, activity_type):
        activity = self.get(activity_type=activity_type)
        activity.active_participants -= 1
        activity.save()


class Activity(models.Model):
    """ Model for Activities within On! Platform, such as Running, Sleeping, etc
        Activity is composed of several users' tasks
    """
    activity_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # dict: 作息-0,跑步-1,阅读-2
    activity_type = models.CharField(max_length=16, choices=ACTIVITY_CHOICES)
    # 总系数
    coefficient = models.DecimalField(max_digits=12, decimal_places=2)
    # 目前已经参与的人数
    active_participants = models.IntegerField(default=0)
    max_participants = models.IntegerField(default=0)
    # 奖金池中的奖金, 需要频繁访问与修改
    bonus_all = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.CharField(max_length=16, default='')
    # 活动名字
    # activity_name = models.CharField(max_length=16,default="")
    # 是否开始活动
    # is_no_start = models.BooleanField(default=False)
    # 活动图片存储路径
    # img_url = models.TextField()

    objects = ActivityManager()

    class Meta:
        unique_together = ("activity_type", "description")

    @property
    def activity_dis(self):
        return self.get_activity_type_display()

    @property
    def status_dis(self):
        return self.get_status_display()


class Goal(models.Model):
    """ Abstract Model for user tasks within On! Platform
        User has his/her own objective for each task

        Detailed objectives will be defined in each specific task
    """
    goal_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.IntegerField(null=False)
    activity_type = models.CharField(null=False, max_length=16, choices=ACTIVITY_CHOICES, default="0")
    # 0为自由模式, 1为日常模式
    goal_type = models.IntegerField(null=False, default=1, choices=GOAL_CHOICES)
    # 开始时间
    start_time = models.DateTimeField(null=False, default=timezone.now)
    # 目标天数
    goal_day = models.IntegerField(null=False, default=0)
    # Task status, pending, active, paused, complete
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='PENDING')
    # User selected task mode, 普通, 学生, 尝试, etc
    MODE_CHOICES = (
        (u'S', u'学生'),
        (u'N', u'普通')
    )
    # 学生或普通模式的选择
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default="N")
    # 保证金
    guaranty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # 底金
    down_payment = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # 系数
    coefficient = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # 瓜分金额
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # 已经发生过的未完成天数, 用于计算下一次扣除底金与保证金的金额数
    none_punch_days = models.IntegerField(null=False, default=0)

    # 判断特定活动类型
    # speci_activate = models.UUIDField(default=uuid.uuid4)

    class Meta:
        abstract = True
        unique_together = ("user_id", "activity_type", "status", "start_time")

    @property
    def past_day(self):
        past = (timezone.now().date() - self.start_time.date()).days + 1
        if past < 0:
            past = 0
        return past

    # 把left_day从模型字段改成属性，是为了保持同步与一致性
    @property
    def left_day(self):
        left = self.goal_day - (timezone.now().date() - self.start_time.date()).days - 1
        return left

    def calc_pay_out(self):
        return 0

    def update_activity_person(self):
        return 0

    # 次日凌晨给各个目标汇入钱款
    def earn_profit(self, average_pay):
        if not settings.DEBUG:
            today = timezone.now().date()
            delta = (today - self.start_time.date()).days
        else:
            delta = 1
        earn_pay = 0
        # 如果当前活动开始了且处于进行中状态才能分钱
        if delta > 0 and self.status == 'ACTIVE':
            earn_pay = math.floor((average_pay * self.coefficient) * 100) / 100
            self.bonus += decimal.Decimal(earn_pay)
            self.save()
            # 修改用户赚得的总金额
            UserInfo.objects.update_balance(user_id=self.user_id, pay_delta=earn_pay)
            # 在settlement表中增加记录
            UserSettlement.objects.earn_profit(self.goal_id, earn_pay)
        return earn_pay

    def exist_punch_last_day(self):
        """
        昨天是否存在有效的打卡记录
        :return: 如果存在，则返回True;否则，返回False
        """
        if self.punch.get_day_record(-1):
            return True
        else:
            return False

    def auto_use_ticket(self, ticket_type):
        # 如果不存在打卡记录,则使用券。注意这里应该是为昨天使用券，而非今天！
        has_ticket = UserTicket.objects.use_ticket(goal_id=self.goal_id, ticket_type="NS",
                                                   use_time=timezone.now() - timedelta(1))
        return has_ticket

    # 每天晚上在活动指定的时间检查前一天的打卡情况
    def check_punch(self):
        # 这里一定要防止因为并发产生的错误，要将timingtaks单独启用
        try:
            pay_out = 0
            # 只有处于活动状态的目标才会检查
            if self.status == "ACTIVE":
                # 如果是日常模式, 才会需要每天扣钱
                if self.goal_type:
                    # 查看前一天到今天是否存在打卡记录
                    if self.exist_punch_last_day():
                        # 如果存在打卡记录,则不付出钱
                        pass
                    else:
                        # 如果有券,则用券,不扣钱; 如果没有券,则扣除一定金额
                        has_ticket = self.auto_use_ticket(ticket_type="NS")
                        if not has_ticket:
                            pay_out = self.calc_pay_out()
                    # 检查目标是否已经算失败了, 在日常模式下如果两者均为0, 则判定目标失败
                    if self.left_day < 0:
                        if self.down_payment == 0 and self.guaranty == 0:
                            self.status = "FAILED"
                        else:
                            self.status = "SUCCESS"
                # 如果今天已经是最后一天，则将目标的状态设置为完成或失败
                else:
                    # 如果是自由模式下，当left_day为负数时结算
                    if self.left_day < 0:
                        # 将自由模式下的钱数结算
                        pay_out = self.calc_pay_out()
                        # 如果付出的钱没有总金额多,算完成,否则算失败
                        if self.guaranty + self.down_payment > 0:
                            self.status = "SUCCESS"
                        else:
                            self.status = "FAILED"
                if self.status == "SUCCESS" or self.status == "FAILED":
                    self.update_activity_person()
                # 更新到数据库中
                self.save()
                UserInfo.objects.update_deposit(user_id=self.user_id, pay_delta=-pay_out)
            return pay_out, self.coefficient
        except AssertionError:
            # 如果断言失败,则记录日志，返回两个0
            logger.error("Assertion Failed! Function: Check Punch Goal:{0}".format(self.goal_id))
            return 0, 0
        except Exception as e:
            logger.error(e)
            return 0, 0
            # 判断是否使用免签卡，暂时修改

    # def use_no_sign_in_date(self, daydelta):
    #     today = timezone.now().date() + timedelta(daydelta)
    #     end = today + timedelta(1)
    #     use_history = UserTicketUseage.objects.filter(useage_time__range=(today, end), goal_id=self.goal_id, ticket_type='NS')
    #     if use_history:
    #         return True
    #     else:
    #         return False

    # 用户触发，如果挑战成功则删除目标，退还押金
    def refund_to_user(self, open_id):
        try:
            refund_trans, status = UserRefund.objects.create_refund(openid=open_id, goal_id=self.goal_id)
            if settings.DEBUG:
                res = payClient.refund.apply(total_fee=1,
                                             refund_fee=1,
                                             out_refund_no=str(refund_trans.refund_id),
                                             transaction_id=refund_trans.transaction_id)
                if res.get('result_code', 'faild') == "SUCCESS":
                    pass
                else:
                    refund_trans.delete()
                    return False
            elif status == "SUCCESS" and refund_trans:
                res = payClient.refund.apply(total_fee=refund_trans.total_fee,
                                             refund_fee=refund_trans.refund_fee,
                                             out_refund_no=str(refund_trans.refund_id),
                                             transaction_id=refund_trans.transaction_id)
                if res.get('result_code', 'faild') == "SUCCESS":
                    pass
                else:
                    refund_trans.delete()
                    return False
            elif status == "FAILED":
                pass
            else:
                return False
        except Exception as e:
            debuglogger.error(e)
            return False
        else:
            return True

    @property
    def activity_dis(self):
        return self.get_activity_type_display()

    @property
    def mode_dis(self):
        return self.get_mode_display()

    @property
    def status_dis(self):
        return self.get_status_display()

    @property
    def money(self):
        activity = Activity.objects.filter(activity_type=self.activity_type).first()
        # TODO:FAKE
        # 作息数据
        if activity.activity_type == "0":
            activity.bonus_all += decimal.Decimal(2310)
        # 跑步数据
        elif activity.activity_type == "1":
            activity.bonus_all += decimal.Decimal(2250)
        # 阅读数据
        else:
            activity.bonus_all += decimal.Decimal(0)
        return activity.bonus_all

    @property
    def detail_status(self):
        detail = self.status
        if detail != "ACTIVE":
            return detail
        else:
            time_now = timezone.now().date()
            if time_now < self.start_time.date():
                detail = "NOSTART"
            return detail

        # class Ticket(models.Model):
        #     #用户id，
        #     user_id = models.IntegerField(null=False)
        #     #免签
        #     Ticket_id = models.UUIDField(default=uuid.uuid4,primary_key=True)
        #     # 获取方式,预留字段
        #     get_way = models.IntegerField(null=True)
        #     # 有效期
        #     indate = models.DateTimeField(null=False)
        #     TICKET_STATUS = (
        #         (u'0', u'未使用'),
        #         (u'1', u'已使用')
        #     )
        # 使用状态
        # is_use = models.IntegerField(null=True,choices=TICKET_STATUS,default=0)

# class OnTicket(models.Model):
#     ticket_id = models.CharField(db_column='Ticket_id', primary_key=True, max_length=32)  # Field name made lowercase.
#     user_id = models.IntegerField()
#     get_way = models.IntegerField(blank=True, null=True)
#     indate = models.DateTimeField()
#     TICKET_STATUS = (
#         (u'0', u'未使用'),
#         (u'1', u'已使用')
#     )
#     is_use = models.IntegerField(null=True,choices=TICKET_STATUS,default=0)
#
#     class Meta:
#         managed = False
#         db_table = 'on_ticket'
