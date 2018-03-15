import json
import requests

WECHAT_APPID = "wx27cb93b4cfdc37af"

WECHAT_APPSECRET = "23f0462bee8c56e09a2ac99321ed9952"

class WechatPush(object):
    # 获取accessToken
    def getToken(self):
        # 获取用户的accesstoken
        url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=' + WECHAT_APPID + "&secret=" + WECHAT_APPSECRET
        token_str = requests.post(url).content.decode()
        token_json = json.loads(token_str)
        token = token_json['access_token']
        return token

    # 开始推送
    def do_push(self,data):
        dict_arr = data
        json_template = json.dumps(dict_arr)
        token = self.getToken()
        requst_url = "https://api.weixin.qq.com/cgi-bin/message/template/send?access_token=" + token
        # 发送post请求并且返回数据{"errcode":0,"errmsg":"ok","msgid":133338823307411456}
        content = requests.post(requst_url, json_template).content.decode()
        # 读取json数据
        json_response = json.loads(content)
        print(json_response)
        errmsg = json_response['errmsg']
        return errmsg
if __name__ == '__main__':
    #测试
    data = {
        "touser": "ojuDK0pUtmreFy6cpXodi8dWVvs0",
        "template_id": "_rMUPRoWnRMxtYmFi3YQuOzpvv2gTBuFnkz7wZYYvyk",
        "url": "http://weixin.qq.com/download",
        "topcolor": "#FF0000",
        "data": {
            "first": {
                "value": "目标:在两周内,每日6:40前起床",
                "color": "#173177"
            },
            "keyword1": {
                "value": "休息",
                "color": "#173177"
            },
            "keyword2": {
                "value": "",
                "color": "#173177"
            },
            "remark": {
                "value": "感谢您的参与",
                "color": "#173177"
            },
        }
    }
    x = WechatPush()
    x.do_push(data)
