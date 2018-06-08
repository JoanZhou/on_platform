import base64
import decimal
import json
import os
import time
from datetime import timedelta
from logging import getLogger

import requests
from django.conf import settings
from django.http import JsonResponse, HttpResponseNotFound
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from wechatpy.utils import random_string

from on.activities.reading.models import ReadTime, BookInfo
from on.models import SleepingGoal, ReadingGoal
from on.activities.running.models import RunningPunchRecord, RunReply, RunningGoal, RunningPunchPraise, \
    RunningPunchReport
from on.activities.sleeping.models import SleepingPunchRecord, SleepingPunchPraise, ReplySleep, CommentSleep
from on.activities.reading.models import ReadingPunchRecord, ReadingPunchPraise, Reply, Comments
from on.activities.sleeping.models import SleepingPunchRecord, SleepingPunchPraise, ReplySleep
from on.activities.reading.models import ReadingPunchRecord, ReadingPunchPraise, Reply
from on.models import RunningGoal, RunningPunchRecord, SleepingGoal, SleepingPunchRecord, ReadingGoal, \
    ReadingPunchRecord #, RidingGoal, RidingPunchRecord
from on.settings.local import DEBUG
from on.task import send_img
from on.temp.push_template import do_push
from on.user import UserTicket, UserRecord, UserInfo, UserOrder
from .task import send_img_test
# from on.activities.riding.punchrecord import RidingPunchRecord
# from on.activities.riding.model import RidingGoal

AppSecret = "23f0462bee8c56e09a2ac99321ed9952"
AppId = "wx4495e2082f63f8ac"

logger = getLogger("app")


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

    """
    跑步签到后端 API
    :param request:
    :return:
    """
    """获取随机数"""
    random = request.POST["random"]
    try:
        resp = send_img.delay(user.user_id, random, user.wechat_id, "1")
        print("第{}张图片的发送结果{}".format(random, resp))
    except Exception as e:
        print(e)
        logger.error(e)

    """获取对应的目标的goal id"""
    goal_id = request.POST.get('goal', ' ')
    distance = float(request.POST.get('distance', 0))
    print(distance, "从前端获取传递的距离")
    goal = RunningGoal.objects.get(goal_id=goal_id)
    """获取前端传递的两个路径"""
    file_filepath = request.POST.get("file_filepath")
    file_refpath = request.POST.get("file_refpath")
    """获取当前的时间"""
    punch_time = timezone.now()
    """存储一段话"""
    document = request.POST.get("document", " ")
    # 如果是日常模式打卡，则规定distance必须为日常距离
    # if goal.goal_type:
    #     distance = goal.kilos_day
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
        except Exception as e:
            print(e)
            logger.error(e)
    return JsonResponse({"status": 200})


@csrf_exempt
def run_test(request):
    print("开始打卡")
    """
        跑步签到后端 API
        :param request:
        :return:
        """
    """获取随机数"""
    user = request.session.get("user")
    random = request.POST.get("random")
    try:
        resp = send_img.delay(user.user_id, random, user.wechat_id, "1")
        print("第{}张图片的发送结果{}".format(random, resp))
    except Exception as e:
        print(e)
        logger.error(e)
    """获取对应的目标的goal id"""
    goal_id = request.POST.get('goal', ' ')
    distance = float(request.POST.get('distance', 0))
    print(distance, user.user_id)
    goal = RunningGoal.objects.get(goal_id=goal_id)
    """获取前端传递的两个路径"""
    file_filepath = request.POST.get("file_filepath")

    file_refpath = request.POST.get("file_refpath")
    document = request.POST.get("document", " ")
    """获取当前的时间"""
    punch_time = timezone.now()
    print("获取参数完成")
    try:
        punch = RunningPunchRecord.objects.create_run_redord(goal=goal,
                                                             user_id=user.user_id,
                                                             voucher_ref=file_refpath,
                                                             voucher_store=file_filepath,
                                                             distance=distance,
                                                             record_time=punch_time,
                                                             document=document)
        if punch:
            goal.punch_day += 1
            goal.save()
        return JsonResponse({"status": 200})
    except Exception as e:
        logger.error(e)
        return JsonResponse({"status": 405})


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


