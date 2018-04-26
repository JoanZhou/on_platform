from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import math
from on.models import Goal, Activity, ReadingGoal, RunningGoal, SleepingGoal,RunningPunchRecord
import logging
import decimal
from on.user import UserInfo
from django.http import HttpResponse
from django.conf import settings
import django.utils.timezone as timezone
import time

# 不参与用户钱数瓜分的活动
NO_PAY_ACTIVITY = [ReadingGoal.__name__]

sched = BackgroundScheduler()

app_logger = logging.getLogger('app')


# 获取Goal的所有参与分成计算的子模型
def get_participate_models(model):
    all_sub_models = {}
    for sub_model in model.__subclasses__():
        if not sub_model.__name__ in NO_PAY_ACTIVITY:
            all_sub_models[sub_model.__name__] = sub_model
    return all_sub_models


# 初始化活动定时任务
def init_jobs():
    sub_models = get_participate_models(Goal)
    for sub_model_key in sub_models:
        goal_class = sub_models[sub_model_key]
        # start_time = goal_class.get_start_date()
        # sched.add_job(calc_bonus_job, 'cron', day_of_week='0-6',
        #               hour=start_time.hour,
        #               minute=start_time.minute,
        #               timezone=pytz.timezone('Asia/Shanghai'),
        #               args=[goal_class])
        sched.add_job(calc_bonus_job, 'cron', day_of_week='0-6',
                      hour=20,
                      minute=1,
                      timezone=pytz.timezone('Asia/Shanghai'),
                      args=[goal_class])


# 清空用户的今日收益值
def clear_user_bonus_job():
    print("Begin to Clear")
    for user in UserInfo.objects.all():
        user.today_profit = 0
        user.save()


# 定时检查读书目标是否已经失败
def timing_reading_settlement():
    for goal in ReadingGoal.objects.filter(status="ACTIVE"):
        goal.check_punch()


# 测试接口
def test_calculate(request):
    if settings.DEBUG:
        calc_bonus_job(SleepingGoal)
        calc_bonus_job(RunningGoal)
    else:
        pass
    return HttpResponse({'status': 200})


# 任务函数
def calc_bonus_job(goal_class):
    print("Begin to calculate")

    time.sleep(1)
    app_logger.warning("Activity {0} start ... calcbonus.py -> calc_bonus_job ".format(goal_class.__name__))
    # 计算goal_class的收益值
    all_pay = 0
    all_coffe = 0
    # 只有处于活动状态的目标才参与计算
    print(timezone.now())
    for goal in goal_class.objects.filter(status="ACTIVE"):
        time.sleep(1)
        print("开始计算需要每日金额分配")
        pay, coffe = goal.check_punch()
        print(pay,"需要被瓜分的金额")
        print(coffe,"每个人的系数")
        # 计算谁需要贡献出奖金分给其他人
        if pay != 0:
            app_logger.info("User:{0} Pay:{1:.2f} Goal:{2}".format(goal.user_id, pay, goal.goal_id))
        all_pay += decimal.Decimal(pay)
        print("计算出的所有瓜分出去的金额{}".format(all_pay))
        all_coffe += coffe
        print(coffe,"总系数")
    if all_pay > 0 and all_coffe > 0:
        print("判断瓜分金额跟总系数是否大大于零")
        average_pay = math.floor(
            decimal.Decimal(100) * (decimal.Decimal(0.996) * all_pay / all_coffe)) * decimal.Decimal(0.01)
        print("平均分配的金额数{}".format(average_pay))
        # 为该种活动类别下的用户分发奖金
        app_logger.info(
            "Profit:{0:.2f} Coffe:{1:.2f} Average:{3:.2f}".format(all_pay, all_coffe, goal_class.__name__, average_pay))
        for goal in goal_class.objects.all():
            print("给每个人分配金额:{}".format(decimal.Decimal(average_pay)))
            goal.earn_profit(decimal.Decimal(average_pay))
        #查询擂主的目前押金
    # 更新活动的奖金池
    try:
        Activity.objects.update_bonus(goal_class.get_activity(), -all_pay)
        print("开始更新奖金池")
    except Exception:
        pass
    app_logger.warning("Activity {0} end ... calcbonus.py -> calc_bonus_job ".format(goal_class.__name__))
    #结束当前活动

# 为活动做准备
init_jobs()
sched.add_job(clear_user_bonus_job, 'cron',
              day_of_week='0-6',
              hour=0,
              minute=0,
              timezone=pytz.timezone('Asia/Shanghai'))
sched.add_job(timing_reading_settlement, 'cron',
              day_of_week='0-6',
              hour=0,
              minute=1,
              timezone=pytz.timezone('Asia/Shanghai'))
sched.start()
