import cv2
import pika
import base64
import json
import time
import os
import sys

# إعدادات
QUEUE_NAME = 'frames'
video_path =  r'C:/Pizza_Store/data/raw_videos/Sah b3dha ghalt.mp4'




# طباعة المسار الحالي ومسار الفيديو
print("Current working directory:", os.getcwd())
print(" Video path:", video_path)

# التحقق من وجود الفيديو
if not os.path.exists(video_path):
    print(f" Video file not found: {video_path}")
    sys.exit(1)

# الاتصال بـ RabbitMQ
try:
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='127.0.0.1'))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME)
    print(f" Connected to RabbitMQ and declared queue '{QUEUE_NAME}'")
except Exception as e:
    print(f"Failed to connect to RabbitMQ: {e}")
    sys.exit(1)

# قراءة الفيديو
cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print(" Failed to open video file.")
    sys.exit(1)

# إرسال الفريمات واحد تلو الآخر
frame_id = 0
print("🚀 Starting frame streaming...")
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print(" End of video reached.")
        break

    # تصغير الفريم لتقليل الحجم
    frame = cv2.resize(frame, (640, 360))

    # ترميز الفريم إلى base64
    _, buffer = cv2.imencode('.jpg', frame)
    encoded_frame = base64.b64encode(buffer).decode('utf-8')

    # إنشاء الرسالة
    message = {
        'frame_id': frame_id,
        'timestamp': time.time(),
        'frame': encoded_frame
    }

    # إرسال الرسالة
    channel.basic_publish(
        exchange='',
        routing_key=QUEUE_NAME,
        body=json.dumps(message)
    )

    print(f" Sent frame #{frame_id}")
    frame_id += 1
    time.sleep(0.03)  # حوالي 30 فريم/ثانية

# تنظيف وإنهاء
cap.release()
connection.close()
print(" All frames sent successfully.")