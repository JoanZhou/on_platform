# coding=utf-8
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import timedelta
import django.utils.timezone as timezone
from on.models import RunningPunchRecord, RunningGoal, ReadingGoal, ReadingPunchRecord, SleepingPunchRecord, Activity
from on.user import UserInfo
import pytz
import json
import logging
import time
import requests
from on.temp.push_template import do_push
import decimal
import math
import xmltodict

WECHAT_APPID = "wx4495e2082f63f8ac"
WECHAT_APPSECRET = "23f0462bee8c56e09a2ac99321ed9952"


# 获取accessToken
def getToken():
    # 获取用户的accesstoken
    url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=' + WECHAT_APPID + "&secret=" + WECHAT_APPSECRET
    token_str = requests.post(url).content.decode()
    token_json = json.loads(token_str)
    token = token_json['access_token']
    return token


sched = BackgroundScheduler()
app_logger = logging.getLogger('app')


# 未完成目标提醒
def initiative(openid, url, detail, category):
    data = {
        "touser": openid,
        "template_id": "CB9aLimSfCXD_ErWqN6mqjKkoL37WGOJ9y9WEo8Ykp8",
        "url": url,
        "topcolor": "#FF0000",
        "data": {
            "first": {
                "value": "您好，你还有目标未完成。",
                "color": "#173177"
            },
            "keyword1": {
                "value": detail,
                "color": "#173177"
            },
            "keyword2": {
                "value": category,
                "color": "#173177"
            },
            "keyword3": {
                "value": "23:00",
                "color": "#173177"
            },
            "remark": {
                "value": "请尽快完成您的目标",
                "color": "#173177"
            },
        }
    }
    return data


# 打卡未完成提醒模板
def field_tem(openid, url, first, target, nosignday, deduct, surplus):
    data = {
        "touser": openid,
        "template_id": "WhQmd66FdEJUXhsMXmgIwlvpMzzdMtiDXcpf1rtpz2g",
        "url": url,
        "topcolor": "#FF0000",
        "data": {
            "first": {
                "value": first,
                "color": "#173177"
            },
            "keyword1": {
                "value": target,
                "color": "#173177"
            },
            "keyword2": {
                "value": nosignday,
                "color": "#173177"
            },
            "keyword3": {
                "value": deduct,
                "color": "#173177"
            },
            "keyword4": {
                "value": surplus,
                "color": "#173177"
            },
            "remark": {
                "value": "加油吧，On将陪你坚持到底。",
                "color": "#173177"
            },
        }
    }
    return data


# 获取没有打卡的用户
def get_no_sign():
    # 获取当天已经打过卡的用户
    # 由于是每天的九点要打卡，所以要查询发送提醒前的21小时的打卡记录
    search_time = timezone.now() - timedelta(hours=21)
    # 在活动时间的范围内查询打卡记录
    punch = RunningPunchRecord.objects.filter(record_time__range=(search_time, timezone.now() + timedelta(hours=8)))
    # 若存在打卡记录则继续
    if punch:
        # 取出所有打卡用户的goal_id
        a = [i.goal_id for i in punch]
        # 获取这个活动所有正在参与的用户，只有status="ACTIVE"才表示正在参加
        rungoal = RunningGoal.objects.filter(status="ACTIVE", goal_type=1)
        # 找出所有已经参加用户的goal_id
        b = [i.goal_id for i in rungoal]
        # 剔除已经参与的用户，找出未打卡的用户的goal_id
        no_sign_in = list(set(b) - set(a))
        if no_sign_in != 0:
            user_list = [RunningGoal.objects.get(goal_id=i).user_id for i in no_sign_in]
            openid_li = list(set([UserInfo.objects.get(user_id=i).wechat_id for i in user_list]))
            print(openid_li, "若未打卡的用户数量不是零的话")
            return openid_li
        # 所有参与用户都打卡了
        else:
            pass
    # 若不存在打卡记录（情况极少）
    else:
        # 将所有正在参与的用户发送打卡记录
        # 查询所有参与用户的user_id
        all_no_sign = [i.user_id for i in RunningGoal.objects.filter(status='ACTIVE', goal_type=1)]
        openid_li = list(set([UserInfo.objects.get(user_id=i).wechat_id for i in all_no_sign]))
        print(openid_li, "所有人都未打卡，查询出所有正在参加用户的openid,数量是{}".format(len(openid_li)))
        return openid_li


