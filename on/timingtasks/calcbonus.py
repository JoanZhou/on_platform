from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import math
from on.models import Goal, Activity, ReadingGoal, RunningGoal, SleepingGoal, RunningPunchRecord, SleepingPunchRecord
import logging
import decimal
from on.user import UserInfo
import django.utils.timezone as timezone
import time
from on.settings.local import DEBUG
from django.views.decorators.csrf import csrf_exempt

# 不参与用户钱数瓜分的活动
NO_PAY_ACTIVITY = [ReadingGoal.__name__]

sched = BackgroundScheduler()

app_logger = logging.getLogger('app')


#
# # 获取Goal的所有参与分成计算的子模型##
# def get_participate_models(model):
#     all_sub_models = {}
#     for sub_model in model.__subclasses__():
#         if not sub_model.__name__ in NO_PAY_ACTIVITY:
#             all_sub_models[sub_model.__name__] = sub_model
#     return all_sub_models


# 初始化活动定时任务

# 清空用户的今日收益值
def clear_user_bonus_job():
    print("Begin to Clear")
    for user in UserInfo.objects.all():
        user.today_profit = 0
        user.save()


# # 定时检查读书目标是否已经失败
# def timing_reading_settlement():
#     for goal in ReadingGoal.objects.filter(status="ACTIVE"):
#         goal.check_punch()


# 测试接口
# def test_calculate(request):
#     if settings.DEBUG:
#         calc_bonus_job(SleepingGoal)
#         calc_bonus_job(RunningGoal)
#     else:
#         pass
#     return HttpResponse({'status': 200})


# 任务函数
def calc_bonus_job():
    print("Begin to calculate")

    time.sleep(1)
    app_logger.warning("跑步活动开始执行处理")
    # 计算goal_class的收益值
    all_pay = 0
    all_coffe = 0
    # 只有处于活动状态的目标才参与计算
    print(timezone.now())
    for goal in RunningGoal.objects.filter(status="ACTIVE"):
        print("开始计算需要每日金额分配")
        if DEBUG:
            pay, coffe = goal.check_run()
            print("------------+-------------------+--------------------------")
        else:
            pay, coffe = goal.check_run()
        print(pay, "需要被瓜分的金额")
        print(coffe, "每个人的系数")
        # 计算谁需要贡献出奖金分给其他人
        if pay != 0:
            app_logger.info("User:{0} Pay:{1:.2f} Goal:{2}".format(goal.user_id, pay, goal.goal_id))
        all_pay += decimal.Decimal(pay)

        all_coffe += coffe
    app_logger.info("本次扣除的总金{}，总系数{}".format(all_pay,all_coffe))
    time.sleep(1)
    if all_pay > 0 and all_coffe > 0:
        print("判断瓜分金额跟总系数是否大大于零")
        average_pay = math.floor(
            decimal.Decimal(100) * (decimal.Decimal(0.996) * all_pay / all_coffe)) * decimal.Decimal(0.01)
        print("平均分配的金额数{}".format(average_pay))
        # 为该种活动类别下的用户分发奖金
        app_logger.info(
            "Profit:{0:.2f} Coffe:{1:.2f} Average:{3:.2f}".format(all_pay, all_coffe, "跑步活动", average_pay))
        for goal in RunningGoal.objects.all():
            print("给每个人分配金额:{}".format(decimal.Decimal(average_pay)))

            goal.earn_run_profit(decimal.Decimal(average_pay))
    else:
        print("此时，没有用户失败，都不需要付出金钱")
        # 重巡出当日打过卡的用户,首先要查询出所有正在参与的用户
        try:
            run_user = RunningGoal.objects.filter(status="ACTIVE")
            for goal in run_user:
                # 其次是要找出今天打了卡的用户
                run = RunningPunchRecord.objects.filter(goal_id=goal.goal_id)
                if run and run[0].record_time.strftime("%Y-%m-%d") == timezone.now().strftime("%Y-%m-%d"):
                    user_run = RunningGoal.objects.get(goal_id=goal.goal_id)
                    # 找出打了卡的用户的user_id跟系数
                    user = UserInfo.objects.get(user_id=user_run.user_id)
                    # 将用户的额外收益加上用户的系数乘以0.01
                    goal.extra_earn += user_run.coefficient * decimal.Decimal(0.01)
                    user.extra_money += user_run.coefficient * decimal.Decimal(0.01)
                    goal.save()
                    user.save()
                    print("给用户分配额外收益成功")
        except Exception as e:
            print("没有用户失败的情况下，给用户分配额外收益失败", e)
        # 查询擂主的目前押金
    # 更新活动的奖金池
    try:
        Activity.objects.update_bonus(RunningGoal.get_activity(), -all_pay)
        print("开始更新奖金池")
    except Exception:
        pass
    app_logger.warning("Activity {0} end ... calcbonus.py -> calc_bonus_job ".format("跑步活动"))
    # 结束当前活动


