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
import time


class ReadingGoalManager(models.Manager):
    # 生成一个目标
    def create_goal(self, user_id, max_return, book_name, goal_page, guaranty, price, imageurl, reality_price,
                    deserve_price):
        start_time = timezone.now()
        # 预定一个goal_day, 读书最多30天完成
        goal_day = 30
        down_payment = 0
        coefficient = 0
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
                           down_payment=0,
                           coefficient=0,
                           price=price,
                           imageurl=imageurl,
                           reality_price=reality_price,
                           deserve_price=deserve_price
                           )
        # 生成活动的时候顺便生成一张时间记录表
        try:
            if not ReadTime.objects.filter(user_id=user_id):
                ReadTime.objects.create(user_id=user_id)
            else:
                pass
        except Exception as e:
            print(e)
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
    book_id = models.IntegerField(primary_key=True, default=1)

    # 目标页数
    goal_page = models.IntegerField(null=False)
    # 已经阅读完成的页数
    finish_page = models.IntegerField(null=True, default=0)
    # 最高返还金额, 阅读是平台与用户之间的活动
    max_return = models.FloatField(null=True)
    # 是否开始了读书, 开始读书后, 将重置活动开始读书的时间
    is_start = models.IntegerField(null=False, default=0)
    # 书的价格
    price = models.FloatField(null=False, default=0)
    # 书的图片
    imageurl = models.CharField(null=False, default='/static/order/demo.png', max_length=1024)
    # 当前看的总页数
    page_num_now = models.IntegerField(default=0)
    # 当前用户读书使用的总时间
    read_total_time = models.IntegerField(default=0)
    # 用户实际要付出的金额
    reality_price = models.DecimalField(max_digits=12, decimal_places=2, null=False)
    # 用户应该要付出的金额
    deserve_price = models.DecimalField(max_digits=12, decimal_places=2, null=False)
    objects = ReadingGoalManager()

    # 读书活动不需要定时
    # def check_punch(self):
    #     if self.status == "ACTIVE":
    #         if self.left_day < 0:
    #             # 如果阅读时间已经结束，则说明读书环节被迫中止
    #             pay_out = self.guaranty
    #             # 本目标的押金被清空
    #             self.guaranty = 0
    #             # 完成的判定在每次打卡中，否则算失败
    #             self.status = "FAILED"
    #             # 更新参加活动的总人数
    #             self.update_activity_person()
    #             # 更新到数据库中
    #             self.save()
    #             # 已经失败了，直接扣除用户的总押金数
    #             UserInfo.objects.update_deposit(user_id=self.user_id, pay_delta=-pay_out)

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

    def create_record(self, goal_id, today_page, today_time, page_avg, record_time, punch_id, user_id, suggest_day):

        # 用户开始打卡
        goal = ReadingGoal.objects.get(goal_id=goal_id)
        goal_page = goal.goal_page
        print(type(goal_page), goal_page, "书的总页数")
        # 已经读完的页数
        finish_page = goal.finish_page
        print(type(finish_page), finish_page, "已经读完的页数")
        print(type(today_page), today_page, "今天，读完的页数")
        print(goal_page, "书的页数")
        reality_page = int(today_page) - int(finish_page)
        print(reality_page, "本次读的页数")
        # 今日完成的页数
        today_page = math.floor(float(today_page))
        print(type(reality_page), reality_page, "今日完成的页数")
        if today_time > 21600:
            today_time = 21600
        # 今天读书消耗的时间
        today_time = math.ceil(float(today_time))
        print(type(today_time), today_time, "完成今日页数需要的时间")

        read = ReadingGoal.objects.filter(goal_id=goal_id)
        if read:
            read = read[0]
            start_time = read.start_time
            time_delta = timezone.now().day - start_time.day + 1
            print(time_delta, "测试用户读书大卡的自动结束，只要这个值等于30就表示是一个月")
            if time_delta >= 30:
                # 无法保存
                ReadingGoal.objects.filter(goal_id=goal_id).update(status="SUCCESS")
            else:
                pass
        # 计算时长返还系数
        avg_time = float(today_time / reality_page) / 60
        print(type(avg_time), avg_time, "根据时长计算返还系数")

        if avg_time <= 0.5:
            read_coffe = 0.1
            print(type(read_coffe), read_coffe, "返还系数")

        elif avg_time > 0.5 and avg_time <= 1.2:
            read_coffe = 0.8
        elif avg_time > 1.2 and avg_time <= 3:
            read_coffe = 1 - math.floor((avg_time - 1.2) / 0.3) * 0.05
        elif avg_time > 3 and avg_time <= 5:
            read_coffe = 1 - math.floor((avg_time - 1.2) / 0.3) * 0.06
        else:
            read_coffe = 0.5
        # 计算天数返还系数
        # 今天是阅读的第几天
        day_num = (timezone.now() - goal.start_time).days + 1

        print(read_coffe, "时长系数")
        print(suggest_day, "建议阅读天数")
        print(day_num, "当前天数")

        if day_num <= suggest_day:
            day_coffe = 1
        else:
            day_coffe = 1 - 0.05 * (day_num - suggest_day)
            if day_coffe <= 0.1:
                day_coffe = 0.1

        print(page_avg, "平均每页获得钱")
        print(reality_page, "本次阅读页数")
        print(day_coffe, "天数系数")

        # 开始计算返还page_avg*today_pge*read_coffe*day_num
        bonus = decimal.Decimal(page_avg) * reality_page * decimal.Decimal(read_coffe) * decimal.Decimal(day_coffe)
        print(type(bonus), bonus, 1111111111111111111111111111)
        # 由于数据保存不成功，绕开最开始的保存方法
        # goal.bonus += decimal.Decimal(bonus)
        # goal.finish_page += today_page
        # goal.save()
        # 取出最开始的收益+打卡收益
        read_bonus = goal.bonus + bonus
        try:
            # 取出最开始的打卡页数+本次打卡的页数
            ReadingGoal.objects.filter(goal_id=goal_id).update(bonus=decimal.Decimal(read_bonus),
                                                               finish_page=today_page)
            user = UserInfo.objects.get(user_id=user_id)
            user.add_money += bonus
            # 更新阅读记录的总收益
            # Activity.objects.add_bonus_coeff(ReadingGoal.get_activity(), bonus, 0)
            # 在用户押金里面减去本地打卡获得的收益
            user.deposit -= bonus
            if user.deposit < 0:
                user.deposit = 0
            user.save()
        except Exception as e:
            print(e, "更新押金失败")

        """增加用户的完成天数"""
        UserRecord.objects.update_finish_day(user=UserInfo.objects.get(user_id=goal.user_id))
        today_record = timezone.now().strftime("%Y-%m-%d")
        if today_record != record_time or len(punch_id) == 0:
            try:
                print(bonus, 1235453236365355)
                self.create(goal_id=str(goal_id), bonus=bonus, start_page=goal.finish_page, reading_page=reality_page,
                            reading_delta=today_time, record_time=record_time, user_id=user_id)
            except Exception as e:
                print("打卡失败", e)
        else:
            try:
                # 表已经存在,
                read_punch = self.filter(record_time=today_record, user_id=user_id)[0]
                read_punch.reading_delta += today_time
                read_punch.reading_page += reality_page
                read_punch.bonus += bonus
                read_punch.save()
            except Exception as e:
                print("保存当天的数据失败", e)

        if goal.status == "SUCCESS":
            UserInfo.objects.update_balance(user_id=goal.user_id, pay_delta=goal.bonus)
            # 更新参加活动的总人数
            goal.update_activity_person()
            # 将本次阅读所赚的的金钱放入累计收益
        return read_coffe


