# import logging

from django.http import JsonResponse, HttpResponseNotFound
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import decimal
from on.activities.reading.views import show_reading_goal
from on.activities.running.views import show_running_goal
from on.activities.sleeping.views import show_sleeping_goal
from on.activities.riding.views import show_riding_goal

from .riding.model import RidingGoal
from on.activities.walking.views import show_walking_goal
from on.models import Activity, Goal, RunningGoal, SleepingGoal, ReadingGoal, RunningPunchRecord, ReadingPunchRecord, \
    SleepingPunchRecord
from on.activities.walking.models import WalkingGoal, WalkingManager
from on.activities.running.models import Running_Finish_Save, RunCoefficient
from on.activities.reading.models import Read_Finish_Save
from on.activities.sleeping.models import Coefficient, Sleep_Finish_Save
from on.activities.riding.model import RidingCoefficient, Riding_Finish_Save
from on.user import UserInfo, UserRecord, FoolsDay, UserInvite, UserOrder, UserAddress
from on.views import oauth
from on.temp.push_template import do_push
from on.wechatconfig import get_wechat_config
from datetime import timedelta, date, datetime
import django.utils.timezone as timezone
from on.errorviews import page_not_found
from on.settings.local import DEBUG
import logging

goal_mapping = {
    RunningGoal.get_activity(): show_running_goal,
    SleepingGoal.get_activity(): show_sleeping_goal,
    ReadingGoal.get_activity(): show_reading_goal,
    RidingGoal.get_activity(): show_riding_goal,
    WalkingGoal.get_activity(): show_walking_goal,

}

"""
每天凌晨遍历每个goal，检查该目标下的打卡记录是否完整；
首先设立一个字典，用于更新每个目标拿到的扣除的钱。

对于每个目标而言，
（日常模式）如果昨日的打卡完成了，则更新一下目标的进度
（日常模式）如果昨日的打卡未完成
    若用户目标下有对应的免签券，则自动使用；
    否则将数据库中的打卡时间设置为前一天晚上10点，
"""


# logger = logging.getLogger("app")


# 展示用户的目标列表
@oauth
def show_goals(request):
    user = request.session['user']
    sub_models = get_son_models(Goal)
    all_goals = []
    status = True
    for sub_model_key in sub_models:
        all_goals += sub_models[sub_model_key].objects.filter(user_id=user.user_id)

    payed_goals = [goal for goal in all_goals if goal.status != 'PENDING']
    if payed_goals == []:
        status = False
    run = RunningGoal.objects.filter(user_id=user.user_id)
    first_day_record = 0

    if run and run[0].status != 'PENDING':
        a = run[0].start_time.strftime("%Y-%m-%d")
        user_end_time = (run[0].start_time + timedelta(days=1)).strftime("%Y-%m-%d")
        punch = RunningPunchRecord.objects.filter(goal_id=run[0].goal_id, record_time__range=(a, user_end_time))
        first_day_record = 1 if len(punch) > 0 else 0
    return render(request, 'goal/index.html',
                  {'goals': payed_goals, "status": status, "first_day_record": first_day_record})


# return render(request, 'goal/index.html',{'goals': payed_goals, "status": status})


# 获取某个模型的所有子模型
def get_son_models(model):
    all_sub_models = {}
    for sub_model in model.__subclasses__():
        all_sub_models[sub_model.__name__] = sub_model
    return all_sub_models


# 展示某个特定的目标
@oauth
def show_specific_goal(request, pk):
    goal_type = request.GET.get('activity_type')
    return goal_mapping[goal_type](request, pk)


# 展示特殊娱乐活动页面
@oauth
def show_activity(request):
    pass


# 展示分享页
@oauth
def show_goal_share(request, pk):
    user = request.session['user']
    wechat_config = get_wechat_config(request)
    sub_models = get_son_models(Goal)
    goal = None
    for sub_model_key in sub_models:
        query = sub_models[sub_model_key].objects.filter(user_id=user.user_id).filter(goal_id=pk)
        if query:
            goal = query[0]
            break
    if goal:
        # 跑步自由模式
        if goal.activity_type == RunningGoal.get_activity() and goal.goal_type == 0:
            if goal.goal_type:
                if goal.goal_day > 30:
                    goal_intro = "每天跑步{}公里".format(goal.goal_distance)
                else:
                    goal_intro = "在{}天内每天跑步{}公里".format(goal.goal_day, goal.goal_distance)
            # 睡眠
            else:
                if goal.goal_day > 30:
                    goal_intro = "每周累计跑步{}公里".format(goal.goal_distance)
                else:
                    goal_intro = "在{}天内每周跑步{}公里".format(goal.goal_day, goal.goal_distance)
        elif goal.activity_type == RunningGoal.get_activity():
            goal_intro = "在{0}天内每天跑步{1}km".format(goal.goal_day, goal.kilos_day)
        elif goal.activity_type == ReadingGoal.get_activity():
            goal_intro = "在30天内阅读完书籍《{0}》".format(goal.book_name)
        elif goal.activity_type == SleepingGoal.get_activity():
            # 早起
            if goal.sleep_type:
                if goal.goal_day > 30:
                    goal_intro = "每天早上八点前起床"
                else:
                    goal_intro = "在{}天内连续早上八点前起床".format(goal.goal_day)
            # 睡眠
            else:
                if goal.goal_day > 30:
                    goal_intro = "每天睡前早起连续打卡"
                else:
                    goal_intro = "在{0}天内睡前早起连续打卡".format(goal.goal_day)

        else:
            goal_intro = ""
        return render(request,
                      'goal/share.html',
                      {
                          "WechatJSConfig": wechat_config,
                          "goal_intro": goal_intro,
                          "activity": goal.activity_type
                      })
    else:
        return HttpResponseNotFound


