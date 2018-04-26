# coding=utf-8
from django.shortcuts import render
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from on.user import UserInfo, UserTicket, UserTicketUseage, UserInvite, Invitenum
from on.models import Activity, Goal, RunningGoal, SleepingGoal, RunningPunchRecord
from .models import RunningPunchReport, RunningPunchPraise
from on.errorviews import page_not_found
from datetime import timedelta, date, datetime
import django.utils.timezone as timezone
from on.wechatconfig import get_wechat_config
from on.views import fake_data
import json
import time
import pytz

#
def get_days(goal):
    days_set = ['一', '二', '三', '四', '五', '六', '日']
    dates = []
    # 头一天的日期
    first_day = goal.start_time.date()
    start = goal.start_time
    # 活动的时间长36

    day_index = (timezone.now().date() - first_day).days + 1
    # 开始星期的星期数
    start_week = first_day.weekday()
    # 现在的时间的星期数4
    day_now = timezone.now().date().weekday()
    add_distance = RunningGoal.objects.get(goal_id=goal.goal_id).add_distance
    for i in range(day_index):
        # 开始的日期
        last_date = first_day + timedelta(days=i)
        # 从那天开始到那一天结束的时间
        end = last_date + timedelta(days=1)
        is_no_sign_in = False
        punch_inform = None
        punchs = goal.punch.filter(record_time__range=(last_date, end))
        is_complete = True if punchs else False
        if is_complete:
            punch_inform = punchs[0]
        else:
            use_history = UserTicketUseage.objects.filter(useage_time__range=(last_date, end), goal_id=goal.goal_id,
                                                          ticket_type='NS')
            if use_history:
                is_no_sign_in = True
            else:
                is_no_sign_in = False
        # 判断是否是当天，格式是月份
        if last_date == timezone.now().date():
            is_day_now = True
        else:
            is_day_now = False
        dates.append({
            "weekday": days_set[last_date.weekday()],
            "is_day_now": is_day_now,
            # 打印测试的字段，无用
            # 'test':punch_inform.voucher_ref,
            "date": last_date.day,
            'add_distance': add_distance,
            "isfinish": is_complete,
            "isnosignin": is_no_sign_in,
            "punch": punch_inform,
            "dayindex": i + 1,

        })
    # 补全日期
    # 前面插入空白日期补全日历start_week=3
    for i in range(start_week):
        blank_date2 = {
            "date": (first_day - timedelta(days=i + 1)).day,
            "isfinish": False,
            "isnosignin": False,
            "punch": "",
            "dayindex": "-1"
        }
        dates.insert(0, blank_date2)
    # 后面插入空白日期补全日历day_now=5

    for i in range(6 - day_now):
        blank_date1 = {
            "date": (timezone.now().date() + timedelta(days=i + 1)).day,
            "isfinish": False,
            "isnosignin": False,
            "punch": "",
            "dayindex": "-1"
        }
        dates.append(blank_date1)
    # [dates.insert(0, blank_date2) for i in range(start_week)]
    # # 后面插入空白日期补全日历day_now=5
    # [dates.append(blank_date1) for i in range(6 - day_now)]
    # 构造[[{},{},{}],[{},{},{}],[{},{},{}],[{},{},{}].....]
    i = 0
    new_date = []
    while i < int(len(dates)):
        date_list = dates[i:i + 7]
        i += 7
        new_date.append(date_list)
    return new_date


def show_running_goal(request, pk):
    # 开始
    user = request.session["user"]
    goal_id = pk
    goal = RunningGoal.objects.filter(goal_id=goal_id).filter(activity_type=RunningGoal.get_activity()).first()
    if goal:
        if goal.status != "ACTIVE":
            return render(request, 'goal/finish.html',
                          {
                              'goal': goal,
                              'goal_type': RunningGoal.get_activity(),
                              "headimg": user.headimgurl
                          })
        else:
            # 免签券数量查询
            nosign_ticket = UserTicket.objects.get_nosigned_tickets(goal_id=goal_id)
            # 天数
            dates_inform = get_days(goal)
            # 查询 Activity 相关的活动信息, 找到第一个符合类型要求且在进行中的活动
            app = Activity.objects.get_active_activity(activity_type=RunningGoal.get_activity())
            # TODO:FAKE
            app = fake_data([app])[0]
            # 查询 Activity 相关的头像信息
            person_goals = RunningGoal.objects.filter(status="ACTIVE")[:10]
            persons = set()
            for person_goal in person_goals:
                persons.add(UserInfo.objects.get(user_id=person_goal.user_id))
            # 随机查询24小时内存在的打卡记录，展示在本页面中
            # lastday, today = timezone.now() - timedelta(days=1), timezone.now()
            lastday = timezone.now() - timedelta(days=1)
            today = timezone.now()
            random_records = RunningPunchRecord.objects.filter(record_time__range=(lastday, today)).order_by(
                "-record_time")[:20]
            # activate_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            # 获取邀请了多少好友
            num = UserInvite.objects.filter(user_id=request.session["user"].user_id).count()

            obj = RunningGoal.objects.filter(user_id=user.user_id, status="ACTIVE")[0]
            #该活动的打卡天数
            punch_day = obj.punch_day
            #该活动的额外收益
            extra_earn = obj.extra_earn
            a = goal.start_time.strftime("%Y-%m-%d")
            user_end_time = (goal.start_time + timedelta(days=1)).strftime("%Y-%m-%d")
            if len(RunningPunchRecord.objects.filter(goal_id=goal_id, record_time__range=(a, user_end_time))) > 0:
                first_day_record = 1
            else:
                first_day_record = 0

            news = []
            for record in random_records:
                voucher_ref_list = record.voucher_ref.split(",")
                userinfo = UserInfo.objects.get(user_id=record.goal.user_id)
                document = record.document
                report = RunningPunchReport.objects.filter(punch_id=record.punch_id).filter(user_id=user.user_id)
                if report:
                    is_no_report = 1
                else:
                    is_no_report = 0
                praise = RunningPunchPraise.objects.filter(punch_id=record.punch_id).filter(user_id=user.user_id)
                if praise:
                    is_no_praise = 1
                else:
                    is_no_praise = 0
                record_time = record.record_time
                dis_day = "今日" if record_time.day == today.day else "昨日"
                dis_date = "%s %s:%02d" % (dis_day,
                                           record_time.hour,
                                           record_time.minute)
                news.append({
                    "headimage": userinfo.headimgurl,
                    "date": dis_date,
                    "distance": record.distance,
                    "praise": record.praise,
                    "report": record.report,
                    'reload': record.reload,
                    'is_no_report': is_no_report,
                    'is_no_praise': is_no_praise,
                    "name": userinfo.nickname,
                    "voucher_ref": voucher_ref_list,
                    "punch_id": record.punch_id,
                    "document": document,
                    'test': timezone.now(),
                })
            if app:
                return render(request, "goal/running.html",
                              {
                                  "WechatJSConfig": get_wechat_config(request),
                                  "app": app,
                                  "goal": goal,
                                  "invite_num": num,
                                  'nosign': nosign_ticket,
                                  "datesinform": dates_inform,
                                  "extra_earn": extra_earn,
                                  "persons": persons,
                                  "news": news,
                                  "punch_day": punch_day,
                                  "first_day_record": first_day_record
                                  # "punch_id":punch_record
                              })
            else:
                return page_not_found(request)
    else:
        return page_not_found(request)
