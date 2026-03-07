import cv2
import numpy as np
import os

def check_renamed():
    base_dir = 'assets/assistant_update/renamed'
    for i in range(1, 6):
        p = os.path.join(base_dir, f'img_{i}.png')
        img = cv2.imread(p)
        if img is not None:
            print(f"File: img_{i}.png")
            print(f"  Shape: {img.shape}")
            print(f"  Mean: {np.mean(img):.2f}")
            # 计算局部特征，识别哪个是按钮
            # 按钮通常很小
            if img.shape[0] < 200 and img.shape[1] < 500:
                print("  => POTENTIAL BUTTON")
        else:
            print(f"File: img_{i}.png - FAILED")

if __name__ == "__main__":
    check_renamed()