# 跑步免签api
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
@csrf_exempt
def sleeping_sleep_handler(request):
    if request.POST:

        user = request.session.get("user")
        goal_id = request.POST['goal']
        random = int(request.POST.get("random"))
        sleep_type = int(request.POST.get("sleep_type"))
        # if not all([goal_id,sleep_type]):
        #     return JsonResponse({"status":403,"errmsg":"数据不完整"})
        goal = SleepingGoal.objects.get(goal_id=goal_id)
        record = ""
        try:
            if DEBUG:
                if sleep_type == 0:
                    # 如果record无误，则打卡成功；否则打卡失败
                    record = SleepingPunchRecord.objects.create_sleep_record(goal=goal, sleep_type=sleep_type,
                                                                             user_id=user.user_id)
                    send_img.delay(user.user_id, random, user.wechat_id, "0")
                    print("第{}张图片的发送结果".format(random))
                elif sleep_type == 1:
                    record = SleepingPunchRecord.objects.update_getup_record(goal=goal, sleep_type=sleep_type,
                                                                             user_id=user.user_id)
                    send_img.delay(user.user_id, random, user.wechat_id, "0")
                    print("第{}张图片的发送结果".format(random))
                if record:
                    return JsonResponse({'status': 200})
                else:
                    return JsonResponse({'status': 201})
            else:

                if sleep_type == 0:
                    # 如果record无误，则打卡成功；否则打卡失败
                    record = SleepingPunchRecord.objects.create_sleep_record(goal=goal, sleep_type=sleep_type,
                                                                             user_id=user.user_id)
                    send_img.delay(user.user_id, random, user.wechat_id, "0")
                    print("第{}张图片的发送结果".format(random))
                elif sleep_type == 1:
                    record = SleepingPunchRecord.objects.update_getup_record(goal=goal, sleep_type=sleep_type,
                                                                             user_id=user.user_id)
                    send_img.delay(user.user_id, random, user.wechat_id, "0")
                    print("第{}张图片的发送结果".format(random))

                if record:
                    return JsonResponse({'status': 200})
                else:
                    return JsonResponse({'status': 201})
        except Exception as e:
            print(e)
            logger.error(e)
            return JsonResponse({"status": 403})

    else:
        return JsonResponse({"status": 403})


# @csrf_exempt
# def get_up_time_record(request):
#     if request.POST:


# # 作息起床打卡
# def sleeping_getup_handler(request):
#     if request.POST:
#         user = request.session['user']
#         goal_id = request.POST['goal']
#         goal = SleepingGoal.objects.get(goal_id=goal_id)
#         punch_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
#
#         # 如果record无误，则返回早起时间；否则打卡失败
#         record = goal.punch.update_getup_record()
#         remark_msg = ""
#         if record:
#             return JsonResponse({'status': 200,
#                                  'getuptime': record.get_up_time.time().strftime("%H:%M"),
#                                  'checktime': record.check_time.time().strftime("%H:%M")})
#         else:
#
#             return JsonResponse({'status': 201})


# 作息确认打卡
def sleeping_confirm_handler(request):
    if request.POST:
        user = request.session['user']
        # 查询当前打卡用户的openid
        # 查询用户的nickname
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
            book = BookInfo.objects.get(book_id=book_id)
            suggest_day = book.suggest_day
            page_num = book.page_num
            guaranty = book.guaranty
            # 每页的金额数
            page_avg = decimal.Decimal(guaranty / page_num)
            record_time = timezone.now().strftime("%Y-%m-%d")
            # 新建一个阅读记录，并返回返回值
            punch = ReadingPunchRecord.objects.create_record(goal_id=goal_id,
                                                             today_page=page,
                                                             today_time=time_range,
                                                             page_avg=page_avg,
                                                             record_time=record_time,
                                                             punch_id=punch_id,
                                                             user_id=user.user_id,
                                                             suggest_day=suggest_day)
            print(punch, "当前的读书系数")
            return JsonResponse({"status": 200, "punch": punch})
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
    if request.POST:
        user = request.session.get("user")
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
    from on.activities.reading.models import Comments
    user = request.session.get("user")
    time_now = timezone.now().strftime("%Y-%m-%d %H:%M")
    if request.POST:
        try:
            content = request.POST.get("content")
            voucher_ref = request.POST.get("voucher_ref")
            voucher_store = request.POST.get("voucher_store")
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
    if request.POST:
        user = request.session.get("user")
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


