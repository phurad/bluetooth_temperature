import os
import threading
from flask import Flask, render_template, request, redirect, url_for,make_response,jsonify
import pandas as pd
import matplotlib.pyplot as plt
import io
import matplotlib
import getdata

lock = threading.Lock()
matplotlib.use('Agg')  # 设置 matplotlib 后端为 'Agg'，适合服务器端渲染
app= Flask(__name__)
filename= 'data.xlsx' #默认文件名

is_running = False
interval = 2
file_path='uploads/data.xlsx' #默认保存文件路径
num_data=10 #默认用最近的十条数据生成图像

# 定义文件上传的目录
UPLOAD_FOLDER = 'uploads/'

# 确保上传目录存在
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_latest_data():
    # 读取 Excel 文件 (假设文件名为 data.xlsx)
    df = pd.read_excel(file_path)

    # 格式化 localtime 列为 "YYYY-MM-DD HH:MM" 格式
    df['localtime'] = pd.to_datetime(df['localtime']).dt.strftime('%Y-%m-%d %H:%M:%S')

    # 获取最新的10条数据
    latest_data = df.tail(num_data)

    # 将数据转换为字典形式
    data = latest_data.to_dict(orient='records')
    return data
# 生成温度图的函数
def generate_temperature_plot():
    with lock:  # 确保线程安全
        df = pd.read_excel(file_path)
        df['localtime'] = pd.to_datetime(df['localtime'])  # 转换为日期时间类型

        # 获取最新的10组数据
        latest_data = df.tail(num_data)

        # 设置图表大小
        plt.figure(figsize=(8, 4))

        # 绘制温度图表，X 轴为 localtime，Y 轴为 temperature
        plt.plot(latest_data['localtime'].dt.strftime('%H:%M:%S'), latest_data['temperature'], marker='o', color='b')

        plt.title('Temperature over Time')
        plt.xlabel('Time (HH:MM:SS)')
        plt.ylabel('Temperature (°C)')
        plt.xticks(rotation=45)  # 旋转 X 轴标签，避免重叠
        plt.tight_layout()

        # 将图表保存为字节流
        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        plt.close()  # 关闭图形，防止重叠
        return img


# 生成湿度图的函数
def generate_humidity_plot():
    with lock:  # 确保线程安全

        df = pd.read_excel(file_path)
        df['localtime'] = pd.to_datetime(df['localtime'])  # 转换为日期时间类型

        # 获取最新的10组数据
        latest_data = df.tail(num_data)

        # 设置图表大小
        plt.figure(figsize=(8, 4))

        # 绘制湿度图表，X 轴为 localtime，Y 轴为 humidity
        plt.plot(latest_data['localtime'].dt.strftime('%H:%M:%S'), latest_data['humidity'], marker='o', color='g')

        plt.title('Humidity over Time')
        plt.xlabel('Time (HH:MM:SS)')
        plt.ylabel('Humidity (%)')
        plt.xticks(rotation=45)  # 旋转 X 轴标签
        plt.tight_layout()

        # 将图表保存为字节流
        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        plt.close()  # 关闭图形，防止重叠
        return img



# 注册装饰器
def register_data_route(app):
    @app.route('/data')
    def data():
        if is_running:
            data = getdata.result
            return jsonify(data.__dict__)
        else:
            return jsonify({"message": "Data route is not active."})
# 注册所有路由
register_data_route(app)



# 返回最新10条数据的JSON
@app.route('/latest-data')
def latest_data():
    data = get_latest_data()
    return jsonify(data)

# 查询蓝牙连接状态
@app.route('/bluetooth_status', methods=['GET'])
def bluetooth_status_endpoint():
    return jsonify({'status': getdata.bluetooth_status})


# 返回温度图
@app.route('/temperature-plot.png')
def temperature_plot():
    img = generate_temperature_plot()
    return make_response(img.getvalue()), 200, {'Content-Type': 'image/png'}


# 返回湿度图
@app.route('/humidity-plot.png')
def humidity_plot():
    img = generate_humidity_plot()
    return make_response(img.getvalue()), 200, {'Content-Type': 'image/png'}


@app.route('/start', methods=['POST'])
def start():
    global is_running, interval
    if not is_running:
        # 这里你可以添加启动程序的逻辑
        print("程序已开始")
        is_running = True
        # 重新启动 getdata.py 中的守护线程
        getdata.start_thread(interval)
        getdata.bluetooth_status='蓝牙连接中...'
    return 'started'

@app.route('/stop', methods=['POST'])
def stop():
    global is_running
    if is_running:
        # 这里你可以添加停止程序的逻辑
        print("程序已终止")
        is_running = False
        # 设置停止标志并停止守护线程
        getdata.stop_thread()
        getdata.bluetooth_status = '未连接'
    return "Stopped"


@app.route('/')
def index():
    print("interval:",interval)

    return render_template('index.html')


@app.route('/set_value', methods=['POST'])
def set_value():
    global interval
    input_value = request.json.get('interval')
    try:
        interval = int(input_value)
        # 重新启动守护线程以应用新的时间间隔
        if is_running:
            getdata.stop_thread()
            getdata.start_thread(interval)
        return jsonify({"status": "success", "message": f"当前的检测时间间隔为是{interval}秒"})
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "请输入整数"}), 400

# 处理文件名提交的路由
@app.route('/set_filename', methods=['POST'])
def set_filename():
    global file_path  # 使用全局变量保存文件路径
    filename = request.form['filename']+'.xlsx'  # 获取表单中的文件名
    if filename:
        file_path = os.path.join('uploads', filename)  # 设置 file_path
        try:
            test = pd.read_excel(file_path)
        except FileNotFoundError:
            getdata.write_init(file_path)
        getdata.path=file_path
        #return jsonify({"status": "success", "message": f"当前的保存路径是:{file_path}"})
        return jsonify({'file_path': file_path})  # 返回 JSON 响应

if __name__ == '__main__':
    app.run(debug=True)
