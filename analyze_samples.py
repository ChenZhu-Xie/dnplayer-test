import cv2
import numpy as np
import os

def analyze_sample_hierarchy():
    folder = 'assets/assistant_update/renamed'
    # 映射之前的重命名对应关系
    # img_2: 游戏背景
    # img_3: 辅助更新界面+游戏背景
    # img_4: 辅助更新界面 (UI Only)
    # img_5: 按钮
    
    mapping = {
        'img_2.png': 'Background (Layer 0)',
        'img_3.png': 'Full State (UI + BG)',
        'img_4.png': 'UI Container (Layer 2)',
        'img_5.png': 'Interaction Button (Layer 3)'
    }
    
    print("--- 教学样板层次关系分析报告 ---")
    for fname, label in mapping.items():
        path = os.path.join(folder, fname)
        img = cv2.imread(path)
        if img is not None:
            print(f"[{label}] -> {fname}: Size={img.shape[1]}x{img.shape[0]}, Mean={np.mean(img):.2f}")
        else:
            print(f"[{label}] -> {fname}: MISSING")

if __name__ == "__main__":
    analyze_sample_hierarchy()
