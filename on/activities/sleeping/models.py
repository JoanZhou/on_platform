from django.db import models
import uuid
from on.activities.base import Goal, Activity
import django.utils.timezone as timezone
from datetime import datetime, timedelta
from on.user import UserTicket, UserRecord, UserInfo, UserTicketUseage, UserSettlement, BonusRank
import logging
from django.conf import settings
import math
import decimal
import time

logger = logging.getLogger("app")

#punch_attention= punch_attention,is_no_use_point=is_no_use_point,
class SleepingGoalManager(models.Manager):
    # 创建一个新的goal
    def create_goal(self, user_id, guaranty, coefficient,multiple, goal_day,punch_attention,is_no_use_point, sleep_type, goal_type, reality_price,
                    deserve_price):
        start_time = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        goal = self.filter(user_id=user_id).filter(start_time=start_time).filter(status="PENDING")
        if goal:
            goal.first().delete()
        goal = self.create(user_id=user_id,
                           activity_type=SleepingGoal.get_activity(),
                           start_time=start_time,
                           goal_day=goal_day,
                           guaranty=guaranty,
                           coefficient=coefficient,
                           sleep_type=sleep_type,
                           goal_type=goal_type,
                           reality_price=reality_price,
                           deserve_price=deserve_price,
                           punch_attention =punch_attention,
                           is_no_use_point = is_no_use_point,
                           down_payment=0,
                           multiple=multiple,
                           extra_earn=0
                           )

        return goal

    # 删除一个目标
    def delete_goal(self, goal_id):
        goal = self.get(goal_id=goal_id)
        # 删除本目标对应的所有打卡记录
        goal.punch.all().delete()
        # 删除本目标
        goal.delete()

    # 坚持榜
    def adhere_to_the_list(self, user):
        # print('进入坚持榜')
        current_user = user.user_id
        current_user_dict = {'punch_day': 0,
                             'ranking': 0,
                             'nickname': user.nickname,
                             'headimgurl': user.headimgurl,
                             }

        users = SleepingGoal.objects.filter(status='ACTIVE').order_by('-punch_day').values('punch_day', 'user_id')
        # print('坚持榜当前users', users)
        datas = []
        for i, u in enumerate(users):
            user_id = u['user_id']
            day = u['punch_day']
            if current_user == user_id:
                current_user_dict['punch_day'] = day
                current_user_dict['ranking'] = i + 1
            name = UserInfo.objects.filter(user_id=user_id).values('nickname', 'headimgurl').first()
            # print('name', name)
            # {'nickname': 'LXIQAG', 'headimgurl': '/static/avatar/101476.jpg'}
            name['punch_day'] = day
            name['ranking'] = i + 1
            # print('name1111', name)
            # {'nickname': '随″', 'punch_day': 1, 'headimgurl': '/static/avatar/100001.jpg'}
            datas.append(name)
        # datas = sorted(datas, key=lambda e: e.__getitem__('day'), reverse=True)
        lasting_data = {
            'current_user': current_user_dict,
            'datas': datas,
        }
        # print('lasting_data', lasting_data)
        return lasting_data

    def sleep_bonus_list(self, user):
        from on.user import BonusRank
        current_user = user.user_id
        current_user_dict = {'bonus': 0,
                             'ranking': 0,
                             'nickname': user.nickname,
                             'headimgurl': user.headimgurl,
                             }
        datas = []
        rank_list = BonusRank.objects.values('user_id', 'sleep').order_by('-sleep')
        # print('rank_list', rank_list)
        # rank_list <QuerySet [{'user_id': 101346, 'sleep': Decimal('0.48')},
        for i, rank in enumerate(rank_list):
            # print('rank',i, rank)
            user_id = rank['user_id']
            bonus = rank['sleep']
            if current_user == user_id:
                current_user_dict['bonus'] = bonus
                current_user_dict['ranking'] = i + 1
            name = UserInfo.objects.filter(user_id=user_id).values('nickname', 'headimgurl').first()
            name['bonus'] = bonus
            name['ranking'] = i + 1
            datas.append(name)
        bonus_data = {
            'current_user': current_user_dict,
            'datas': datas,
        }
        # print('lasting_data', lasting_data)
        return bonus_data