"""
# 展示目标结束页面，可能是失败也可能是成功
def show_goal_finish(request, pk):
    user = request.session['user']
    sub_models = get_son_models(Goal)
    goals = []
    for sub_model_key in sub_models:
        goals += sub_models[sub_model_key].objects.filter(goal_id=pk).filter(user_id=user.user_id)
    return render(request, "goal/finish.html")
"""


def finish_tem(openid, url, activate, finish_time, earn_money, earn_time, balance):
    data = {
        "touser": openid,
        "template_id": "AGL7ztiilHdjd4-5UDIscJOMlUdUGWr2gXvRJiy_ulQ",
        "url": url,
        "topcolor": "#FF0000",
        "data": {
            "first": {
                "value": "您好，有一笔活动收入结算成功",
                "color": "#173177"
            },
            "keyword1": {
                "value": activate,
                "color": "#173177"
            },
            "keyword2": {
                "value": finish_time,
                "color": "#173177"
            },
            "keyword3": {
                "value": earn_money,
                "color": "#173177"
            },
            "keyword4": {
                "value": earn_time,
                "color": "#173177"
            },
            "keyword5": {
                "value": balance,
                "color": "#173177"
            },
            "remark": {
                "value": "点击详情，查看个人中心",
                "color": "#173177"
            },
        }
    }
    return data


# # 结束目标任务
# def delete_goal(request):
#     try:
#         user = request.session['user']
#         if request.method == "POST":
#             # 删除当前的目标活动并退还钱
#             activity_type = request.POST['goal_type']
#             goal_id = request.POST['goal']
#             delete_map = {
#                 RunningGoal.get_activity(): RunningGoal,
#                 ReadingGoal.get_activity(): ReadingGoal,
#                 SleepingGoal.get_activity(): SleepingGoal
#             }
#
#             if activity_type == "1":
#                 goal = RunningGoal.objects.get(goal_id=goal_id)
#                 # 增加用户的完成次数
#                 UserRecord.objects.finish_goal(user=user)
#                 # 用户触发，如果挑战成功则删除目标，退还押金
#                 # 判断用户是否挑战成功
#                 Run = RunningGoal.objects.get(user_id=user.user_id)
#                 # 更新用户的押金
#                 UserInfo.objects.update_deposit(user_id=user.user_id,
#                                                 pay_delta=-(goal.guaranty + goal.down_payment))
#                 # 更新目前的奖金池
#                 try:
#                     obj = Activity.objects.get(activity_type=goal.activity_type)
#                     obj.bonus_all -= (goal.guaranty + goal.down_payment)
#                     obj.active_participants -= 1
#                     obj.coefficient -= Run.coefficient
#                     obj.save()
#                 except Exception as e:
#                     print(e)
#
#                 # 获取邀请了多少好友
#                 num = UserInvite.objects.filter(user_id=request.session["user"].user_id).count()
#                 # 用户获取收益的百分比
#                 add_up = num * 0.5 + 1
#                 if add_up >= 10:
#                     add_up = 10
#                 # 查询用户的额外收益
#                 extra = UserInfo.objects.get(user_id=user.user_id)
#                 # 查询用户当前的额外收益
#                 extra_earn = Run.extra_earn
#                 print(extra_earn)
#                 price = decimal.Decimal(Run.guaranty) + decimal.Decimal(Run.down_payment) + decimal.Decimal(
#                     Run.bonus * decimal.Decimal(add_up)) + decimal.Decimal(extra.extra_money)
#                 # 将用户获取的收益存入余额
#                 UserInfo.objects.save_balance(user_id=user.user_id, price=price,add_money = extra.add_money)
#                 # 删除用户的目标
#                 RunningGoal.objects.delete_goal(goal_id)
#                 openid = user.wechat_id
#                 url = 'http://wechat.onmytarget.cn/user/index'
#                 activate = "跑步"
#                 finish_time = timezone.now().strftime('%Y-%m-%d %H:%M')
#                 earn_money = str(goal.guaranty + goal.down_payment)
#                 earn_time = (goal.start_time + timedelta(days=goal.goal_day)).strftime('%Y-%m-%d %H:%M')
#                 balance = str(UserInfo.objects.get(user_id=user.user_id).balance)
#                 # 发送模板提醒
#                 data = finish_tem(openid, url, activate, finish_time, earn_money, earn_time, balance)
#                 do_push(data)
#                 return JsonResponse({'status': 200})
#             elif activity_type == "2":
#                 goal = ReadingGoal.objects.get(goal_id=goal_id)
#                 UserRecord.objects.finish_goal(user=user)
#                 # 更新用户的押金
#                 UserInfo.objects.update_deposit(user_id=user.user_id,
#                                                 pay_delta=-(goal.guaranty + goal.down_payment))
#                 price = decimal.Decimal(goal.guaranty) + decimal.Decimal(goal.down_payment) + decimal.Decimal(goal.bonus)
#                 # 将用户获取的收益存入余额
#                 UserInfo.objects.money_handle(user_id=user.user_id, price=price,bonus=goal.bonus)
#                 # 删除用户的目标
#                 RunningGoal.objects.delete_goal(goal_id)
#                 return JsonResponse({'status': 200})
#
#             '''
#             if activity_type == RunningGoal.get_activity():
#                 # 获取相应的goal,准备退款给用户
#                 goal = RunningGoal.objects.get(goal_id=goal_id)
#                 # 增加用户的完成次数
#                 if goal.status == "SUCCESS":
#                     UserRecord.objects.finish_goal(user=user)
#                 if goal.refund_to_user(user.wechat_id):
#                     RunningGoal.objects.delete_goal(goal_id)
#                     return JsonResponse({'status': 200})
#                 else:
#                     return JsonResponse({'status':403})
#             elif activity_type == SleepingGoal.get_activity():
#                 goal = SleepingGoal.objects.get(goal_id=goal_id)
#                 UserRecord.objects.finish_goal(user=user)
#                 if goal.refund_to_user(user.wechat_id):
#                     SleepingGoal.objects.delete_goal(goal_id)
#                     return JsonResponse({'status': 200})
#                 else:
#                     return JsonResponse({'status': 403})
#             elif activity_type == ReadingGoal.get_activity():
#                 goal = ReadingGoal.objects.get(goal_id=goal_id)
#                 UserRecord.objects.finish_goal(user=user)
#                 if goal.refund_to_user(user.wechat_id):
#                     ReadingGoal.objects.delete_goal(goal_id)
#                     return JsonResponse({'status': 200})
#                 else:
#                     return JsonResponse({'status': 403})
# '''
#         else:
#             return JsonResponse({'status': 404})
#     except Exception:
#         return HttpResponseNotFound
#     else:
#         return JsonResponse({'status': 200})

