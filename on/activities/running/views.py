from django.shortcuts import render
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from on.user import UserInfo, UserTicket, UserTicketUseage
from on.models import Activity, Goal, RunningGoal, SleepingGoal, RunningPunchRecord
from .models import RunningPunchReport
from on.errorviews import page_not_found
from datetime import timedelta, date, datetime
import django.utils.timezone as timezone
from on.wechatconfig import get_wechat_config
from on.views import fake_data
import json


def get_days(goal):
    days_set = ['一', '二', '三', '四', '五', '六', '日']
    dates = []
    # 头一天的日期
    first_day = goal.start_time.date()
    # 活动的时间长36
    day_index = (timezone.now().date() - first_day).days + 1
    # 开始星期的星期数
    start_week = first_day.weekday()
    # 现在的时间的星期数4
    day_now = timezone.now().date().weekday()
    for i in range(day_index):
        # 开始的日期
        last_date = first_day + timedelta(days=i)
        # 从那天开始到那一天结束的时间
        end = last_date + timedelta(1)
        # Y 表示 yes, N 表示 no, S 表示未开始
        # is_complete = True
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
                # is_no_sign_in = goal.use_no_sign_in_date(i)
        # 判断是否是当天，格式是月份
        if last_date == timezone.now().date():
            is_day_now = True
        else:
            is_day_now = False
        dates.append({
            "weekday": days_set[last_date.weekday()],
            "is_day_now": is_day_now,
            # 打印测试的字段，无用
            'test': (timezone.now().date() + timedelta(days=i)).day,
            "date": last_date.day,
            "isfinish": is_complete,
            "isnosignin": is_no_sign_in,
            "punch": punch_inform,
            "dayindex": i + 1
        })
    # 补全日期

    # 前面插入空白日期补全日历start_week=3
    for i in range(start_week):
        blank_date2 = {
            "date": (first_day - timedelta(days=i + 1)).day,
            "isfinish": False,
            "isnosignin": False,
            "punch": None,
            "dayindex": "0"
        }

        dates.insert(0, blank_date2)
    # 后面插入空白日期补全日历day_now=5

    for i in range(6 - day_now):
        blank_date1 = {
            "date": (timezone.now().date() + timedelta(days=i + 1)).day,
            "isfinish": False,
            "isnosignin": False,
            "punch": None,
            "dayindex": "0"
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
    # 测试代码，解决bug，但是正式上线的时候需要改回来
    user = request.session["user"]

    goal_id = pk
    goal = RunningGoal.objects.filter(goal_id=goal_id).filter(activity_type=RunningGoal.get_activity()).first()
    if goal:
        if goal.status != "ACTIVE":
            return render(request, 'goal/finish.html',
                          {
                              'goal': goal,
                              'goal_type': RunningGoal.get_activity()
                          })
        else:
            # 免签券
            nosign_ticket = UserTicket.objects.get_nosigned_tickets(goal_id=goal_id)
            # 天数
            dates_inform = get_days(goal)
            # 查询 Activity 相关的活动信息, 找到第一个符合类型要求且在进行中的活动
            app = Activity.objects.get_active_activity(activity_type=RunningGoal.get_activity())
            # TODO:FAKE
            app = fake_data([app])[0]
            # 查询 Activity 相关的头像信息
            person_goals = RunningGoal.objects.filter(status="ACTIVE")[:5]
            persons = set()
            for person_goal in person_goals:
                # 测试代码，解决bug，但是正式上线的时候需要改回来
                # persons.add(UserInfo.objects.get(user_id=person_goal.user_id))
                persons.add(UserInfo.objects.get(user_id=user.user_id))
            # 随机查询24小时内存在的打卡记录，展示在本页面中
            lastday, today = timezone.now() - timedelta(days=1), timezone.now()
            random_records = RunningPunchRecord.objects.filter(record_time__range=(lastday, today)).order_by('?')[:5]
            news = []
            for record in random_records:
                userinfo = UserInfo.objects.get(user_id=record.goal.user_id)
                report = RunningPunchReport.objects.filter(punch_id=record.punch_id, user_id=userinfo.user_id)
                if report:
                    status = "1"
                else:
                    status = "0"
                record_time = record.record_time
                dis_day = "今日" if record_time.day == today.day else "昨日"
                dis_date = "{0} {1}:{2}".format(dis_day,
                                                record_time.hour,
                                                record_time.minute)
                news.append({
                    "headimage": userinfo.headimgurl,
                    "date": dis_date,
                    "distance": record.distance,
                    "praise": record.praise,
                    "status": status,
                    "report": record.report,
                    "name": userinfo.nickname,
                    "voucher_ref": record.voucher_ref,
                    "punch_id": record.punch_id
                })
            if app:
                return render(request, "goal/running.html",
                              {
                                  "WechatJSConfig": get_wechat_config(request),
                                  "app": app,
                                  "goal": goal,
                                  'nosign': nosign_ticket,
                                  "datesinform": dates_inform,
                                  "persons": persons,
                                  "news": news,
                              })
            else:
                return page_not_found(request)
    else:
        return page_not_found(request)