#
class SleepingGoal(Goal):
    """ Model for running goal
        User needs to set running duration days and distance as
        objective
    """

    getup_time = models.TimeField(null=True)
    SLEEP_TYPE = (
        (0, "睡眠"),
        (1, '早起')
    )
    # 活动类型,
    sleep_type = models.SmallIntegerField(null=False, choices=SLEEP_TYPE, default=0)
    reality_price = models.DecimalField(max_digits=12, decimal_places=2, null=False)
    # 用户应该要付出的金额
    deserve_price = models.DecimalField(max_digits=12, decimal_places=2, null=False)
    # 活动额外收益
    extra_earn = models.DecimalField(max_digits=12, decimal_places=2, null=False, default=0)

    deduction_point = models.IntegerField(null=False,default=0)
    deduction_guaranty = models.IntegerField(null=False, default=0)

    punch_attention = models.IntegerField(null=False, default=1)
    is_no_use_point = models.IntegerField(null=False, default=0)
    multiple = models.IntegerField(null=False, default=1)
    punch_day = models.IntegerField(null=True, default=0)
    objects = SleepingGoalManager()

    @property
    def extra_coeff(self):
        coeff = Coefficient.objects.get(user_id=self.user_id)
        if coeff.new_coeff:
            extra_coeff = coeff.new_coeff - coeff.default_coeff
        else:
            extra_coeff = None
        return extra_coeff

    @property
    def is_first_day(self):
        if self.start_time.strftime("%Y-%m-%d") == timezone.now().strftime("%Y-%m-%d"):
            return True
        else:
            return False

    def auto_use_ticket(self, ticket_type):
        # 如果不存在打卡记录,则使用券。起床打卡应该是为今天使用券，因为确认是否免签所用的时间都是今天
        has_ticket = UserTicket.objects.use_ticket(goal_id=self.goal_id, ticket_type="NS",
                                                   use_time=timezone.now())
        return has_ticket

    # 开始检测睡眠打卡任务，此任务的运行时间是在每天早上的8点之后，每三秒运行一次

    def check_sleep(self):
        try:
            pay_out = 0
            new_coeff = 0
            user = UserInfo.objects.get(user_id=self.user_id)
            punch_record = SleepingPunchRecord.objects.exist_record_today(goal_id=self.goal_id)
            coeff = Coefficient.objects.get(user_id=self.user_id)
            # 只有处于活动状态的目标才会检查
            if self.status == "ACTIVE":
                print("{}：开始检查睡眠活动的打卡情况".format(self.user_id))
                # 若是用户的目标天数小于30，则是表示用户的参加的是有限的模式
                if self.goal_day > 30:
                    print("{}：若是目标天数大于30天".format(self.user_id))
                    # 判断是哪个模式，若是早起模式的话
                    if self.sleep_type:
                        # 首先判断今天是不是第一天，若是第一天则不付出任何代价，pay_out=0，coeff = 0
                        if self.is_first_day:
                            print("{}：若是第一天的话不做任何处理".format(self.user_id))
                            pass
                        else:
                            print("若不是第一天则判断在当天0点到8点之间有没有打卡记录")
                            # 若不是第一天则判断在当天0点到8点之间有没有打卡记录
                            if punch_record:
                                print("今天早上有打卡记录")
                                # 获取当天打卡记录的起床时间
                                try:
                                    new_coeff = coeff.new_coeff
                                    print("新的系数")
                                except Exception as e:
                                    print(e)

                            # 若有打卡记录则开始计算系数，首先调用方法，生成今天的基本系数
                            else:
                                print("由于在早上没有打卡记录用户在无限的睡眠模式中失败{}".format(self.user_id))
                                # 若是没有打卡记录，则一次性扣完保证金
                                new_coeff = coeff.default_coeff
                                pay_out = self.guaranty
                                user.deposit -= self.guaranty
                                self.guaranty = 0
                                self.status = "DEALWITH"
                    # 若是睡眠模式的话
                    else:
                        print("开始进入睡眠模式，天数无线")
                        # 判断是否是第一天，若是第一天的话由于只能晚上打卡，所以不用现在处理，直接跳过
                        if self.is_first_day:
                            # 不做处理
                            pass
                        # 若不是第一天，则系数跟比例直接根据时间来计算
                        else:
                            # 若不是第一天，则需要判断昨天夜晚有没有打卡记录，若是没有打卡，则新的系数为原系数×50%
                            if punch_record:
                                print("今天早上有打卡记录")
                                # 此系数是根据早起时间获取的
                                try:
                                    new_coeff = coeff.new_coeff
                                except Exception as e:
                                    print(e)
                            else:
                                new_coeff = coeff.default_coeff
                                pay_out = self.guaranty
                                user.deposit -= self.guaranty
                                self.guaranty = 0
                                self.status = "DEALWITH"
                # 表示是有限的模式
                else:
                    print("{}：开始进入有限标准模式".format(self.user_id))
                    if self.sleep_type:
                        # 目标天数7,14,21，无限制
                        # 若是有目标天数限制，则left——day<=0的时候，活动结束
                        # 若是无限制，则不会结束，直到活动失败的时候才会结束
                        # 首先判断今天是不是第一天，若是第一天则不付出任何代价，pay_out=0，coeff = 0
                        if self.is_first_day:
                            pass
                        else:
                            if self.left_day > 0:
                                # 若不是第一天则判断在当天0点到8点之间有没有打卡记录

                                if punch_record:
                                    print("今天早上有打卡记录")
                                    try:
                                        # 获取当天打卡记录的起床时间
                                        # 若有打卡记录则开始计算系数，首先调用方法，生成今天的基本系数
                                        new_coeff = coeff.new_coeff
                                    except Exception as e:
                                        print(e, '用户早起更新系数失败{}'.format(self.user_id))
                                else:
                                    # 若是没有打卡记录，则一次性扣完保证金
                                    print("用户在有限的标准模式中失败{}".format(self.user_id))
                                    new_coeff = coeff.default_coeff
                                    pay_out = self.guaranty
                                    user.deposit -= self.guaranty
                                    self.status = "DEALWITH"
                                    self.guaranty = 0
                            else:
                                # 用户剩余天数小鱼或等于0
                                if punch_record:
                                    print("今天早上有打卡记录")
                                    try:
                                        # 获取当天打卡记录的起床时间
                                        # 若有打卡记录则开始计算系数，首先调用方法，生成今天的基本系数
                                        new_coeff = coeff.new_coeff
                                    except Exception as e:
                                        print(e, '用户早起更新系数失败{}'.format(self.user_id))
                                    pay_out = 0
                                    self.status = "SUCCESS"
                                else:
                                    new_coeff = coeff.default_coeff
                                    pay_out = self.guaranty
                                    user.deposit -= self.guaranty
                                    self.status = "DEALWITH"
                                    self.guaranty = 0

                    # 若是睡眠模式的话
                    else:
                        # 判断是否是第一天，若是第一天的话由于只能晚上打卡，所以不用现在处理，直接跳过
                        if self.is_first_day:
                            # 不做处理
                            pass
                        # 若不是第一天，则系数跟比例直接根据时间来计算
                        else:
                            # 若不是第一天，则需要判断昨天夜晚有没有打卡记录，若是没有打卡，则新的系数为原系数×50%
                            if self.left_day > 0:
                                if punch_record:
                                    # 此系数是根据早起时间获取的
                                    new_coeff = coeff.new_coeff
                                else:
                                    # 表示没有打卡记录
                                    print("用户在有限的睡眠模式中失败{}".format(self.user_id))
                                    new_coeff = coeff.default_coeff
                                    pay_out = self.guaranty
                                    user.deposit -= self.guaranty
                                    self.guaranty = 0
                                    self.status = "DEALWITH"
                            else:
                                print("用户{}开始进入睡眠模式".format(self.user_id))
                                if punch_record:
                                    print("用户{}今天早上大了卡".format(self.user_id))
                                    try:
                                        new_coeff = coeff.new_coeff
                                        self.status = "SUCCESS"
                                    except Exception as e:
                                        print(e)
                                else:
                                    new_coeff = coeff.default_coeff
                                    # 表示没有打卡记录
                                    pay_out = self.guaranty
                                    user.deposit -= self.guaranty
                                    self.guaranty = 0
                                    self.status = "DEALWITH"
                # 更新到数据库中
                self.save()
                user.save()
                UserInfo.objects.update_deposit(user_id=self.user_id, pay_delta=-pay_out)
                print("{}：用户需要付出去的金钱{}，用户的系数是{},用户的剩余天数是{}".format(self.user_id, pay_out, new_coeff, self.left_day))
                return pay_out, new_coeff
        except AssertionError:
            # 如果断言失败,则记录日志，返回两个0
            logger.error("Assertion Failed! Function: Check Punch Goal:{0}".format(self.goal_id))
            return 0, 0
        except Exception as e:
            logger.error(e)
            return 0, 0

    def update_default_coeff(self):
        try:
            Coefficient.objects.update_every_coeff(user_id=self.user_id,
                                                   sleep_type=self.sleep_type,
                                                   goal_day=self.goal_day)
            return True
        except Exception as e:
            print("更新是失败，但是不做处理", e)

    # 活动期间每日分钱
    def extra_earn_today(self, every_day_pay):

        if self.status == "ACTIVE":
            coeff_obj = Coefficient.objects.get(user_id=self.user_id)
            money = decimal.Decimal(coeff_obj.default_coeff) * decimal.Decimal(every_day_pay)

            try:
                SleepingPunchRecord.objects.addMoneyToRecord(user_id=self.user_id,extra_earn = money)
                rank = BonusRank.objects.filter(user_id=self.user_id)
                if rank:
                    BonusRank.objects.add_sleep(user_id=self.user_id, profit=money)
                else:
                    BonusRank.objects.create(user_id=self.user_id, sleep=money)
            except Exception as e:
                logger.error(e)
            user = UserInfo.objects.get(user_id=self.user_id)
            user.extra_money += money
            self.extra_earn += money
            try:
                self.save()
                user.save()
            except Exception as e:
                print(e)

    # 所有人都完成后分钱
    def update_all_finaly(self):
        try:
            if self.status == "ACTIVE":
                coeff_obj = Coefficient.objects.get(user_id=self.user_id)
                money = decimal.Decimal(coeff_obj.new_coeff) * decimal.Decimal(0.01)
                try:
                    rank = BonusRank.objects.filter(user_id=self.user_id)
                    if rank:
                        BonusRank.objects.add_sleep(user_id=self.user_id, profit=money)
                    else:
                        BonusRank.objects.create(user_id=self.user_id, sleep=money)
                except Exception as e:
                    logger.error(e)
                user = UserInfo.objects.get(user_id=self.user_id)
                user.extra_money += money
                self.extra_earn += money
                user.save()
                self.save()
        except Exception as e:
            print(e)

    # 用户的收益计算
    def earn_profit_sleep(self, average_pay):
        time_now = timezone.now().strftime("%Y-%m-%d")
        # 第一天参与的用户不要进行计算
        if not settings.DEBUG:
            time.sleep(4)
            today = timezone.now().date()
            # 今天的日期减去开始日期
            delta = (today - self.start_time.date()).days
        else:
            delta = 1
        earn_pay = 0
        # 只有用户状态为active的才是需要计算的
        if delta > 0 and self.status == 'ACTIVE':
            # 查询当前用户的新系数
            coeff = Coefficient.objects.filter(user_id=self.user_id)
            new_coeff = 1
            if coeff:
                coeff = coeff[0]
                new_coeff = coeff.new_coeff
            # 用户当前的赚到的金额为平均金额乘以系数
            earn_pay = math.floor((average_pay * decimal.Decimal(new_coeff)) * 100) / 100
            self.bonus += decimal.Decimal(earn_pay)
            self.save()
            try:
                print("开始更新每日收益")
                SleepingPunchRecord.objects.update_today_bonus(user_id=self.user_id, bonusTime=time_now,
                                                               today_bonus=earn_pay)
                print("开始更新每日收益")
            except Exception as e:
                print(e)
            try:
                rank = BonusRank.objects.filter(user_id=self.user_id)
                if rank:
                    BonusRank.objects.add_sleep(user_id=self.user_id, profit=earn_pay)
                else:
                    BonusRank.objects.create(user_id=self.user_id, sleep=earn_pay)
            except Exception as e:
                logger.error(e)
            UserInfo.objects.update_balance(user_id=self.user_id, pay_delta=earn_pay)
            # 在settlement表中增加记录
            UserSettlement.objects.earn_profit(self.goal_id, earn_pay)
        else:
            if self.left_day >= 0 and self.status == "DEALWITH":
                # 查询当前用户的新系数
                coeff = Coefficient.objects.filter(user_id=self.user_id)
                if coeff:
                    coeff = coeff[0]
                # 用户当前的赚到的金额为平均金额乘以系数
                earn_pay = math.floor((average_pay * decimal.Decimal(coeff.default_coeff)) * 100) / 100
                self.bonus += decimal.Decimal(earn_pay)
                self.status = "FAILED"
                self.save()
                try:
                    SleepingPunchRecord.objects.update_today_bonus(user_id=self.user_id, bonusTime=time_now,
                                                                   today_bonus=earn_pay)
                except Exception as e:
                    print(e)
                try:
                    rank = BonusRank.objects.filter(user_id=self.user_id)
                    if rank:
                        BonusRank.objects.add_sleep(user_id=self.user_id, profit=earn_pay)
                    else:
                        BonusRank.objects.create(user_id=self.user_id, sleep=earn_pay)
                except Exception as e:
                    logger.error(e)
                UserInfo.objects.update_balance(user_id=self.user_id, pay_delta=earn_pay)
                # 在settlement表中增加记录
                UserSettlement.objects.earn_profit(self.goal_id, earn_pay)
            elif (self.left_day <= 0 and self.left_day > -2) and self.status == "SUCCESS":
                coeff = Coefficient.objects.filter(user_id=self.user_id)
                if coeff:
                    coeff = coeff[0]
                # 用户当前的赚到的金额为平均金额乘以系数
                earn_pay = math.floor((average_pay * decimal.Decimal(coeff.new_coeff)) * 100) / 100
                self.bonus += decimal.Decimal(earn_pay)
                self.save()
                try:
                    print("开始更新每日收益")
                    SleepingPunchRecord.objects.update_today_bonus(user_id=self.user_id, bonusTime=time_now,
                                                                   today_bonus=earn_pay)
                    print("开始更新每日收益")
                except Exception as e:
                    print(e)
                try:
                    rank = BonusRank.objects.filter(user_id=self.user_id)
                    if rank:
                        BonusRank.objects.add_sleep(user_id=self.user_id, profit=earn_pay)
                    else:
                        BonusRank.objects.create(user_id=self.user_id, sleep=earn_pay)
                except Exception as e:
                    logger.error(e)
                UserInfo.objects.update_balance(user_id=self.user_id, pay_delta=earn_pay)
                # 在settlement表中增加记录
                UserSettlement.objects.earn_profit(self.goal_id, earn_pay)
        return earn_pay

    def use_no_sign_in_date(self, daydelta):
        today = (timezone.now() + timedelta(days=daydelta) + timedelta(hours=8)).date()
        end = today + timedelta(days=1)
        use_history = UserTicketUseage.objects.filter(useage_time__range=(today, end), goal_id=self.goal_id,
                                                      ticket_type='NS')
        if use_history:
            return True
        else:
            return False

    def get_time_for_display(self, daydelta):
        """
        用于展示该天打卡记录中的部分信息
        :param daydelta: 距离今天有多长时间
        :return:
        """
        # 查找昨天到今天睡前打卡的记录
        lastday = (timezone.now() + timedelta(days=daydelta)).date()
        today = lastday + timedelta(days=1)
        # 如果存在任意一条打卡记录
        record = self.punch.filter(before_sleep_time__range=(lastday, today))
        if record:
            record = record[0]
            sleeptime = record.before_sleep_time.strftime("%H:%M") if record.before_sleep_time else None
            getuptime = record.get_up_time.strftime("%H:%M") if record.get_up_time else None
            confirmtime = record.confirm_time.strftime("%H:%M") if record.confirm_time else None
            checktime = record.check_time.strftime("%H:%M") if record.check_time else None
            checktimeend = (record.check_time + timedelta(minutes=15)).strftime("%H:%M") if record.check_time else None
            return sleeptime, getuptime, confirmtime, checktime, checktimeend
        else:
            return None, None, None, None, None

    @staticmethod
    def get_start_date():
        return datetime.strptime("18:44", "%H:%M").time()

    @staticmethod
    def get_activity():
        return "0"

    def update_activity(self, user_id):
        # 更新该种活动的总系数
        print("更新作息活动的系数")
        Activity.objects.add_bonus_coeff(SleepingGoal.get_activity(), self.guaranty + self.down_payment,
                                         self.coefficient)
        # 增加用户的累计参加次数
        print("更新用户的累计参加次数")
        UserRecord.objects.update_join(user=UserInfo.objects.get(user_id=user_id), coeff=self.coefficient)

    # 结算后的系数更新
    def update_activity_person(self):
        Activity.objects.update_person(SleepingGoal.get_activity())
        Activity.objects.update_coeff(SleepingGoal.get_activity(), -self.coefficient)

    @property
    def left_day(self):
        left = 0
        if self.sleep_type == 0:
            # 剩下多少天 = 目标日期-（现在的日期-开始日期）-1
            left = self.goal_day - (timezone.now().date() - self.start_time.date()).days - 1
        elif self.sleep_type == 1:
            left = self.goal_day - (timezone.now().date() - self.start_time.date()).days
        print("用户{}还剩{}天".format(self.user_id, left))
        return left