#
def search_message():
    open_list = get_no_sign()

    for openid in open_list:
        user = UserInfo.objects.get(wechat_id=openid)
        goal = RunningGoal.objects.get(user_id=user.user_id)
        url = "http://wechat.onmytarget.cn/goal/{}?activity_type=1".format(goal.goal_id)
        goal_type = goal.goal_type
        # 目标距离
        goal_distance = goal.goal_distance
        # 单日距离
        kilos_day = goal.kilos_day
        # 目标天数
        goal_day = goal.goal_day
        if goal_type == 1:
            detail = "在{}天内，每天完成{}公里".format(goal_day, kilos_day)
            category = "跑步日常模式"
        else:
            detail = "在{}天内，一共完成{}公里".format(goal_day, goal_distance)
            category = "跑步自由模式"

        end_time = (goal.start_time + timedelta(days=goal_day)).strftime("%m月%d日")
        data = initiative(openid, url, detail, category)
        do_push(data)


# 查询昨日没有打卡的用户
def search_nosign():
    user = RunningGoal.objects.all()
    user_list = []
    for goal in user:
        if goal.status == "ACTIVE":
            user_list.append(goal)
    return user_list


# 发送
def save_openid():
    obj = search_nosign()
    for goal in obj:
        # 判断该用户昨天是否有打卡记录
        # 说明不是第一天
        if not goal.exist_punch_last_day():
            user = goal.user_id
            openid = UserInfo.objects.get(user_id=user).wechat_id
            url = 'http://wechat.onmytarget.cn/user/index'
            goal_day = goal.goal_day
            kilos_day = goal.kilos_day
            first = "跑步"
            target = "在{}天，每天完成{}公里".format(goal_day, kilos_day)
            nosignday = (timezone.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            guaranty = goal.guaranty
            down_payment = goal.down_payment
            if goal.goal_type == 1:
                # 每次扣多少钱
                money = goal.average
                # 剩下应该扣多少次
                # 当是日常模式的时候
                times = int(down_payment) / int(money)
                if int(guaranty) != 0:
                    deduct = " 保证金￥{}".format(guaranty)
                else:
                    deduct = " 底金￥{}".format(down_payment / int(times))

                surplus = "底金￥{}X{}次".format(money, int(times))

                data = field_tem(openid, url, first, target, nosignday, deduct, surplus)
                if goal.is_first_day:
                    print("first day do nothing ")
                    return
                else:
                    do_push(data)
        else:
            return


# def allot_money():
#     time.sleep(1)
#     print("开始查询擂主的奖金")
#     leimoney = RunningGoal.objects.get(user_id="100101").activate_deposit
#     print("擂主的金额{}".format(leimoney))
#     #查询出昨天参加的用户,yester_day,today_time
#     today_time = timezone.now().strftime("%Y-%m-%d")
#     tomorrow = (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%d")
#     #查询出今天参加的用户
#     today_joiner = RunningGoal.objects.filter(start_time__range=(today_time,tomorrow))
#     print("今天参与的用户{}".format(today_joiner.count()))
#     #查询出所有参加的用户
#     all_joiner = RunningGoal.objects.filter(status="ACTIVE")
#     print("所有正在参与的用户{}".format(all_joiner.count()))
#     tomorrow_joiner = list(set(all_joiner)-set(today_joiner))
#     # 每个用户应该分配的金额
#     # goals = RunningGoal.objects.filter(status="ACTIVE")
#     print("所有的用户数量减去昨天参与的用户数量{}".format(len(tomorrow_joiner)))
#     average_lei = round(decimal.Decimal(leimoney) * decimal.Decimal(0.01) / len(tomorrow_joiner),2)
#     print(average_lei, "平均每个人分出去的金额")
#     # 查询出所有状态为ACTIVE的用户
#     for goal in tomorrow_joiner:
#         goal.extra_earn += decimal.Decimal(average_lei)
#         print("开始保存")
#         goal.save()
#         print("extra_earn保存成功")
#         for user in UserInfo.objects.filter(user_id=goal.user_id):
#             user.extra_money += decimal.Decimal(average_lei)
#             user.all_profit += decimal.Decimal(average_lei)
#             user.save()
#             print("extra_money，all_profit保存成功")





# 每天九点运行任务
sched.add_job(search_message, 'cron', day_of_week='0-6', hour=21, minute=0, timezone=pytz.timezone('Asia/Shanghai'))
sched.add_job(save_openid, 'cron', day_of_week='0-6', hour=9, minute=0, timezone=pytz.timezone('Asia/Shanghai'))

# 定时分配金额
# sched.add_job(allot_money, 'cron', day_of_week='0-6', hour=23, minute=50, timezone=pytz.timezone('Asia/Shanghai'))
sched.start()