# 结束目标任务
def delete_run_goal(request):
    try:
        user = request.session['user']
        if request.POST:
            # 删除当前的目标活动并退还钱
            activity_type = request.POST['goal_type']
            goal_id = request.POST['goal']
            goal = RunningGoal.objects.get(goal_id=goal_id)
            try:
                # 增加用户的完成次数
                UserRecord.objects.finish_goal(user=user)
                # 用户触发，如果挑战成功则删除目标，退还押金
                # 判断用户是否挑战成功
                # 更新用户的押金
                UserInfo.objects.update_deposit(user_id=user.user_id,
                                                pay_delta=-(goal.guaranty + goal.down_payment))
                # 查询用户的额外收益
                extra = UserInfo.objects.get(user_id=user.user_id)
                # 查询用户当前的额外收益
                price = decimal.Decimal(goal.guaranty) + decimal.Decimal(goal.down_payment) + decimal.Decimal(
                    goal.bonus) + decimal.Decimal(goal.extra_earn)
                # 将用户获取的收益存入余额
                UserInfo.objects.save_balance(user_id=user.user_id, price=price, bonus=decimal.Decimal(goal.bonus),
                                              extra_earn=decimal.Decimal(goal.extra_earn))
            except Exception as e:
                print(e)
            # 用户结算之后就将用户的所有信息放进记录存储表中
            try:
                print("开始保存用户的数据")
                Running_Finish_Save.objects.save_finish(goal_id=goal_id)
                import time
                time.sleep(1)
            except Exception as e:
                print("记录用户的结束保存信息失败", e)

            # 删除用户的目标
            RunningGoal.objects.delete_goal(goal_id)

            # 用户的目标结束之后，更新参加人数跟奖金池，系数
            try:
                goal.update_activity_person()
                act = Activity.objects.get(activity_id="32f2a8dbe89d43c7b9ecfea19947b057")
                act.bonus_all -= (goal.guaranty + goal.down_payment)
                act.save()
            except Exception as e:
                print("更新失败", e)

            url = 'http://wechat.onmytarget.cn/user/index'
            activate = "跑步"
            finish_time = timezone.now().strftime('%Y-%m-%d %H:%M')
            earn_money = str(goal.guaranty + goal.down_payment)
            # money = Running_Finish_Save.objects.get(user_id=user.user_id,settle_time=timezone.now().strftime('%Y-%m-%d')).bonus
            money = Running_Finish_Save.objects.filter(user_id=user.user_id,
                                                       settle_time=timezone.now().strftime('%Y-%m-%d'))
            if money:
                earn_money = money[0].bonus
            earn_time = (goal.start_time + timedelta(days=goal.goal_day)).strftime('%Y-%m-%d %H:%M')
            balance = str(UserInfo.objects.get(user_id=user.user_id).balance)
            # 发送模板提醒
            data = finish_tem(user.wechat_id, url, activate, finish_time, str(earn_money), earn_time, balance)
            do_push(data)
            return JsonResponse({'status': 200})
        else:
            return JsonResponse({'status': 403})
    except Exception:
        return JsonResponse({"status": 403})


