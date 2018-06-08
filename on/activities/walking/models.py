from django.db import models
import uuid
from on.activities.base import Goal, Activity
from on.user import UserInfo, UserTicket, UserRecord, UserSettlement,BonusRank
import django.utils.timezone as timezone
from django.conf import settings
import os
import pytz
import math
from datetime import timedelta, datetime

# Create your models here.
#
class WalkingManager(models.Manager):
    # 创建一个新的goal
    def create_goal(self, user_id, goal_type, guaranty, down_payment, activate_deposit, coefficient, mode, goal_day
                    , average, nosign, activity_type,reality_price, deserve_price, down_num):

        if settings.DEBUG:
            start_time = timezone.now()
            user_id=100274
        else:
            # 当天创建活动只有后一天才能参加，所以以后一天为开始日期
            start_time = timezone.now()  # + timedelta(days=1)
            # start_time = datetime.strptime("2018-01-01 00:00:01", "%Y-%m-%d %H:%M:%S")
        kilos_day, goal_distance, left_distance = None, None, None
        # 查询出没有支付的活动
        goal = self.filter(user_id=user_id).filter(start_time=start_time).filter(status="PENDING")
        # 如果存在的话就删掉
        if goal:
            goal.first().delete()
        goal = self.create(user_id=user_id,
                           activity_type=activity_type,
                           start_time=start_time,
                           goal_day=goal_day,
                           mode=mode,
                           guaranty=guaranty,
                           down_payment=down_payment,
                           activate_deposit=activate_deposit,
                           coefficient=coefficient,
                           goal_type=goal_type,
                           goal_distance=goal_distance,
                           left_distance=left_distance,
                           kilos_day=kilos_day,
                           average=average,
                           reality_price=reality_price,
                           deserve_price=deserve_price,
                           down_num=down_num
                           )
        # 更新活动的免签卡券
        return goal

    # 删除一个目标
    def delete_goal(self, goal_id):
        goal = self.get(goal_id=goal_id)
        # 删除本目标对应的所有打卡记录
        goal.punch.all().delete()
        # 删除本目标
        goal.delete()

    # 用户每一次打卡成功后就加一
    def update_punch(self, goal_id):
        record = self.get(goal_id=goal_id)
        record.punch_day += 1
        record.save()

    # 当用户结算的时候将用户的打卡记录改成0
    def clear_punch(self, goal_id):
        record = self.get(goal_id=goal_id)
        record.punch_day += 1
        record.save()




class WalkingGoal(Goal):
    """ Model for running goal
        User needs to set running duration days and distance as
        objective
    """
    # 目标距离
    goal_distance = models.FloatField(null=True)
    # 单日目标距离，对于自由模式来说，kilos_day为单日目标上限
    kilos_day = models.FloatField(null=True)
    # 剩余距离, 只针对自由模式有效
    left_distance = models.FloatField(null=True)
    # 用户实际要付出的金额
    reality_price = models.DecimalField(max_digits=12, decimal_places=2, null=False)
    # 用户应该要付出的金额
    deserve_price = models.DecimalField(max_digits=12, decimal_places=2, null=False)
    # 扣完底金需要的次数
    down_num = models.IntegerField(default=1, null=False)
    # 平均每次要扣的
    average = models.DecimalField(max_digits=12, decimal_places=2, null=False)
    # 活动押金
    activate_deposit = models.DecimalField(max_digits=12, decimal_places=2, null=False)
    # 累计距离,只对自由模式有效
    add_distance = models.FloatField(default=0, null=True)
    # 活动额外收益
    extra_earn = models.DecimalField(max_digits=12, decimal_places=2, null=False,default=0)
    # 用户打卡的天数
    punch_day = models.IntegerField(null=False,default=0)
    objects = WalkingManager()

    @staticmethod
    def get_activity():
        return "3"


    class Meta:
        db_table= "on_walkinggoal"



class RunningPunchRecordManager(models.Manager):



    #
    # 获取时间
    def get_day_record(self, daydelta):
        """
        :param day: 表示一个timedelta
        :return:
        """
        # 判断现在的时间距离开始时间的时长
        # day = (timezone.now()-self.recod_time)
        # print(day)
        # 今天的日期加上
        today = timezone.now().date() + timedelta(daydelta)
        print(today, "这个时间加上一个时间段")
        # 明天
        end = today + timedelta(1)
        print(end, "today加上一天，表示的是那一天的一整天的时间段")
        return self.filter(record_time__range=(today, end))

    # 第一天是否存在打卡记录

    # user对某punch点赞
    def praise_walk(self, user_id, punch_id):
        try:
            praise = WalkingPunchPraise(user_id=user_id, punch_id=punch_id)
            praise.save()
            record = self.get(punch_id=punch_id)
            record.praise += 1
            record.save()
        except Exception:
            pass

    # user对某punch举报
    def report_walk(self, user_id, punch_id):
        try:
            report = WalkingPunchReport(user_id=user_id, punch_id=punch_id)
            report.save()
            record = self.get(punch_id=punch_id)
            record.report += 1
            record.save()
        except Exception:
            pass

    # 是否存在某user对某punch的点赞
    def exist_praise_punch(self, user_id, punch_id):
        record = WalkingPunchPraise.objects.filter(user_id=user_id, punch_id=punch_id)
        if record:
            return True
        else:
            return False

    # 是否存在某user对某punch的点赞
    def exist_report_punch(self, user_id, punch_id):
        record = WalkingPunchReport.objects.filter(user_id=user_id, punch_id=punch_id)
        if record:
            return True
        else:
            return False


class WalkingPunchRecord(models.Model):
    """ Model for running task record
        To save user's actual running distance per day
    """
    # 主键ID,标识打卡记录
    punch_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # 外键ID,标识对应目标
    goal = models.ForeignKey(WalkingGoal, related_name="punch", on_delete=models.PROTECT)
    # Time when user creates the record
    record_time = models.DateTimeField(null=False)
    # 截图的引用地址
    # voucher_ref = models.CharField(max_length=256, null=False)
    voucher_ref = models.TextField(null=False)
    # 截图的存储地址
    voucher_store = models.CharField(max_length=512, null=False)
    # 跑步距离
    distance = models.FloatField(default=0)
    # 被赞数
    praise = models.IntegerField(default=0)
    # 被举报数
    report = models.IntegerField(default=0)
    # 保存的一段话
    document = models.TextField(default=" ", null=True)
    # 重新打卡
    reload = models.IntegerField(default=0, null=True)
    # 指定一个Manager
    objects = RunningPunchRecordManager()


# 点赞
class WalkingPunchPraise(models.Model):
    # 点赞的人
    user_id = models.IntegerField()
    # punch id
    punch_id = models.UUIDField()

    class Meta:
        unique_together = ("punch_id", "user_id")
        db_table = "on_walkingpunchpraise"


# 举报
class WalkingPunchReport(models.Model):
    # 举报的人
    user_id = models.IntegerField(null=False, default=0)
    # punch id
    punch_id = models.UUIDField(null=False, default=uuid.uuid4)

    class Meta:
        unique_together = ("punch_id", "user_id")
        db_table = "on_walkingpunchreport"


class WalkReply(models.Model):
    id = models.IntegerField(primary_key=True, auto_created=True)
    user_id = models.IntegerField()
    other_id = models.CharField(null=False, max_length=255)
    r_content = models.TextField(null=False)
    create_time = models.DateTimeField(null=True)


    @property
    def get_user_message(self):
        user = UserInfo.objects.filter(user_id=self.user_id)
        if user:
            user = user[0]
            return user

    class Meta:
        db_table = "on_walkreply"