def get_ten_list(c_num, comm_list):
    has_next = 1
    # 评论的数量qq@
    c_count = len(comm_list)
    # 要调整绕的条数
    finish = c_num + 10
    if c_count >= finish:
        comm_list = comm_list[c_num:finish]
    else:
        has_next = 0
        comm_list = comm_list[c_num:c_count]
    return has_next, comm_list, finish


def comment_message(comm_list, reply_obj, prase_obj, user):
    cont = []
    for comm in comm_list:
        reply = reply_obj.objects.filter(other_id=str(comm.id))
        response = [{"content": i.r_content, "other_id": i.user_id, "nickname": i.get_user_message.nickname} for
                    i in reply] if len(reply) > 0 else ""

        prise = prase_obj.objects.filter(punch_id=comm.id, user_id=user.user_id)

        is_no_prise = 1 if len(prise) > 0 else 0
        ref = comm.voucher_ref.split(",") if len(comm.voucher_ref) > 0 else ""
        top = comm.is_top
        if top == True or top == 0 and comm.is_delete == False or comm.is_delete == 0:
            cont.append({
                "id": str(comm.id),
                'user_id': str(comm.user_id),
                "content": comm.content.decode(),
                "c_time": str(comm.c_time),
                "prise": comm.prise,
                "report": comm.report,
                "voucher_ref": ref,
                "is_top": comm.is_top,
                "headimgurl": comm.get_some_message.headimgurl,
                "nickname": comm.get_some_message.nickname,
                "is_no_prise": is_no_prise,
                "reply_data": response
            })
    return cont


def load_sleep(c_num, user):
    from on.activities.sleeping.models import CommentSleep, ReplySleep, SleepingPunchPraise
    comm_list = CommentSleep.objects.all().order_by('-c_time')
    try:
        has_next, comm_list, finish = get_ten_list(c_num, comm_list)
        cont = comment_message(comm_list, ReplySleep, SleepingPunchPraise, user)
        return cont, has_next, finish
    except Exception as e:
        logger.error(e)
        print(e)


def load_riding(c_num, user):
    from on.activities.riding.model import CommentRiding, RidingReply, RidingPunchPraise
    comm_list = CommentRiding.objects.all().order_by('-c_time')
    try:
        has_next, comm_list, finish = get_ten_list(c_num, comm_list)
        cont = comment_message(comm_list, RidingReply, RidingPunchPraise, user)
        return cont, has_next, finish
    except Exception as e:
        logger.error(e)
        print(e)


def load_read(c_num, user):
    from on.activities.reading.models import Comments, Reply, ReadingPunchPraise
    comm_list = Comments.objects.all().order_by('-c_time')
    try:
        has_next, comm_list, finish = get_ten_list(c_num, comm_list)
        cont = comment_message(comm_list, Reply, ReadingPunchPraise, user)
        return cont, has_next, finish
    except Exception as e:
        print(e)
        logger.error(e)


def load_run(c_num, user):
    from on.activities.running.models import RunningPunchRecord, RunReply, RunningGoal, RunningPunchPraise, \
        RunningPunchReport

    comm_list = RunningPunchRecord.objects.all().order_by("-record_time")
    has_next = 1
    # 评论的数量qq@
    c_count = len(comm_list)
    # 要调整绕的条数
    finish = c_num + 10
    if c_count >= finish:
        comm_list = comm_list[c_num:finish]
    else:
        has_next = 0
        comm_list = comm_list[c_num:c_count]
    datas = []
    for comm in comm_list:
        every_user = UserInfo.objects.get(user_id=comm.goal.user_id)
        report = RunningPunchReport.objects.filter(punch_id=comm.punch_id)
        reply = RunReply.objects.filter(other_id=str(comm.punch_id).replace("-", ""))
        # print("用户回复的条数", len(reply), reply, comm.punch_id)
        response = [{"content": i.r_content, "other_id": i.user_id, "nickname": user.nickname} for
                    i in reply] if len(reply) > 0 else ""
        # print(response, "用户回复的内容")
        is_no_report = 1 if len(report) > 0 else 0
        prise = RunningPunchPraise.objects.filter(punch_id=comm.punch_id, user_id=user.user_id)
        is_no_prise = 1 if len(prise) > 0 else 0
        ref = comm.voucher_ref.split(",") if len(comm.voucher_ref) > 0 else ""
        nickname = every_user.nickname
        datas.append({
            'user_id': str(comm.goal.user_id),
            "punch_id": str(comm.punch_id),
            "content": comm.document,
            "c_time": str(comm.record_time),
            "prise": comm.praise,
            "report": comm.report,
            "voucher_ref": ref,
            "headimgurl": every_user.headimgurl,
            "nickname": nickname,
            "is_no_report": is_no_report,
            "is_no_prise": is_no_prise,
            "reply_data": response,
            "distance": comm.distance
        })
    return datas, has_next, finish


