import cv2
import numpy as np
import os

def check_images():
    paths = [
        'assets/assistant_update/辅助更新的公告界面.png',
        'assets/assistant_update/辅助更新的公告界面+游戏背景.png',
        'assets/assistant_update/辅助更新的公告界面中的“开始更新”按钮（略微有点按钮外的面板）.png',
        'assets/assistant_update/游戏背景.png'
    ]
    
    for p in paths:
        img = cv2.imread(p)
        if img is not None:
            print(f"File: {os.path.basename(p)}")
            print(f"  Shape: {img.shape}")
            print(f"  Mean Brightness: {np.mean(img):.2f}")
        else:
            print(f"File: {os.path.basename(p)} - FAILED TO READ")

if __name__ == "__main__":
    check_images()
