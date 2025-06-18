import base64
import json
import pika
import cv2
import numpy as np
from ultralytics import YOLO
import os
import time
import sqlite3

# تحميل النموذج
model = YOLO("yolo12m-v2.pt")

# تحميل ROIs
roi_path = os.path.join(os.path.dirname(__file__), "roi.json")
with open(roi_path, "r") as f:
    roi_data = json.load(f)
ROI_BOXES = {name: tuple(coords) for name, coords in roi_data.items()}

# إنشاء قاعدة البيانات
conn = sqlite3.connect("violations.db", check_same_thread=False)
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS violations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        frame_id INTEGER,
        timestamp TEXT,
        roi TEXT,
        labels TEXT,
        bbox TEXT
    )
''')
conn.commit()

# متغيرات منطق الانتهاك الحقيقي
violation_active = False
violation_start_frame = None
VIOLATION_DURATION_FRAMES = 30

# دالة التأكد من وجود مركز الكائن داخل ROI معين
def is_inside_roi(bbox, roi_box):
    x1, y1, x2, y2 = bbox
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    rx1, ry1, rx2, ry2 = roi_box
    return rx1 <= cx <= rx2 and ry1 <= cy <= ry2

# فك تشفير الفريم
def decode_frame(encoded_frame):
    decoded = base64.b64decode(encoded_frame)
    np_data = np.frombuffer(decoded, dtype=np.uint8)
    return cv2.imdecode(np_data, cv2.IMREAD_COLOR)

# التحقق من وجود انتهاك في الفريم الحالي
def is_violation(detections):
    for roi_name, roi_box in ROI_BOXES.items():
        hand_inside = any(det['name'] == 'hand' and is_inside_roi(det['bbox'], roi_box) for det in detections)
        scooper_inside = any(det['name'] == 'scooper' and is_inside_roi(det['bbox'], roi_box) for det in detections)

        if hand_inside and not scooper_inside:
            return True, roi_name
    return False, None

# المعالجة
def process_frame(ch, method, properties, body):
    global violation_active, violation_start_frame

    data = json.loads(body)
    frame_id = data.get("frame_id", 0)
    frame = decode_frame(data['frame'])
    results = model(frame, verbose=False)[0]

    detections = []
    for box in results.boxes.data.tolist():
        x1, y1, x2, y2, score, class_id = box
        name = results.names[int(class_id)]
        detections.append({
            'name': name,
            'bbox': [int(x1), int(y1), int(x2), int(y2)],
            'score': float(score)
        })

    print(f"\n📦 Frame #{frame_id} processed.")
    violation_now, roi_name = is_violation(detections)

    confirmed_violation = False
    ts = None

    if violation_now:
        if not violation_active:
            violation_active = True
            violation_start_frame = frame_id
            print("⚠️ Violation started...")
        elif frame_id - violation_start_frame >= VIOLATION_DURATION_FRAMES:
            confirmed_violation = True
            violation_active = False
            ts = time.strftime('%Y-%m-%d %H:%M:%S')

            # حفظ قاعدة البيانات
            c.execute('''
                INSERT INTO violations (frame_id, timestamp, roi, labels, bbox)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                frame_id,
                ts,
                roi_name,
                json.dumps([d['name'] for d in detections]),
                json.dumps([d['bbox'] for d in detections])
            ))
            conn.commit()

            # تسجيل JSON
            log_path = os.path.join(os.path.dirname(__file__), "violations_log.json")
            log_entry = {
                "frame_id": frame_id,
                "timestamp": ts,
                "roi": roi_name,
                "detected": [d['name'] for d in detections]
            }
            if not os.path.exists(log_path):
                with open(log_path, "w") as f:
                    json.dump([], f)

            with open(log_path, "r+") as f:
                try:
                    logs = json.load(f)
                except json.JSONDecodeError:
                    logs = []
                logs.append(log_entry)
                f.seek(0)
                f.truncate()
                json.dump(logs, f, indent=2)

            print(f"🚨 Confirmed violation in ROI: {roi_name}")
    else:
        violation_active = False
        violation_start_frame = None
        print("✅ Safe - No violation detected.")

    # إرسال النتيجة
    result = {
        "frame_id": frame_id,
        "frame": data['frame'],
        "detections": detections,
        "violation": confirmed_violation
    }

    channel.basic_publish(
        exchange='',
        routing_key='processed_frames',
        body=json.dumps(result)
    )

# RabbitMQ setup
try:
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='frames')
    channel.queue_declare(queue='processed_frames')
    channel.basic_consume(queue='frames', on_message_callback=process_frame, auto_ack=True)

    print("🚀 Detection service running...")
    channel.start_consuming()

except KeyboardInterrupt:
    print("🛑 Detection stopped by user.")

finally:
    conn.close()
    print("🗃️ SQLite connection closed.")