@csrf_exempt
def delete_read_goal(request):
    try:
        user = request.session['user']
        if request.POST:
            activity_type = request.POST['goal_type']
            goal_id = request.POST['goal']
            if not all([activity_type, goal_id]):
                return JsonResponse({"status": 403})
            print("参数完整")
            read = ReadingGoal.objects.get(goal_id=goal_id)
            UserRecord.objects.finish_goal(user=user)
            # 更新用户的押金
            print("开始更新押金")
            UserInfo.objects.update_deposit(user_id=user.user_id,
                                            pay_delta=-(read.guaranty - read.bonus))
            print("更新成功")
            UserInfo.objects.read_handle(user_id=user.user_id, bonus=read.bonus)
            print("更新用户的余额成功")
            try:
                print("开始保存用户的数据")
                Read_Finish_Save.objects.save_finish(goal_id=goal_id)
                import time
                time.sleep(1)
            except Exception as e:
                print("记录用户的结束保存信息失败", e)
            try:
                ReadingPunchRecord.objects.filter(goal_id=goal_id).delete()
                ReadingGoal.objects.filter(goal_id=goal_id).delete()
            except Exception as e:
                print("删除读书活动失败", e)
            try:
                read.update_activity_person()
                act = Activity.objects.get(activity_id="fac28454e818458f86639e7d40554597")
                act.bonus_all -= read.guaranty
                act.save()
            except Exception as e:
                print("更新失败", e)
            # 更新用户的余额
            try:
                url = 'http://wechat.onmytarget.cn/user/index'
                activate = "阅读"
                finish_time = timezone.now().strftime('%Y-%m-%d %H:%M')
                earn_money = str(read.bonus)
                earn_time = timezone.now().strftime('%Y-%m-%d %H:%M')
                # 发送模板提醒
                data = finish_tem(user.wechat_id, url, activate, finish_time, earn_money, earn_time, str(user.balance))
                do_push(data)
                return JsonResponse({'status': 200})
            except Exception as e:
                print("发送读书模板失败", e)
    except Exception as e:
        print("读书结束失败", e)
        return JsonResponse({"status": 403})


@csrf_exempt
def delete_sleep_goal(request):
    user = request.session['user']
    try:
        if request.POST:
            activity_type = request.POST['goal_type']
            goal_id = request.POST['goal']
            if not all([activity_type, goal_id]):
                return JsonResponse({"status": 403})
            print("参数完整")
            sleep = SleepingGoal.objects.get(goal_id=goal_id)
            UserRecord.objects.finish_goal(user=user)
            print("开始更新押金")
            UserInfo.objects.update_deposit(user_id=user.user_id,
                                            pay_delta=-sleep.guaranty)
            print("更新成功", sleep.bonus)
            UserInfo.objects.sleep_handle(user_id=user.user_id, bonus=sleep.bonus, guaranty=sleep.guaranty,
                                          extra_earn=sleep.extra_earn)
            print("更新用户的余额成功")
            try:
                print("开始保存用户的数据")
                Sleep_Finish_Save.objects.save_finish(goal_id=goal_id)
                import time
                time.sleep(1)
            except Exception as e:
                print("记录用户的结束保存信息失败", e)
            try:
                SleepingPunchRecord.objects.filter(goal_id=goal_id).delete()
                SleepingGoal.objects.filter(goal_id=goal_id).delete()
                Coefficient.objects.filter(user_id=user.user_id).delete()
            except Exception as e:
                print("删除读书活动失败", e)
            # 用户的目标结束之后，更新参加人数跟奖金池，系数
            try:
                sleep.update_activity_person()
                act = Activity.objects.get(activity_id="a5a0206fb2aa4e8995263c7ab0afa1b5")
                act.bonus_all -= (sleep.guaranty + sleep.down_payment)
                act.save()
            except Exception as e:
                print("更新失败", e)
            return JsonResponse({"status": 200})
        else:
            return JsonResponse({"status": 403})
    except Exception as e:
        print(e)
        return JsonResponse({"status": 401})


