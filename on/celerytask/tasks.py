from celery import Celery
import time
import json
import requests
import os
import random
from selenium import webdriver

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.local")

# app = Celery('celerytask.tasks', broker='redis://119.29.191.32:6379/5')
app = Celery('celerytask.tasks', broker='redis://119.29.191.32:6379/1')



@app.task
def send_img(user_id, openid, screen_time, random_str, token):
    try:
        print("开始截图")
        driver = webdriver.PhantomJS()
        driver.set_window_size(1080, 1710)
        # driver.viewportSize = {'width': 1920, 'height': 1080}
        driver.get(
            "http://wechat.onmytarget.cn/user/user_screenshot?user_id={}&img_random={}".format(user_id, random))

        img_name = "{}_{}_{}.png".format(user_id, screen_time, random_str)
        screen_path = os.path.join("./screenshot/", str(user_id) + "/", screen_time + "/")
        print(screen_path, "保存的路径")
        if not os.path.exists(screen_path):
            os.makedirs(screen_path)
        # 将截取的图片保存到截图文件夹中
        driver.save_screenshot(screen_path + img_name)
        full_path = screen_path + img_name
        print("保存成功")
        url = "https://api.weixin.qq.com/cgi-bin/media/upload?access_token={}&type={}".format(token, "image")
        file = {"file": open(full_path, "rb")}
        date = requests.post(url, files=file)
        resp_json = json.loads(date.content.decode())
        print(resp_json, "发送图片的返回值")
        media_id = resp_json["media_id"]
        kefu = "https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={}".format(token)
        data_str = {
            "touser": "{}".format(openid),
            "msgtype": "image",
            "image":
                {
                    "media_id": "{}".format(media_id)
                }
        }
        data = json.dumps(data_str)
        response = requests.post(kefu, data)
        print("发送成功")
        print(response.content.decode())
    except Exception as e:
        print(e)


@app.task
def print_test():
    time.sleep(3)
    print("测试成功")
