import time
import re
import requests
from django.shortcuts import render
from datetime import timedelta
from django.conf import settings
from django.http import HttpResponse, JsonResponse, HttpResponseNotFound
from django.utils import timezone
from wechatpy.utils import random_string
from selenium import webdriver
from on.models import RunningGoal, RunningPunchRecord, SleepingGoal, SleepingPunchRecord, ReadingGoal, \
    ReadingPunchRecord

from on.activities.reading.models import ReadTime, BookInfo

from on.temp.push_template import do_push
from on.temp.template_map import template
from on.user import UserTicket, UserRecord, UserInfo, UserOrder
from on.wechatconfig import mediaApiClient
import os
from django.views.decorators.csrf import csrf_exempt
import base64
from .QR_invite import user_qrcode
import requests
import json
import decimal


AppSecret = "23f0462bee8c56e09a2ac99321ed9952"
AppId = "wx4495e2082f63f8ac"


# 获取用户的access_token
def get_token():
    url = "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}".format(AppId,
                                                                                                           AppSecret)
    token_str = requests.get(url).content.decode()
    token_json = json.loads(token_str)
    token = token_json['access_token']
    return token


def punch_success(openid, url, first, punch_time, punch_day, days):
    punch = {
        "touser": openid,
        "template_id": "Pd6cbEhAgyaDH3yAJOtiyIpjSLnaw7g04Q14dhsbw7w",
        "url": url,
        "topcolor": "#FF0000",
        "data": {
            "first": {
                "value": first,
                "color": "#173177"
            },
            "keyword1": {
                "value": punch_time,
                "color": "#173177"
            },
            "keyword2": {
                "value": punch_day,
                "color": "#173177"
            },
            "keyword3": {
                "value": days,
                "color": "#173177"
            },
            "remark": {
                "value": "坚持下去，改变就从现在开始",
                "color": "#173177"
            },
        }
    }
    return punch


# 举报模板提醒
def report_tem(openid, url, content, nickname):
    data = {
        "touser": openid,
        "template_id": "U4UwUUHXqj2EsM3L2x4cOBsLDbQNxZi8OXJdBtd_q2w",
        "url": url,
        "topcolor": "#FF0000",
        "data": {
            "first": {
                "value": "当举报审核通过，被举报人或当日直接记为未完成",
                "color": "#173177"
            },
            "keyword1": {
                "value": content,
                "color": "#173177"
            },
            "keyword2": {
                "value": nickname,
                "color": "#173177"
            },
            "remark": {
                "value": '感谢您的举报',
                "color": "#173177"
            },
        }
    }
    return data


@csrf_exempt
def get_base(request):
    print("开始上传图片")
    user = request.session["user"]
    if request.POST:
        base_str = request.POST.get("base64", "")
        activity = request.POST.get("activity")
        print(activity, '222222222222222222')
        print("获取base成功")
        bash_str = "".join(base_str).split("base64,")[1]
        imgdata = base64.b64decode(bash_str)
        fileName = "{}".format(user.user_id) + "_" + "{}".format(
            timezone.now().strftime("%Y-%m-%d")) + "_" + random_string(16) + ".jpg"
        # 文件存储的实际路径
        filePath = os.path.join(settings.MEDIA_DIR, activity, timezone.now().strftime("%Y-%m-%d") + "/")
        # # 引用所使用的路径
        refPath = os.path.join(settings.MEDIA_ROOT, activity, timezone.now().strftime("%Y-%m-%d") + "/")
        # mysql存储的地址
        file_filepath = filePath + fileName
        file_refpath = refPath + fileName
        if not os.path.exists(filePath):
            os.makedirs(filePath)
        with open(filePath + fileName, 'wb') as f:
            f.write(imgdata)
            print("上传图片保存成功")
        return JsonResponse({"status": 200, "file_filepath": file_filepath, "file_refpath": file_refpath})
    else:
        return JsonResponse({"status": 403})


