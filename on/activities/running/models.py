from django.db import models
import uuid
from on.activities.base import Goal, Activity
from on.user import UserInfo, UserTicket, UserRecord, UserSettlement, BonusRank
import django.utils.timezone as timezone
from django.conf import settings
import os
import pytz
import math
from datetime import timedelta, datetime
import decimal
from logging import getLogger

logger = getLogger("app")


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

        if running_type:
            nosgin_number = int(nosign)
            UserTicket.objects.create_ticket(goal.goal_id, "NS", nosgin_number)
        return goal


    def create_rungoal(self, user_id, start_time, goal_type, guaranty, down_payment, activate_deposit, coefficient,
                       mode, punch_attention, is_no_use_point, goal_day, deduction_point, deduction_guaranty,
                       distance, reality_price, deserve_price, down_num, kilos_day, multiple):
        goal = self.create(user_id=user_id,
                           activity_type=RunningGoal.get_activity(),
                           start_time=start_time,
                           goal_day=goal_day,
                           mode=mode,
                           guaranty=guaranty,
                           down_payment=down_payment,
                           activate_deposit=activate_deposit,
                           coefficient=coefficient,
                           goal_type=goal_type,
                           goal_distance=distance,
                           left_distance=distance,
                           kilos_day=kilos_day,
                           average=10,
                           reality_price=reality_price,
                           deserve_price=deserve_price,
                           down_num=down_num,
                           punch_attention=punch_attention,
                           is_no_use_point=is_no_use_point,
                           multiple=multiple,
                           deduction_guaranty=deduction_guaranty,
                           deduction_point=deduction_point
                           )
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

    # def first_day(self,user_id,punch_time,goal_id):
    #     try:
    #         record = self.filter(user_id=user_id,goal_id=goal_id)
    #         if record:
    #             record=record[0]
    #             if record.start_time.strftime("%Y-%m-%d") == punch_time:
    #                 record.first_day_record = 1
    #             else:
    #                 record.first_day_record = 0
    #     except Exception as e:
    #         logger.info(e)
    #         pass