class ReadingPunchRecord(models.Model):
    """ Model for running task record
        To save user's actual running distance per day
    """
    # 主键ID,标识打卡记录
    punch_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.IntegerField(null=False)
    # 外键ID,标识对应目标
    goal_id = models.UUIDField(default=uuid.uuid4, editable=False)
    # Time when user creates the record
    record_time = models.DateTimeField(null=False)
    # Bonus can be -/+, depends on user complete the task or not
    bonus = models.DecimalField(max_digits=12, decimal_places=2)
    # 本次阅读的起始页
    start_page = models.IntegerField(default=0, null=False)
    # 本次阅读的页面数
    reading_page = models.IntegerField(default=0, null=False)
    # 读书的时长
    reading_delta = models.IntegerField(default=0, null=False)
    objects = ReadingPunchRecordManager()


class BookInfoManager(models.Manager):
    def get_book_info(self, book_id):
        readinginfo = {}
        book = self.filter(book_id=book_id)[0]
        readinginfo["id"] = book.book_id
        readinginfo["title"] = book.bookname
        readinginfo["intro"] = book.introduction
        readinginfo["imageurl"] = book.imgurl
        readinginfo["price"] = book.book_price
        readinginfo["return"] = book.return_price
        readinginfo["guaranty"] = book.guaranty
        readinginfo["page_num"] = book.page_num
        readinginfo["suggest_day"] = book.suggest_day
        readinginfo["author"] = book.author
        readinginfo["book_type"] = book.book_type
        return readinginfo


