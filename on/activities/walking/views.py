# coding=utf-8
from django.shortcuts import render, redirect
from on.user import UserInfo, UserTicket, UserTicketUseage, UserInvite, Invitenum
from on.models import Activity, Goal
from .models import WalkingGoal,WalkingPunchRecord,WalkReply,WalkingPunchPraise,WalkingPunchReport
from on.errorviews import page_not_found
from datetime import timedelta, date, datetime
import django.utils.timezone as timezone
from on.wechatconfig import get_wechat_config
import random

#
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
    add_distance = WalkingGoal.objects.get(goal_id=goal.goal_id).add_distance
    for i in range(day_index):
        # 开始的日期
        last_date = first_day + timedelta(days=i)
        # 从那天开始到那一天结束的时间
        end = last_date + timedelta(days=1)
        is_no_sign_in = False
        punch_inform = None
        punchs = goal.punch.filter(record_time__range=(last_date, end))
        is_complete = True if punchs else False
        ref = []
        if is_complete:
            punch_inform = punchs[0]
            ref = random.choice(punch_inform.voucher_ref.split(","))
        else:
            use_history = UserTicketUseage.objects.filter(useage_time__range=(last_date, end), goal_id=goal.goal_id,
                                                          ticket_type='NS')
            is_no_sign_in = True if use_history else False
        # 判断是否是当天，格式是月份
        is_day_now = True if last_date == timezone.now().date() else False
        dates.append({
            "weekday": days_set[last_date.weekday()],
            "is_day_now": is_day_now,
            # 打印测试的字段，无用
            'ref':ref,
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

#
def show_walking_goal(request, pk):
    print("进入步行活动")
    # 开始
    user = request.session["user"]
    goal_id = pk
    goal = WalkingGoal.objects.filter(goal_id=goal_id).filter(activity_type=WalkingGoal.get_activity()).first()
    if goal:
        if goal.status != "ACTIVE":
            return render(request, 'goal/finish.html',
                          {
                              'goal': goal,
                              'goal_type': WalkingGoal.get_activity(),
                              "headimg": user.headimgurl
                          })
        else:
            # 免签券数量查询
            nosign_ticket = UserTicket.objects.get_nosigned_tickets(goal_id=goal_id)
            # 天数
            dates_inform = get_days(goal)
            # 查询 Activity 相关的活动信息, 找到第一个符合类型要求且在进行中的活动
            app = Activity.objects.get_active_activity(activity_type=WalkingGoal.get_activity())
            # 查询 Activity 相关的头像信息
            person_goals = WalkingGoal.objects.filter(status="ACTIVE")[:10]
            persons = set()
            for person_goal in person_goals:
                persons.add(UserInfo.objects.get(user_id=person_goal.user_id))
            # 随机查询24小时内存在的打卡记录，展示在本页面中
            # lastday, today = timezone.now() - timedelta(days=1), timezone.now()
            lastday = timezone.now() - timedelta(days=1)
            today = timezone.now()
            random_records = WalkingPunchRecord.objects.filter(record_time__range=(lastday, today)).order_by(
                "-record_time")[:20]
            # activate_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            # 获取邀请了多少好友
            num = UserInvite.objects.filter(user_id=request.session["user"].user_id).count()

            obj = WalkingGoal.objects.filter(user_id=user.user_id, status="ACTIVE")[0]
            #该活动的打卡天数
            punch_day = obj.punch_day
            #该活动的额外收益
            extra_earn = obj.extra_earn
            a = goal.start_time.strftime("%Y-%m-%d")
            user_end_time = (goal.start_time + timedelta(days=1)).strftime("%Y-%m-%d")
            if len(WalkingPunchRecord.objects.filter(goal_id=goal_id, record_time__range=(a, user_end_time))) > 0:
                first_day_record = 1
            else:
                first_day_record = 0

            news = []
            for record in random_records:
                voucher_ref_list = record.voucher_ref.split(",")
                userinfo = UserInfo.objects.get(user_id=record.goal.user_id)
                reply = WalkReply.objects.filter(other_id=str(record.punch_id).replace("-", "")).order_by('-id')
                response = [{"content": i.r_content, "user_id": i.user_id, "nickname": i.get_user_message.nickname} for
                            i in reply] if len(reply) > 0 else ""
                document = record.document
                report = WalkingPunchReport.objects.filter(punch_id=record.punch_id).filter(user_id=user.user_id)
                is_no_report = 1 if report else 0
                praise = WalkingPunchPraise.objects.filter(punch_id=record.punch_id).filter(user_id=user.user_id)
                is_no_praise = 1 if praise else 0
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
                    "reply_data": response
                })
            if app:
                return render(request, "goal/walking.html",
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
                                  'nickname':user.nickname,
                                  "punch_day": punch_day,
                                  "first_day_record": first_day_record
                              })
            else:
                return page_not_found(request)
    else:
        return page_not_found(request)
