from django.db import models
import uuid
from on.activities.base import Goal, Activity
import django.utils.timezone as timezone
from datetime import datetime, timedelta
from on.user import UserTicket, UserRecord, UserInfo, UserTicketUseage
import logging
import random
from django.conf import settings

logger = logging.getLogger("app")


class SleepingGoalManager(models.Manager):
    # 创建一个新的goal
    def create_goal(self, user_id, guaranty, down_payment, coefficient, mode, goal_day, nosign, delay, getuptime):
        if settings.DEBUG:
            start_time = timezone.now() + timedelta(-1)
        else:
            start_time = datetime.strptime("2018-01-01 00:00:01", "%Y-%m-%d %H:%M:%S")
        getuptime_dump = datetime.strptime(getuptime, "%H:%M").time()
        goal = self.filter(user_id=user_id).filter(start_time=start_time).filter(status="PENDING")
        if goal:
            goal.first().delete()
        goal = self.create(user_id=user_id,
                           activity_type=SleepingGoal.get_activity(),
                           start_time=start_time,
                           goal_day=goal_day,
                           mode=mode,
                           guaranty=guaranty,
                           down_payment=down_payment,
                           coefficient=coefficient,
                           goal_type=1,
                           getup_time=getuptime_dump,
                           )
        # 更新活动的免签卡券
        nosgin_number = int(nosign)
        delay_number = int(delay)
        UserTicket.objects.create_ticket(goal.goal_id, "NS", nosgin_number)
        UserTicket.objects.create_ticket(goal.goal_id, "D", delay_number)
        return goal

    # 删除一个目标
    def delete_goal(self, goal_id):
        goal = self.get(goal_id=goal_id)
        # 删除本目标对应的所有打卡记录
        goal.punch.all().delete()
        # 删除本目标
        goal.delete()


class SleepingGoal(Goal):
    """ Model for running goal
        User needs to set running duration days and distance as
        objective
    """
    # 目标起床时间
    getup_time = models.TimeField(null=False)
    objects = SleepingGoalManager()

    def auto_use_ticket(self, ticket_type):
        # 如果不存在打卡记录,则使用券。起床打卡应该是为今天使用券，因为确认是否免签所用的时间都是今天
        has_ticket = UserTicket.objects.use_ticket(goal_id=self.goal_id, ticket_type="NS",
                                                   use_time=timezone.now())
        return has_ticket

    def calc_pay_out(self):
        pay_out = 0
        # 如果是自律模式且之前没有过不良记录, 则扣除保证金
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
        # 更新值
        self.save()
        # 完成所有瓜分金额的计算
        return pay_out

    def use_no_sign_in_date(self, daydelta):
        today = (timezone.now() + timedelta(days=daydelta) + timedelta(hours=8)).date()
        end = today + timedelta(days=1)
        use_history = UserTicketUseage.objects.filter(useage_time__range=(today, end), goal_id=self.goal_id, ticket_type='NS')
        if use_history:
            return True
        else:
            return False

    def use_delay_date(self, daydelta):
        today = (timezone.now() + timedelta(days=daydelta) + timedelta(hours=8)).date()
        end = today + timedelta(days=1)
        use_history = UserTicketUseage.objects.filter(useage_time__range=(today, end), goal_id=self.goal_id, ticket_type='D')
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
        Activity.objects.add_bonus_coeff(SleepingGoal.get_activity(), self.guaranty + self.down_payment, self.coefficient)
        # 增加用户的累计参加次数
        UserRecord.objects.update_join(user=UserInfo.objects.get(user_id=user_id), coeff=self.coefficient)

    def update_activity_person(self):
        Activity.objects.update_person(SleepingGoal.get_activity())
        Activity.objects.update_coeff(SleepingGoal.get_activity(), -self.coefficient)

    @property
    def past_day(self):
        past = ((timezone.now()+timedelta(hours=8)).date() - self.start_time.date()).days + 1
        if past < 0:
            past = 0
        return past

    # 把left_day从模型字段改成属性，是为了保持同步与一致性
    @property
    def left_day(self):
        return self.goal_day - self.past_day