# 创建一个目标任务
# @helper.json_render
@csrf_exempt
def create_goal(request):
    print("开始创建活动")
    user = request.session['user']
    if request.POST:
        reality = request.POST['reality']
        deserve = request.POST["deserve"]
        down_num = request.POST["down_num"]
        guaranty = float(request.POST["guaranty"])
        down_payment = float(request.POST["down_payment"])
        extra_earn = 0
        average = decimal.Decimal(down_payment) / int(down_num)
        print("每次要扣除的金额{}".format(average), "底金次数是{}".format(down_num))
        print(average)
        activate_deposit = guaranty + down_payment
        print(activate_deposit)
        # 日志记录用户支付的钱数
        # logger.info("[Money] User {0} Pay {1} To Create A Goal".format(user.user_id, guaranty + down_payment))
        activity = request.POST["activity"]
        coefficient = float(request.POST["coefficient"])
        mode = request.POST["mode"]
        goal_day = int(request.POST["goal_day"])
        goal_type = request.POST["goal_type"]
        activity_type = Activity.objects.get(activity_id=activity).activity_type
        punch_day = 0

        if activity_type == RunningGoal.get_activity():
            # activate = "跑步"
            distance = request.POST["distance"]
            nosign = request.POST["nosign"]
            rem = 0
            try:
                run = RunningGoal.objects.get(user_id=user.user_id)
            except Exception as e:
                # logger.info("用户活动记录不存在")
                rem = 1
                goal = RunningGoal.objects.create_goal(user_id=user.user_id,
                                                       runningtype=goal_type,
                                                       guaranty=guaranty,
                                                       down_payment=down_payment,
                                                       activate_deposit=activate_deposit,
                                                       coefficient=coefficient,
                                                       mode=mode,
                                                       goal_day=goal_day,
                                                       distance=distance,
                                                       nosign=nosign,
                                                       extra_earn=extra_earn,
                                                       average=average,
                                                       reality_price=reality,
                                                       deserve_price=deserve,
                                                       down_num=down_num,
                                                       punch_day=punch_day)
                return JsonResponse({'status': 200, 'goal': goal.goal_id, "rem": rem})
            else:
                if run.status != "ACTIVE":
                    rem = 1
                    goal = RunningGoal.objects.create_goal(user_id=user.user_id,
                                                           runningtype=goal_type,
                                                           guaranty=guaranty,
                                                           down_payment=down_payment,
                                                           activate_deposit=activate_deposit,
                                                           coefficient=coefficient,
                                                           mode=mode,
                                                           goal_day=goal_day,
                                                           distance=distance,
                                                           nosign=nosign,
                                                           extra_earn=extra_earn,
                                                           average=average,
                                                           reality_price=reality,
                                                           deserve_price=deserve,
                                                           down_num=down_num,
                                                           punch_day=punch_day)
                    return JsonResponse({'status': 200, 'goal': goal.goal_id, "rem": rem})
                else:
                    rem = 0
                    return JsonResponse({'status': 403, "rem": rem})
        else:
            pass
            return JsonResponse({"status": 200})
    else:
        return HttpResponseNotFound


@csrf_exempt
def create_run(request):
    print(111111111111)
    if request.POST:
        user = request.session.get("user")
        # if DEBUG:
        #     user_id = 100274
        # else:
        user_id = user.user_id
        data_json = request.POST
        reality_price = data_json.get("reality_price")
        deserve_price = data_json.get('deserve_price')
        activate_deposit = data_json.get("activate_deposit")
        down_num = data_json.get("down_num")
        guaranty = data_json.get("guaranty")
        down_payment = data_json.get("down_payment")
        coefficient = data_json.get("coefficient")
        mode = data_json.get("mode")
        goal_day = data_json.get("goal_day")
        goal_type = data_json.get("goal_type")
        punch_attention = data_json.get("punch_attention")
        is_no_use_point = data_json.get("is_no_use_point")
        distance = data_json.get("distance", "")
        kilos_day = data_json.get("kilos_day", "")
        deduction_point = data_json.get("deduction_point")
        deduction_guaranty = data_json.get("deduction_guaranty")
        multiple = data_json.get("multiple")
        start_time = timezone.now()
        # 参数教检
        # 自由模式与日常模式的个别参数不一样,自由模式没有每日距离,distance表示的都是目标距离
        if goal_type == 0:
            if not all([reality_price, deserve_price, down_num, guaranty, down_payment, coefficient
                           , mode, goal_day, punch_attention, is_no_use_point, distance, deduction_point,
                        deduction_guaranty, multiple]):
                return JsonResponse({"status": 403, "errmsg": "参数不完整"})
        # 日常模式，有每日距离，distance表示的是剩余距离
        elif goal_type == 1:
            if not all([reality_price, deserve_price, down_num, guaranty, down_payment, coefficient
                           , mode, goal_day, punch_attention, is_no_use_point, kilos_day, distance, deduction_point,
                        deduction_guaranty, multiple]):
                return JsonResponse({"status": 403, "errmsg": "参数不完整"})

        # 若参数完整，处理业务
        try:
            print("开始创建")
            goal = RunningGoal.objects.create_rungoal(user_id=user_id,
                                                      goal_type=goal_type,
                                                      guaranty=guaranty,
                                                      down_payment=down_payment,
                                                      activate_deposit=activate_deposit,
                                                      coefficient=coefficient,
                                                      mode=mode,
                                                      goal_day=goal_day,
                                                      distance=distance,
                                                      reality_price=reality_price,
                                                      deserve_price=deserve_price,
                                                      down_num=down_num,
                                                      start_time=start_time,
                                                      kilos_day=kilos_day,
                                                      punch_attention=punch_attention,
                                                      is_no_use_point=is_no_use_point,
                                                      multiple=multiple,
                                                      deduction_point=deduction_point,
                                                      deduction_guaranty=deduction_guaranty
                                                      )
            print("参与成功")
            coeff = RunCoefficient.objects.filter(user_id=user.user_id)
            if coeff:
                coeff.delete()
                RunCoefficient.objects.create(user_id=user.user_id, goal_type=goal_type, default_coeff=coefficient)
                print("创建成功")
            else:
                RunCoefficient.objects.create(user_id=user.user_id, goal_type=goal_type, default_coeff=coefficient)
                print("创建成功")
            return JsonResponse({"status": 200, "goal": goal.goal_id})
        except Exception as e:
            print(e)
            return JsonResponse({"status": 502})


