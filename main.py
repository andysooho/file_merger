import tkinter as tk
from tkinter import filedialog, ttk
import os
from datetime import datetime

# 기본 윈도우
root = tk.Tk()
root.title("파일 병합기")


# 경로 입력 필드
path_entry = tk.Entry(root, width=50)
path_entry.pack()


# 경로 선택 버튼
def browse_path():
    path = filedialog.askdirectory()
    path_entry.delete(0, tk.END)
    path_entry.insert(0, path)
    load_tree(path)

browse_button = tk.Button(root, text="경로 선택", command=browse_path)
browse_button.pack()

# 파일 리스트를 담을 프레임 생성
frame = tk.Frame(root)
frame.pack(fill=tk.BOTH, expand=True)

# 트리뷰 생성 및 프레임에 배치
tree = ttk.Treeview(frame)
tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# 스크롤바 생성 및 프레임에 배치
scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# 트리뷰와 스크롤바 연동
tree.configure(yscrollcommand=scrollbar.set)


def load_tree(path):
    for i in tree.get_children():
        tree.delete(i)
    for root, dirs, files in os.walk(path):
        for file in files:
            tree.insert('', 'end', text=os.path.join(root, file))


# 트리뷰에 체크박스 추가
def add_checkboxes():
    pass  # 체크박스 추가 로직 구현


def merge_files():
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"result_{current_time}.txt"

    selected_items = tree.selection()
    with open(filename, "w", encoding="utf-8") as result_file:
        for item in selected_items:
            path = tree.item(item, 'text')
            result_file.write(path + "\n")
            with open(path, "r", encoding="utf-8") as file:
                content = file.read()
                result_file.write(content + "\n\n")


merge_button = tk.Button(root, text="파일 병합", command=merge_files)
merge_button.pack()

root.mainloop()