class SleepingPunchRecordManager(models.Manager):

    # 创建一个新的打卡记录，首先是从睡觉开始的
    def create_sleep_record(self, goal):
        # 首先要判断现在的时间是处于合法打卡时间内的
        try:
            if not settings.DEBUG:
                time_now = timezone.now().time()
                assert time_now.hour < 24
                assert time_now.hour >= 21
            record = self.create(goal=goal)
            return record
        except AssertionError:
            logger.error("Goal:{0} Sleep time out of limit:{1}".format(goal.goal_id, timezone.now()))
            return None

    # 早上起床，只能通过 goal.punch.update_getup_record来调用
    def update_getup_record(self):
        try:
            time_now = timezone.now().time()
            # 这里判断的还不够强烈
            if not settings.DEBUG:
                assert time_now.hour >= 5
            # 获取昨日的睡眠的记录
            today = timezone.now().date() + timedelta(days=1)
            lastday = today - timedelta(days=1)
            # 寻找睡眠时间在昨日的记录
            record = self.filter(before_sleep_time__range=(lastday, today))
            # 如果不为空，则说明昨晚睡觉的时候打过卡了
            if record:
                # 修改记录里的起床时间
                record = record[0]
                # 判断现在的时间是否早于当时设定的时间
                is_delay = record.goal.use_delay_date(0)
                if not settings.DEBUG:
                    if is_delay:
                        assert time_now <= record.goal.getup_time + timedelta(hours=1)
                    else:
                        assert time_now <= record.goal.getup_time
                record.get_up_time = timezone.now()
                # 以一定概率给出新的检查时间
                sleep_time_delta = record.get_up_time - record.before_sleep_time
                last_hours = sleep_time_delta.seconds // 3600
                # 12点打卡时间对象
                check_twleve = datetime.combine(datetime.now().date(), datetime.min.time()) + timedelta(hours=12)
                if is_delay:
                    # 如果在今天使用过延时卡，则必然半小时后确认
                    record.check_time = record.get_up_time + timedelta(hours=0.5)
                elif last_hours < 6:
                    # 如果睡眠时长小于6小时，则100% 12点打卡
                    record.check_time = check_twleve
                elif last_hours < 7:
                    # 如果睡眠时长小于7小时，则50% 不打卡，50% 12点
                    num =random.randint(1, 2)
                    if num == 1:
                        record.check_time = check_twleve
                    else:
                        record.check_time = timezone.now()
                        record.confirm_time = timezone.now()
                elif last_hours < 9:
                    num = random.randint(1, 100)
                    if num <= 80:
                        # 80% 无需再打卡，直接确认
                        record.check_time = timezone.now()
                        record.confirm_time = timezone.now()
                    elif num <= 83:
                        # 3% 起床后 12点打卡
                        record.check_time = check_twleve
                    else:
                        # 17% 起床后 半小时打卡
                        record.check_time = record.get_up_time + timedelta(hours=0.5)
                else:
                    num = random.randint(1, 10)
                    if num <= 9:
                        # 90% 无需再打卡，直接确认
                        record.check_time = timezone.now()
                        record.confirm_time = timezone.now()
                    else:
                        # 10% 起床后半小时仍需要打卡
                        record.check_time = record.get_up_time + timedelta(hours=0.5)
                # 记录保存到数据库，生效
                record.save()
                return record
            else:
                # 说明昨晚睡前没有打卡，以失败论处。
                return None
        except AssertionError:
            return None

    # 更新早上起床后的检查时间
    def update_confirm_time(self):
        try:
            time_now = timezone.now()
            # 获取今早起床的记录
            today = timezone.now().date()
            tomorrow = today + timedelta(days=1)
            record = self.filter(get_up_time__range=(today, tomorrow))
            if record:
                record = record[0]
                # 既然用户已经确定了，那就没必要继续找了
                if record.confirm_time:
                    return None
                check_time = record.check_time
                # 现在的时间要满足一定条件
                assert time_now >= check_time
                assert time_now <= check_time + timedelta(minutes=15)
                # 如果满足，记录最后一次打卡的时间即可
                record.confirm_time = time_now
                record.save()
            else:
                return None
        except AssertionError:
            return None

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
    # 外键ID,标识对应目标
    goal = models.ForeignKey(SleepingGoal, related_name="punch", on_delete=models.PROTECT)
    # 确认记录的时间
    confirm_time = models.DateTimeField(null=True)
    # 用户实际的睡前打卡时间
    before_sleep_time = models.DateTimeField(null=False, default=timezone.now)
    # 用户实际的起床打卡时间
    get_up_time = models.DateTimeField(null=True)
    # 用户起床后，根据起床时间随机生成的确认记录打卡的时间
    check_time = models.DateTimeField(null=True)
    # 由于本打卡记录判断失败与成功的状态过于复杂，所以采用独立字段判断
    # 第一次打卡时应该是前一天的晚上，当用户打卡睡觉了之后就插入该记录
    is_success = models.BooleanField(null=False, default=True)
    objects = SleepingPunchRecordManager()