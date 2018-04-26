from django.db import models
import uuid
from on.activities.base import Goal, Activity
from on.user import UserInfo, UserTicket, UserRecord, UserSettlement
import django.utils.timezone as timezone
from django.conf import settings
import os
import pytz
import math
from datetime import timedelta, datetime


class RunningGoalManager(models.Manager):
    # 创建一个新的goal
    def create_goal(self, user_id, runningtype, guaranty, down_payment, activate_deposit, coefficient, mode, goal_day,
                    distance, average, nosign, extra_earn, reality_price, deserve_price, punch_day, down_num):
        running_type = 0 if runningtype == "FREE" else 1
        if settings.DEBUG:
            start_time = timezone.now()
        else:
            # 当天创建活动只有后一天才能参加，所以以后一天为开始日期
            start_time = timezone.now()  # + timedelta(days=1)
            # start_time = datetime.strptime("2018-01-01 00:00:01", "%Y-%m-%d %H:%M:%S")
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
            distances = int(distance)
            kilos_day = 2 * distances // actual_day_map[goal_day]
        # 查询出没有支付的活动
        goal = self.filter(user_id=user_id).filter(start_time=start_time).filter(status="PENDING")
        # 如果存在的话就删掉
        if goal:
            goal.first().delete()
        goal = self.create(user_id=user_id,
                           activity_type=RunningGoal.get_activity(),
                           start_time=start_time,
                           goal_day=goal_day,
                           mode=mode,
                           guaranty=guaranty,
                           down_payment=down_payment,
                           activate_deposit=activate_deposit,
                           coefficient=coefficient,
                           goal_type=running_type,
                           goal_distance=goal_distance,
                           left_distance=left_distance,
                           kilos_day=kilos_day,
                           extra_earn=extra_earn,
                           average=average,
                           reality_price=reality_price,
                           deserve_price=deserve_price,
                           punch_day=0,
                           down_num=down_num
                           )
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
    extra_earn = models.DecimalField(max_digits=12, decimal_places=2, null=False)
    # 用户打卡的天数
    punch_day = models.IntegerField(null=False)
    objects = RunningGoalManager()

    @staticmethod
    def get_start_date():
        return datetime.strptime("00:01", "%H:%M").time()

    def calc_pay_out(self):
        print("计算开始..........")
        pay_out = 0
        # 如果是日常模式
        if self.goal_type == 1:
            # 如果之前没有过不良记录, 则扣除保证金
            if self.none_punch_days == 0:
                pay_out = self.guaranty
                print(pay_out, '如果之前没有过不良记录, 则扣除保证金，扣除金额就是保证金的数量')
                # 清除个人的保证金数额
                self.guaranty = 0
                print("将保证金改为0")
                # 增加不良记录天数
                self.none_punch_days = 1
            elif self.none_punch_days >= 1 and self.down_payment > 0:
                print("如果不良天数不等于1")
                if self.guaranty == 0:
                    # 底金次数
                    pay_out = self.average
                    print(pay_out, "当保证金等于0的时候需要扣除的底金金额")
                # 如果有降低投入
                # 从账户中扣除金额
                self.down_payment -= pay_out
                print("扣除之后需要将用户的底金减去")
                # 不良天数记录+1
                self.none_punch_days += 1
        # 如果是自由模式
        else:
            print("若是自由模式，开始扣款")
            if float(self.left_distance) > 0.0:
                print("当剩余距离大于0的时候才开始扣款")
                # 剩余的距离
                left_distance = self.left_distance
                # 求解剩余距离
                if left_distance <= 1:
                    pay_out = self.guaranty
                    print("当剩余的距离小于1的时候，直接扣除用户的保证金{}".format(self.guaranty))
                    self.guaranty = 0
                else:
                    remain = math.floor(self.left_distance) - 1
                    print("剩余的距离减去1是：{}".format(remain))
                    if remain <= self.down_num:
                        print(type(remain), type(self.down_num), "remain:{},down_num{}".format(remain, self.down_num))
                        print("走这里就对了")
                        pay_out = remain * self.average + self.guaranty
                        self.guaranty = 0
                        print("用户的剩余距离减去1之后的距离数{}".format(math.floor(self.left_distance) - 1),
                              "平均需要扣除的金额{}".format(self.average))
                        self.down_payment -= remain * self.average
                    else:
                        # remain = self.down_num
                        print("若剩余距离大于底金次数，那么剩余距离{}".format(remain))
                        pay_out = self.down_payment + self.guaranty

                        self.guaranty = 0
                        print("用户的剩余距离减去1之后的距离数{}".format(math.floor(self.left_distance) - 1),
                              "平均需要扣除的金额{}".format(self.average))

                        self.down_payment -= 0
            else:
                pay_out = 0
                print("当剩余的距离大于零的时候，需要付出的金额就是保证金")
        if pay_out > 0:
            # 更新值
            self.save()
            # 把本次瓜分金额写入数据库记录中
            UserSettlement.objects.loose_pay(goal_id=self.goal_id, bonus=pay_out)
            print("瓜分记录写入成功")
        # 完成所有瓜分金额的计算
        return pay_out

    @staticmethod
    def get_activity():
        return "1"

    def update_activity(self, user_id):
        # 更新该种活动的总系数
        Activity.objects.add_bonus_coeff(RunningGoal.get_activity(), self.guaranty + self.down_payment,
                                         self.coefficient)
        # 增加用户的累计参加次数
        UserRecord.objects.update_join(user=UserInfo.objects.get(user_id=user_id), coeff=self.coefficient)

    def update_activity_person(self):
        Activity.objects.update_person(RunningGoal.get_activity())
        Activity.objects.update_coeff(RunningGoal.get_activity(), -self.coefficient)