# punch_attention = punch_attention,is_no_use_point=is_no_use_point,
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
    left_distance = models.FloatField(null=True, default=0)
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
    extra_earn = models.DecimalField(max_digits=12, decimal_places=2, null=False, default=0)
    punch_attention = models.IntegerField(null=False,default=1)
    is_no_use_point = models.IntegerField(null=False,default=0)
    deduction_point = models.IntegerField(null=False, default=0)
    deduction_guaranty = models.IntegerField(null=False, default=0)
    # first_day_record = models.IntegerField(null=False, default=0)
    multiple = models.IntegerField(null=False, default=0)
    # 这一周累计跑的距离数
    week_distance = models.FloatField(null=False, default=0)
    # 日常模式完成的天数
    finish_week_day = models.IntegerField(null=False, default=0)
    # 用户打卡的天数
    punch_day = models.IntegerField(null=False, default=0)
    objects = RunningGoalManager()

    @staticmethod
    def get_start_date():
        return datetime.strptime("00:01", "%H:%M").time()

    @property
    def first_day_record(self):
        start_time = self.start_time.strftime("%Y-%m-%d")
        user_end_time = (self.start_time + timedelta(days=1)).strftime("%Y-%m-%d")
        if len(RunningPunchRecord.objects.filter(goal_id=self.goal_id,
                                                 record_time__range=(start_time, user_end_time))) > 0:
            return True
        else:
            return False

    def update_default_run_coeff(self):
        try:
            coeff = RunCoefficient.objects.get(user_id=self.user_id)
            if self.goal_day > 30:
                coeff.default_coeff += decimal.Decimal(1 * self.multiple)
                coeff.save()
            return True
        except Exception as e:
            logger.error(e)
            pass

    # 由于是用户不需要投一天参加第二天开始，所以不需要riqi
    def earn_run_profit(self, average_pay):
        '''获取系数对象'''

        runCoeff = RunCoefficient.objects.get(user_id=self.user_id)
        coefficient = 1
        if runCoeff.new_coeff:
            coefficient = runCoeff.new_coeff
        else:
            coefficient = runCoeff.default_coeff

        if self.status == "ACTIVE" or self.status == "DEALWITH":
            earn_pay = math.floor((average_pay * coefficient) * 100) / 100
            self.bonus += decimal.Decimal(earn_pay)
            self.save()
            try:
                rank = BonusRank.objects.filter(user_id=self.user_id)
                if rank:
                    BonusRank.objects.add_run(user_id=self.user_id, profit=decimal.Decimal(earn_pay))
                else:
                    BonusRank.objects.create(user_id=self.user_id, run=decimal.Decimal(earn_pay))
            except Exception as e:
                logger.info("用户的累计收益增加失败，失败原因{}".format(e))
            # 修改用户赚得的总金额
            UserInfo.objects.update_balance(user_id=self.user_id, pay_delta=decimal.Decimal(earn_pay))

            # 在settlement表中增加记录
            UserSettlement.objects.earn_profit(self.goal_id, decimal.Decimal(earn_pay))
            if self.status == "DEALWITH":
                self.status = "FAILED"
                self.save()

    def calc_pay_out(self):
        print("计算开始..........")
        pay_out = 0
        # 如果是日常模式
        if self.goal_type == 1:
            # 如果之前没有过不良记录, 则扣除保证金
            if self.none_punch_days == 0:
                pay_out = self.guaranty
                # 清除个人的保证金数额
                self.guaranty = 0
                # 增加不良记录天数
                self.none_punch_days = 1
            elif self.none_punch_days >= 1 and self.down_payment > 0:
                if self.guaranty == 0:
                    # 底金次数
                    pay_out = self.average
                # 如果有降低投入
                # 从账户中扣除金额
                self.down_payment -= pay_out
                # 不良天数记录+1
                self.none_punch_days += 1
        # 如果是自由模式
        else:
            if float(self.left_distance) > 0.0:
                # 剩余的距离
                left_distance = self.left_distance
                # 求解剩余距离
                if left_distance <= 1:
                    pay_out = self.guaranty
                    self.guaranty = 0
                else:
                    remain = math.floor(self.left_distance) - 1
                    if remain <= self.down_num:

                        pay_out = remain * self.average + self.guaranty
                        self.guaranty = 0

                        self.down_payment -= remain * self.average
                    else:
                        # remain = self.down_num

                        pay_out = self.down_payment + self.guaranty

                        self.guaranty = 0

                        self.down_payment = 0
            else:
                pay_out = 0
        if pay_out > 0:
            # 更新值
            self.save()
            # 把本次瓜分金额写入数据库记录中
            UserSettlement.objects.loose_pay(goal_id=self.goal_id, bonus=pay_out)
        # 完成所有瓜分金额的计算
        return pay_out

    def run_pay_out(self):
        try:
            pay_out = 0
            # 如果是日常模式
            if self.goal_type:
                if self.none_punch_days <= 3:
                    pay_out = 0
                elif self.none_punch_days == 4:
                    pay_out = self.guaranty
                    self.guaranty = 0
                elif self.none_punch_days >= 5 and self.down_payment > 0:
                    self.guaranty = 0
                    pay_out = self.average
                    self.down_payment -= pay_out
            # 进入自由模式
            else:
                if self.goal_day < 30:
                    if self.left_distance > 0:
                        pay_out = self.guaranty
                        self.guaranty = 0
                else:
                    # 此时就是无线模式
                    print("开始进入自由模式扣钱")
                    if self.left_distance > 0:
                        if self.guaranty > 0:
                            pay_out = self.guaranty
                            self.guaranty = 0
                        elif self.guaranty == 0 and self.down_payment > 0:
                            pay_out = self.average
                            self.down_payment -= pay_out
            self.save()
            if pay_out > 0:
                # 更新值
                # 把本次瓜分金额写入数据库记录中
                UserSettlement.objects.loose_pay(goal_id=self.goal_id, bonus=pay_out)
                print("瓜分记录写入成功")
            # 完成所有瓜分金额的计算

            return pay_out
        except Exception as e:
            print(e)

    def data_init(self):
        try:
            if self.get_remainder == True:
                self.none_punch_days = 0
                self.add_distance = 0
                self.left_distance = self.goal_distance
                self.finish_week_day = 0
                self.save()
                print("初始化成功")
            else:
                print("还没到初始化的时候")
                pass
        except Exception as e:
            logger.error(e)
            print("初始化失败")

    def check_run(self):
        try:
            pay_out = 0
            # 用户的系数不是从活动表里面取出来，现在是在
            coeff = RunCoefficient.objects.get(user_id=self.user_id)
            new_coeff = coeff.new_coeff
            # 只有处于活动状态的目标才会检查
            if self.status == "ACTIVE":
                # 如果是日常模式, 才会需要每天扣钱
                if self.goal_type:
                    if self.goal_day < 30:
                        print("进入日常模式，开始扣除金额，当前的活动类型是{}".format(self.goal_type))
                        # 查看前一天到今天是否存在打卡记录
                        if self.exist_punch_last_day():
                            # 如果存在打卡记录,则不付出钱
                            if self.left_day < 0:
                                print("日常模式的剩余天数小于零，说明活动结束")
                                if self.down_payment <= 0 and self.guaranty <= 0:
                                    self.status = "DEALWITH"
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
                                    print("该用户没有打卡也不是第一天，所以需要从扣钱，并且未打卡天数需要加一", self.user_id)
                                    pay_out = self.run_pay_out()
                                    self.none_punch_days += 1
                                    coeff.new_coeff = 0
                                    new_coeff = coeff.default_coeff
                                    print(pay_out, "若是日常模式且没有免签券，则扣除此金额")
                                if self.down_payment <= 0 and self.guaranty <= 0:
                                    self.status = "DEALWITH"
                                    print("押金保证金都小于0，表示失败")
                                # 检查目标是否已经算失败了, 在日常模式下如果两者均为0, 则判定目标失败
                                if self.left_day < 0:
                                    print("日常模式的剩余天数小于零，说明活动结束")
                                    if self.down_payment <= 0 and self.guaranty <= 0:
                                        self.status = "DEALWITH"
                                        print("押金保证金都小于0，表示失败")
                                    else:
                                        self.status = "SUCCESS"
                                        print("押金保证金都大于0，表示成功")
                    else:
                        print("进入日常模式的无限模式")
                        if self.exist_punch_last_day():
                            """查看前一天是否有打卡记录，若是有的话直接pass"""
                            pass
                        else:
                            if self.is_first_day == True:
                                print("今天是第一天，不做任何处理")
                                # 有返回值的时候是第一天，直接pass
                                pass
                            else:
                                """不是第一天"""
                                has_ticket = self.auto_use_ticket(ticket_type="NS")
                                if not has_ticket:
                                    pay_out = self.run_pay_out()
                                    # todo 当天系数清零
                                    coeff.new_coeff = 0
                                    new_coeff = coeff.default_coeff
                                    self.none_punch_days += 1
                                    print(pay_out, "若是日常模式且没有免签券，则扣除此金额")
                                if self.down_payment <= 0 and self.guaranty <= 0:
                                    self.status = "DEALWITH"
                                    print("押金保证金都小于0，表示失败")
                else:
                    print("进入自由模式，开始扣除金额，当前的活动类型是{}".format(self.goal_type))

                    # 如果是自由模式下，当left_day为负数时结算
                    if self.exist_punch_last_day():
                        """查看前一天是否有打卡记录，若是有的话直接pass"""
                        pass
                    else:
                        # 若是昨天没有打卡记录，则把信息数初始化成默认系数
                        coeff.new_coeff = coeff.default_coeff
                        new_coeff = coeff.default_coeff
                        self.none_punch_days += 1
                    if self.goal_day < 30:

                        # print("现在的left_day：{}自由模式下，当剩余天数小于零的时候开始结算".format(self.left_day))
                        # 将自由模式下的钱数结算
                        if self.left_day < 0:
                            if self.guaranty == 0:
                                self.status = "DEALWITH"
                            else:
                                self.status = "SUCCESS"
                        else:
                            pass
                        if self.get_remainder == True:
                            pay_out = self.run_pay_out()

                        print(pay_out, "用户{}自由模式下要扣除的金额数{}".format(self.user_id, pay_out))
                        # 如果付出的钱没有总金额多,算完成,否则算失败


                    else:
                        if self.get_remainder == True:
                            pay_out = self.run_pay_out()
                        print(pay_out, "用户{}自由模式下要扣除的金额数{}".format(self.user_id, pay_out))
                        # 如果付出的钱没有总金额多,算完成,否则算失败
                        if self.guaranty == 0 and self.down_payment == 0:
                            self.status = "DEALWITH"

                    # else:
                    #     if new_coeff <= 0:
                    #         new_coeff= coeff.default_coeff
                # 更新到数据库中
                self.data_init()
                self.save()
                coeff.save()
                UserInfo.objects.update_deposit(user_id=self.user_id, pay_delta=-pay_out)

                return pay_out, new_coeff
        except Exception as e:
            print(e)
            logger.error(e)
            return 0, 0

    """first_day_record"""

    @property
    def get_remainder(self):
        remainder = (timezone.now() - self.start_time).days
        remain = 1
        if self.start_time.strftime("%Y-%m-%d") == (timezone.now() - timedelta(days=1)).strftime("%Y-%m-%d"):
            pass
        else:
            if self.first_day_record == True:
                remain = remainder % 7
            else:
                remain = (remainder - 1) % 7
        print(remain, "remain", remainder, "remainder")
        if remain == 0:
            return True
        else:
            return False

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
    def create_run_redord(self, goal, user_id, voucher_ref, voucher_store, distance, record_time, document):
        print("开始打卡")
        try:
            # run_obj = RunningGoal.objects.get(goal_id=goal.goal_id)
            if goal.goal_type:
                print("若是日常模式", distance, goal.kilos_day)
                if distance >= goal.kilos_day:
                    # 若是距离大于每日距离，求出超出的距离数量
                    goal.finish_week_day += 1
                    if goal.finish_week_day >= 7:
                        goal.finish_week_day = 7
                    goal.left_distance -= distance
                    goal.week_distance += distance
                    goal.add_distance += distance
                    beyond_distance = math.floor(distance - goal.kilos_day)
                    if beyond_distance >= 5:
                        beyond_distance = 5
                    RunCoefficient.objects.update_daily(user_id=user_id, beyond_distance=beyond_distance,
                                                        finish_week_day=goal.finish_week_day)

                    goal.save()
                else:
                    print("打卡距离没有超过自己的每日距离，所以没有系数加成，新系数等于默认系数")
                    RunCoefficient.objects.defaultTonew(user_id=user_id, goal_id=goal.goal_id)
            else:
                '''进入自由模式'''
                # 先将距离加进表里面的累计距离跟周距离
                print("开始进入自由模式")
                goal.add_distance += distance
                goal.left_distance -= distance
                goal.week_distance += distance
                goal.finish_week_day += 1
                goal.save()
                print("累计距离增加成功")
                # 若是累计的周距离大于目标距离,求出超出了多少距离

                print("若是现在累计距离已经大于自己的目标距离，则根据超出的距离数生成新系数")
                beyond_distance = math.floor(goal.add_distance - goal.goal_distance)
                print("beyond_distance", beyond_distance)
                if beyond_distance >= 5:
                    beyond_distance = 5
                RunCoefficient.objects.update_freedom(user_id=user_id, beyond_distance=beyond_distance)

            print("即将创建打卡记录")
            record = self.create(
                goal_id=goal.goal_id,
                voucher_ref=voucher_ref,
                voucher_store=voucher_store,
                distance=distance,
                record_time=record_time,
                document=document
            )
            return record
        except Exception as e:
            logger.error(e)
            print(e)
            return None

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

    def get_some_message(self, user_id):
        user = UserInfo.objects.get(user_id=user_id)
        return user


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
    def save_finish(self, goal_id):
        print("打印一下用户的id，看看是不是自己的", goal_id)
        goal = RunningGoal.objects.filter(goal_id=goal_id)
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
                "goal_distance": goal.goal_distance,
                "kilos_day": goal.kilos_day,
                "left_distance": goal.left_distance,
                "reality_price": goal.reality_price,
                "deserve_price": goal.deserve_price,
                "down_num": goal.down_num,
                "activate_deposit": goal.activate_deposit,
                "average": goal.average,
                "add_distance": goal.add_distance,
                "extra_earn": goal.extra_earn,
                "punch_day": goal.punch_day,
                "settle_time": timezone.now().strftime("%Y-%m-%d")
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