# 跑步签到时上传图片
@csrf_exempt
def running_sign_in_api(request):
    user = request.session["user"]
    token = get_token()

    """
    跑步签到后端 API
    :param request:
    :return:
    """
    """获取随机数"""
    random = request.POST["random"]
    print("第{}张图片".format(random))
    # request.session['img_random'] = random
    """获取对应的目标的goal id"""
    goal_id = request.POST.get('goal', ' ')
    distance = float(request.POST.get('distance', 0))
    goal = RunningGoal.objects.get(goal_id=goal_id)
    """获取前端传递的两个路径"""
    file_filepath = request.POST.get("file_filepath")
    file_refpath = request.POST.get("file_refpath")
    """获取当前的时间"""
    punch_time = timezone.now()
    """存储一段话"""
    document = request.POST.get("document", " ")
    # 如果是日常模式打卡，则规定distance必须为日常距离
    if goal.goal_type:
        distance = goal.kilos_day
    """将打卡记录存储到数据库中,增加一段话"""
    punch = RunningPunchRecord.objects.create(goal=goal, voucher_ref=file_refpath, voucher_store=file_filepath,
                                              distance=distance,
                                              record_time=punch_time,
                                              document=document)
    goal.add_distance += distance
    goal.save()
    """增加用户的完成天数"""
    UserRecord.objects.update_finish_day(user=user)
    if not goal.goal_type:
        goal.left_distance -= distance
        goal.save()
    if punch:
        try:
            # 将用户的打卡天数加一
            goal.punch_day += 1
            goal.save()
            print("用户{}打卡成功".format(user.user_id))
            if goal.goal_type == 1:
                first = "在{}天内，每日完成{}公里".format(goal.goal_day, goal.kilos_day)
            else:
                first = "在{}天内，一共完成{}公里".format(goal.goal_day, goal.goal_distance)
            # 发送打卡成功模板提醒
            punch_time = timezone.now().strftime("%m-%d")
            # 用户的开始时间是多少
            start_time = RunningGoal.objects.get(goal_id=goal.goal_id).start_time
            print(start_time, "用户的开始时间")
            end_time = start_time + timedelta(days=goal.goal_day)
            print("用户的结束时间", end_time)
            print(end_time.strftime("%Y-%m"))
            url = 'http://wechat.onmytarget.cn/'
            days = '{}/{}'.format(goal.punch_day, goal.goal_day)
            punch_day = "{}到{}".format(start_time.strftime('%m-%d'), end_time.strftime("%m-%d"))
            data = punch_success(user.wechat_id, url, first, punch_time, punch_day, days)
            print("{}用户开始打卡".format(user.user_id))
            do_push(data)
            screen_time = timezone.now().strftime("%Y%m%d")
            random_str = random_string(9)
            user_id = user.user_id
            openid = user.wechat_id
            # print("任务开始")
            from on.celerytask.tasks import send_img
            send_img.delay(user_id, openid, screen_time, random_str, token)
        except Exception as e:
            print(e)
    return JsonResponse({"status": 200})


# 重新上传打卡图片
def upload_again(request):
    user = request.session["user"]
    if request.method == "POST":
        try:
            punch_id = request.POST.get("punch_id")
            document = request.POST.get("document", " ")
            distance = request.POST.get("distance", " ")
            """获取前端传递的两个路径"""
            file_filepath = request.POST.get("file_filepath")
            file_refpath = request.POST.get("file_refpath")
            # 写入文件内容
            record = RunningPunchRecord.objects.get(punch_id=punch_id)
            record.reload += 1
            record.voucher_ref = file_refpath
            record.document = document
            record.voucher_store = file_filepath
            record.record_time = timezone.now()
            record.save()
            goal = RunningGoal.objects.get(user_id=user.user_id)
            # 自由模式剩余距离
            left_distance = goal.left_distance
            if goal.goal_type == 0:
                # 重写之前还剩下的距离
                killo = record.distance + left_distance
                # 重写累计距离
                goal.add_distance = float(goal.add_distance) - float(record.distance) + float(distance)
                goal.left_distance = float(killo) - float(distance)
                goal.save()
                record.distance = distance
                record.save()
        except Exception as e:
            print(e)
        # record.save()
        return JsonResponse({'status': 201})
    else:
        return HttpResponseNotFound


# 跑步面签api
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
        print("用户{}举报他人".format(user.user_id))
        openid = user.wechat_id
        content = "被举报用户发布了虚假信息"
        nickname = UserInfo.objects.get(user_id=user.user_id).nickname
        RunningPunchRecord.objects.report_punch(user_id=user.user_id, punch_id=punch)
        url = 'http://wechat.onmytarget.cn/'
        data = report_tem(openid, url, content, nickname)
        do_push(data)
        return JsonResponse({'status': 200})
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
        user_wechat_id = request.session['user'].wechat_id
        goal = request.POST['goal']
        # 免签卡记录的时间是8个小时以后的时间, 这一点作息与跑步不同
        use_ticket = UserTicket.objects.use_ticket(goal_id=goal, ticket_type='NS',
                                                   use_time=timezone.now() + timezone.timedelta(hours=8))
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
        use_ticket = UserTicket.objects.use_ticket(goal_id=goal, ticket_type='D',
                                                   use_time=timezone.now() + timezone.timedelta(hours=8))
        if use_ticket:
            return JsonResponse({'status': 200})
        else:
            return JsonResponse({'status': 201})
    else:
        return HttpResponseNotFound