# 创建读书活动表
@csrf_exempt
def create_read(request):
    user = request.session["user"]
    if request.POST:
        print("开始创建读书活动")
        maxreturn = request.POST["maxreturn"]
        bookname = request.POST["bookname"]
        goalpage = request.POST["goalpage"]
        bookprice = request.POST["bookprice"]
        imageurl = request.POST["imageurl"]
        guaranty = request.POST["guaranty"]

        reality_price = request.POST["reality_price"]
        deserve_price = request.POST["deserve_price"]
        if not all([maxreturn, bookname, goalpage, bookprice, imageurl, guaranty, reality_price,
                    deserve_price]):
            print("创建图书活动的参数不全")
            return JsonResponse({"status": 201})
        try:
            goal = ReadingGoal.objects.create_goal(user_id=user.user_id,
                                                   guaranty=guaranty,
                                                   max_return=maxreturn,
                                                   book_name=bookname,
                                                   goal_page=goalpage,
                                                   price=bookprice,
                                                   imageurl=imageurl,
                                                   reality_price=reality_price,
                                                   deserve_price=deserve_price
                                                   )
            print("创建目标成功{}".format(user.user_id))
            response_data = {'status': 200, 'goal': goal.goal_id}
            return JsonResponse(response_data)
        except Exception as e:
            print("读书目标或订单创建失败", e)
    else:
        return HttpResponseNotFound


@csrf_exempt
def create_sleep_goal(request):
    if request.POST:
        user = request.session.get("user")
        guaranty = request.POST.get("guaranty")
        coefficient = request.POST.get("coefficient")
        goal_type = request.POST.get("goal_type")
        goal_day = request.POST.get("goal_day")
        sleep_type = request.POST.get("sleep_type")
        reality_price = request.POST["reality_price"]
        deserve_price = request.POST["deserve_price"]
        multiple = request.POST.get("multiple",1)
        punch_attention = request.POST.get("punch_attention", 1)
        is_no_use_point = request.POST.get("is_no_use_point", 0)
        if not all([guaranty, coefficient, goal_day, sleep_type, reality_price, deserve_price]):
            return JsonResponse({"status": 403, "errmsg": "参数不完整"})

        if DEBUG:
            try:
                goal = SleepingGoal.objects.create_goal(user_id=user.user_id,
                                                        guaranty=guaranty,
                                                        coefficient=coefficient,
                                                        goal_day=goal_day,
                                                        goal_type=goal_type,
                                                        sleep_type=sleep_type,
                                                        punch_attention=punch_attention,
                                                        is_no_use_point=is_no_use_point,
                                                        reality_price=reality_price,
                                                        deserve_price=deserve_price
                                                        )
                if not Coefficient.objects.filter(user_id=user.user_id):
                    Coefficient.objects.create(user_id=user.user_id, default_coeff=coefficient, sleep_type=sleep_type)
                # 顺便创建一条打卡记录
                # SleepingPunchRecord.objects.create(goal=goal, punch_time=timezone.now().strftime("%Y-%m-%d"),user_id=100274)
                response_data = {'status': 200, 'goal': goal.goal_id}
                return JsonResponse(response_data)
            except Exception as e:
                print("创建作息活动失败", e)
                return JsonResponse({"status": 403})
        else:
            try:
                goal = SleepingGoal.objects.create_goal(user_id=user.user_id,
                                                        guaranty=guaranty,
                                                        coefficient=coefficient,
                                                        goal_day=goal_day,
                                                        goal_type=goal_type,
                                                        multiple = multiple,
                                                        punch_attention=punch_attention,
                                                        is_no_use_point=is_no_use_point,
                                                        sleep_type=sleep_type,
                                                        reality_price=reality_price,
                                                        deserve_price=deserve_price
                                                        )
                coeff = Coefficient.objects.filter(user_id=user.user_id)
                if coeff:
                    coeff.delete()
                    Coefficient.objects.create(user_id=user.user_id, sleep_type=sleep_type, default_coeff=coefficient)
                else:
                    Coefficient.objects.create(user_id=user.user_id, sleep_type=sleep_type, default_coeff=coefficient)
                print(goal.goal_id)
                # 顺便创建一条打卡记录
                response_data = {'status': 200, 'goal': goal.goal_id}
                return JsonResponse(response_data)
            except Exception as e:
                print("创建作息活动失败", e)
                return JsonResponse({"status": 403})