class SleepingPunchRecordManager(models.Manager):

    # 创建一个新的打卡记录，首先是从睡觉开始的
    def create_sleep_record(self, goal, sleep_type, user_id):
        print('create_sleep_record')
        # 首先要判断现在的时间是处于合法打卡时间内的
        record = None
        try:
            record_time = timezone.now()
            # 若是打卡时间在表里面存在，那么就不创建
            punch_record = SleepingPunchRecord.objects.filter(punch_time=record_time.strftime("%Y-%m-%d"), goal=goal)
            if len(punch_record) > 0:
                print('若打卡记录已经有的话')
                """
                1,不创建 且需要判断当前的打卡时间，若打卡时间是在21-24点之间，那么就将数据加进sleep_time里面,
                若是打卡时间是在0-8点之间，那么就把时间存进get_up_time里面.
                """

                if 21 <= record_time.hour and record_time.hour <= 24:
                    """
                    若是在这个时间段打卡，那么需要创建一条明天的打卡记录，由于活动的结束是在定时任务里面控制，所以只有白天打了卡之后才结束，
                    那么此时就不用管，直接创建一条明天的新纪录就是了
                    """
                    # 那么就是说是晚上开始的，只有在早起打卡之后才开始计算系数
                    record = self.filter(punch_time=record_time.strftime("%Y-%m-%d"), goal=goal).update(
                        sleep_time=record_time,
                        punch_time=record_time.strftime(
                            "%Y-%m-%d"))
                    self.create(punch_time=(record_time + timedelta(days=1)).strftime("%Y-%m-%d"),
                                before_sleep_time=record_time, user_id=user_id, sleep_type=sleep_type, goal=goal,extra_earn=0)
                elif 5 <= record_time.hour and record_time.hour < 8:
                    print("开始睡眠早上打卡")

                    """开始计算系数，1,计算时间差2,根据时间差来判断系数"""
                    # coefficient = self.get_time_range(goal=goal)
                    # Coefficient.objects.filter(user_id=user_id).update(new_coeff=coefficient)
                    try:

                        coeff = Coefficient.objects.update_get_up_coeff(user_id=user_id,
                                                                        getup_time=record_time,
                                                                        sleep_type=sleep_type)

                        self.filter(punch_time=(record_time - timedelta(days=1)).strftime("%Y-%m-%d"),
                                    goal=goal).update(
                            after_get_up_time=record_time)
                        record = self.filter(punch_time=record_time.strftime("%Y-%m-%d"), goal=goal).update(
                            get_up_time=record_time)
                        prop = SleepingPunchRecord.objects.get_sleep_time_range(goal_id=goal.goal_id, user_id=user_id)
                        new = coeff.new_coeff * decimal.Decimal(prop)
                        coeff.new_coeff = new
                        coeff.save()

                        goal.punch_day += 1
                        goal.save()

                    except Exception as e:
                        print(e)


                else:
                    return None
            else:
                """这个则是不存在的情况，需要重新创建新表,但是也是要根据时间来看的"""
                if 21 <= record_time.hour and record_time.hour < 24:

                    record = self.create(punch_time=record_time.strftime("%Y-%m-%d"), goal=goal, sleep_time=record_time,
                                         sleep_type=sleep_type, user_id=user_id,extra_earn=0)
                    self.create(punch_time=(record_time + timedelta(days=1)).strftime("%Y-%m-%d"), user_id=user_id,
                                before_sleep_time=record_time, goal=goal,extra_earn=0)
                elif 5 <= record_time.hour and record_time.hour < 8:
                    if goal.is_first_day:
                        print("今天是第一天，不做任何处理")
                        return None
                    else:
                        print("开始创建")
                        try:
                            record = self.create(goal=goal, user_id=user_id, get_up_time=record_time,
                                                 punch_time=record_time.strftime("%Y-%m-%d"), sleep_type=sleep_type,extra_earn=0)
                            coeff = Coefficient.objects.update_get_up_coeff(user_id=user_id,
                                                                            getup_time=timezone.now(),
                                                                            sleep_type=sleep_type)
                            new = coeff.new_coeff * decimal.Decimal(0.5)
                            coeff.new_coeff = new
                            coeff.save()
                            goal.punch_day += 1
                            goal.save()
                        except Exception as e:
                            print(e)
                        print("创建成功")
                else:
                    return None
            return record
        except Exception as e:
            print(e)
            # except AssertionError:
            #     logger.error("Goal:{0} Sleep time out of limit:{1}".format(goal.goal_id, timezone.now()))
            return None

    def get_time_range(self, goal):
        record = self.filter(goal=goal)
        if record:
            record = record[0]
            time_range = record.get_up_time - record.before_sleep_time
            time_range_hour = math.floor(int(time_range.seconds) / (60 * 60))
            coefficient = 0.5
            if time_range_hour < 7:
                coefficient = 0.9
            elif time_range_hour >= 7 and time_range_hour < 9:
                coefficient = 1
            elif time_range_hour >= 9:
                coefficient = 0.9
            return coefficient

    # 早上起床，只能通过 goal.punch.update_getup_record来调用
    def update_getup_record(self, goal, sleep_type, user_id):
        print('update_getup_record, 早起打卡')
        # 首先要判断现在的时间是处于合法打卡时间内的
        try:
            if not settings.DEBUG:
                time_now = timezone.now().time()
                assert time_now.hour < 8
                assert time_now.hour >= 5
            record_time = timezone.now()
            # 若是打卡时间在表里面存在，那么就不创建
            punch_record = SleepingPunchRecord.objects.filter(punch_time=record_time.strftime("%Y-%m-%d"),
                                                              goal=goal)
            if len(punch_record) > 0:
                print('若打卡记录已经有的话')
                """
                1,不创建 且需要判断当前的打卡时间，若是打卡时间是在5-8点之间，那么就把时间存进get_up_time里面.
                """
                if 5 <= record_time.hour and record_time.hour < 8:
                    # record = today.update(get_up_time=record_time)

                    """开始计算系数，1,计算时间差2,根据时间差来判断系数"""
                    # coefficient = self.get_time_range(goal=goal)
                    # Coefficient.objects.filter(user_id=user_id).update(new_coeff=coefficient)
                    record = self.filter(punch_time=record_time.strftime("%Y-%m-%d"), goal=goal).update(
                        get_up_time=record_time)

                    Coefficient.objects.update_get_up_coeff(user_id=user_id, getup_time=record_time,
                                                            sleep_type=sleep_type)
                    goal.punch_day += 1
                    goal.save()
                else:
                    return None
            else:
                """这个则是不存在的情况，需要重新创建新表,但是也是要根据时间来看的"""

                if 5 <= record_time.hour and record_time.hour < 8:
                    if goal.is_first_day:
                        print("如果是第一天的话")
                        return None
                    else:
                        print("开始创建")
                        record = self.create(goal=goal, user_id=user_id, get_up_time=record_time,
                                             punch_time=record_time.strftime("%Y-%m-%d"), sleep_type=sleep_type,extra_earn=0)

                        Coefficient.objects.update_get_up_coeff(user_id=user_id, getup_time=record_time,
                                                                sleep_type=sleep_type)
                        goal.punch_day += 1
                        goal.save()
                        print("创建成功")
                else:
                    return None
            return record
        except AssertionError:
            logger.error("Goal:{0} Sleep time out of limit:{1}".format(goal.goal_id, timezone.now()))
            return None

    #


    # # 更新早上起床后的检查时间
    # def update_confirm_time(self):
    #     try:
    #         time_now = timezone.now()
    #         # 获取今早起床的记录
    #         today = timezone.now().date()
    #         tomorrow = today + timedelta(days=1)
    #         record = self.filter(get_up_time__range=(today, tomorrow))
    #         if record:
    #             record = record[0]
    #             # 既然用户已经确定了，那就没必要继续找了
    #             if record.confirm_time:
    #                 return None
    #             check_time = record.check_time
    #             # 现在的时间要满足一定条件
    #             assert time_now >= check_time
    #             assert time_now <= check_time + timedelta(minutes=15)
    #             # 如果满足，记录最后一次打卡的时间即可
    #             record.confirm_time = time_now
    #             record.save()
    #         else:
    #             return None
    #     except AssertionError:
    #         return None

    # 获取今天产生的打卡时间
    def get_today_check_time(self):
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)
        # 获取今早检查打卡的时间
        record = self.filter(check_time__range=(today, tomorrow))
        if record:
            record = record[0]
            return record.check_time
        else:
            return None

    # 获取完整有效记录的时间，以confirm_time为准
    def get_day_record(self, daydelta):
        """
        :param day: 表示一个timedelta
        :return:
        """
        # 统一按照过12小时计算时间，这样可以区分第1或第2天
        today = (timezone.now() + timedelta(days=daydelta) + timedelta(hours=12)).date()
        end = today + timedelta(days=1)
        # 是否完成了全部以最终确认的时间进行计算
        return self.filter(confirm_time__range=(today, end))

    # 获取今天早上的打卡时间
    def get_getup_time_today(self, user_id):
        today = timezone.now().strftime("%Y-%m-%d")
        record = self.filter(punch_time=today, user_id=user_id)
        if record:
            record = record[0]
            get_up_time = record.get_up_time
            return get_up_time
        else:
            return None

    # 判断当天早上有没有打卡记录
    def exist_record_today(self, goal_id):
        # print("{}：查询今天有没有打卡记录".format(self.user_id))
        today = timezone.now().strftime("%Y-%m-%d")
        print(today, 'today')
        if self.filter(punch_time=today, goal_id=goal_id, get_up_time__isnull=False):
            print("该用户今天早上有打卡记录")
            return True
        else:
            print("该用户今天早上没有打卡记录")
            return False

    """判断昨天晚上有没有打卡记录,若是昨天夜晚有打卡记录的话，那么在今天肯定会生成一条打卡记录，
    所以直接判断有没有今天的记录就知道昨天夜晚有没有大卡"""

    def exist_record_tomorrow(self, user_id):

        if self.filter(punch_time=timezone.now().strftime("%Y-%m-%d"), user_id=user_id):
            print("{}昨天夜晚有打卡记录".format(user_id))
            return True
        else:
            print("{}昨天夜晚没有打卡记录".format(user_id))
            return False

    # 获取睡眠模式的睡眠时间区间，返回系数加成比例
    def get_sleep_time_range(self, user_id, goal_id):
        today = timezone.now().strftime("%Y-%m-%d")
        try:
            record = self.get(goal_id=goal_id, punch_time=today)
            after_sleep_time = record.before_sleep_time
            get_up_time = record.get_up_time
            prop = 1
            if after_sleep_time:
                time_range = (get_up_time - after_sleep_time).seconds
                hour = math.floor(time_range / (60 * 60))
                if hour >= 7 and hour < 9:
                    prop = 1.1
                elif hour >= 6 and hour < 7 or hour > 9:
                    prop = 1
                elif hour < 6:
                    prop = 0.5
            else:
                prop = 0.5
            return prop
        except Exception as e:
            print("获取系数加成比例错误{}--{}".format(user_id, e))

    # 更新用户的每日的收益
    def update_today_bonus(self, user_id, bonusTime, today_bonus):
        sleep = self.filter(user_id=user_id, punch_time=bonusTime)
        try:
            if sleep:
                sleep = sleep[0]
                sleep.today_bonus = today_bonus
                sleep.save()
            else:
                pass
        except Exception as e:
            print(e)

    # 早起bh
    def morning_list(self, user):
        current_user = user.user_id
        current_user_dict = {'ranking': None,
                             'nickname': user.nickname,
                             'get_up_time': '您未打卡！',
                             'headimgurl': user.headimgurl,
                             }
        datas = []
        now_time = timezone.now().day
        data = SleepingPunchRecord.objects.filter(punch_time__day=now_time). \
            exclude(get_up_time=None).order_by('get_up_time', 'user_id').values('get_up_time', 'user_id')
        for i, d in enumerate(data):
            # print('d>>>', i, d)
            user_id = d.get('user_id')
            if current_user == user_id:
                current_user_dict['ranking'] = i + 1
                current_user_dict['get_up_time'] = d['get_up_time']
            # print('user_id', user_id)
            u = UserInfo.objects.filter(user_id=user_id).values('nickname', 'headimgurl')[0]
            d.update(u)
            d['ranking'] = i + 1
            datas.append(d)
        morning_data = {
            'datas': datas,
            'current_user': current_user_dict,
        }
        # print('morning_data', morning_data)
        return morning_data