def get_mine(user_id, punchrecord_obj, reply_obj, prase_obj):
    mine = []
    comm_list = punchrecord_obj.objects.filter(user_id=user_id)
    for comm in comm_list:
        reply = reply_obj.objects.filter(other_id=str(comm.id))
        response = [{"content": i.r_content, "other_id": i.user_id, "nickname": i.get_user_message.nickname} for
                    i in reply] if len(reply) > 0 else ""

        prise = prase_obj.objects.filter(punch_id=comm.id, user_id=user_id)

        is_no_prise = 1 if len(prise) > 0 else 0
        ref = comm.voucher_ref.split(",") if len(comm.voucher_ref) > 0 else ""
        top = comm.is_top
        mine.append({
            "id": str(comm.id),
            'user_id': str(comm.user_id),
            "content": comm.content.decode(),
            "c_time": str(comm.c_time),
            "prise": comm.prise,
            "report": comm.report,
            "voucher_ref": ref,
            "is_top": top,
            "headimgurl": comm.get_some_message.headimgurl,
            "nickname": comm.get_some_message.nickname,
            "is_no_prise": is_no_prise,
            "reply_data": response
        })
    return mine


@csrf_exempt
def load_mine(request):
    if request.method == "POST":
        try:
            user = request.session.get("user")
            user_id = user.user_id
            activity_type = int(request.POST.get("activity_type"))
            # print(activity_type, type(activity_type))
            mine = []
            if activity_type == 1:

                nickname = user.nickname
                headimgurl = user.headimgurl
                comm_list = RunningPunchRecord.objects.filter(goal__user_id=user_id).order_by("-record_time")
                mine = []
                for comm in comm_list:
                    report = RunningPunchReport.objects.filter(punch_id=str(comm.punch_id).replace("-", ""))
                    reply = RunReply.objects.filter(other_id=str(comm.punch_id).replace("-", ""))
                    response = [{"content": i.r_content, "other_id": i.user_id, "nickname": i.get_user_message.nickname}
                                for
                                i in reply] if len(reply) > 0 else ""
                    is_no_report = 1 if len(report) > 0 else 0
                    prise = RunningPunchPraise.objects.filter(punch_id=comm.punch_id, user_id=user_id)
                    is_no_prise = 1 if len(prise) > 0 else 0
                    ref = comm.voucher_ref.split(",") if len(comm.voucher_ref) > 0 else ""
                    mine.append({
                        'user_id': str(comm.goal.user_id),
                        "punch_id": str(comm.punch_id),
                        "content": comm.document,
                        "c_time": str(comm.record_time),
                        "prise": comm.praise,
                        "report": comm.report,
                        "voucher_ref": ref,
                        "headimgurl": headimgurl,
                        "nickname": nickname,
                        "is_no_report": is_no_report,
                        "is_no_prise": is_no_prise,
                        "reply_data": response,
                        "distance": comm.distance
                    })
            elif activity_type == 0:

                mine = get_mine(user_id=user_id, prase_obj=SleepingPunchPraise, punchrecord_obj=CommentSleep,
                                reply_obj=ReplySleep)
            elif activity_type == 2:

                mine = get_mine(user_id=user_id, prase_obj=ReadingPunchPraise, punchrecord_obj=Comments,
                                reply_obj=Reply)
            return JsonResponse({"status": 200, "mine": json.dumps(mine)})
        except RunningPunchRecord.DoesNotExist as e:
            print(e)
            return JsonResponse({"status": 404, "errmsg": "没有查询到该用户的打卡记录"})
        except Exception as e:
            logger.error(e)
            print(e)
            return JsonResponse({"status": 405})