#
def order_confirm_temp(openid, url, order_time, content, user_name, user_address):
    data = {
        "touser": openid,
        "template_id": "pda7H3fWF8aqwPJ_y6PHbnmq6qmxQrShFMeTRE4wgQ4",
        "url": url,
        "topcolor": "#FF0000",
        "data": {
            "first": {
                "value": "尊敬的客户，您的订单已完成。",
                "color": "#173177"
            },
            "keyword1": {
                "value": order_time,
                "color": "#173177"
            },
            "keyword2": {
                "value": content,
                "color": "#173177"
            },
            "keyword3": {
                "value": user_name,
                "color": "#173177"
            },
            "keyword4": {
                "value": user_address,
                "color": "#173177"
            },
            "remark": {
                "value": "感谢您对我们的支持和理解，期待再次为您服务，祝您生活愉快！",
                "color": "#173177"
            },
        }
    }
    return data


# 订单确认
@csrf_exempt
def order_confirm(request):
    user = request.session["user"]
    print("开始确认订单{}".format(user.user_id))
    if request.POST:
        try:
            response_dict = request.POST
            order_id = response_dict.get("order_id")
            goal_id = response_dict.get("goal_id", " ")
            activity_type = response_dict.get("activity_type", "")
            print(type(activity_type), activity_type)
            if activity_type == "1":
                try:
                    order = UserOrder.objects.filter(order_id=order_id)[0]
                    order.owner_name = response_dict.get("name")
                    order.owner_phone = response_dict.get("phone")
                    order.address = response_dict.get("address")
                    order.area = response_dict.get("area")
                    order.remarks = response_dict.get("remarks", " ")
                    order.is_no_confirm = 1
                    order.save()
                    order_time = timezone.now().strftime("%Y-%m-%d %H:%M")
                    content = order.order_name
                    user_name = response_dict.get("name")
                    user_address = response_dict.get("address")
                    url = 'http://wechat.onmytarget.cn/user/index'
                    data = order_confirm_temp(user.wechat_id, url, order_time, content, user_name,
                                              order.area + " " + user_address)
                    do_push(data)
                    print("发送确认订单信息成功")
                    return JsonResponse({"status": 200})
                except Exception as e:
                    print(e)
            elif activity_type == "2":
                if goal_id:
                    order = UserOrder.objects.filter(order_id=order_id, goal_id=goal_id)[0]
                else:
                    order = UserOrder.objects.filter(order_id=order_id)[0]
                order.owner_name = response_dict.get("name")
                order.owner_phone = response_dict.get("phone")
                order.address = response_dict.get("address")
                order.area = response_dict.get("area")
                order.remarks = response_dict.get("remarks", " ")

                print("开始修改数据")
                order.is_no_confirm = 1
                print("修改成功")
                order.save()
                print("保存成功", order.is_no_confirm)
                order_time = timezone.now().strftime("%Y-%m-%d %H:%M")
                content = order.order_name
                user_name = response_dict.get("name")
                user_address = response_dict.get("address")
                url = 'http://wechat.onmytarget.cn/user/index'
                data = order_confirm_temp(user.wechat_id, url, order_time, content, user_name,
                                          order.area + " " + user_address)
                do_push(data)
                print("发送确认订单信息成功")
                return JsonResponse({"status": 200})
        except Exception as e:
            print(e)
            return JsonResponse({"status": 201})
        # 确认订单成功，开始发送信息
    else:
        return JsonResponse({"status": 201})


# 确认收货
@csrf_exempt
def receive_confirm(request):
    user = request.session["user"]
    print("{}用户正在确认收货".format(user.user_id))
    if request.POST:
        try:
            goal_id = request.POST.get("goal_id", "")
            activity_type = request.POST.get("activity_type")
            order_id = request.POST.get("order_id")
            if not all([activity_type, order_id]):
                return JsonResponse({"status": 201, "errmsg": "确认订单参数不全"})
            if activity_type == "2":
                if goal_id:
                    order = UserOrder.objects.filter(order_id=order_id, goal_id=goal_id, activity_type=activity_type)[0]
                    ReadingGoal.objects.filter(goal_id=goal_id).update(start_time=timezone.now(), is_start=1)
                else:

                    order = UserOrder.objects.filter(order_id=order_id, activity_type=activity_type)[0]
                order.confirm_time = timezone.now()
                order.save()
                return JsonResponse({"status": 200})
            elif activity_type == "1":
                order = UserOrder.objects.filter(order_id=order_id, activity_type=activity_type)[0]
                order.confirm_time = timezone.now()
                order.save()
                return JsonResponse({"status": 200})
        except Exception as e:
            print('收获确认失败，失败原因：{}'.format(e))
    else:
        return JsonResponse({"status": 201})


