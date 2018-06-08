# coding=utf-8
from django.shortcuts import render, redirect
from on.user import UserInfo, UserTicket, UserTicketUseage, UserInvite, Invitenum, BonusRank
from on.models import Activity, Goal, RunningGoal, SleepingGoal, RunningPunchRecord
from .models import RunningPunchReport, RunningPunchPraise, RunReply, RunCoefficient
from on.errorviews import page_not_found
from datetime import timedelta, date, datetime
import django.utils.timezone as timezone
from on.wechatconfig import get_wechat_config
import random
import decimal


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
        # run_punch = RunningPunchRecord.objects.filter(goal=goal)
        # run_punch.voucher_ref.split()
        is_complete = True if punchs else False

        ref = []
        if is_complete:
            punch_inform = punchs[0]
            ref = random.choice(punch_inform.voucher_ref.split(","))
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
            'ref': ref,
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
    user_id = user.user_id
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
            # app = fake_data([app])[0]
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
            new_coeff = 0
            default = 0
            extra_coeff = 0
            try:
                coeff = RunCoefficient.objects.get(user_id=user_id)
                default = coeff.default_coeff
                new_coeff = coeff.new_coeff
                if new_coeff:
                    extra_coeff = (new_coeff - default) / default * decimal.Decimal(100)
                    if extra_coeff > 0:
                        extra_coeff = "+%2d" % extra_coeff + "%"
                    elif extra_coeff < 0:
                        extra_coeff = "%2d" % extra_coeff + "%"
                    else:
                        pass
                else:
                    extra_coeff = ""
            except RunCoefficient.DoesNotExist as e:
                print(e)
            # 该活动的打卡天数
            punch_day = obj.punch_day
            # 该活动的额外收益
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
                reply = RunReply.objects.filter(other_id=str(record.punch_id).replace("-", "")).order_by('-id')
                response = [{"content": i.r_content, "user_id": i.user_id, "nickname": i.get_user_message.nickname} for
                            i in reply] if len(reply) > 0 else ""
                document = record.document
                report = RunningPunchReport.objects.filter(punch_id=record.punch_id).filter(user_id=user.user_id)
                is_no_report = 1 if report else 0
                praise = RunningPunchPraise.objects.filter(punch_id=record.punch_id).filter(user_id=user.user_id)
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
                                  'nickname': user.nickname,
                                  "punch_day": punch_day,
                                  "first_day_record": first_day_record,
                                  "default": default,
                                  "extra_coeff": extra_coeff
                                  # "punch_id":punch_record
                              })
            else:
                return page_not_found(request)
    else:
        return page_not_found(request)


def run_ranking_list(user):
    # print('跑步榜')
    run_user_id = user.user_id
    run_last_dict = {
        'ranking': 0,
        'punch_day': 0,
        'nickname': user.nickname,
        'headimgurl': user.headimgurl,
    }
    puncher = RunningGoal.objects.filter(status='ACTIVE').values('punch_day', 'user_id').order_by('-punch_day')
    # print('跑步坚持榜', puncher)
    last_list = []
    for i, pun in enumerate(puncher):
        # print(i,  pun)
        user_id = pun['user_id']
        # print('user_id', user_id)
        if run_user_id == user_id:
            run_last_dict['ranking'] = i + 1
            run_last_dict['punch_day'] = pun['punch_day']
        users = UserInfo.objects.filter(user_id=user_id).values('nickname', 'headimgurl').first()
        # print('users', users)
        users['ranking'] = i + 1
        users['punch_day'] = pun['punch_day']
        last_list.append(users)

    lasting_data = {
        'current_user': run_last_dict,
        'datas': last_list,
    }

    run_add_dict = {
        'ranking': 0,
        'add_distance': 0,
        'nickname': user.nickname,
        'headimgurl': user.headimgurl,
    }
    all_distance = RunningGoal.objects.filter(status='ACTIVE').values('add_distance', 'user_id').order_by(
        '-add_distance')
    # print('跑步累计距离榜', all_distance)
    add_list = []
    for i, d in enumerate(all_distance):
        user_id = d['user_id']
        if run_user_id == user_id:
            run_add_dict['ranking'] = i + 1
            run_add_dict['add_distance'] = d['add_distance']
        users = UserInfo.objects.filter(user_id=user_id).values('nickname', 'headimgurl').first()
        users['ranking'] = i + 1
        users['add_distance'] = d['add_distance']
        add_list.append(users)
    add_data = {
        'current_user': run_add_dict,
        'datas': add_list,
    }

    run_prise_dict = {
        'bonus': 0,
        'ranking': 0,
        'nickname': user.nickname,
        'headimgurl': user.headimgurl,
    }
    datas = []
    rank_list = BonusRank.objects.values('user_id', 'run').order_by('-run')
    for i, rank in enumerate(rank_list):
        user_id = rank['user_id']
        # print('rank',i, rank)
        if user_id == run_user_id:
            run_prise_dict['ranking'] = i + 1
            run_prise_dict['bonus'] = rank['run']
        users = UserInfo.objects.filter(user_id=user_id).values('nickname', 'headimgurl').first()
        users['bonus'] = rank['run']
        users['ranking'] = i + 1
        datas.append(users)

    bonus_data = {
        'current_user': run_prise_dict,
        'datas': datas,
    }

    run_week_dict = {
        'ranking': 0,
        'week_distance': 0,
        'nickname': user.nickname,
        'headimgurl': user.headimgurl,
    }
    weeks = RunningGoal.objects.filter(status='ACTIVE').values('week_distance', 'user_id').order_by('-week_distance')
    # print('跑步坚持榜', puncher)
    week_list = []
    for i, wek in enumerate(weeks):
        # print('week', i, wek)
        user_id = wek['user_id']
        # print('user_id', user_id)
        if run_user_id == user_id:
            run_last_dict['ranking'] = i + 1
            run_last_dict['week_distance'] = wek['week_distance']
        users = UserInfo.objects.filter(user_id=user_id).values('nickname', 'headimgurl').first()
        # print('users', users)
        users['ranking'] = i + 1
        users['week_distance'] = wek['week_distance']
        week_list.append(users)

    week_data = {
        'current_user': run_week_dict,
        'datas': week_list,
    }

    run_list = {
        'bonus_data': bonus_data,
        'add_data': add_data,
        'lasting_data': lasting_data,
        'week_data': week_data,
    }

    return run_list
