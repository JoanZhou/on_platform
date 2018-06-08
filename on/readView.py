
from on.models import Activity, Goal, RunningGoal, SleepingGoal, ReadingGoal, RunningPunchRecord, ReadingPunchRecord
from on.activities.reading.models import Read_Finish_Save
import decimal
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
from on.models import ReadingGoal,ReadingPunchRecord
from on.settings.local import DEBUG
from on.task import send_img
from on.temp.push_template import do_push
from on.user import UserTicket, UserRecord, UserInfo, UserOrder


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

