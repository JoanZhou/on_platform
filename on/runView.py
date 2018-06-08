from datetime import timedelta
from logging import getLogger
from django.http import JsonResponse, HttpResponseNotFound
from on.settings.local import DEBUG
from on.task import send_img
from on.temp.push_template import do_push
from on.user import UserTicket, UserRecord, UserInfo, UserOrder
from django.http import Http404
from django.shortcuts import render, redirect

from django.http import HttpResponse, JsonResponse
from on.user import UserInfo, UserRelation, UserTrade, UserAddress, UserOrder, UserInvite, FoolsDay, Invitenum, \
    Tutorial, LoginRecord
from on.models import Activity, Goal, RunningPunchRecord, RunningGoal
from on.activities.running.models import Running_Finish_Save,RunCoefficient
import decimal
from .QR_invite import user_qrcode
from django.views.decorators.csrf import csrf_exempt
from on.errorviews import page_not_found

import django.utils.timezone as timezone

logger = getLogger("app")


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
    # try:
    #     resp = send_img.delay(user.user_id, random, user.wechat_id, "1")
    #     print("第{}张图片的发送结果{}".format(random, resp))
    # except Exception as e:
    #     print(e)
    #     logger.error(e)
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

def delete_run_goal(request):
    try:
        user = request.session['user']
        if request.POST:
            # 删除当前的目标活动并退还钱
            activity_type = request.POST['goal_type']
            goal_id = request.POST['goal']
            goal = RunningGoal.objects.get(goal_id=goal_id)
            try:
                # 增加用户的完成次数
                UserRecord.objects.finish_goal(user=user)
                # 用户触发，如果挑战成功则删除目标，退还押金
                # 判断用户是否挑战成功
                # 更新用户的押金
                UserInfo.objects.update_deposit(user_id=user.user_id,
                                                pay_delta=-(goal.guaranty + goal.down_payment))
                # 查询用户的额外收益
                extra = UserInfo.objects.get(user_id=user.user_id)
                # 查询用户当前的额外收益
                price = decimal.Decimal(goal.guaranty) + decimal.Decimal(goal.down_payment) + decimal.Decimal(
                    goal.bonus) + decimal.Decimal(goal.extra_earn)
                # 将用户获取的收益存入余额
                UserInfo.objects.save_balance(user_id=user.user_id, price=price, bonus=decimal.Decimal(goal.bonus),
                                              extra_earn=decimal.Decimal(goal.extra_earn))
            except Exception as e:
                print(e)
            # 用户结算之后就将用户的所有信息放进记录存储表中
            try:
                print("开始保存用户的数据")
                Running_Finish_Save.objects.save_finish(goal_id=goal_id)
                import time
                time.sleep(1)
            except Exception as e:
                print("记录用户的结束保存信息失败", e)

            # 删除用户的目标
            RunningGoal.objects.delete_goal(goal_id)

            # 用户的目标结束之后，更新参加人数跟奖金池，系数
            try:
                goal.update_activity_person()
                act = Activity.objects.get(activity_id="32f2a8dbe89d43c7b9ecfea19947b057")
                act.bonus_all -= (goal.guaranty + goal.down_payment)
                act.save()
            except Exception as e:
                print("更新失败", e)

            url = 'http://wechat.onmytarget.cn/user/index'
            activate = "跑步"
            finish_time = timezone.now().strftime('%Y-%m-%d %H:%M')
            earn_money = str(goal.guaranty + goal.down_payment)
            # money = Running_Finish_Save.objects.get(user_id=user.user_id,settle_time=timezone.now().strftime('%Y-%m-%d')).bonus
            money = Running_Finish_Save.objects.filter(user_id=user.user_id,
                                                       settle_time=timezone.now().strftime('%Y-%m-%d'))
            if money:
                earn_money = money[0].bonus
            earn_time = (goal.start_time + timedelta(days=goal.goal_day)).strftime('%Y-%m-%d %H:%M')
            balance = str(UserInfo.objects.get(user_id=user.user_id).balance)
            # 发送模板提醒
            data = finish_tem(user.wechat_id, url, activate, finish_time, str(earn_money), earn_time, balance)
            do_push(data)
            return JsonResponse({'status': 200})
        else:
            return JsonResponse({'status': 403})
    except Exception:
        return JsonResponse({"status": 403})


@csrf_exempt
def create_run(request):
    print(111111111111)
    if request.POST:
        user = request.session.get("user")
        # if DEBUG:
        #     user_id = 100274
        # else:
        user_id = user.user_id
        data_json = request.POST
        reality_price = data_json.get("reality_price")
        deserve_price = data_json.get('deserve_price')
        activate_deposit = data_json.get("activate_deposit")
        down_num = data_json.get("down_num")
        guaranty = data_json.get("guaranty")
        down_payment = data_json.get("down_payment")
        coefficient = data_json.get("coefficient")
        mode = data_json.get("mode")
        goal_day = data_json.get("goal_day")
        goal_type = data_json.get("goal_type")
        punch_attention = data_json.get("punch_attention")
        is_no_use_point = data_json.get("is_no_use_point")
        distance = data_json.get("distance", "")
        kilos_day = data_json.get("kilos_day", "")
        deduction_point = data_json.get("deduction_point")
        deduction_guaranty = data_json.get("deduction_guaranty")
        multiple = data_json.get("multiple")
        start_time = timezone.now()
        # 参数教检
        # 自由模式与日常模式的个别参数不一样,自由模式没有每日距离,distance表示的都是目标距离
        if goal_type == 0:
            if not all([reality_price, deserve_price, down_num, guaranty, down_payment, coefficient
                           , mode, goal_day, punch_attention, is_no_use_point, distance, deduction_point,
                        deduction_guaranty, multiple]):
                return JsonResponse({"status": 403, "errmsg": "参数不完整"})
        # 日常模式，有每日距离，distance表示的是剩余距离
        elif goal_type == 1:
            if not all([reality_price, deserve_price, down_num, guaranty, down_payment, coefficient
                           , mode, goal_day, punch_attention, is_no_use_point, kilos_day, distance, deduction_point,
                        deduction_guaranty, multiple]):
                return JsonResponse({"status": 403, "errmsg": "参数不完整"})

        # 若参数完整，处理业务
        try:
            print("开始创建")
            goal = RunningGoal.objects.create_rungoal(user_id=user_id,
                                                      goal_type=goal_type,
                                                      guaranty=guaranty,
                                                      down_payment=down_payment,
                                                      activate_deposit=activate_deposit,
                                                      coefficient=coefficient,
                                                      mode=mode,
                                                      goal_day=goal_day,
                                                      distance=distance,
                                                      reality_price=reality_price,
                                                      deserve_price=deserve_price,
                                                      down_num=down_num,
                                                      start_time=start_time,
                                                      kilos_day=kilos_day,
                                                      punch_attention=punch_attention,
                                                      is_no_use_point=is_no_use_point,
                                                      multiple=multiple,
                                                      deduction_point=deduction_point,
                                                      deduction_guaranty=deduction_guaranty
                                                      )
            print("参与成功")
            coeff = RunCoefficient.objects.filter(user_id=user.user_id)
            if coeff:
                coeff.delete()
                RunCoefficient.objects.create(user_id=user.user_id, goal_type=goal_type, default_coeff=coefficient)
                print("创建成功")
            else:
                RunCoefficient.objects.create(user_id=user.user_id, goal_type=goal_type, default_coeff=coefficient)
                print("创建成功")
            return JsonResponse({"status": 200, "goal": goal.goal_id})
        except Exception as e:
            print(e)
            return JsonResponse({"status": 502})
