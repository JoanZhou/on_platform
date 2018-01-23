from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseNotFound
from on.user import UserInfo, UserTicket, UserRecord
from on.models import Activity, Goal, RunningGoal, SleepingGoal, ReadingGoal
from on.activities.running.views import show_running_goal
from on.activities.sleeping.views import show_sleeping_goal
from on.activities.reading.views import show_reading_goal
from on.wechatconfig import get_wechat_config
import logging
from on.views import oauth

goal_mapping = {
    RunningGoal.get_activity(): show_running_goal,
    SleepingGoal.get_activity(): show_sleeping_goal,
    ReadingGoal.get_activity(): show_reading_goal
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

logger = logging.getLogger("app")


# 展示用户的目标列表
@oauth
def show_goals(request):
    user = request.session['user']
    sub_models = get_son_models(Goal)
    all_goals = []
    for sub_model_key in sub_models:
        all_goals += sub_models[sub_model_key].objects.filter(user_id=user.user_id)
    payed_goals = [goal for goal in all_goals if goal.status != 'PENDING']
    return render(request, 'goal/index.html', {'goals': payed_goals})


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
            goal_intro = "在{0}天内累计跑步{1}km".format(goal.goal_day, goal.goal_distance)
        elif goal.activity_type == RunningGoal.get_activity():
            goal_intro = "在{0}天内每天跑步{1}km".format(goal.goal_day, goal.kilos_day)
        elif goal.activity_type == ReadingGoal.get_activity():
            goal_intro = "在30天内阅读完书籍《{0}》".format(goal.book_name)
        elif goal.activity_type == SleepingGoal.get_activity():
            goal_intro = "在{0}天内每天早上{1}前起床".format(goal.goal_day, goal.getup_time.strftime("%H:%M"))
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


# 结束目标任务
def delete_goal(request):
    try:
        user = request.session['user']
        if request.method == "POST":
            # 删除当前的目标活动并退还钱
            activity_type = request.POST['goal_type']
            goal_id = request.POST['goal']
            delete_map = {
                RunningGoal.get_activity(): RunningGoal,
                ReadingGoal.get_activity(): ReadingGoal,
                SleepingGoal.get_activity(): SleepingGoal
            }
            for goal_type in delete_map.keys():
                if activity_type == goal_type:
                    goal_class = delete_map[goal_type]
                    goal = goal_class.objects.get(goal_id=goal_id)
                    # 增加用户的完成次数
                    if goal.status == "SUCCESS":
                        UserRecord.objects.finish_goal(user=user)
                        if goal.refund_to_user(user.wechat_id):
                            # 删除用户的目标
                            goal_class.objects.delete_goal(goal_id)
                            # 更新用户的押金
                            UserInfo.objects.update_deposit(user_id=user.user_id, pay_delta=-(goal.guaranty+goal.down_payment))
                            return JsonResponse({'status': 200})
                        else:
                            return JsonResponse({'status': 403})
            """
            if activity_type == RunningGoal.get_activity():
                # 获取相应的goal,准备退款给用户
                goal = RunningGoal.objects.get(goal_id=goal_id)
                # 增加用户的完成次数
                if goal.status == "SUCCESS":
                    UserRecord.objects.finish_goal(user=user)
                if goal.refund_to_user(user.wechat_id):
                    RunningGoal.objects.delete_goal(goal_id)
                    return JsonResponse({'status': 200})
                else:
                    return JsonResponse({'status':403})
            elif activity_type == SleepingGoal.get_activity():
                goal = SleepingGoal.objects.get(goal_id=goal_id)
                UserRecord.objects.finish_goal(user=user)
                if goal.refund_to_user(user.wechat_id):
                    SleepingGoal.objects.delete_goal(goal_id)
                    return JsonResponse({'status': 200})
                else:
                    return JsonResponse({'status': 403})
            elif activity_type == ReadingGoal.get_activity():
                goal = ReadingGoal.objects.get(goal_id=goal_id)
                UserRecord.objects.finish_goal(user=user)
                if goal.refund_to_user(user.wechat_id):
                    ReadingGoal.objects.delete_goal(goal_id)
                    return JsonResponse({'status': 200})
                else:
                    return JsonResponse({'status': 403})
            """
        else:
            return JsonResponse({'status': 404})
    except Exception:
        return HttpResponseNotFound
    else:
        return JsonResponse({'status':200})


# 创建一个目标任务
def create_goal(request):
    user = request.session['user']
    if request.POST:
        guaranty = float(request.POST["guaranty"])
        down_payment = float(request.POST["down_payment"])
        # 日志记录用户支付的钱数
        logger.info("[Money] User {0} Pay {1} To Create A Goal".format(user.user_id, guaranty + down_payment))
        activity = request.POST["activity"]
        coefficient = float(request.POST["coefficient"])
        mode = request.POST["mode"]
        goal_day = int(request.POST["goal_day"])
        goal_type = request.POST["goal_type"]
        activity_type = Activity.objects.get(activity_id=activity).activity_type
        if activity_type == RunningGoal.get_activity():
            distance = int(request.POST["distance"])
            nosign = request.POST["nosign"]
            goal = RunningGoal.objects.create_goal(user_id=user.user_id,
                                                   runningtype=goal_type,
                                                   guaranty=guaranty,
                                                   down_payment=down_payment,
                                                   coefficient=coefficient,
                                                   mode=mode,
                                                   goal_day=goal_day,
                                                   distance=distance,
                                                   nosign=nosign)
            response_data = {'status': 200, 'goal': goal.goal_id}
            return JsonResponse(response_data)
        elif activity_type == SleepingGoal.get_activity():
            nosign = request.POST["nosign"]
            delay = request.POST["delay"]
            getuptime =request.POST["getuptime"]
            goal = SleepingGoal.objects.create_goal(user_id=user.user_id,
                                                    guaranty=guaranty,
                                                    down_payment=down_payment,
                                                    coefficient=coefficient,
                                                    mode=mode,
                                                    goal_day=goal_day,
                                                    getuptime=getuptime,
                                                    nosign=nosign,
                                                    delay=delay)
            response_data = {'status': 200, 'goal': goal.goal_id}
            return JsonResponse(response_data)
        elif activity_type == ReadingGoal.get_activity():
            maxreturn = request.POST["maxreturn"]
            bookname = request.POST["bookname"]
            goalpage = request.POST["goalpage"]
            bookprice = request.POST["bookprice"]
            imageurl = request.POST["imageurl"]
            goal = ReadingGoal.objects.create_goal(user_id=user.user_id,
                                                   guaranty=guaranty,
                                                   max_return=maxreturn,
                                                   book_name=bookname,
                                                   goal_page=goalpage,
                                                   price=bookprice,
                                                   imageurl=imageurl)
            response_data = {'status': 200, 'goal': goal.goal_id}
            return JsonResponse(response_data)
    else:
        return HttpResponseNotFound