# # 坚持榜
# def adhere_to_the_list(self, user):
# 	# print('进入坚持榜')
# 	current_user = user.user_id
# 	current_user_dict = {'day': 0,
# 	                     'nickname': user.nickname,
# 	                     'headimgurl': user.headimgurl,
# 	                     }
# 	users = SleepingPunchRecord.objects.exclude(get_up_time=None, punch_time=None).values( 'user_id').distinct()
# 	# print('坚持榜data', users)
# 	datas = []
# 	for i, u in enumerate(users):
# 		user_id = u['user_id']
# 		day = SleepingPunchRecord.objects.filter(user_id=user_id).order_by('get_up_time')
# 		if current_user == user_id:
# 			current_user_dict['day'] = len(day)
# 			current_user_dict['ranking'] = i
# 		name = UserInfo.objects.filter(user_id=user_id).values('nickname', 'headimgurl')[0]
# 		# {'nickname': 'LXIQAG', 'headimgurl': '/static/avatar/101476.jpg'}
# 		name['day'] = len(day)
# 		# {'nickname': '随″', 'day': 1, 'headimgurl': '/static/avatar/100001.jpg'}
# 		datas.append(name)
# 	datas = sorted(datas, key=lambda e: e.__getitem__('day'), reverse=True)
# 	lasting_data = {
# 		'current_user': current_user_dict,
# 		'datas': datas,
# 	}
# 	# print('lasting_data', lasting_data)
# 	return lasting_data

    def addMoneyToRecord(self, user_id, extra_earn):
        try:
            timeNow = timezone.now().strftime("%Y-%m-%d")
            record = self.filter(user_id=user_id,punch_time=timeNow)
            if record:
                record = record[0]
                record.extra_earn = extra_earn
                record.save()
        except Exception as e:
            print(e)
            pass