# 处理睡眠活动的金额与系数，分配方式发生改变
def sleep_handle():
    from on.activities.sleeping.models import Coefficient
    print("开始处理睡眠活动的金额系数分配，处理时间是早上八点之后")
    goal_list = SleepingGoal.objects.filter(status="ACTIVE")
    all_pay = 0
    all_coeff = 0
    all_body_coeff = 0
    for goal in goal_list:
        time.sleep(2)
        pay, new_coeff = goal.check_sleep()
        # 若是需要分配出去的金额不等于零
        if pay != 0:
            app_logger.info("User:{0}在作息活动中 Pay:{1:.2f} Goal:{2}".format(goal.user_id, pay, goal.goal_id))
        all_pay += decimal.Decimal(pay)
        all_coeff += new_coeff

        """获取所有用户的系数的和"""
        coeff_obj = Coefficient.objects.get(user_id=goal.user_id)
        all_body_coeff += coeff_obj.default_coeff
    if all_pay > 0 and all_coeff > 0:
        print('当前参与用户的总系数', all_coeff)
        average_pay = math.floor(
            decimal.Decimal(100) * (decimal.Decimal(0.996) * all_pay / decimal.Decimal(all_coeff))) * decimal.Decimal(
            0.01)
        print("平均分配的金额数{}".format(average_pay))
        # 为该种活动类别下的用户分发奖金
        time.sleep(2)
        for goal in SleepingGoal.objects.all():
            goal.earn_profit_sleep(decimal.Decimal(average_pay))
    else:
        try:
            for goal in goal_list:
                # 走到这里说名所有人的付出金额的和跟系数和都为零，所有参与用户都是打了卡的
                goal.update_all_finaly()
                print("给用户分配额外收益成功，用户现在的额外收益是{}".format(goal.extra_earn))
        except Exception as e:
            print("没有用户失败的情况下，给用户分配额外收益失败", e)

    try:
        Activity.objects.update_bonus("0", -all_pay)
        print("开始更新奖金池")
    except Exception as e:
        print(e)

def update_extra_earn_everyday():
    from on.activities.sleeping.models import Coefficient
    try:
        print("处理时间是早上8.30点之后")
        goal_list = SleepingGoal.objects.filter(status="ACTIVE")
        all_body_coeff = 0
        for goal in goal_list:
            coeff_obj = Coefficient.objects.get(user_id=goal.user_id)
            all_body_coeff += coeff_obj.default_coeff
        if all_body_coeff > 0:
            every_day_pay = math.floor(
                decimal.Decimal(100) * decimal.Decimal(10) / decimal.Decimal(all_body_coeff)) * decimal.Decimal(0.01)
            for goal in SleepingGoal.objects.all():
                goal.extra_earn_today(decimal.Decimal(every_day_pay))
                """将用户平均金额分配给每个用户"""
    except Exception as e:
        print(e)



def init_sleep_coeff():
    from on.activities.sleeping.models import Coefficient
    Coefficient.objects.all().update(new_coeff=0)
    try:
        goal_list = SleepingGoal.objects.filter(status="ACTIVE")
        for goal in goal_list:
            goal.update_default_coeff()
    except Exception as e:
        app_logger.error(e)
        print(e)
#init_run_coeff
def init_run_coeff():
    from on.activities.running.models import RunCoefficient
    RunCoefficient.objects.all().update(new_coeff=0)
    try:
        goal_list = RunningGoal.objects.filter(status="ACTIVE")
        for goal in goal_list:
            goal.update_default_run_coeff()
    except Exception as e:
        app_logger.error(e)
        print(e)

# 为活动做准备
# 跑步活动
sched.add_job(calc_bonus_job, 'cron', day_of_week='0-6',
              hour=0,
              minute=5,
              timezone=pytz.timezone('Asia/Shanghai'),
              )
# 清空收益
sched.add_job(clear_user_bonus_job, 'cron',
              day_of_week='0-6',
              hour=0,
              minute=0,
              timezone=pytz.timezone('Asia/Shanghai'))
#
# sched.add_job(timing_reading_settlement, 'cron',
#               day_of_week='0-6',
#               hour=0,
#               minute=1,
#               timezone=pytz.timezone('Asia/Shanghai'))
# 作息活动
sched.add_job(sleep_handle, 'cron',
              day_of_week='0-6',
              hour=8,
              minute=0,
              timezone=pytz.timezone('Asia/Shanghai'))
sched.add_job(init_sleep_coeff, 'cron',
              day_of_week='0-6',
              hour=21,
              minute=0,
              timezone=pytz.timezone('Asia/Shanghai'))
sched.add_job(init_run_coeff, 'cron',
              day_of_week='0-6',
              hour=1,
              minute=30,
              timezone=pytz.timezone('Asia/Shanghai'))
sched.add_job(update_extra_earn_everyday, 'cron',
              day_of_week='0-6',
              hour=8,
              minute=30,
              timezone=pytz.timezone('Asia/Shanghai'))
sched.start()
