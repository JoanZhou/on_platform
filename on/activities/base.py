# -*- coding: utf-8 -*-
import uuid
from django.db import models
from on.user import UserInfo, UserTicket, UserTicketUseage, UserSettlement, UserRefund,BonusRank
import django.utils.timezone as timezone, datetime
from datetime import timedelta
import math
import decimal
import logging
from django.conf import settings

ACTIVITY_CHOICES = (
    (u'0', u'作息'),
    (u'1', u'跑步'),
    (u'2', u'阅读(尝新)'),
    (u'3', u'步行'),
    (u'4', u'骑行')
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
    def get_read_activity(self, activity_id):
        app = self.filter(activity_id=activity_id)
        if app:
            return app[0]
        else:
            return None

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
    is_no_start = models.BooleanField(default=0)
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
    start_time = models.DateTimeField(null=False)
    # 目标天数
    goal_day = models.IntegerField(null=False, default=0)
    # Task status, pending, active, paused, complete
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='PENDING')
    # User selected task mode, 普通, 学生, 尝试, etc
    MODE_CHOICES = (
        (u'N', u'尝新'),
        (u'O', u'普通'),
        (u'P', u'体验'),
        (u'U', u'升级'),
    )
    # 学生或普通模式的选择
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default="N")
    # 保证金
    guaranty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # 底金
    down_payment = models.DecimalField(max_digits=12, decimal_places=2)
    # 系数
    coefficient = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # 瓜分金额
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # 已经发生过的未完成天数, 用于计算下一次扣除底金与保证金的金额数
    none_punch_days = models.IntegerField(null=False, default=0)


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
        from on.activities.running.models import RunningPunchRecord

        # 若第一天打了卡，那么就把目标天数减一天
        start_time = self.start_time.strftime("%Y-%m-%d")
        user_end_time = (self.start_time + timedelta(days=1)).strftime("%Y-%m-%d")
        if len(RunningPunchRecord.objects.filter(goal_id=self.goal_id,
                                                 record_time__range=(start_time, user_end_time))) > 0:

            # 目标天数 - （现在的时间天数 - 开始的时间数）- 1天
            left = self.goal_day - (timezone.now().date() - self.start_time.date()).days - 1
        else:
            left = self.goal_day - (timezone.now().date() - self.start_time.date()).days
        print(timezone.now().date(), "取出来的现在时间", self.start_time, "取出来的开始时间")
        print(left, "剩余天数", self.user_id)
        return left

    def calc_pay_out(self):
        print("开始计算扣除金额.....")
        return 0

    def update_activity_person(self):
        return 0

    # 次日凌晨给各个目标汇入钱款
    def earn_profit(self, average_pay):
        print("开始进行分配奖金")
        if not settings.DEBUG:
            today = timezone.now().date()
            delta = (today - self.start_time.date()).days
            print("今天到开始日期的时间段{}".format(delta))
        else:
            delta = 1
        earn_pay = 0
        if self.goal_type == 1:
            # 如果当前活动开始了且处于进行中状态才能分钱
            if delta > 0 and self.status == 'ACTIVE':
                print("要分配的平均金额数是{}".format(average_pay))
                earn_pay = math.floor((average_pay * self.coefficient) * 100) / 100
                print("用户赚的的金额{}".format(earn_pay))
                self.bonus += decimal.Decimal(earn_pay)
                self.save()
                try:
                    rank = BonusRank.objects.filter(user_id=self.user_id)
                    if rank:
                        BonusRank.objects.add_run(user_id=self.user_id, profit=decimal.Decimal(earn_pay))
                    else:
                        BonusRank.objects.create(user_id=self.user_id, run=decimal.Decimal(earn_pay))
                except Exception as e:
                    logger.error(e)
                # 修改用户赚得的总金额
                UserInfo.objects.update_balance(user_id=self.user_id, pay_delta=earn_pay)

                # 在settlement表中增加记录
                UserSettlement.objects.earn_profit(self.goal_id, earn_pay)
        else:
            if self.left_day >= 0:
                print("要分配的平均金额数是{}".format(average_pay))
                earn_pay = math.floor((average_pay * self.coefficient) * 100) / 100
                print("用户赚的的金额{}".format(earn_pay))
                self.bonus += decimal.Decimal(earn_pay)
                self.save()
                try:
                    rank = BonusRank.objects.filter(user_id=self.user_id)
                    if rank:
                        BonusRank.objects.add_run(user_id=self.user_id, profit=earn_pay)
                    else:
                        BonusRank.objects.create(user_id=self.user_id, run=earn_pay)
                except Exception as e:
                    logger.error(e)
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

    # 判断是否是第一天
    def is_first_day(self):
        print("开始判断是不是第一天")
        if timezone.now().strftime("%Y-%m-%d") == self.start_time.strftime("%Y-%m-%d"):
            a = timezone.now().strftime("%Y-%m-%d") - self.start_time.strftime("%Y-%m-%d")
            print(a,"若是现在的时间跟开始时间相等，那么就是第一天，返回的是true")
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
                    print("进入日常模式，开始扣除金额，当前的活动类型是{}".format(self.goal_type))
                    # 查看前一天到今天是否存在打卡记录
                    if self.exist_punch_last_day():
                        # 如果存在打卡记录,则不付出钱
                        if self.left_day < 0:
                            print("日常模式的剩余天数小于零，说明活动结束")
                            if self.down_payment <= 0 and self.guaranty <= 0:
                                self.status = "FAILED"
                                print("押金保证金都小于0，表示失败")
                            else:
                                self.status = "SUCCESS"
                                print("押金保证金都大于0，表示成功")
                        else:
                            pass
                    else:
                        # 如果不存在打卡记录
                        if self.is_first_day == True:
                            print("今天是第一天，不做任何处理")
                            # 有返回值的时候是第一天，直接pass
                            pass
                        else:
                            # 如果有券,则用券,不扣钱; 如果没有券,则扣除一定金额
                            has_ticket = self.auto_use_ticket(ticket_type="NS")
                            if not has_ticket:
                                pay_out = self.calc_pay_out()
                                print(pay_out, "若是日常模式且没有免签券，则扣除此金额")
                            if self.down_payment <= 0 and self.guaranty <= 0:
                                self.status = "FAILED"
                                print("押金保证金都小于0，表示失败")
                            # 检查目标是否已经算失败了, 在日常模式下如果两者均为0, 则判定目标失败
                            if self.left_day < 0:
                                print("日常模式的剩余天数小于零，说明活动结束")
                                if self.down_payment <= 0 and self.guaranty <= 0:
                                    self.status = "FAILED"
                                    print("押金保证金都小于0，表示失败")
                                else:
                                    self.status = "SUCCESS"
                                    print("押金保证金都大于0，表示成功")

                # 如果今天已经是最后一天，则将目标的状态设置为完成或失败
                else:
                    print("进入自由模式，开始扣除金额，当前的活动类型是{}".format(self.goal_type))
                    # 如果是自由模式下，当left_day为负数时结算

                    if self.left_day < 0:
                        print("现在的left_day：{}自由模式下，当剩余天数小于零的时候开始结算".format(self.left_day))
                        # 将自由模式下的钱数结算
                        pay_out = self.calc_pay_out()
                        print(pay_out, "用户{}自由模式下要扣除的金额数{}".format(self.user_id, pay_out))
                        # 如果付出的钱没有总金额多,算完成,否则算失败
                        if self.guaranty + self.down_payment > 0:
                            self.status = "SUCCESS"
                        else:
                            self.status = "FAILED"

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
    #
    # 用户触发，如果挑战成功则删除目标，退还押金
    # def refund_to_user(self, open_id):
    #     try:
    #         refund_trans, status = UserRefund.objects.create_refund(openid=open_id, goal_id=self.goal_id)
    #         if settings.DEBUG:
    #             res = payClient.refund.apply(total_fee=1,
    #                                          refund_fee=1,
    #                                          out_refund_no=str(refund_trans.refund_id),
    #                                          transaction_id=refund_trans.transaction_id)
    #             if res.get('result_code', 'faild') == "SUCCESS":
    #                 pass
    #             else:
    #                 refund_trans.delete()
    #                 return False
    #         elif status == "SUCCESS" and refund_trans:
    #             res = payClient.refund.apply(total_fee=refund_trans.total_fee,
    #                                          refund_fee=refund_trans.refund_fee,
    #                                          out_refund_no=str(refund_trans.refund_id),
    #                                          transaction_id=refund_trans.transaction_id)
    #             if res.get('result_code', 'faild') == "SUCCESS":
    #                 pass
    #             else:
    #                 refund_trans.delete()
    #                 return False
    #         elif status == "FAILED":
    #             pass
    #         else:
    #             return False
    #     except Exception as e:
    #         debuglogger.error(e)
    #         return False
    #     else:
    #         return True

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
            activity.bonus_all += decimal.Decimal(0)
        # 跑步数据
        elif activity.activity_type == "1":
            activity.bonus_all += decimal.Decimal(0)
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