"""
今晚与明早算同一天
当用户该天开始打卡的时候，则
晚上该睡觉的时候没睡觉，算打卡失败
早上该起床的时候没起床，算打卡失败
该确认时间的时候没确认，算打卡失败
"""




class SleepingPunchRecord(models.Model):
    """ Model for running task record
        To save user's actual running distance per day
    """
    # 主键ID,标识打卡记录
    punch_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.IntegerField()
    # 外键ID,标识对应目标
    goal = models.ForeignKey(SleepingGoal, related_name="punch", on_delete=models.PROTECT)
    SLEEP_TYPE = (
        (0, "睡眠"),
        (1, '早起')
    )
    # 活动类型,
    sleep_type = models.SmallIntegerField(null=False, choices=SLEEP_TYPE, default=0)
    # 确认记录的时间
    confirm_time = models.DateTimeField(null=True)
    # 用户昨天睡前打卡时间，可以为空
    before_sleep_time = models.DateTimeField(null=True)
    # 用户实际的睡前打卡时间
    sleep_time = models.DateTimeField(null=True)
    # 用户实际的起床打卡时间
    get_up_time = models.DateTimeField(null=True)
    # 用户起床后，根据起床时间随机生成的确认记录打卡的时间
    check_time = models.DateTimeField(null=True)
    record_times = models.IntegerField(null=True)
    # 打卡时间
    punch_time = models.DateTimeField(null=True)
    today_bonus = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    # 由于本打卡记录判断失败与成功的状态过于复杂，所以采用独立字段判断
    # 若是睡眠模式第一次打卡时应该是前一天的晚上，当用户打卡睡觉了之后就插入该记录，若是早起模式，则是第二天才开始活动
    # 这个字段的意思是第几天打卡，刚创建的时候为1
    punch_day = models.IntegerField(null=True, default=1)
    after_get_up_time = models.DateTimeField(null=True)
    extra_earn  = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    is_success = models.BooleanField(null=False, default=True)
    objects = SleepingPunchRecordManager()


