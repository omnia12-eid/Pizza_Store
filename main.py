import base64
import json
import pika
import threading
import cv2
import numpy as np
from flask import Flask, Response, jsonify, render_template, send_file
import os
import io
import time
import matplotlib.pyplot as plt
from datetime import datetime
import atexit
#تهيئة تطبيق flask
app = Flask(__name__)
frames_buffer = []
violation_count = 0
violations_log = []

# إعداد الفيديو
video_output_path = "c:/Pizza_Store/shared/output1.mp4"
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
video_writer = cv2.VideoWriter(video_output_path, fourcc, 25.0, (640, 480))
# تعرض صفحة html
@app.route('/')
def index():
    return render_template('index.html')
#بث الفيديو
@app.route('/video')
def video_feed():
    def generate():
        last_frame = None
        while True:
            if frames_buffer:
                last_frame = frames_buffer[-1]
            if last_frame is not None:
                _, jpeg = cv2.imencode('.jpg', last_frame)
                frame = jpeg.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(1 / 30.0)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')
#API: ارجاع عدد الانتهاكات والفريمات
@app.route('/metadata')
def metadata():
    return jsonify({
        "violations": violation_count,
        "frames_received": len(frames_buffer)
    })
# عرض سجل الانتهاكات
@app.route('/violations')
def get_violations():
    return jsonify({"violations": violations_log})
# رسم مخطط للانتهاكات
@app.route('/plot')
def plot():
    try:
        times = [datetime.strptime(entry['timestamp'], "%Y-%m-%d %H:%M:%S") for entry in violations_log]
        if not times:
            return "<h3>No violations to display</h3>"

        times.sort()
        plt.figure(figsize=(8, 4))
        plt.hist(times, bins=10, color='red', edgecolor='black')
        plt.title("Violations Over Time")
        plt.xlabel("Time")
        plt.ylabel("Count")
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        return Response(buf.getvalue(), mimetype='image/png')

    except Exception as e:
        return f"<h3>Error generating plot: {str(e)}</h3>"
# تنزيل الفيديو المحفوظ
@app.route('/download')
def download():
    return send_file(video_output_path, as_attachment=True)
# تنزيل تقرير الانتهاكات
@app.route('/report')
def report():
    path = "violations_log.json"
    with open(path, "w") as f:
        json.dump(violations_log, f, indent=2)
    return send_file(path, as_attachment=True)
# رسم الكائنات و roi علي الفريم 
def draw_detections(frame, detections, rois, violation, count):
    # رسم كل الـ ROIs
    for name, box in rois.items():
        x1, y1, x2, y2 = box
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
        cv2.putText(frame, name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 200), 2)

    # رسم الكائنات
    for d in detections:
        x1, y1, x2, y2 = d['bbox']
        label = f"{d['name']} | {d['score']*100:.1f}%"
        color = (0, 0, 255) if violation else (0, 255, 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # عرض عدد الانتهاكات
    cv2.putText(frame, f"Violations: {count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # عرض الحالة
    status_text = "🚨 Violation!" if violation else "✅ Safe"
    status_color = (0, 0, 255) if violation else (0, 255, 0)
    cv2.putText(frame, status_text, (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.9, status_color, 2)

    return frame
# فك ترميز الفريم المرسل
def decode_frame(encoded):
    decoded = base64.b64decode(encoded)
    np_data = np.frombuffer(decoded, dtype=np.uint8)
    return cv2.imdecode(np_data, cv2.IMREAD_COLOR)
# استقبال rabbitmq للرسائل واستماعها
def start_listening():
    global violation_count
    try:
        roi_path = os.path.join(os.path.dirname(__file__), "roi.json")
        with open(roi_path, "r") as f:
            rois = json.load(f)
#الاتصال ب rabbitmq
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='processed_frames')
# الدالة التي تتعامل مع كل فريم مستلم
        def callback(ch, method, properties, body):
            global violation_count
            try:
                data = json.loads(body)
                frame = decode_frame(data['frame'])
                detections = data['detections']
                violation = data.get('violation', False)
                ts = data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                roi_name = data.get("roi", "unknown")

                if violation:
                    violation_count += 1
                    violations_log.append({"timestamp": ts, "roi": roi_name})

                drawn = draw_detections(frame, detections, rois, violation, violation_count)
                frames_buffer.append(drawn)
                video_writer.write(drawn)

            except Exception as e:
                print(f"Callback error: {e}")
# ربط الاستماع مع callback
        channel.basic_consume(queue='processed_frames', on_message_callback=callback, auto_ack=True)
        print("📺 Streaming service is running and receiving frames...")
        channel.start_consuming()

    except Exception as e:
        print(f"❌ Error in start_listening: {e}")
# بدء التطبيق
if __name__ == '__main__':
    t = threading.Thread(target=start_listening)
    t.daemon = True
    t.start()
    app.run(host='0.0.0.0', port=5000)
#لاغلاق الفيديو بشكل صحيح
@atexit.register
def release_video_writer():
    global video_writer
    if video_writer.isOpened():
        print("💾 Closing video file properly...")
        video_writer.release()