#
@csrf_exempt
def load_comments(request):
    if request.method == 'POST':
        user = request.session.get("user")
        user_id = user.user_id
        # 当前是第几条
        c_num = int(request.POST.get("c_num"))
        activate_type = int(request.POST.get("activate_type"))
        try:
            finish = None
            cont = None
            has_next = None
            if activate_type == 2:
                cont, has_next, finish = load_read(c_num, user)
            elif activate_type == 0:
                cont, has_next, finish = load_sleep(c_num, user)
            elif activate_type == 1:
                cont, has_next, finish = load_run(c_num, user)
            elif activate_type == 4:
                cont, has_next, finish = load_riding(c_num, user)
            return JsonResponse({"status": 200, "cont": json.dumps(cont), "has_next": has_next, "finish": finish})
        except Exception as e:
            logger.error(e)
            print(e)
            return JsonResponse({"status": 405})

    return JsonResponse({"status": 403})


@csrf_exempt
def num_test(request):
    return render(request, 'user/test.html')


# def send_img(user_id,random,openid,activity_type):
@csrf_exempt
def update_all_profit(request):
    from on.user import BonusRank
    sleep = SleepingGoal.objects.all()
    for user in sleep:
        money = user.bonus + user.extra_earn
        rank = BonusRank.objects.filter(user_id=user.user_id)
        if rank:
            rank = rank[0]
            rank.sleep = money
            rank.save()
        else:
            BonusRank.objects.create(user_id=user.user_id, sleep=money)
    print("睡眠活动成功")
    run = RunningGoal.objects.all()
    for user in run:
        money = user.bonus + user.extra_earn
        rank = BonusRank.objects.filter(user_id=user.user_id)
        if rank:
            rank = rank[0]
            rank.run = money
            rank.save()
        else:
            BonusRank.objects.create(user_id=user.user_id, run=money)
    print("跑步活动成功")
    read = ReadingGoal.objects.all()
    for user in read:
        money = user.bonus + user.extra_earn
        rank = BonusRank.objects.filter(user_id=user.user_id)
        if rank:
            rank = rank[0]
            rank.read = money
            rank.save()
        else:
            BonusRank.objects.create(user_id=user.user_id, read=money)
    print("读书活动成功")
    return JsonResponse({"status": 200})


@csrf_exempt
def update_punchday(request):
    # from on.activities.sleeping.models import Coefficient
    # sleep = SleepingGoal.objects.filter(status="ACTIVE")
    # for user in sleep:
    #     # punch = SleepingPunchRecord.objects.filter(user_id=user.user_id, get_up_time__isnull=False)
    #     # user.punch_day = int(len(punch))
    #     # user.save()
    #     if user.goal_day>30:
    #         coeff = Coefficient.objects.get(user_id=user.user_id)
    #         if user.sleep_type == 1:
    #             if coeff.new_coeff > 0:
    #                 coeff.new_coeff -= decimal.Decimal(2)
    #         else:
    #             if coeff.new_coeff > 0:
    #                 coeff.new_coeff -= decimal.Decimal(2.4)
    #         print("更新成功")
    #         coeff.save()
    # return JsonResponse({"status": 200})
    run = RunningGoal.objects.all()
    from on.activities.running.models import RunCoefficient
    for user in run:
        coeff = RunCoefficient.objects.filter(user_id=user.user_id)
        if coeff:
            print("已经有了就不需要创建")
        else:
            RunCoefficient.objects.create(user_id=user.user_id, goal_type=user.goal_type,
                                          default_coeff=user.coefficient)
            print("创建成功")
    return JsonResponse({"status": 200})