# 作息睡觉打卡
def sleeping_sleep_handler(request):
    if request.POST:
        user = request.session['user']
        # 查询当前打卡用户的openid
        openid = user.wechat_id
        # 查询用户的nickname
        nickname = user.nickname
        goal_id = request.POST['goal']
        goal = SleepingGoal.objects.get(goal_id=goal_id)
        # 当前用户的打卡时间
        punch_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        # 如果record无误，则打卡成功；否则打卡失败
        record = SleepingPunchRecord.objects.create_sleep_record(goal=goal)
        remark_msg = "记得明天早晨也要打卡哦"
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
        user = request.session['user']
        # 查询当前打卡用户的openid
        openid = user.wechat_id
        # 查询用户的nickname
        nickname = user.nickname
        goal_id = request.POST['goal']
        goal = SleepingGoal.objects.get(goal_id=goal_id)
        punch_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

        # 如果record无误，则返回早起时间；否则打卡失败
        record = goal.punch.update_getup_record()
        remark_msg = ""
        if record:
            return JsonResponse({'status': 200,
                                 'getuptime': record.get_up_time.time().strftime("%H:%M"),
                                 'checktime': record.check_time.time().strftime("%H:%M")})
        else:

            return JsonResponse({'status': 201})


# 作息确认打卡
def sleeping_confirm_handler(request):
    if request.POST:
        user = request.session['user']
        # 查询当前打卡用户的openid
        openid = user.wechat_id
        # 查询用户的nickname
        nickname = user.nickname
        goal_id = request.POST['goal']
        goal = SleepingGoal.objects.get(goal_id=goal_id)
        punch_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        # 如果record无误，则返回确认时间；否则打卡失败
        record = goal.punch.update_confirm_time()
        if record:
            """增加用户的完成天数"""
            UserRecord.objects.update_finish_day(user=request.session['user'])
            return JsonResponse({'status': 200,
                                 'time': record.confirm_time.time().strftime("%H:%M")})
        else:
            return JsonResponse({'status': 201})


# 查询擂主押金
def search_deposit(request):
    if request.GET:

        winner = RunningGoal.objects.get(user_id='100101').activate_deposit
        if winner:
            return JsonResponse({'status': 200, "winner": winner})
        else:
            return JsonResponse({'status': 403})
    else:
        return HttpResponseNotFound


# 开启书籍阅读
def reading_start_handler(request):
    if request.POST:
        user = request.session.get("user")
        goal_id = request.POST.get("goal")
        try:
            ReadingGoal.objects.filter(goal_id=goal_id).update(is_start=1, start_time=timezone.now())
            UserOrder.objects.filter(goal_id=goal_id).update(confirm_time=timezone.now())
            return JsonResponse({"status": 200})
        except Exception as e:
            print("没有保存成功{}".format(e))
            return JsonResponse({'status': 201})
    else:
        return HttpResponseNotFound


#
# 书籍阅读打卡
@csrf_exempt
def reading_record_handler(request):
    if request.POST:
        user = request.session['user']
        try:
            read = ReadTime.objects.filter(user_id=user.user_id)[0]
            time_range = (timezone.now() - read.start_read).seconds
            read.time_range = time_range
            read.is_reading = 0
            read.save()
            book_id = request.POST.get("book_id")
            # 本次阅读了page页，耗时time秒
            goal_id = request.POST['goal']
            # timedelta = request.POST['time']
            page = request.POST['page']
            if not all([goal_id, page, book_id]):
                return JsonResponse({"status": 201, "errmsg": "参数不完整"})
            punch_id = ReadingPunchRecord.objects.filter(record_time=timezone.now().strftime("%Y-%m-%d"),
                                                         user_id=user.user_id)
            print(punch_id, 11111111111111111111111111)
            book = BookInfo.objects.get(book_id=book_id)
            suggest_day = book.suggest_day
            page_num = book.page_num
            guaranty = book.guaranty
            # 每页的金额数
            page_avg = decimal.Decimal(guaranty / page_num)
            record_time = timezone.now().strftime("%Y-%m-%d")
            print("金额计算成功")
            # 新建一个阅读记录，并返回返回值
            punch = ReadingPunchRecord.objects.create_record(goal_id=goal_id,
                                                             today_page=page,
                                                             today_time=time_range,
                                                             page_avg=page_avg,
                                                             record_time=record_time,
                                                             punch_id=punch_id,
                                                             user_id=user.user_id,
                                                             suggest_day=suggest_day)
            print(punch,"当前的读书系数")
            return JsonResponse({"status": 200,"punch":punch})
        except Exception as e:
            print(e)
    else:
        return HttpResponseNotFound


# 开始阅读
def save_start_time(request):
    user = request.session.get("user")
    if request.POST:
        read = ReadTime.objects.get_start_read(user_id=user.user_id)
        if read:
            return JsonResponse({"status": 200})
        else:
            return JsonResponse({"status": 201})
    else:
        return HttpResponseNotFound