# TODO
class RunningPunchRecordManager(models.Manager):
    # 创建一个新的record
    # def create_record(self, goal, filecontent, filename, distance,punch_time, document):
    #     # 文件存储的实际路径
    #     filePath = os.path.join(settings.MEDIA_DIR, filename)
    #     # 引用所使用的路径
    #     refPath = os.path.join(settings.MEDIA_ROOT, filename)
    #     # 写入文件内容
    #     with open(filePath, 'wb') as f:
    #         f.write(filecontent)
    #     # 如果是日常模式打卡，则规定distance必须为日常距离
    #     if goal.goal_type:
    #         distance = goal.kilos_day
    #     record = self.create(goal=goal, voucher_ref=refPath, voucher_store=filePath, distance=distance,record_time = punch_time,
    #                          document=document)
    #     # 如果是自由模式, 则计算剩余距离
    #     if not goal.goal_type:
    #         goal.left_distance -= distance
    #         goal.save()
    #     return record
    # 创建一个新的record
    def create_record(self, goal, filename, distance, punch_record_time, document, base64_str):
        # 文件存储的实际路径
        filePath = os.path.join(settings.MEDIA_DIR, timezone.now().strftime("%Y-%m-%d") + "/")
        # # 引用所使用的路径
        refPath = os.path.join(settings.MEDIA_ROOT, timezone.now().strftime("%Y-%m-%d") + "/")
        # mysql存储的地址
        file_filepath = filePath + filename
        file_refpath = refPath + filename
        if not os.path.exists(filePath):
            os.makedirs(filePath)
            # 写入文件内容
        with open(filePath + filename, 'wb') as f:
            f.write(base64_str)
            print("保存图片成功")
        # 如果是日常模式打卡，则规定distance必须为日常距离
        if goal.goal_type:
            distance = goal.kilos_day
        record = self.create(goal=goal, voucher_ref=file_refpath, voucher_store=file_filepath, distance=distance,
                             record_time=punch_record_time,
                             document=document)
        # 如果是自由模式, 则计算剩余距离
        if not goal.goal_type:
            goal.left_distance -= distance
            goal.save()
        return record

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
        record = RunningPunchPraise.objects.filter(user_id=user_id, punch_id=punch_id)
        if record:
            return True
        else:
            return False

    # 是否存在某user对某punch的点赞
    def exist_report_punch(self, user_id, punch_id):
        record = RunningPunchReport.objects.filter(user_id=user_id, punch_id=punch_id)
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
class RunningPunchPraise(models.Model):
    # 点赞的人
    user_id = models.IntegerField()
    # punch id
    punch_id = models.UUIDField()

    class Meta:
        unique_together = ("punch_id", "user_id")


# 举报
class RunningPunchReport(models.Model):
    # 举报的人
    user_id = models.IntegerField(null=False, default=0)
    # punch id
    punch_id = models.UUIDField(null=False, default=uuid.uuid4)

    class Meta:
        unique_together = ("punch_id", "user_id")


class Finish_SaveManager(models.Manager):
    def save_finish(self,goal_id):
        print("打印一下用户的id，看看是不是自己的",goal_id)
        goal = RunningGoal.objects.filter(goal_id=goal_id)
        print(goal,"看看是否查询到了值")
        if goal:
            goal = goal[0]
            finish_dict = {
                "goal_id":str(goal_id),
                "user_id":goal.user_id,
                "activity_type":goal.activity_type,
                "goal_type":goal.goal_type,
                "start_time":goal.start_time,
                "goal_day":goal.goal_day,
                "status":"已经结束",
                "mode":goal.mode,
                "guaranty":goal.guaranty,
                "down_payment":goal.down_payment,
                "coefficient":goal.coefficient,
                "bonus":goal.bonus,
                "none_punch_days":goal.none_punch_days,
                "goal_distance":goal.goal_distance,
                "kilos_day":goal.kilos_day,
                "left_distance":goal.left_distance,
                "reality_price":goal.reality_price,
                "deserve_price":goal.deserve_price,
                "down_num":goal.down_num,
                "activate_deposit":goal.activate_deposit,
                "average":goal.average,
                "add_distance":goal.add_distance,
                "extra_earn":goal.extra_earn,
                "punch_day":goal.punch_day,
                "settle_time":timezone.now().strftime("%Y-%m-%d")
            }
            try:
                self.create(**finish_dict)
                return True
            except Exception as e:
                print("创建记录失败",e)
        else:
            return False


ACTIVITY_CHOICES = (
    (u'0', u'作息'),
    (u'1', u'跑步'),
    (u'2', u'阅读(尝新)'),
    # (u'2', u'购书阅读2期')
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
class Running_Finish_Save(models.Model):
    id = models.IntegerField(primary_key=True,auto_created=True)
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
    extra_earn = models.DecimalField(max_digits=12, decimal_places=2, null=False)
    # 用户打卡的天数
    punch_day = models.IntegerField(null=False)
    goal_id = models.CharField(max_length=255,null=True)
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
    settle_time = models.DateTimeField()
    objects = Finish_SaveManager()

    class Meta:
        db_table = "on_running_finish_save"