@csrf_exempt
def init_profit(request):
    for i in range(100100, 101585):
        s_b = 0
        run_b = 0
        read_b = 0
        s_e = 0
        run_e = 0
        read_e = 0
        s_d = 0
        run_d = 0
        read_d = 0
        user = None
        try:
            user = UserInfo.objects.get(user_id=i)
        except Exception as e:
            print(e)
            continue
        sleep = SleepingGoal.objects.filter(user_id=i).exclude(status="PENDING")
        if len(sleep) > 0:
            sleep = sleep[0]
            s_b = sleep.bonus
            s_e = sleep.extra_earn
            s_d = sleep.guaranty + sleep.down_payment
        run = RunningGoal.objects.filter(user_id=i).exclude(status="PENDING")
        if len(run) > 0:
            run = run[0]
            run_b = run.bonus
            run_e = run.extra_earn
            run_d = run.guaranty + run.down_payment
        read = ReadingGoal.objects.filter(user_id=i).exclude(status="PENDING")
        if len(read) > 0:
            read = read[0]
            read_b = read.bonus
            read_e = read.extra_earn
            read_d = read.guaranty + read.down_payment
        total_b = s_b + run_b + read_b
        total_e = s_e + run_e + read_e
        total_d = s_d + run_d + read_d
        user.deposit = total_d
        user.add_money = total_b
        user.extra_money = total_e
        try:
            user.save()
            print("保存成功", user.user_id)
        except Exception as e:
            print(e)
    return JsonResponse({"status": 200})

@csrf_exempt
def sendImg(request):
    print("测试发送图片")
    send_img_test.delay()
    return JsonResponse({"status":200})

# 用户评论回复
@csrf_exempt
def reply(request):
    user = request.session.get("user")
    from on.activities.reading.models import Reply
    if request.POST:
        r_content = request.POST.get("r_content")
        other_id = request.POST.get("other_id")
        time_now = timezone.now().strftime("%Y-%m-%d %H:%M")
        try:
            Reply.objects.create(user_id=user.user_id, other_id=other_id.replace("-", ""), r_content=r_content)
            return JsonResponse({"status": 200})
        except Exception as e:
            print("用户评论失败", e)
            return JsonResponse({"status": 403})
    return JsonResponse({"status": 403})


# 用户评论回复,两种活动，不可共用一个表
@csrf_exempt
def run_reply(request):
    user = request.session.get("user")
    from on.activities.running.models import RunReply
    if request.POST:
        r_content = request.POST.get("r_content")
        other_id = request.POST.get("other_id")
        time_now = timezone.now().strftime("%Y-%m-%d %H:%M")
        try:
            RunReply.objects.create(user_id=user.user_id, other_id=other_id.replace("-", ""), r_content=r_content,
                                    create_time=time_now)
            return JsonResponse({"status": 200})
        except Exception as e:
            print("用户评论失败", e)
            return JsonResponse({"status": 403})
    return JsonResponse({"status": 403})


# sleeping 评论
@csrf_exempt
def save_sleep_comments(request):
    from on.activities.sleeping.models import CommentSleep
    user = request.session.get("user")
    time_now = timezone.now().strftime("%Y-%m-%d %H:%M")
    if request.POST:
        try:
            content = request.POST.get("content")
            voucher_ref = request.POST.get("voucher_ref")
            voucher_store = request.POST.get("voucher_store")
            # 若用户表不存在，则先给用户创建一个jilu
            CommentSleep.objects.create(user=user, content=content, voucher_ref=voucher_ref,
                                        voucher_store=voucher_store,
                                        c_time=time_now)
            return JsonResponse({"status": 200})
        except Exception as e:
            print("评论失败", e)
            return JsonResponse({"status": 401})
    else:
        return JsonResponse({"status": 401})


# sleeping 回复
@csrf_exempt
def sleep_reply(request):
    user = request.session.get("user")
    from on.activities.sleeping.models import ReplySleep
    if request.POST:
        r_content = request.POST.get("r_content")
        other_id = request.POST.get("other_id")
        try:
            ReplySleep.objects.create(user_id=user.user_id, other_id=other_id.replace("-", ""), r_content=r_content)
            return JsonResponse({"status": 200})
        except Exception as e:
            print("用户评论失败", e)
            return JsonResponse({"status": 403})
    return JsonResponse({"status": 403})


