import socket
import datetime
import threading
import os
import time

# 设置IP和端口
HOST = '0.0.0.0'
PORT = 514

# 存放日志的目录
LOG_DIR = 'log'

def debug_log(message):
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{current_time}] {message}")

def get_filename(client_ip):
    """根据当前日期和客户端IP获取文件名"""
    today = datetime.datetime.now().strftime('%Y%m%d')  # 获取今天的日期
    # 将IP地址的点替换为下划线，以便用作文件名的一部分
    formatted_ip = client_ip.replace('.', '_')
    filename = f"ATS_PSD_log_{today}_{formatted_ip}.txt"
    # 指向log文件夹
    return os.path.join(LOG_DIR, filename)

def save_data(data, client_ip):
    # 检查log文件夹是否存在，如果不存在则创建
    if not os.path.exists(LOG_DIR):
        os.mkdir(LOG_DIR)
        
    """保存接收到的数据以及时间戳"""
    filename = get_filename(client_ip)
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    with open(filename, 'a') as file:
        file.write(f"[{timestamp}] {data}\n")

def cleanup_old_files():
    """删除超过30天的文件"""
    if not os.path.exists(LOG_DIR):
        return
        
    current_time = datetime.datetime.now()
    for file in os.listdir(LOG_DIR):
        if "ATS_PSD_log_" in file:
            file_path = os.path.join(LOG_DIR, file)
            file_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            delta = current_time - file_time
            if delta.days > 30:  # 文件超过30天
                try:
                    os.remove(file_path)
                    debug_log(f"Deleted old file: {file}")
                except OSError as e:
                    debug_log(f"Failed to delete {file}. Error: {e}")

def handle_client(conn, addr):
    """处理客户端连接"""
    debug_log(f"Connected by: {addr}")
    client_ip, _ = addr
    conn.settimeout(60)  # 如果60秒没有数据则超时

    with conn:
        while True:
            try:
                data = conn.recv(2048)
                if not data:  # 客户端断开连接
                    break
                try:
                    decoded_data = data.decode('gbk')  # 尝试使用GBK编码解码
                    save_data(decoded_data, client_ip)
                    try:
                        conn.sendall(b"Data received")
                    except socket.error as e:
                        debug_log(f"Failed to send reply to {client_ip}. Error: {e}")
                except UnicodeDecodeError:
                    debug_log("Received data could not be decoded as GBK.")
            except socket.timeout:  # 处理超时异常
                debug_log(f"Connection timed out for {addr}. Closing connection.")
                break
            except ConnectionResetError:
                debug_log(f"Connection reset by {addr}.")
                break  # 结束当前客户端的处理

def cleanup_loop():
    """持续进行文件清理的循环"""
    while True:
        cleanup_old_files()  # 在程序启动时首先执行一次清理操作
        time.sleep(86400)  # 每天执行一次

def main():
    # 启动文件清理线程
    cleanup_thread = threading.Thread(target=cleanup_loop)
    cleanup_thread.daemon = True  # 将线程设置为守护线程
    cleanup_thread.start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        debug_log(f"Server started on {HOST}:{PORT}. Press Ctrl+C to exit.")
        
        try:
            while True:
                conn, addr = s.accept()
                # 为每个客户端连接创建新的线程
                client_thread = threading.Thread(target=handle_client, args=(conn, addr))
                client_thread.start()
        except KeyboardInterrupt:
            debug_log("\nShutting down the server.")

if __name__ == '__main__':
    main()
