import os  
from openai import AzureOpenAI
from flask import Flask, request, jsonify, abort, send_from_directory  
from collections import deque
import http.client  
import json
import urllib.parse
from gettoken import get_token 
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
appKey = 'gzu3Qn6dPavwpBIl'  
token =  get_token() 
audioSaveFile = 'syAudio.wav'
format = 'wav'
sampleRate = 16000


def load_api_keys(file_path):
     with open(file_path, 'r') as f:  
        return [line.strip() for line in f.readlines()]  

api_keys = load_api_keys('key.txt')

#语音转文本服务
def recognize_audio(appKey, token, audioFile):  
    host = 'nls-gateway-cn-shanghai.aliyuncs.com'  
    url = 'https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/asr'  
  
    # 读取音频文件  
    with open(audioFile, mode='rb') as f:  
        audioContent = f.read()  
  
    # 设置HTTPS请求头部  
    httpHeaders = {  
        'X-NLS-Token': token,  
        'Content-type': 'application/octet-stream',  
        'Content-Length': len(audioContent)  
    }  
  
    # 发送HTTP请求  
    conn = http.client.HTTPSConnection(host)  
    conn.request(method='POST', url=url + '?appkey=' + appKey, body=audioContent, headers=httpHeaders)  
    response = conn.getresponse()  
  
    # 处理响应  
    body = response.read()  
    try:  
        body = json.loads(body)  
        status = body['status']  
        if status == 20000000:  
            result = body['result']  
            return result  
        else:  
            return '识别失败！'  
    except ValueError:  
        return '响应不是JSON格式。'  


#文本转语音服务  
def processGETRequest(appKey, token, text, audioSaveFile, format, sampleRate) :
    text = urllib.parse.quote_plus(text)
    text = text.replace("+", "%20")
    text = text.replace("*", "%2A")
    text = text.replace("%7E", "~")
       
    host = 'nls-gateway-cn-shanghai.aliyuncs.com'
    url = 'https://' + host + '/stream/v1/tts'
    # 设置URL请求参数
    url = url + '?appkey=' + appKey
    url = url + '&token=' + token
    url = url + '&text=' + text
    url = url + '&format=' + format
    url = url + '&sample_rate=' + str(sampleRate)
    # voice 发音人，可选，默认是xiaoyun。
    url = url + '&voice=' + 'zhimiao_emo'
    # volume 音量，范围是0~100，可选，默认50。
    # url = url + '&volume=' + str(50)
    # speech_rate 语速，范围是-500~500，可选，默认是0。
    # url = url + '&speech_rate=' + str(0)
    # pitch_rate 语调，范围是-500~500，可选，默认是0。
    # url = url + '&pitch_rate=' + str(0)
    print(url)
    # Python 2.x请使用httplib。
    # conn = httplib.HTTPSConnection(host)
    # Python 3.x请使用http.client。
    conn = http.client.HTTPSConnection(host)
    conn.request(method='GET', url=url)
    # 处理服务端返回的响应。
    response = conn.getresponse()
    print('Response status and response reason:')
    print(response.status ,response.reason)
    contentType = response.getheader('Content-Type')
    print(contentType)
    body = response.read()
    if 'audio/mpeg' == contentType :
        with open(audioSaveFile, mode='wb') as f:
            f.write(body)
        print('The GET request succeed!')
    else :
        print('The GET request failed: ' + str(body))
    conn.close()



# 初始化聊天记录队列，最大长度为10  
chat_history = deque(maxlen=10) 

# 从环境变量中获取 API 密钥和终端  
api_key = os.getenv("AZURE_OPENAI_API_KEY")  
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")  
  
  
# 初始化 AzureOpenAI 客户端  
client = AzureOpenAI(  
    api_key=api_key,  
    api_version="2024-02-01",  
    azure_endpoint=azure_endpoint  
)  
  
deployment_name = '0104-test'  # 这个名字需要与你部署模型时的自定义名字对应

system_message = {  
    "role": "system",  
    "content": "你是英文儿童陪伴助理，请一直使用英文回复我。请你一定要说英语"  
}  



def chat(usr_input):


    # 添加用户输入到聊天记录队列  
    chat_history.append({"role": "user", "content": usr_input})  

    messages = [system_message] + list(chat_history) 
    print(messages)
    
    # 发送完成请求以生成答案  
    completion = client.chat.completions.create(
    model=deployment_name,
    messages=messages
    
    )

    # 获取GPT的回复  
    gpt_reply = completion.choices[0].message.content

    # 将GPT的回复添加到聊天记录队列  
    chat_history.append({"role": "assistant", "content": gpt_reply})

    return gpt_reply
      
@app.route('/upload', methods=['POST']) 
def upload():
    api_key = request.headers.get('API-Key')
    if api_key not in api_keys:  
        abort(401)  
    
    audio_file = request.files.get('audio')
    if audio_file:
         # 使用 secure_filename 清洁文件名  
        filename = secure_filename(audio_file.filename)  
        # 保存文件到上传文件夹  
        audio_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)  
        audio_file.save(audio_file_path) 

    else:
        print("No audio file found in the request")

    tts_result = recognize_audio(appKey,token,audio_file_path)
    print("tts-result:",tts_result)
    chat_response = chat(tts_result)
    #print("AI:",chat_response)
    
    #print("encodetext:",textUrlencode)
    processGETRequest(appKey,token,chat_response,audioSaveFile,format,sampleRate)
    audio_file_url = request.host_url + "download/" + audioSaveFile
    
    
    return jsonify({  
        "user_text:": tts_result,
        "audio_url": audio_file_url,  
        "text": chat_response  
    })

@app.route('/download/<filename>',methods=['GET'])
def download_file(filename):
    safe_filename = secure_filename(filename)
    directory = '.'
    try:
        return send_from_directory(directory,safe_filename,as_attachment=True)
    except FileNotFoundError:  
        abort(404)  


if __name__ == '__main__':  
    app.run(host='0.0.0.0',port=5051)  