# sleeping 点赞
@csrf_exempt
def sleep_prise(request):
    from on.activities.sleeping.models import CommentSleep

    user = request.session.get("user")
    if request.POST:
        id = request.POST.get("id")
        try:
            CommentSleep.objects.praise_comment(user_id=user.user_id, punch_id=id)
            return JsonResponse({"status": 200})
        except Exception as e:
            print("点赞失败", e)
            return JsonResponse({"status": 401})
    else:
        return JsonResponse({"status": 401})


# sleeping删除评论
@csrf_exempt
def delete_sleep_comments(request):
    from on.activities.sleeping.models import CommentSleep
    if request.POST:
        user = request.session.get("user")
        id = request.POST.get("id")
        try:
            CommentSleep.objects.filter(id=id).update(is_delete=1)
            return JsonResponse({"status": 200})
        except Exception as e:
            print("删除失败", e)
            return JsonResponse({"status": 403})
    else:
        return JsonResponse({"status": 403})


#  收益转余额
active = {
    '0': SleepingGoal,
    '1': RunningGoal,
    # '4': RidingGoal,
}


@csrf_exempt
def bonus_to_balance(request):
    if request.POST:
        try:
            user = request.session.get('user')
            goal_id = request.POST['goal']
            activity_type = request.POST.get('activity_type')
            obj = active.get(activity_type)

            instance = obj.objects.get(goal_id=goal_id)
            user = UserInfo.objects.get(user_id=user.user_id)

            balance = decimal.Decimal(instance.bonus) + decimal.Decimal(instance.extra_earn)
            user.balance += balance
            user.add_money -= instance.bonus
            user.extra_money -= instance.extra_earn
            user.save()

            instance.bonus = 0
            instance.extra_earn = 0
            instance.save()
            print('成功')
            return JsonResponse({'status': 200})
        except Exception as e:
            print('操作失败', e)
            return JsonResponse({"status": 403})
    else:
        return JsonResponse({'status': 403})


@csrf_exempt
def walk_punch(request):
    if request.POST:
        from on.activities.walking.models import WalkingPunchRecord
        user = request.session.get("user")
        record_time = timezone.now().strftime("%Y-%m-%d")
        voucher_ref = request.POST.get("voucher_ref")
        distance = request.POST.get("distance")
        goal_id = request.POST.get("goal_id")
        document = request.POST.get("document", " ")
        if not all([distance, goal_id, document]):
            return JsonResponse({"status": 403, "errmsg": "the argument is not enough"})
        try:
            goal = WalkingPunchRecord.objects.create(record_time=record_time,
                                                     voucher_ref=voucher_ref,
                                                     distance=distance,
                                                     goal_id=goal_id,
                                                     document=document)
            return JsonResponse({"status": 200, "goal": goal})
        except Exception as e:
            print(e)


@csrf_exempt
def save_walk_comments(request):
    pass


@csrf_exempt
def delete_walk_comments(request):
    pass


@csrf_exempt
def walk_report(request):
    if request.POST:
        from on.activities.walking.models import WalkingPunchRecord
        user = request.session.get("user")
        id = request.POST.get("id")
        try:
            WalkingPunchRecord.objects.report_walk(user_id=user.user_id, punch_id=id)
            return JsonResponse({"status": 200})
        except Exception as e:
            print("点赞失败", e)
            return JsonResponse({"status": 401})
    else:
        return JsonResponse({"status": 401})


@csrf_exempt
def walk_praise(request):
    if request.POST:
        from on.activities.walking.models import WalkingPunchRecord
        user = request.session.get("user")
        id = request.POST.get("id")
        try:
            WalkingPunchRecord.objects.praise_walk(user_id=user.user_id, punch_id=id)
            return JsonResponse({"status": 200})
        except Exception as e:
            print("点赞失败", e)
            return JsonResponse({"status": 401})
    else:
        return JsonResponse({"status": 401})


@csrf_exempt
def goal_ranking_list(request):
    if request.method == 'GET':
        activity_type = int(request.GET.get('activity_type'))
        user = request.session.get('user')
        if activity_type == 0:
            from on.activities.sleeping.models import sleep_ranking_list
            sleep_list = sleep_ranking_list(user)
            # print('sleep_list', sleep_list)
            return JsonResponse({'status': 200, 'sleep_list': sleep_list})
        if activity_type == 1:
            from on.activities.running.views import run_ranking_list
            run_list = run_ranking_list(user)
            return JsonResponse({'status': 200, 'run_list': run_list})
    else:
        return JsonResponse({'status': 403})