# def change_num(num):
#     # 辅助函数， 根据num=int(distance - goal_distance)向下取整
#     addition_coeff = {
#         '3': 0.1,
#         '6': 0.2,
#         '9': 0.3,
#         '12': 0.4,
#         '15': 0.5,
#     }
#     num


class CoefficientManager(models.Manager):
    # 更新系数
    def update_every_coeff(self, user_id, sleep_type, goal_day):
        coefficient = self.filter(user_id=user_id)
        sleep = SleepingGoal.objects.filter(user_id=user_id)
        multiple = 1
        if sleep:
            sleep = sleep[0]
            multiple = sleep.multiple
        if coefficient:
            coefficient = coefficient[0]

            if sleep_type == 0 and goal_day > 30:
                if coefficient.default_coeff < 60*multiple:
                    coefficient.default_coeff += decimal.Decimal(1.2)*multiple
                else:
                    coefficient.default_coeff = 60*multiple
            elif sleep_type == 1 and goal_day > 30:
                if coefficient.default_coeff < 50*multiple:
                    coefficient.default_coeff += decimal.Decimal(1)*multiple
                else:
                    coefficient.default_coeff = 50*multiple
            coefficient.save()
            # time.sleep(5)
            return True
        return False

    def update_get_up_coeff(self, user_id, getup_time, sleep_type):
        print("开始生成用户的基本系数{}".format(getup_time))
        hour = getup_time.hour
        print(type(hour), hour, "穿过来的小时数")
        try:
            coeff = self.filter(user_id=user_id)
            if coeff:
                coeff = coeff[0]

                if hour >= 5 and hour < 6:
                    coeff.new_coeff = coeff.default_coeff * decimal.Decimal(1.2)
                elif hour >= 6 and hour < 7:
                    coeff.new_coeff = coeff.default_coeff * decimal.Decimal(1.1)
                elif hour >= 7 and hour < 8:
                    coeff.new_coeff = coeff.default_coeff
                else:
                    coeff.new_coeff = coeff.default_coeff
                if sleep_type == 0:
                    if coeff.new_coeff >= 60:
                        coeff.new_coeff = 60
                elif sleep_type == 1:
                    if coeff.new_coeff >= 50:
                        coeff.new_coeff = 50
                coeff.save()
                return coeff
        except Exception as e:
            print("早起更新系数失败，{}————{}".format(user_id, e))

    def riding_update_coeff(self, distance, goal):
        user_id = goal.user_id
        goal_distance = goal.goal_distance
        print('当前实际距离是：', distance)
        num = int(distance - goal_distance)
        print('当前超出目标距离是：', num)

        coeffe = Coefficient.objects.get(user_id=user_id)
        print('系数是', coeffe)


