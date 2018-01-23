from django.http import Http404
from django.shortcuts import render, redirect
import json
import functools
from wechatpy.oauth import WeChatOAuth
from django.http import HttpResponse, JsonResponse
from on.user import UserInfo, UserRelation, UserTrade, UserAddress, UserOrder
from on.models import Activity, Goal, RunningPunchRecord, ReadingGoal, SleepingGoal, RunningGoal
from on.serializers import UserSerializer, ActivitySerializer
from django.views.decorators.csrf import csrf_exempt
from functools import wraps
from django.http import HttpResponseRedirect
from on.wechatconfig import oauthClient, client
from django.conf import settings
from on.wechatconfig import get_wechat_config
import decimal

mappings = {
    "0": "sleeping.html",
    "1": "running.html",
    "2": "reading.html",
    "3": "origami.html"
}


def oauth(method):
    @functools.wraps(method)
    def warpper(request, *args, **kwargs):
        if settings.DEBUG:
            user_info ={"openid":"o0jd6wk8OK77nbVqPNLKG-2urQxQ",
                        "nickname": "SivilTaram 乾",
                        "sex":"1",
                        "headimgurl": "http://wx.qlogo.cn/mmopen/g3MonUZtNHkdmzicIlibx6iaFqAc56vxLSUfpb6n5WKSYVY0ChQKkiaJSgQ1dZuTOgvLLrhJbERQQ4eMsv84eavHiaiceqxibJxCfHe/46",
                        }
            wechat_id = user_info["openid"]
            user = UserInfo.objects.check_user(wechat_id)
            if not user:
                user = UserInfo.objects.create_user(user_info["openid"],
                                                    user_info["nickname"],
                                                    user_info["headimgurl"],
                                                    int(user_info["sex"]))
            request.session['user'] = user
            return method(request, *args, **kwargs)
        else:
            if request.session.get('user', False):
                return method(request, *args, **kwargs)
            if request.method == 'GET':
                code = request.GET['code'] if 'code' in request.GET else None
                oauthClient.redirect_uri = settings.HOST + request.get_full_path()
                # 如果有授权code, 说明是重定向后的页面
                if code:
                    # 利用code来换取网页授权的access_token
                    oauthClient.fetch_access_token(code=code)
                    # 如果access_token有效，则进行下一步
                    if not oauthClient.check_access_token():
                        redirect_url = oauthClient.authorize_url
                        return redirect(redirect_url)
                    else:
                        pass
                    # 利用access_token获取用户信息
                    try:
                        user_info = client.user.get(user_id=oauthClient.open_id)
                        wechat_id = user_info["openid"]
                        # 如果微信号不存在，则新建一个用户
                        user = UserInfo.objects.check_user(wechat_id)
                        if not user:
                            user = UserInfo.objects.create_user(user_info["openid"],
                                                                user_info["nickname"],
                                                                user_info["headimgurl"],
                                                                int(user_info["sex"]))
                    except Exception as e:
                        print(e)
                    else:
                        request.session['user'] = user
                        return method(request, *args, **kwargs)
                # 否则直接到重定向后的页面去
                else:
                    redirect_url = oauthClient.authorize_url
                    return redirect(redirect_url)
            else:
                return method(request, *args, **kwargs)
    return warpper


# 显示主页
@oauth
def show_activities(request):
    activities = Activity.objects.all()
    # TODO: fake
    activities = fake_data(activities)
    return render(request, 'activity/index.html', {
        'activities': activities})


def fake_data(activities):
    for activity in activities:
        # 作息数据
        if activity.activity_type == "0":
            activity.coefficient += decimal.Decimal(155)
            activity.active_participants += 15
            activity.bonus_all += decimal.Decimal(2310)
        # 跑步数据
        elif activity.activity_type == "1":
            activity.coefficient += decimal.Decimal(202)
            activity.active_participants += 21
            activity.bonus_all += decimal.Decimal(2250)
        # 阅读数据
        else:
            activity.active_participants += 0
            activity.bonus_all += decimal.Decimal(0)
    return activities

# 获取某个模型的所有子模型
def get_son_models(model):
    all_sub_models = {}
    for sub_model in model.__subclasses__():
        all_sub_models[sub_model.__name__] = sub_model
    return all_sub_models


