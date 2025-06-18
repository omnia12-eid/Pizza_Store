🍕 Real-time Pizza Hygiene Violation Monitoring System

A microservices-based computer vision system to monitor hygiene protocol violations in a pizza preparation environment.


---

🚀 Project Overview

This project uses YOLO object detection to monitor video feeds in real-time and detect hygiene violations such as hands touching ingredients without a scooper. Violations are logged, visualized, and available for download.


---

🧠 Key Features

Real-time object detection using YOLOv8/YOLOv12

Detect hands, scoopers, pizzas, and more

Custom ROI (Region of Interest) drawing tool

Violation logic: If a hand is inside a specific ROI without a scooper, it triggers a violation

Violations must persist across multiple frames to be considered valid

Logs violations in a SQLite database and JSON file

Saves output video with overlaid detections and status

Web interface for live monitoring and report download



---

📁 Project Structure

Pizza_Store/
├── detection_service/
       |----- violations 
       |----- violations.db
│   ├── main.py                # Handles object detection and violation logic
│   └── roi.json              # Defined ROIs per ingredient zone
│
├── streaming_service/
│   ├── main.py                # Displays video, renders overlays, handles metadata
│   ├── templates/
│   │   └── index.html        # Frontend HTML page
│   └── roi.json/ou
│
├── data/
│   └── raw_videos/           # Test input videos
│
├── frame_reader/
│   └── main.py        # Sends video frames to RabbitMQ
│
├── shared/
│   └──   output.mp4     # Output video saved here
│   └── violations_log.json   # JSON log of violations
| Docker-compose.yml
| venv
| requirements.txt


---

🛠️ How It Works

1. send_frames.py reads frames from a video and sends them to RabbitMQ.


2. detection_service receives frames, runs YOLO detection, applies violation logic.


3. If a real violation is confirmed (e.g., hand without scooper inside ROI), it logs it and sends metadata to streaming_service.


4. streaming_service draws bounding boxes, overlays status text, and saves the full video.


5. A web interface shows:

Live video feed

Total violations

Violations table (timestamp + ROI)

Download buttons for report and video





---

🔧 Technologies Used

Python 3

OpenCV

Flask

RabbitMQ

SQLite

Pika

Numby 

Torch

Matplotlib 

Metadata

YOLO (Ultralytics)

HTML/CSS + JS (for frontend)



---

📅 Sample Violation Rule

if hand_in_roi and not scooper_in_roi:
    violation = True


---

📊 Output

output.mp4 - Video with bounding boxes and status overlay

violations_log.json - List of confirmed violations with timestamps

violations.db - SQLite DB with detailed records

status between violation and safe if there violation count it



---

🔹 Usage

1. Define ROIs using the provided drawing tool script.


2. Run each service:

send_frames.py

detection_service/main.py

streaming_service/main.py



3. Open the browser at http://localhost:5000 to monitor

---------------

## 🧪 Project Setup Instructions

To run the project, follow these steps:

1. **Activate the virtual environment**  
   Make sure you are inside the project directory, then activate  Python virtual environment venv:

   **Windows:**
   ```bash
   .\venv\Scripts\activate

Linux/macOS:

source venv/bin/activate

2. Install the required Python libraries
After activating the environment, install all required dependencies:

pip install -r requirements.txt


3. Start RabbitMQ using Docker Compose
Use Docker Compose to start the RabbitMQ server:

docker-compose up -d


4. Run the microservices manually
In separate terminal windows, run the following services one by one:

Frame Reader:

python frame_reader.py

Detection Service:

cd detection_service
python main.py

Streaming Service:

cd streaming_service
python main.py




Once all services are running, open your browser and go to:

http://localhost:5000

to access the live hygiene monitoring dashboard.




---

⚖️ License

This project is for educational purposes under MIT License.


---

🙏 Acknowledgments

Developed by : omnia abduo