import json
import requests

# 建议用一个专用文件存储所有这种常量
AppSecret = "23f0462bee8c56e09a2ac99321ed9952"
AppId = "wx4495e2082f63f8ac"


# 获取用户的access_token
def get_token():
    url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=' + AppId + "&secret=" + AppSecret
    token_str = requests.get(url).content.decode()
    token_json = json.loads(token_str)
    token = token_json['access_token']
    return token


# 生成用户邀请二维码
def user_qrcode(code):
    """
    scene_id场景值ID
    :param code: 可以使用用户的id
    :return: 二维码
    """
    qr_code_url = None
    data = {
        "action_name": "QR_LIMIT_SCENE",
        "action_info": {
            "scene": {
                "scene_id": int(str(code)[1:])
            }
        }
    }
    data = json.dumps(data)
    try_times = 0
    while not qr_code_url and try_times < 5:
        try_times += 1
    try:
        # 调用方法，获取access_token
        token = get_token()
        request_url = "https://api.weixin.qq.com/cgi-bin/qrcode/create?access_token={}".format(token)
        req_json = requests.post(request_url, data).content.decode()
        req_dict = json.loads(req_json)
        qr_code_url = req_dict["ticket"]
        return qr_code_url
    except:
        pass

def save_qrcode(user_id):
    code = user_qrcode(user_id)
    url = "https://mp.weixin.qq.com/cgi-bin/showqrcode?ticket={}".format(code)
    qr_data = requests.get(url).content
    with open("/home/ubuntu/{}.jpg".format(user_id),"wb") as f:
        f.write(qr_data)
        print("保存成功")

if __name__ == '__main__':
    for i in range(1088):
        save_qrcode(100100+int(i))
