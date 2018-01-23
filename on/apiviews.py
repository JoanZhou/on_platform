from django.conf import settings
from django.http import HttpResponse, JsonResponse, HttpResponseNotFound
from on.wechatconfig import mediaApiClient
import requests
from wechatpy.utils import random_string, to_text
import os
from on.models import RunningGoal,RunningPunchRecord,SleepingGoal,SleepingPunchRecord,ReadingGoal,ReadingPunchRecord
from on.user import UserTicket, UserRecord
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone
from datetime import timedelta


# 跑步签到时上传图片
def running_sign_in_api(request):
    """
    跑步签到后端 API
    :param request:
    :return:
    """
    """获取对应的目标的goal id"""
    goal_id = request.GET.get('goal', ' ')
    distance = float(request.GET.get('distance', 0))
    goal = RunningGoal.objects.get(goal_id=goal_id)
    """获取User的WechatID"""
    user_wechat_id = request.session['user'].wechat_id
    """存储图片"""
    mediaid = request.GET.get('serverId', ' ')
    apiLink = mediaApiClient.get_url(mediaid)
    response = requests.get(apiLink)
    # User 名字加随机字符串
    fileName = user_wechat_id + "_" + random_string(16) + ".jpg"
    # 文件的实际存储路径
    """将打卡记录存储到数据库中"""
    punch = RunningPunchRecord.objects.create_record(goal, response.content, filename=fileName, distance=distance)
    """增加用户的完成天数"""
    UserRecord.objects.update_finish_day(user=request.session['user'])
    return HttpResponse("200")


# 跑步免签API
def running_no_sign_in_handler(request):
    if request.POST:
        goal = request.POST['goal']
        use_ticket = UserTicket.objects.use_ticket(goal_id=goal, ticket_type='NS')
        if use_ticket:
            return JsonResponse({'status': 200})
        else:
            return JsonResponse({'status': 201})
    else:
        return HttpResponseNotFound


# 跑步举报API
def running_report_handler(request):
    if request.POST:
        punch = request.POST['punch']
        user = request.session['user']
        RunningPunchRecord.objects.report_punch(user_id=user.user_id,punch_id=punch)
        return JsonResponse({'status':200})
    else:
        return HttpResponseNotFound


# 跑步点赞API
def running_praise_handler(request):
    if request.POST:
        punch = request.POST['punch']
        user = request.session['user']
        RunningPunchRecord.objects.praise_punch(user_id=user.user_id, punch_id=punch)
        return JsonResponse({'status': 200})
    else:
        return HttpResponseNotFound


# 作息免签API
def sleeping_no_sign_in_handler(request):
    if request.POST:
        goal = request.POST['goal']
        # 免签卡记录的时间是8个小时以后的时间, 这一点作息与跑步不同
        use_ticket = UserTicket.objects.use_ticket(goal_id=goal, ticket_type='NS', use_time=timezone.now() + timezone.timedelta(hours=8))
        if use_ticket:
            return JsonResponse({'status': 200})
        else:
            return JsonResponse({'status': 201})
    else:
        return HttpResponseNotFound


# 作息延时API
def sleeping_delay_handler(request):
    if request.POST:
        goal = request.POST['goal']
        # 延时记录的应该是第二天早上的起床时间延迟，为了检索方便，直接定位到第二天。因为一定是9点以后打卡睡眠，所以打卡在4小时后即可
        use_ticket = UserTicket.objects.use_ticket(goal_id=goal, ticket_type='D', use_time=timezone.now() + timezone.timedelta(hours=8))
        if use_ticket:
            return JsonResponse({'status': 200})
        else:
            return JsonResponse({'status': 201})
    else:
        return HttpResponseNotFound


# 作息睡觉打卡
def sleeping_sleep_handler(request):
    if request.POST:
        goal_id = request.POST['goal']
        goal = SleepingGoal.objects.get(goal_id=goal_id)
        # 如果record无误，则打卡成功；否则打卡失败
        record = SleepingPunchRecord.objects.create_sleep_record(goal=goal)
        if record:
            return JsonResponse({'status': 200,
                                 'time': record.before_sleep_time.time().strftime("%H:%M")})
        else:
            return JsonResponse({'status': 201})
    else:
        return HttpResponseNotFound


# 作息起床打卡
def sleeping_getup_handler(request):
    if request.POST:
        goal_id = request.POST['goal']
        goal = SleepingGoal.objects.get(goal_id=goal_id)
        # 如果record无误，则返回早起时间；否则打卡失败
        record = goal.punch.update_getup_record()
        if record:
            return JsonResponse({'status': 200,
                                 'getuptime': record.get_up_time.time().strftime("%H:%M"),
                                 'checktime': record.check_time.time().strftime("%H:%M")})
        else:
            return JsonResponse({'status': 201})


# 作息确认打卡
def sleeping_confirm_handler(request):
    if request.POST:
        goal_id = request.POST['goal']
        goal = SleepingGoal.objects.get(goal_id=goal_id)
        # 如果record无误，则返回确认时间；否则打卡失败
        record = goal.punch.update_confirm_time()
        if record:
            """增加用户的完成天数"""
            UserRecord.objects.update_finish_day(user=request.session['user'])
            return JsonResponse({'status': 200,
                                 'time': record.confirm_time.time().strftime("%H:%M")})
        else:
            return JsonResponse({'status': 201})


# 开启书籍阅读
def reading_start_handler(request):
    if request.POST:
        goal_id = request.POST['goal']
        goal = ReadingGoal.objects.get(goal_id=goal_id)
        # 开始阅读后，更改阅读时间
        if settings.DEBUG:
            # 只是暂定一个时间，最迟1个月后开始
            goal.start_time = timezone.now() - timedelta(days=30)
        else:
            goal.start_time = timezone.now()
        goal.is_start = True
        goal.save()
        return JsonResponse({'status': 200})
    else:
        return JsonResponse({'status': 201})


# 书籍阅读打卡
def reading_record_handler(request):
    if request.POST:
        # 本次阅读了page页，耗时time秒
        goal_id = request.POST['goal']
        timedelta = request.POST['time']
        page = request.POST['page']
        # 新建一个阅读记录，并返回返回值
        return ReadingPunchRecord.objects.create_record(goal_id=goal_id,
                                                        today_page=page,
                                                        today_time=timedelta)
    else:
        return HttpResponseNotFound

