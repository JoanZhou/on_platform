import json
import requests
from redis import StrictRedis
from on.settings.local import DEBUG

# from .wechatconfig import getToken
WECHAT_APPID = "wx4495e2082f63f8ac"

WECHAT_APPSECRET = "23f0462bee8c56e09a2ac99321ed9952"


# conn = StrictRedis(host='119.29.191.32',port=6379,db=1)

# 获取accessToken
def getToken():
    # 获取用户的accesstoken
    url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=' + WECHAT_APPID + "&secret=" + WECHAT_APPSECRET
    token_str = requests.post(url).content.decode()
    token_json = json.loads(token_str)
    token = token_json['access_token']
    # conn.set("token",token)
    return token


# 开始推送
def do_push(data):
    try:

        json_template = json.dumps(data)

        # token = conn.get('token').decode()
        token = getToken()
        requst_url = "https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={}".format(token)
        # 发送post请求并且返回数据{"errcode":0,"errmsg":"ok","msgid":133338823307411456}
        if DEBUG:
            return
        else:
            content = requests.post(requst_url, json_template).content.decode()
        # 读取json数据
        json_response = json.loads(content)
        errmsg = json_response['errmsg']
        return errmsg
    except Exception as e:
        print(e)


if __name__ == '__main__':
    # 测试
    data = {
        "touser": "o0jd6wgPxXAFK9aifqR858FOWDV0",
        "template_id": "WlJal_LqCkIPcwId9cITDXw97c_V9AjF4cPRtZUPWTM",
        "url": "http://weixin.qq.com/download",
        "topcolor": "#FF0000",
        "data": {
            "first": {
                "value": "恭喜你成功报名参加活动",
                "color": "#173177"
            },
            "keyword1": {
                "value": "跑步活动",
                "color": "#173177"
            },
            "keyword2": {
                "value": "2018-3-24",
                "color": "#173177"
            },
            "remark": {
                "value": "感谢您的参与",
                "color": "#173177"
            },
        }
    }
    # json_template = json.dumps(data)
    do_push(data)