class Coefficient(models.Model):
    # 用户id
    user_id = models.IntegerField(null=False, primary_key=True)
    # 用户的默认系数
    default_coeff = models.FloatField(default=1.2)
    # 当用户打卡之后生成的新系数
    new_coeff = models.FloatField(default=0, null=True)
    SLEEP_TYPE = (
        (0, "睡眠"),
        (1, '早起')
    )
    sleep_type = models.SmallIntegerField(null=False, choices=SLEEP_TYPE, default=0)
    objects = CoefficientManager()


class CommentManager(models.Manager):
    def praise_comment(self, user_id, punch_id):
        try:
            praise = SleepingPunchPraise(user_id=user_id, punch_id=punch_id)
            praise.save()
            record = self.get(id=punch_id)
            record.prise += 1
            record.save()
        except Exception as e:
            print(e)

    # user对某punch举报

    def report_comment(self, user_id, punch_id):
        try:
            report = SleepingPunchReport(user_id=user_id, punch_id=punch_id)
            report.save()
            record = self.get(id=punch_id)
            record.report += 1
            record.save()
        except Exception as e:
            print(e)

    def sum_prises(self, user):
        # print('进入膜拜榜')
        current_user = user.user_id
        current_user_dict = {'sum_prise': 0,
                             'ranking': 0,
                             'nickname': user.nickname,
                             'headimgurl': user.headimgurl,
                             }
        user_list = CommentSleep.objects.values('user_id').distinct()
        mobai_list = []
        for u in user_list:
            user_id = u['user_id']
            u = UserInfo.objects.filter(user_id=user_id).values('nickname', 'headimgurl', 'user_id')[0]
            # print('u', u)
            user = u
            prise = CommentSleep.objects.filter(user_id=user_id).values('prise')
            sum_prise = 0
            for i in prise:
                sum_prise += int(i['prise'])
            if current_user == user_id:
                current_user_dict['sum_prise'] = sum_prise
            user['sum_prise'] = sum_prise
            mobai_list.append(user)
        mobai_list = sorted(mobai_list, key=lambda e: e.__getitem__('sum_prise'), reverse=True)
        mobai = []
        for i, k in enumerate(mobai_list):
            # print('k', k.get('user_id'))
            if current_user == k.get('user_id'):
                current_user_dict['ranking'] = i + 1
            k['ranking'] = i + 1
            mobai.append(k)
        watch_list = {
            'datas': mobai,
            'current_user': current_user_dict,
        }
        return watch_list


