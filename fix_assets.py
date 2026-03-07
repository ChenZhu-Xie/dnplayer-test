import os
import glob

def fix_filenames():
    folder = 'assets/assistant_update'
    # 查找带有“开始更新”字样的文件
    for f in os.listdir(folder):
        if '开始更新' in f and f.endswith('.png'):
            old_path = os.path.join(folder, f)
            new_path = os.path.join(folder, 'update_btn_alt.png')
            os.rename(old_path, new_path)
            print(f"Renamed {f} to update_btn_alt.png")

if __name__ == "__main__":
    fix_filenames()
