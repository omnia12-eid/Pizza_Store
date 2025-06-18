import cv2
import json
import os

# المتغيرات العامة
rois = {}
drawing = False
start_point = (-1, -1)
end_point = (-1, -1)
preview_image = None

# ألوان
COLOR_BOX = (0, 255, 255)      # أصفر
COLOR_TEXT = (255, 0, 0)       # أزرق

# مسار الصورة
image_path = "C:/Pizza_Store/detection_service/violations/frame_202.jpg"
if not os.path.exists(image_path):
    print("❌ Image not found. Please make sure shared/frame.jpg exists.")
    exit()

image = cv2.imread(image_path)
preview_image = image.copy()

def mouse_draw(event, x, y, flags, param):
    global start_point, end_point, drawing, preview_image

    temp = image.copy()

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        start_point = (x, y)

    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        cv2.rectangle(temp, start_point, (x, y), COLOR_BOX, 2)

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        end_point = (x, y)
        cv2.rectangle(temp, start_point, end_point, COLOR_BOX, 2)

        name = input("💬 Enter ROI name: ").strip()
        if name:
            x1, y1 = start_point
            x2, y2 = end_point
            x1, x2 = sorted([x1, x2])
            y1, y2 = sorted([y1, y2])
            rois[name] = [x1, y1, x2, y2]
            print(f"✅ ROI '{name}' added with coordinates: ({x1}, {y1}) to ({x2}, {y2})")

    preview_image = temp

# النافذة
cv2.namedWindow("Draw ROIs")
cv2.setMouseCallback("Draw ROIs", mouse_draw)

# عرض التعليمات
print("🖱️ Instructions:")
print(" - Draw ROI by dragging with left mouse button.")
print(" - Press 'u' to undo last ROI.")
print(" - Press 'c' to clear all ROIs.")
print(" - Press 's' to save and exit.")
print(" - Press 'q' to quit without saving.")

# تأكيد وجود مجلد الحفظ
save_path = os.path.join("detection_service", "roi.json")
os.makedirs(os.path.dirname(save_path), exist_ok=True)

# حلقة العرض والرسم
while True:
    temp_display = preview_image.copy()

    for name, (x1, y1, x2, y2) in rois.items():
        cv2.rectangle(temp_display, (x1, y1), (x2, y2), COLOR_BOX, 2)
        cv2.putText(temp_display, name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_TEXT, 2)

    cv2.imshow("Draw ROIs", temp_display)
    key = cv2.waitKey(10) & 0xFF

    if key == ord('q'):
        print("👋 Exit without saving.")
        break
    elif key == ord('s'):
        with open(save_path, "w") as f:
            json.dump(rois, f, indent=2)
        print(f"💾 ROIs saved successfully at: {os.path.abspath(save_path)}")
        break
    elif key == ord('u'):
        if rois:
            last = list(rois.keys())[-1]
            del rois[last]
            print(f"↩️ Removed last ROI: {last}")
    elif key == ord('c'):
        rois.clear()
        print("🗑️ Cleared all ROIs.")

cv2.destroyAllWindows()