@csrf_exempt
def create_walk_goal(request):
    if request.POST:
        user = request.session.get("user")
        print("kdui ")
        if DEBUG:
            user_id = 100274
        else:
            user_id = user.user_id
        reality_price = request.POST.get('reality_price')
        deserve_price = request.POST.get("deserve_price")
        down_num = request.POST.get("down_num")
        guaranty = float(request.POST.get("guaranty"))
        down_payment = float(request.POST.get("down_payment"))
        average = decimal.Decimal(down_payment) / int(down_num)
        activate_deposit = guaranty + down_payment
        coefficient = float(request.POST.get("coefficient"))
        mode = request.POST.get("mode")
        goal_day = int(request.POST.get("goal_day"))
        goal_type = request.POST.get("goal_type")
        nosign = request.POST.get("nosign")
        activity_type = "3"
        if not all(
                [reality_price, deserve_price, down_num, guaranty, down_payment, coefficient, mode, goal_day, goal_type
                 ]):
            return JsonResponse({"status": 405, "errmsg": "参数不完整"})
        try:
            print("开始创建")
            goal = WalkingGoal.objects.create_goal(user_id=user_id,
                                                   reality_price=reality_price,
                                                   deserve_price=deserve_price,
                                                   down_num=down_num,
                                                   guaranty=guaranty,
                                                   down_payment=down_payment,
                                                   average=average,
                                                   activate_deposit=activate_deposit,
                                                   coefficient=coefficient,
                                                   mode=mode,
                                                   goal_day=goal_day,
                                                   goal_type=goal_type,
                                                   nosign=nosign,
                                                   activity_type=activity_type
                                                   )
            response_data = {'status': 200, 'goal': goal.goal_id}
            return JsonResponse(response_data)
        except Exception as e:
            print(e)
            return JsonResponse({"status": 201})


@csrf_exempt
def create_riding_goal(request):
    print('开始创建骑行活动')
    if request.POST:
        print(11111111111)
        user = request.session.get("user")
        # if DEBUG:
        # 	user_id = 101077
        # else:
        user_id = user.user_id
        print(222222222222)
        data_json = request.POST
        print(3333333333333)
        goal_type = data_json.get("goal_type")
        print(444444444444444)
        guaranty = data_json.get("guaranty")
        print(444444444444)
        coefficient = data_json.get("coefficient")
        print(55555555555555555)
        multiple = data_json.get("multiple")
        print(6666666666666666666)
        kilos_day = data_json.get("kilos_day", "")
        print(77777777777777777777777)
        goal_distance = data_json.get('goal_distance', '')
        print(9999999999)
        print('goal_distance', goal_distance)
        print(100000000000000000)
        mode = data_json.get("mode")
        print(122222222222222)
        goal_day = data_json.get("goal_day")
        print(13333333333333333333333)
        reality_price = data_json.get("reality_price")
        print(14444444444444444444444444)
        deserve_price = data_json.get('deserve_price')
        print(15555555555555555555)
        down_num = data_json.get("down_num")
        print(16666666666666666)
        down_payment = data_json.get("down_payment")
        print(17777777777777777777777)
        activate_deposit = data_json.get("activate_deposit")
        print(1888888888888888888888)

        punch_attention = data_json.get("punch_attention", 1)
        # print('punch_attention', punch_attention)
        print(199999999999999999)
        is_no_use_point = data_json.get("is_no_use_point", 0)
        # distance = data_json.get("distance", "")
        print(2000000000000000000000)
        deduction_point = data_json.get("deduction_point", 0)
        print(211111111111111111111111)
        deduction_guaranty = data_json.get("deduction_guaranty", 0)
        print(233333333333333333333333333333)
        start_time = timezone.now()
        print(244444444444444444444)
        # 参数教检

        # 自由模式与日常模式的个别参数不一样,自由模式没有每日距离,goal_distance表示的是目标距离
        if goal_type == 0:
            print('自由模式')
            if not all([reality_price, deserve_price, down_num, guaranty, down_payment, coefficient
                           , mode, goal_day, punch_attention, is_no_use_point, goal_distance, deduction_point,
                        deduction_guaranty, multiple]):
                print('333333333')
                return JsonResponse({"status": 403, "errmsg": "参数不完整"})
        # 日常模式，有每日距离，kilos_day表示的是剩余距离
        elif goal_type == 1:
            print('日常模式')
            if not all([reality_price, deserve_price, down_num, guaranty, down_payment, coefficient
                           , mode, goal_day, punch_attention, is_no_use_point, kilos_day, deduction_point,
                        deduction_guaranty, multiple]):
                return JsonResponse({"status": 403, "errmsg": "参数不完整"})

        # 若参数完整，处理业务
        try:
            goal = RidingGoal.objects.create_ridinggoal(user_id=user_id,
                                                        goal_type=goal_type,
                                                        guaranty=guaranty,
                                                        down_payment=down_payment,
                                                        activate_deposit=activate_deposit,
                                                        coefficient=coefficient,
                                                        mode=mode,
                                                        goal_day=goal_day,
                                                        goal_distance=goal_distance,
                                                        reality_price=reality_price,
                                                        deserve_price=deserve_price,
                                                        down_num=down_num,
                                                        start_time=start_time,
                                                        kilos_day=kilos_day,
                                                        multiple=multiple,
                                                        deduction_point=deduction_point,
                                                        deduction_guaranty=deduction_guaranty,
                                                        )
            coeff = RidingCoefficient.objects.filter(user_id=user_id)
            if coeff is not None:
                coeff.delete()
                RidingCoefficient.objects.create(user_id=user_id, default_coeff=coefficient, goal_type=goal_type)
            else:
                RidingCoefficient.objects.create(user_id=user_id, default_coeff=coefficient, goal_type=goal_type)
            print('骑行活动创建成功')
            return JsonResponse({"status": 200, "goal": goal.goal_id})
        except Exception as e:
            print(e)
            return JsonResponse({"status": 502})