# 用户评论表
class CommentSleep(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(UserInfo, related_name="slep")
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
        user = UserInfo.objects.filter(user_id=self.user_id)
        if user:
            user = user[0]
            return user

    class Meta:
        db_table = "on_sleep_comments"


# 点赞
class SleepingPunchPraise(models.Model):
    id = models.IntegerField(primary_key=True, auto_created=True)
    # 点赞的人的id
    user_id = models.IntegerField()
    punch_id = models.CharField(max_length=255)

    class Meta:
        db_table = "on_sleepingpunchpraise"


# 举报
class SleepingPunchReport(models.Model):
    id = models.IntegerField(primary_key=True, auto_created=True)
    # 举报的人
    user_id = models.IntegerField()
    # punch id
    punch_id = models.CharField(max_length=255)

    class Meta:
        db_table = "on_sleepingpunchreport"


class ReplySleep(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user_id = models.IntegerField()
    other_id = models.UUIDField(null=False)
    r_content = models.TextField(null=False)

    @property
    def get_user_message(self):
        user = UserInfo.objects.filter(user_id=self.user_id)
        if user:
            user = user[0]
            return user

    class Meta:
        db_table = "on_sleep_reply"


class Finish_SaveManager(models.Manager):
    def save_finish(self, goal_id):
        print("打印一下用户的id，看看是不是自己的", goal_id)
        goal = SleepingGoal.objects.filter(goal_id=goal_id)
        import time
        print(goal, "看看是否查询到了值")
        if goal:
            goal = goal[0]
            finish_dict = {
                "id": str(time.time()),
                "goal_id": str(goal_id),
                "user_id": goal.user_id,
                "activity_type": goal.activity_type,
                "goal_type": goal.goal_type,
                "sleep_type": goal.sleep_type,
                "start_time": goal.start_time,
                "goal_day": goal.goal_day,
                "status": "已经结束",
                "mode": goal.mode,
                "guaranty": goal.guaranty,
                "down_payment": goal.down_payment,
                "coefficient": goal.coefficient,
                "bonus": goal.bonus,
                "none_punch_days": goal.none_punch_days,
                "reality_price": goal.reality_price,
                "deserve_price": goal.deserve_price,
                "getup_time": "",
                "settle_time": timezone.now().strftime("%Y-%m-%d"),
                "extra_earn":goal.extra_earn
            }
            try:
                self.create(**finish_dict)
                return True
            except Exception as e:
                print("创建记录失败", e)
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


class Sleep_Finish_Save(models.Model):
    # 用户实际要付出的金额
    id = models.CharField(primary_key=True, max_length=33)
    reality_price = models.DecimalField(max_digits=12, decimal_places=2, null=False)
    sleep_type = models.IntegerField()
    # 用户应该要付出的金额
    deserve_price = models.DecimalField(max_digits=12, decimal_places=2, null=False)
    goal_id = models.CharField(max_length=66)
    user_id = models.IntegerField(null=True)
    activity_type = models.CharField(null=True, max_length=16, choices=ACTIVITY_CHOICES, default="0")
    # 0为自由模式, 1为日常模式
    goal_type = models.IntegerField(null=True, default=1, choices=GOAL_CHOICES)
    # 开始时间
    start_time = models.DateTimeField(null=True)
    # 目标天数
    goal_day = models.IntegerField(null=True, default=0)
    #
    getup_time = models.CharField(max_length=22, null=True)
    # Task status, pending, active, paused, complete
    status = models.CharField(max_length=32)
    # User selected task mode, 普通, 学生, 尝试, etc
    MODE_CHOICES = (
        (u'N', u'尝新'),
        (u'O', u'普通'),
        (u'P', u'体验'),
        (u'U', u'升级'),
    )
    # 学生或普通模式的选择
    mode = models.CharField(max_length=10)
    # 保证金
    guaranty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    extra_earn = models.DecimalField(max_digits=12, decimal_places=2, null=False, default=0)
    # 底金
    down_payment = models.DecimalField(max_digits=12, decimal_places=2)
    # 系数
    coefficient = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # 瓜分金额
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # 已经发生过的未完成天数, 用于计算下一次扣除底金与保证金的金额数
    none_punch_days = models.IntegerField(null=True, default=0)
    settle_time = models.DateTimeField()
    objects = Finish_SaveManager()

    class Meta:
        db_table = "on_sleep_finish_save"


# sleep 排行
def sleep_ranking_list(user):
    # print('sleeping 排名榜单')
    morning_data = SleepingPunchRecord.objects.morning_list(user)
    # print('早起榜', morning_data)
    # 坚持榜adhere_to_the_list
    lasting_data = SleepingGoal.objects.adhere_to_the_list(user)
    # print('坚持榜', lasting_data)
    # # 膜拜帮 所有评论的点赞次数累加，
    watch_list = CommentSleep.objects.sum_prises(user)
    # print('膜拜榜', watch_lists)
    bonus_data = SleepingGoal.objects.sleep_bonus_list(user)
    sleep_list = {
        'morning': morning_data,
        'lasting': lasting_data,
        'watch_lists': watch_list,
        'bonus_rank': bonus_data,
    }
    # print('sleep_list', sleep_list)
    return sleep_list