class BookInfo(models.Model):
    book_id = models.IntegerField(primary_key=True, default=1)
    bookname = models.CharField(max_length=255, null=False)
    book_type = models.CharField(max_length=55, null=False)
    author = models.CharField(max_length=100, null=False)
    publish_time = models.DateTimeField(null=False)
    page_num = models.IntegerField(null=False)
    book_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    return_price = models.DecimalField(max_digits=12, decimal_places=2)
    introduction = models.TextField()
    suggest_day = models.IntegerField()
    imgurl = models.CharField(max_length=512, null=False)
    guaranty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    objects = BookInfoManager()

    class Meta:
        db_table = "on_bookinfo"


class ReadMessage(models.Model):
    user_id = models.IntegerField(default=0, primary_key=True)
    read_times = models.IntegerField(default=0)
    # 当天看的总页数
    page_day_num = models.IntegerField(default=0)
    # 看到哪一页
    this_page_num = models.IntegerField(default=0)


class ReadTimeManager(models.Manager):
    # 获取当前的时间戳，记录开始时间
    def get_start_read(self, user_id):
        user = self.filter(user_id=user_id)[0]
        user.start_read = timezone.now()
        user.is_reading = 1
        user.save()
        return True

    # 获取用户的阅读的状态
    def get_reading_state(self, user_id):
        user = self.filter(user_id=user_id)[0]
        return user.is_reading


class ReadTime(models.Model):
    user_id = models.IntegerField(primary_key=True, null=False)
    start_read = models.DateTimeField(null=True, default=timezone.now)
    time_range = models.IntegerField(null=True, )
    is_reading = models.IntegerField(null=False, default=0)
    objects = ReadTimeManager()


class Saying(models.Model):
    id = models.IntegerField(primary_key=True, null=False)
    content = models.TextField(null=False)

    class Meta:
        db_table = "on_say"


class CommentManager(models.Manager):
    def praise_comment(self, user_id, punch_id):
        try:
            praise = ReadingPunchPraise(user_id=user_id, punch_id=punch_id)
            praise.save()
            record = self.get(id=punch_id)
            record.prise += 1
            record.save()
        except Exception as e:
            print(e)

        # user对某punch举报

    def report_comment(self, user_id, punch_id):
        try:
            report = ReadingPunchReport(user_id=user_id, punch_id=punch_id)
            report.save()
            record = self.get(id=punch_id)
            record.report += 1
            record.save()
        except Exception as e:
            print(e)


# 用户评论表
class Comments(models.Model):
    id = models.IntegerField(primary_key=True, default=uuid.uuid4, auto_created=True)
    user = models.ForeignKey(UserInfo, related_name="com")
    content = models.CharField(null=False, max_length=255)
    c_time = models.DateTimeField()
    prise = models.IntegerField(default=0)
    report = models.IntegerField(default=0)
    voucher_ref = models.TextField(null=True)
    # 截图的存储地址
    voucher_store = models.TextField()
    is_delete = models.BooleanField(default=0, auto_created=True)
    is_top = models.BooleanField(default=0)
    objects = CommentManager()

    @property
    def get_some_message(self):
        user = UserInfo.objects.get(user_id=self.user_id)
        return user

    class Meta:
        db_table = "on_comments"


