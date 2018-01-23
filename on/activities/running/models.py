from django.db import models
import uuid
from on.activities.base import Goal, Activity
from on.user import UserInfo, UserTicket, UserRecord, UserSettlement
import django.utils.timezone as timezone
from django.conf import settings
import os
from datetime import timedelta, datetime


class RunningGoalManager(models.Manager):
    # 创建一个新的goal
    def create_goal(self, user_id, runningtype, guaranty, down_payment, coefficient, mode, goal_day, distance, nosign):
        running_type = 0 if runningtype == "FREE" else 1
        if settings.DEBUG:
            start_time = timezone.now()
        else:
            # start_time = timezone.now() + timedelta(days=1)
            start_time = datetime.strptime("2018-01-01 00:00:01", "%Y-%m-%d %H:%M:%S")
        kilos_day, goal_distance, left_distance = None, None, None
        if running_type:
            kilos_day = distance
        else:
            actual_day_map = {
                7: 6,
                14: 12,
                21: 18,
                30: 25,
                61: 50
            }
            goal_distance = distance
            left_distance = distance
            kilos_day = 2 * distance // actual_day_map[goal_day]
        goal = self.filter(user_id=user_id).filter(start_time=start_time).filter(status="PENDING")
        if goal:
            goal.first().delete()
        goal = self.create(user_id=user_id,
                           activity_type=RunningGoal.get_activity(),
                           start_time=start_time,
                           goal_day=goal_day,
                           mode=mode,
                           guaranty=guaranty,
                           down_payment=down_payment,
                           coefficient=coefficient,
                           goal_type=running_type,
                           goal_distance=goal_distance,
                           left_distance=left_distance,
                           kilos_day=kilos_day)
        # 更新活动的免签卡券
        if running_type:
            nosgin_number = int(nosign)
            UserTicket.objects.create_ticket(goal.goal_id, "NS", nosgin_number)
        return goal

    # 删除一个目标
    def delete_goal(self, goal_id):
        goal = self.get(goal_id=goal_id)
        # 删除本目标对应的所有打卡记录
        goal.punch.all().delete()
        # 删除本目标
        goal.delete()


class RunningGoal(Goal):
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
    objects = RunningGoalManager()

    @staticmethod
    def get_start_date():
        return datetime.strptime("00:01", "%H:%M").time()

    def calc_pay_out(self):
        pay_out = 0
        # 如果是自律模式
        if self.goal_type:
            # 如果之前没有过不良记录, 则扣除保证金
            if self.none_punch_days == 0:
                pay_out = self.guaranty
                # 清除个人的保证金数额
                self.guaranty = 0
                # 增加不良记录天数
                self.none_punch_days = 1
            elif self.none_punch_days >= 1 and self.down_payment > 0:
                # 如果是普通模式
                if self.mode == "N":
                    pay_out = 15
                # 如果有降低投入
                else:
                    pay_out = 10.5
                # 从账户中扣除金额
                self.down_payment -= pay_out
                # 不良天数记录+1
                self.none_punch_days += 1
        # 如果是自由模式
        else:
            if float(self.left_distance) > 0.0:
                pay_out = self.guaranty
                remain = int(self.left_distance) - 1
                # 求解剩余距离
                if self.mode == "N":
                    left_pay = 15 * remain
                # 如果有降低投入
                else:
                    left_pay = 10.5 * remain
                if left_pay >= self.down_payment:
                    left_pay = self.down_payment
                    self.down_payment = 0
                else:
                    self.down_payment -= left_pay
                pay_out += left_pay
                self.guaranty = 0
            else:
                pay_out = 0
        if pay_out > 0:
            # 更新值
            self.save()
            # 把本次瓜分金额写入数据库记录中
            UserSettlement.objects.loose_pay(goal_id=self.goal_id,bonus=pay_out)
        # 完成所有瓜分金额的计算
        return pay_out

    @staticmethod
    def get_activity():
        return "1"

    def update_activity(self, user_id):
        # 更新该种活动的总系数
        Activity.objects.add_bonus_coeff(RunningGoal.get_activity(), self.guaranty + self.down_payment, self.coefficient)
        # 增加用户的累计参加次数
        UserRecord.objects.update_join(user=UserInfo.objects.get(user_id=user_id), coeff=self.coefficient)

    def update_activity_person(self):
        Activity.objects.update_person(RunningGoal.get_activity())
        Activity.objects.update_coeff(RunningGoal.get_activity(), -self.coefficient)