# 显示活动的页面
@oauth
def show_specific_activity(request, pk):
    activity = Activity.objects.get(activity_id=pk)
    # TODO:FakeDATA
    activity = fake_data([activity])[0]
    # TODO
    if not settings.DEBUG:
        user = request.session['user']
        sub_models = get_son_models(Goal)
        for sub_model_key in sub_models:
            sub_model = sub_models[sub_model_key]
            goal = sub_model.objects.filter(user_id=user.user_id).filter(activity_type=activity.activity_type)
            if goal:
                goal = goal.first()
                if goal.status != "PENDING":
                    redirect_url = '/goal/{0}?activity_type={1}'.format(goal.goal_id, activity.activity_type)
                    return HttpResponseRedirect(redirect_url)
                else:
                    pass
    # 专门为读书设立的字段
    readinginfo = {
        'title': '你的生命有什么可能',
        'intro': '本书探讨了以下问题：高竞争的工作、高不可攀的房价和房租、 拥挤的交通、糟糕的空气、不安全的食品……在竭尽全力才能生存的时代，年轻人如何追求自己的梦想？在这样的时代，我们的生命又有什么可能？如何才能越过现实和理想的鸿沟，找到和进入自己希望的人生？如何修炼自己在现实中活得更好的能力？如何在现实之中发展自己的兴趣？如何连接现实和理想？如何面对生命里的苦难、贫穷、不完美或者不公正？如何获得心灵的自由？',
        'imageurl': '/static/images/reading_book_demo.png',
        'price': 35,
        'return': 20,
        'guaranty': 30,
        'page': 315
    }

    if activity.activity_type == ReadingGoal.get_activity():
        person_goals = ReadingGoal.objects.filter(status="ACTIVE")[:5]
    elif activity.activity_type == SleepingGoal.get_activity():
        person_goals = SleepingGoal.objects.filter(status="ACTIVE")[:5]
    else:
        person_goals = RunningGoal.objects.filter(status="ACTIVE")[:5]

    persons = set()
    for person_goal in person_goals:
        persons.add(UserInfo.objects.get(user_id=person_goal.user_id))

    return render(request, 'activity/{0}'.format(mappings[activity.activity_type]), {
        "app": activity,
        "readinginfo": readinginfo,
        "WechatJSConfig": get_wechat_config(request),
        "persons": persons,
        "DEBUG": settings.DEBUG
    })


# 显示个人页面
@oauth
def show_user(request):
    user = request.session['user']
    userinfo = UserInfo.objects.get(user_id=user.user_id)
    record = userinfo.record.first()
    success_rate = 0 if record.join_times == 0 else int(float(record.finish_times)*100/record.join_times)
    return render(request, 'user/index.html', {
        'user': userinfo,
        'record': record,
        'successrate': success_rate
    })


# 更新个人信息
@oauth
@csrf_exempt
def update_address(request):
    user = request.session['user']
    if request.method == 'POST':
        address_dict = json.loads(request.POST.get("data"))
        UserAddress.objects.update_address(user=user, field_dict=address_dict)
        return JsonResponse({'status':200})
    else:
        return JsonResponse({'status':403})


# 获取用户的打卡记录信息
def show_history(request):
    user = request.session['user']
    punch_inform = user.record.first()
    # 找到 User 所有的Goal,按照时间排列
    all_goals = []
    all_punchs = []
    for sub_model in Goal.__subclasses__():
        all_goals.append(sub_model)
    # 遍历所有的Goal, 找到其对应的 Punch 的类型
    for goal in all_goals:
        try:
            punchs = goal.objects.get(user=user)
            all_punchs += [format_record(record) for record in punchs.punch.all()]
        except:
            pass
    all_punchs.sort(key=lambda x: x['time'])
    all_punchs.reverse()
    # TODO: 添加更多活动的 punchs 显示
    record = user.record.first()
    success_rate = 0 if record.join_times == 0 else int(float(record.finish_times)*100/record.join_times)
    return render(request, 'user/history.html', {
        'punchs': all_punchs,
        'punchinform': punch_inform,
        'successrate': success_rate
    })


# 格式化所有的打卡记录
def format_record(punch):
    # 添加更多punch record
    if isinstance(punch, RunningPunchRecord):
        target_days = int(punch.goal.goal_day)
        target_distance = int(punch.goal.goal_distance)
        target = '{0:d}天,{1:d}km'.format(target_days, target_distance)
        if punch.goal.running_type == 0:
            punch_type = "跑步 自由模式"
        elif punch.goal.running_type == 1:
            punch_type = "跑步 自律模式"
        else:
            punch_type = "默认"
    else:
        target = '暂无'
    bonus = '{0:f}元'.format(punch.bonus)
    time = punch.record_time.strftime('%Y{0} %m{1} %d{2}').format('年','月','日')
    return {"type": punch_type, "target": target, "bonus": bonus, "time": time}


# 展示支付页面
@oauth
def show_cash(request):
    user = request.session['user']
    user_info = UserInfo.objects.get(user_id=user.user_id)
    return render(request, 'user/cash.html', {'balance':user_info.balance})


# 展示我的圈子
@oauth
def show_circle(request):
    user = request.session['user']
    return render(request, 'user/circle.html')


# 展示我的订单
@oauth
def show_order(request):
    user = request.session['user']
    address = UserAddress.objects.get_address(user.user_id)
    orders = UserOrder.objects.filter(user_id=user.user_id)
    return render(request, 'user/order.html', {
        "address":address,
        "orders":orders
    })