class Running_Finish_Save(models.Model):
    id = models.IntegerField(primary_key=True, auto_created=True)
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
    goal_id = models.CharField(max_length=255, null=True)
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


class RunReply(models.Model):
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
        db_table = "on_runreply"


class RunCoefficientManager(models.Manager):
    # todo
    # 自由模式更新系数，beyond_distance：比基础目标多余的距离
    def update_freedom(self, beyond_distance, user_id):
        """每次自由模式打卡时候调用此函数，获取用户输入的距离，获取用户之前的累计距离"""
        try:
            user = self.filter(user_id=user_id)
            if user:
                user = user[0]
            if beyond_distance <= 0:
                user.new_coeff = decimal.Decimal(user.default_coeff)
            elif beyond_distance <= 5 and beyond_distance > 0:
                user.new_coeff = decimal.Decimal(user.default_coeff) * decimal.Decimal(
                    "1.{}".format(int(beyond_distance)))
            else:
                user.new_coeff = decimal.Decimal(user.default_coeff) * decimal.Decimal("1.{}".format(5))
            user.save()
            return user.new_coeff
        except Exception as e:
            logger.error(e)
            print(e)

    # 更新日常模式的每日悉数加成
    def update_daily(self, user_id, beyond_distance, finish_week_day):
        user = self.filter(user_id=user_id)
        try:
            default = 1
            if user:
                user = user[0]
                default = user.default_coeff
            # 若是超出的距离大于5
            if finish_week_day <= 4:
                if beyond_distance <= 0:
                    user.new_coeff = default
                else:
                    user.new_coeff = default * decimal.Decimal("1.{}".format(beyond_distance))

                user.save()
                return user.new_coeff
            else:
                extra_day = finish_week_day - 4

                if extra_day > 3:
                    extra_day = 3
                if beyond_distance <= 0:
                    user.new_coeff = default
                else:
                    user.new_coeff = default * decimal.Decimal(
                        "1.{}".format(beyond_distance + extra_day))
                user.save()
                return user.new_coeff

        except Exception as e:
            logger.error(e)
            print(e)

    # 由于用户没有打卡，或者是用户打卡的距离不符合要求，此时用户的新系数等于默认系数
    def defaultTonew(self, user_id, goal_id):
        user = self.filter(user_id=user_id)
        try:
            if user:
                user = user[0]
                user.new_coeff = user.default_coeff
                user.save()
        except Exception as e:
            logger.error(e)


class RunCoefficient(models.Model):
    # 用户id
    user_id = models.IntegerField(null=False, primary_key=True)
    # 用户的默认系数
    default_coeff = models.DecimalField(max_digits=12, decimal_places=2, null=False, default=1)
    # 当用户打卡之后生成的新系数
    new_coeff = models.DecimalField(max_digits=12, decimal_places=2, null=False, default=0)
    SLEEP_TYPE = (
        (0, "自由"),
        (1, '日常')
    )
    goal_type = models.SmallIntegerField(null=False, choices=SLEEP_TYPE, default=0)
    objects = RunCoefficientManager()

    class Meta:
        db_table = "on_runcoefficient"