class RunningPunchRecordManager(models.Manager):
    # 创建一个新的record
    def create_record(self, goal, filecontent, filename, distance):
        # 文件存储的实际路径
        filePath = os.path.join(settings.MEDIA_DIR, filename)
        # 引用所使用的路径
        refPath = os.path.join(settings.MEDIA_ROOT, filename)
        # 写入文件内容
        with open(filePath, 'wb') as f:
            f.write(filecontent)
        # 如果是日常模式打卡，则规定distance必须为日常距离
        if goal.goal_type:
            distance = goal.kilos_day
        record = self.create(goal=goal, voucher_ref=refPath, voucher_store=filePath, distance=distance)
        # 如果是自由模式, 则计算剩余距离
        if not goal.goal_type:
            goal.left_distance -= distance
            goal.save()
        return record

    # 获取时间
    def get_day_record(self, daydelta):
        """
        :param day: 表示一个timedelta
        :return:
        """
        today = timezone.now().date() + timedelta(daydelta)
        end = today + timedelta(1)
        return self.filter(record_time__range=(today, end))

    # user对某punch点赞
    def praise_punch(self, user_id, punch_id):
        try:
            praise = RunningPunchPraise(user_id=user_id, punch_id=punch_id)
            praise.save()
            record = self.get(punch_id=punch_id)
            record.praise += 1
            record.save()
        except Exception:
            pass

    # user对某punch举报
    def report_punch(self, user_id, punch_id):
        try:
            praise = RunningPunchReport(user_id=user_id, punch_id=punch_id)
            praise.save()
            record = self.get(punch_id=punch_id)
            record.report += 1
            record.save()
        except Exception:
            pass

    # 是否存在某user对某punch的点赞
    def exist_praise_punch(self, user_id, punch_id):
        record = RunningPunchPraise.objects.filter(user_id=user_id).filter(punch_id=punch_id)
        if record:
            return True
        else:
            return False

    # 是否存在某user对某punch的点赞
    def exist_report_punch(self, user_id, punch_id):
        record = RunningPunchReport.objects.filter.filter(user_id=user_id).filter(punch_id=punch_id)
        if record:
            return True
        else:
            return False


class RunningPunchRecord(models.Model):
    """ Model for running task record
        To save user's actual running distance per day
    """
    # 主键ID,标识打卡记录
    punch_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # 外键ID,标识对应目标
    goal = models.ForeignKey(RunningGoal, related_name="punch", on_delete=models.PROTECT)
    # Time when user creates the record
    record_time = models.DateTimeField(null=False, default=timezone.now)
    # 截图的引用地址
    voucher_ref = models.CharField(max_length=256, null=False)
    # 截图的存储地址
    voucher_store = models.CharField(max_length=512, null=False)
    # 跑步距离
    distance = models.FloatField(default=0)
    # 被赞数
    praise = models.IntegerField(default=0)
    # 被举报数
    report = models.IntegerField(default=0)
    # 指定一个Manager
    objects = RunningPunchRecordManager()


# 点赞与举报
class RunningPunchPraise(models.Model):
    # 点赞的人
    user_id = models.IntegerField()
    # punch id
    punch_id = models.UUIDField()

    class Meta:
        unique_together = ("punch_id", "user_id")


# 点赞与举报
class RunningPunchReport(models.Model):
    # 举报的人
    user_id = models.IntegerField(null=False, default=0)
    # punch id
    punch_id = models.UUIDField(null=False,default=uuid.uuid4)

    class Meta:
        unique_together = ("punch_id", "user_id")
