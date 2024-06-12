#! /usr/bin/env python  
# coding=utf-8  
import os  
import time  
import json  
from aliyunsdkcore.client import AcsClient  
from aliyunsdkcore.request import CommonRequest  
  
TOKEN_FILE = 'token.json'  
  
def save_token(token, expire_time):  
    with open(TOKEN_FILE, 'w') as f:  
        json.dump({'token': token, 'expire_time': expire_time}, f)  
  
def load_token():  
    if not os.path.exists(TOKEN_FILE):  
        return None, None  
    with open(TOKEN_FILE, 'r') as f:  
        data = json.load(f)  
        return data.get('token'), data.get('expire_time')  
  
def is_token_valid(expire_time):  
    return expire_time and time.time() < expire_time  
  
def get_token():  
    token, expire_time = load_token()  
    if is_token_valid(expire_time):  
        print("Using cached token")  
        return token  
      
    # 创建AcsClient实例  
    client = AcsClient(  
        os.getenv('ALIYUN_AK_ID'),  
        os.getenv('ALIYUN_AK_SECRET'),  
        "cn-shanghai"  
    )  
      
    # 创建request，并设置参数  
    request = CommonRequest()  
    request.set_method('POST')  
    request.set_domain('nls-meta.cn-shanghai.aliyuncs.com')  
    request.set_version('2019-02-28')  
    request.set_action_name('CreateToken')  
      
    try:  
        response = client.do_action_with_exception(request)  
        jss = json.loads(response)  
        if 'Token' in jss and 'Id' in jss['Token']:  
            token = jss['Token']['Id']  
            expire_time = jss['Token']['ExpireTime']  
            save_token(token, expire_time)  
            print("New token obtained")  
            print("token = " + token)  
            print("expireTime = " + str(expire_time))  
            return token  
    except Exception as e:  
        print(e)  
        return None  
  

