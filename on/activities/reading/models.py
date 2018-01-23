from django.db import models
from django.http import JsonResponse
import uuid
from on.activities.base import Goal, Activity
from on.user import UserInfo, UserRecord
import django.utils.timezone as timezone
from django.conf import settings
import os
from datetime import datetime, timedelta
import math
import decimal

class ReadingGoalManager(models.Manager):
    # 生成一个目标
    def create_goal(self, user_id, max_return, book_name, goal_page, guaranty, price, imageurl):
        if settings.DEBUG:
            # 只是暂定一个时间，最迟1个月后开始
            start_time = timezone.now() - timedelta(days=30)
        else:
            start_time = datetime.strptime("2018-01-01 00:00:01", "%Y-%m-%d %H:%M:%S") + timedelta(days=30)
        # 预定一个goal_day, 读书最多30天完成
        goal_day = 30
        goal = self.filter(user_id=user_id).filter(start_time=start_time).filter(status="PENDING")
        if goal:
            goal.first().delete()
        goal = self.create(user_id=user_id,
                           max_return=max_return,
                           book_name=book_name,
                           goal_page=goal_page,
                           activity_type=ReadingGoal.get_activity(),
                           start_time=start_time,
                           goal_day=goal_day,
                           guaranty=guaranty,
                           price=price,
                           imageurl=imageurl)
        return goal

    # 删除一个目标
    def delete_goal(self, goal_id):
        goal = self.get(goal_id=goal_id)
        # 删除本目标对应的所有打卡记录
        goal.punch.all().delete()
        # 删除本目标
        goal.delete()


class ReadingGoal(Goal):
    """ Model for running goal
        User needs to set running duration days and distance as
        objective
    """
    # 书的名字
    book_name = models.CharField(null=False, max_length=128, default='无名书籍')
    # 目标页数
    goal_page = models.IntegerField(null=False)
    # 已经阅读完成的页数
    finish_page = models.IntegerField(null=True, default=0)
    # 最高返还金额, 阅读是平台与用户之间的活动
    max_return = models.FloatField(null=True)
    # 是否开始了读书, 开始读书后, 将重置活动开始读书的时间
    is_start = models.BooleanField(null=False, default=False)
    # 书的价格
    price = models.FloatField(null=False, default=0)
    # 书的图片
    imageurl = models.CharField(null=False, default='/static/order/demo.png', max_length=1024)
    objects = ReadingGoalManager()

    def check_punch(self):
        if self.status == "ACTIVE":
            if self.left_day < 0:
                # 如果阅读时间已经结束，则说明读书环节被迫中止
                pay_out = self.guaranty
                # 本目标的押金被清空
                self.guaranty = 0
                # 完成的判定在每次打卡中，否则算失败
                self.status = "FAILED"
                # 更新参加活动的总人数
                self.update_activity_person()
                # 更新到数据库中
                self.save()
                # 已经失败了，直接扣除用户的总押金数
                UserInfo.objects.update_deposit(user_id=self.user_id, pay_delta=-pay_out)

    @staticmethod
    def get_activity():
        return "2"

    def update_activity_person(self):
        Activity.objects.update_person(ReadingGoal.get_activity())

    def update_activity(self, user_id):
        # 更新该种活动的总系数，虽然都是0，但会增加人数
        Activity.objects.add_bonus_coeff(ReadingGoal.get_activity(), 0, 0)
        # 增加用户的累计参加次数
        UserRecord.objects.update_join(user=UserInfo.objects.get(user_id=user_id), coeff=self.coefficient)


class ReadingPunchRecordManager(models.Manager):

    # 获取时间
    def get_day_record(self, daydelta):
        """
        :param day: 表示一个timedelta
        :return:
        """
        today = timezone.now().date() + timedelta(daydelta)
        end = today + timedelta(1)
        return self.filter(record_time__range=(today, end))

    # 插入一条新的读书打卡记录
    def create_record(self, goal_id, today_page, today_time):
        goal = ReadingGoal.objects.get(goal_id=goal_id)
        today, tomorrow = timezone.now().date(), timezone.now().date() + timedelta(days=1)
        today_punch = goal.punch.filter(record_time__range=(today, tomorrow))
        if today_punch:
            return JsonResponse({'stauts': 403})
        else:
            # 书的总页数
            goal_page = goal.goal_page
            finish_page = goal.finish_page
            today_page = math.floor(float(today_page))
            today_time = math.ceil(float(today_time))
            # 如果已经把书读完了
            if int(today_page) >= goal_page - finish_page:
                today_page = goal_page - finish_page
                goal.status = "SUCCESS"
            # 天数限制表
            days_limit = [0] + [math.ceil(float(goal_page)/aver_page) for aver_page in [60,40,20]] + [30]
            days_coeffs = [1.0, 0.9, 0.8, 0.2]
            # 计算天数返还系数
            day_coeff = 0
            time_delta = goal.past_day
            for i in range(1, 5):
                if days_limit[i-1] <= time_delta <= days_limit[i]:
                    day_coeff = days_coeffs[i-1]
            # 就算时长返还系数
            average_time = math.floor(float(today_time) / float(today_page))
            times_limit = [0, 30, 45, 60, 120, 180, 3600]
            times_coeffs = [0, 0.2, 0.9, 1, 0.9, 0.2]
            time_coeff = 0
            for i in range(1, 7):
                if times_limit[i-1] <= average_time <= times_limit[i]:
                    time_coeff = times_coeffs[i-1]
            # 计算今日应该返还的钱
            bonus = day_coeff * time_coeff * goal.max_return * today_page / goal_page
            # 插入打卡记录中
            self.create(goal=goal, bonus=bonus, reading_page=today_page, reading_delta=today_time, start_page=finish_page)
            # 更新目标的累计收益
            goal.bonus += decimal.Decimal(bonus)
            # 更新目标的完成页数
            goal.finish_page += today_page
            # 更新阅读记录的总收益
            Activity.objects.add_bonus_coeff(ReadingGoal.get_activity(), bonus, 0)
            # 更新到数据库中
            goal.save()
            """增加用户的完成天数"""
            UserRecord.objects.update_finish_day(user=UserInfo.objects.get(user_id=goal.user_id))
            if goal.status == "SUCCESS":
                # 将目标内的收益更新到用户余额，只在最后一天更新。用户的押金有另外的页面去退，不必担心。
                UserInfo.objects.update_balance(user_id=goal.user_id, pay_delta=goal.bonus)
                # 更新参加活动的总人数
                goal.update_activity_person()
                return JsonResponse({'status': 400})
            else:
                return JsonResponse({'status': 200})


class ReadingPunchRecord(models.Model):
    """ Model for running task record
        To save user's actual running distance per day
    """
    # 主键ID,标识打卡记录
    punch_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # 外键ID,标识对应目标
    goal = models.ForeignKey(ReadingGoal, related_name="punch", on_delete=models.PROTECT)
    # Time when user creates the record
    record_time = models.DateTimeField(null=False, default=timezone.now)
    # Bonus can be -/+, depends on user complete the task or not
    bonus = models.DecimalField(max_digits=12, decimal_places=2)
    # 本次阅读的起始页
    start_page = models.IntegerField(default=0, null=False)
    # 本次阅读的页面数
    reading_page = models.IntegerField(default=0, null=False)
    # 读书的时长
    reading_delta = models.IntegerField(default=0, null=False)
    objects = ReadingPunchRecordManager()