# 完成阅读
def finish_read(request):
    user = request.session.get("user")
    if request.POST:
        read = ReadTime.objects.filter(user_id=user.user_id)[0]
        try:
            time_range = (timezone.now() - read.start_read).seconds
            print(type(time_range))
            read.time_range = time_range
            read.save()
            return JsonResponse({"status": 200, "time_range": time_range})
        except Exception as e:
            print(e)
    else:
        return HttpResponseNotFound


# 用户主动结束
def success_read(request):
    user = request.session.get("user")
    if request.POST:
        try:
            goal_id = request.POST.get("goal")
            ReadingGoal.objects.filter(goal_id=goal_id, user_id=user.user_id).update(status="SUCCESS")
            return JsonResponse({"status": 200})
        except Exception as e:
            print("未结束成功", e)
    else:
        return HttpResponseNotFound


# 放弃阅读
@csrf_exempt
def give_up_read(request):
    user = request.session.get("user")
    if request.POST:
        try:
            ReadTime.objects.filter(user_id=user.user_id).update(start_read=timezone.now(), is_reading=0)
            return JsonResponse({"status": 200})
        except Exception as e:
            print("放弃阅读失败", e)
            return JsonResponse({"status": 403})
    else:
        return JsonResponse({"status": 403})


@csrf_exempt
def delete_comments(request):
    from on.activities.reading.models import Comments
    user = request.session.get("user")
    print("开始删除")
    if request.POST:
        id = request.POST.get("id")
        try:
            Comments.objects.filter(id=id).update(is_delete=1)
            return JsonResponse({"status": 200})
        except Exception as e:
            print("删除失败", e)
            return JsonResponse({"status": 403})
    else:
        return JsonResponse({"status": 403})


# 存储用户评论
@csrf_exempt
def save_comments(request):
    print("用户开始评论")
    from on.activities.reading.models import Comments
    user = request.session.get("user")
    time_now = timezone.now().strftime("%Y-%m-%d %H:%M")
    if request.POST:
        try:
            content = request.POST.get("content")
            print(content)
            voucher_ref = request.POST.get("voucher_ref")
            print(voucher_ref)
            voucher_store = request.POST.get("voucher_store")
            print(voucher_store)
            # 若用户表不存在，则先给用户创建一个jilu
            Comments.objects.create(user=user, content=content, voucher_ref=voucher_ref, voucher_store=voucher_store,
                                    c_time=time_now)
            return JsonResponse({"status": 200})
        except Exception as e:
            print("评论失败", e)
            return JsonResponse({"status": 401})
    else:
        return JsonResponse({"status": 401})


# 对用户的评论点赞

@csrf_exempt
def read_prise(request):
    from on.activities.reading.models import Comments

    user = request.session.get("user")
    if request.POST:
        id = request.POST.get("id")
        try:
            Comments.objects.praise_comment(user_id=user.user_id, punch_id=id)
            return JsonResponse({"status": 200})
        except Exception as e:
            print("点赞失败", e)
            return JsonResponse({"status": 401})
    else:
        return JsonResponse({"status": 401})


# 对用户的评论举报
@csrf_exempt
def read_report(request):
    from on.activities.reading.models import Comments

    user = request.session.get("user")
    if request.POST:
        id = request.POST.get("id")
        try:
            Comments.objects.report_comment(user_id=user.user_id, punch_id=id)
            return JsonResponse({"status": 200})
        except Exception as e:
            print("举报失败", e)
            return JsonResponse({"status": 401})
    else:
        return JsonResponse({"status": 401})


@csrf_exempt
def load_comments(request):
    from on.activities.reading.models import Comments
    if request.POST:
        # 当前是第几条
        c_num = int(request.POST.get("c_num"))
        comm_list = Comments.objects.all().order_by('-c_time')
        # 评论的数量
        c_count = len(comm_list)
        # 要调整绕的条数
        finish = c_num + 10
        if c_count >= finish:
            is_final = 1
            is_final = is_final
            comm_list = comm_list[c_num:finish]
        else:
            is_final = 0
            comm_list = comm_list[c_num:c_count]
        print(is_final,comm_list)
        # return JsonResponse({"status": 200, "is_final": is_final ,"comm_list": comm_list})
        return JsonResponse({"status": 200,"finish":finish})

    return JsonResponse({"status": 403})


@csrf_exempt
def num_test(request):
    return render(request, 'user/test.html')

#用户评论回复
@csrf_exempt
def reply(request):
    user = request.session.get("user")
    from on.activities.reading.models import Reply
    if request.POST:
        r_content = request.POST.get("r_content")
        other_id = request.POST.get("other_id")
        try:
            Reply.objects.create(user_id=user.user_id,other_id=other_id.replace("-",""),r_content=r_content)
            return JsonResponse({"status":200})
        except Exception as e:
            print("用户评论失败",e)
            return JsonResponse({"status":403})
    return JsonResponse({"status":403})

