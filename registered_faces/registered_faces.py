import cv2
import os

save_path = "rcaptured_faces"

if not os.path.exists(save_path):
    os.makedirs(save_path)

video_capture = cv2.VideoCapture(0)

print("Press 'c' to capture face.")
print("Press 'q' to quit.")

while True:
    ret, frame = video_capture.read()
    cv2.imshow('Register Face', frame)

    key = cv2.waitKey(1)

    if key & 0xFF == ord('c'):
        name = input("Enter name of the person: ")
        filename = os.path.join(save_path, f"{name}.jpg")
        cv2.imwrite(filename, frame)
        print(f"Saved {filename}")

    elif key & 0xFF == ord('q'):
        break

video_capture.release()
cv2.destroyAllWindows()