# 点赞
class ReadingPunchPraise(models.Model):
    id = models.IntegerField(primary_key=True, auto_created=True)
    # 点赞的人的id
    user_id = models.IntegerField()
    punch_id = models.CharField(max_length=255)

    class Meta:
        db_table = "on_readingpunchpraise"


# 举报
class ReadingPunchReport(models.Model):
    id = models.IntegerField(primary_key=True, auto_created=True)
    # 举报的人
    user_id = models.IntegerField()
    # punch id
    punch_id = models.CharField(max_length=255)

    class Meta:
        db_table = "on_readingpunchreport"


class Reply(models.Model):
    id = models.IntegerField(primary_key=True, auto_created=True)
    user_id = models.IntegerField()
    other_id = models.CharField(null=False, max_length=255)
    r_content = models.TextField(null=False)

    @property
    def get_user_message(self):
        user = UserInfo.objects.filter(user_id=self.user_id)
        if user:
            user = user[0]
            return user

    class Meta:
        db_table = "on_reply"


class Read_Finish_SaveManager(models.Manager):
    def save_finish(self, goal_id):
        print("打印一下用户的id，看看是不是自己的", goal_id)
        goal = ReadingGoal.objects.filter(goal_id=goal_id)
        print(goal, "看看是否查询到了值")
        if goal:
            goal = goal[0]
            finish_dict = {
                "goal_id": str(goal_id),
                "user_id": goal.user_id,
                "activity_type": goal.activity_type,
                "goal_type": goal.goal_type,
                "start_time": goal.start_time,
                "goal_day": goal.goal_day,
                "status": "已经结束",
                "mode": goal.mode,
                "guaranty": goal.guaranty,
                "down_payment": goal.down_payment,
                "coefficient": goal.coefficient,
                "bonus": goal.bonus,
                "none_punch_days": goal.none_punch_days,
                "book_name": goal.book_name,
                "goal_page": goal.goal_page,
                "finish_page": goal.finish_page,
                "reality_price": goal.reality_price,
                "deserve_price": goal.deserve_price,
                "max_return": goal.max_return,
                "is_start": goal.is_start,
                "price": goal.price,
                "imageurl": goal.imageurl,
                "page_num_now": goal.page_num_now,
                "read_total_time": goal.read_total_time,
                "book_id": goal.book_id,
                "settle_time": timezone.now().strftime("%Y-%m-%d %H:%M")
            }
            try:
                self.create(**finish_dict)
                return True
            except Exception as e:
                print("创建记录失败", e)
        else:
            return False


class Read_Finish_Save(models.Model):
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
    # 书的名字
    book_name = models.CharField(null=False, max_length=128, default='无名书籍')
    book_id = models.IntegerField(primary_key=True, default=1)

    # 目标页数
    goal_page = models.IntegerField(null=False)
    # 已经阅读完成的页数
    finish_page = models.IntegerField(null=True, default=0)
    # 最高返还金额, 阅读是平台与用户之间的活动
    max_return = models.FloatField(null=True)
    # 是否开始了读书, 开始读书后, 将重置活动开始读书的时间
    is_start = models.IntegerField(null=False, default=0)
    # 书的价格
    price = models.FloatField(null=False, default=0)
    # 书的图片
    imageurl = models.CharField(null=False, default='/static/order/demo.png', max_length=1024)
    # 当前看的总页数
    page_num_now = models.IntegerField(default=0)
    # 当前用户读书使用的总时间
    read_total_time = models.IntegerField(default=0)
    # 用户实际要付出的金额
    reality_price = models.DecimalField(max_digits=12, decimal_places=2, null=False)
    # 用户应该要付出的金额
    deserve_price = models.DecimalField(max_digits=12, decimal_places=2, null=False)
    goal_id = models.CharField(primary_key=True, max_length=255)
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

    objects = Read_Finish_SaveManager()