"""   骑行活动   """


# @csrf_exempt
# def riding_punch(request):
#     print("进入骑行打卡")
#     """获取随机数"""
#     user = request.session.get("user")
#     random = request.POST.get("random")
#     if DEBUG:
#         user_id = 101077
#     else:
#         user_id = user.user_id
#     # try:
#     #     resp = send_img.delay(user.user_id, random, user.wechat_id, "1")
#     #     print("第{}张图片的发送结果{}".format(random, resp))
#     # except Exception as e:
#     #     print(e)
#     #     logger.error(e)
#     """获取对应的目标的goal id"""
#     goal_id = request.POST.get('goal', ' ')
#     distance = float(request.POST.get('distance', 0))
#     goal = RidingGoal.objects.get(goal_id=goal_id)
#     """获取前端传递的两个路径"""
#     file_filepath = request.POST.get("file_filepath")
#
#     file_refpath = request.POST.get("file_refpath")
#     document = request.POST.get("document", " ")
#     """获取当前的时间"""
#     punch_time = timezone.now()
#     print("获取参数完成")
#     try:
#         punch = RidingPunchRecord.objects.create_riding_redord(goal=goal,
#                                                                user_id=user_id,
#                                                                voucher_ref=file_refpath,
#                                                                voucher_store=file_filepath,
#                                                                distance=distance,
#                                                                record_time=punch_time,
#                                                                document=document)
#         # goal.punch_day += 1
#         print('打卡成功')
#         return JsonResponse({"status": 200})
#     except Exception as e:
#         logger.error(e)
#         return JsonResponse({"status": 405})
#
#
# @csrf_exempt
# def save_riding_comments(request):
#     from on.activities.riding.model import CommentRiding
#     user = request.session.get("user")
#     time_now = timezone.now().strftime("%Y-%m-%d %H:%M")
#     if request.POST:
#         try:
#             content = request.POST.get("content")
#             voucher_ref = request.POST.get("voucher_ref")
#             voucher_store = request.POST.get("voucher_store")
#             # 若用户表不存在，则先给用户创建一个jilu
#             CommentRiding.objects.create(user=user, content=content, voucher_ref=voucher_ref,
#                                          voucher_store=voucher_store,
#                                          c_time=time_now)
#             return JsonResponse({"status": 200})
#         except Exception as e:
#             print("评论失败", e)
#             return JsonResponse({"status": 401})
#     else:
#         return JsonResponse({"status": 401})
#
#
# # sleeping 回复
# @csrf_exempt
# def riding_reply(request):
#     user = request.session.get("user")
#     from on.activities.riding.model import RidingReply
#     if request.POST:
#         r_content = request.POST.get("r_content")
#         other_id = request.POST.get("other_id")
#         try:
#             RidingReply.objects.create(user_id=user.user_id, other_id=other_id.replace("-", ""), r_content=r_content)
#             return JsonResponse({"status": 200})
#         except Exception as e:
#             print("用户评论失败", e)
#             return JsonResponse({"status": 403})
#     return JsonResponse({"status": 403})
#
#
# # sleeping 点赞
# @csrf_exempt
# def riding_prise(request):
#     from on.activities.riding.model import CommentRiding
#
#     user = request.session.get("user")
#     if request.POST:
#         id = request.POST.get("id")
#         try:
#             CommentRiding.objects.praise_comment(user_id=user.user_id, punch_id=id)
#             return JsonResponse({"status": 200})
#         except Exception as e:
#             print("点赞失败", e)
#             return JsonResponse({"status": 401})
#     else:
#         return JsonResponse({"status": 401})
#
#
# # sleeping删除评论
# @csrf_exempt
# def delete_riding_comments(request):
#     from on.activities.riding.model import CommentRiding
#     if request.POST:
#         user = request.session.get("user")
#         id = request.POST.get("id")
#         try:
#             CommentRiding.objects.filter(id=id).update(is_delete=1)
#             return JsonResponse({"status": 200})
#         except Exception as e:
#             print("删除失败", e)
#             return JsonResponse({"status": 403})
#     else:
#         return JsonResponse({"status": 403})
