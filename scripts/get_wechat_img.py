import requests
import json

WECHAT_APPID = "wx4495e2082f63f8ac"
WECHAT_APPSECRET = "23f0462bee8c56e09a2ac99321ed9952"


# 获取accessToken
def getToken():
    # 获取用户的accesstoken
    url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=' + WECHAT_APPID + "&secret=" + WECHAT_APPSECRET
    token_str = requests.post(url).content.decode()
    token_json = json.loads(token_str)
    print(token_json)
    token = token_json['access_token']
    print(token)
    return token


def get_media_id():
    file = {"file": open("yty.jpg", "rb")}
    token = getToken()
    url = "https://api.weixin.qq.com/cgi-bin/media/upload?access_token={}&type={}".format(token, "image")

    date = requests.post(url, files=file)
    resp_json = json.loads(date.content.decode())
    print(resp_json, "发送图片的返回值")
    media_id = resp_json["media_id"]
    print(media_id)
    return media_id


def send_text_msg(openid):
    # media = get_media_id()
    token = getToken()
    url = "https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={}".format(token)
    data = {
        "touser": openid,
        "msgtype": "image",
        "image":
            {
                "media_id": "DZo63X4IPhy7BvSRnRBrStUupf0P1rV0Kw2oam4yHJxDyjRGRlX2sTOQ2V1j5-6o"
            }
    }
    data_json = json.dumps(data)
    response = requests.post(url=url, data=data_json)
    print(response.content.decode())


def get_img_url():
    token = getToken()
    file = {"file": open("1794295707.jpg", "rb")}

    url = "https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={}".format(token)
    date = requests.post(url, files=file)
    resp_json = json.loads(date.content.decode())
    print(resp_json)


if __name__ == '__main__':
    send_text_msg(openid=100274)
