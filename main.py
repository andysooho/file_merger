import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import os
from datetime import datetime
import threading
import queue
import fnmatch


class FileMerger:
    def __init__(self, master):
        self.master = master
        master.title("고오급 파일 병합기")
        master.geometry("1000x700")

        self.create_widgets()
        self.file_queue = queue.Queue()
        self.stop_thread = threading.Event()

    def create_widgets(self):
        # 경로 입력 프레임
        path_frame = ttk.Frame(self.master, padding="10")
        path_frame.pack(fill=tk.X)

        self.path_entry = ttk.Entry(path_frame, width=50)
        self.path_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

        browse_button = ttk.Button(path_frame, text="경로 선택", command=self.browse_path)
        browse_button.pack(side=tk.RIGHT)

        # 파일 리스트 프레임
        list_frame = ttk.Frame(self.master, padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True)

        # 체크박스 열 추가
        self.tree = ttk.Treeview(list_frame, columns=("Checked", "Size", "Date Modified"), selectmode="extended")
        self.tree.heading("#0", text="파일 경로")
        self.tree.column("#0", minwidth=400, width=400, stretch=True)  # 파일 경로 열 넓게
        self.tree.heading("Checked", text="선택")
        self.tree.column("Checked", width=50, anchor="center", stretch=False)
        self.tree.heading("Size", text="크기")
        self.tree.column("Size", width=80, anchor="center", stretch=False)
        self.tree.heading("Date Modified", text="수정일")
        self.tree.column("Date Modified", width=120, anchor="center", stretch=False)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # 체크박스 클릭 이벤트 바인딩
        self.tree.bind("<Button-1>", self.toggle_check)

        # 필터 프레임
        filter_frame = ttk.Frame(self.master, padding="10")
        filter_frame.pack(fill=tk.X)

        ttk.Label(filter_frame, text="확장자 필터:").pack(side=tk.LEFT)
        self.extension_entry = ttk.Entry(filter_frame, width=10)
        self.extension_entry.pack(side=tk.LEFT)
        self.extension_entry.insert(0, "*")

        ttk.Label(filter_frame, text="제외 항목:").pack(side=tk.LEFT)
        self.exclude_entry = ttk.Entry(filter_frame, width=30)
        self.exclude_entry.pack(side=tk.LEFT)
        self.exclude_entry.insert(0,
                                  ".env,logs,*.csv,*.xlsx,*.pyc,*.pyc,*.log,.idea,.github,.git,.DS_Store,*.json,*.lock,*.md,*.yml,*.yaml,*.erb,"
                                  "*.scss,*.css,*.svg,*.png,*.gif,*.jpg,*.ico,*.woff,*.woff2,*.mp3,*.xlsx,.venv,.gitignore,.env,*.db")

        refresh_button = ttk.Button(filter_frame, text="새로고침", command=self.refresh_tree)
        refresh_button.pack(side=tk.RIGHT)

        # 선택 도구 프레임
        select_frame = ttk.Frame(self.master, padding="10")
        select_frame.pack(fill=tk.X)

        select_all_button = ttk.Button(select_frame, text="모두 선택", command=self.select_all)
        select_all_button.pack(side=tk.LEFT)

        deselect_all_button = ttk.Button(select_frame, text="모두 선택 해제", command=self.deselect_all)
        deselect_all_button.pack(side=tk.LEFT)

        # 진행 상황 표시 바
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.master, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=10, pady=5)

        # 상태 레이블
        self.status_label = ttk.Label(self.master, text="준비")
        self.status_label.pack(pady=5)

        # 병합 버튼
        merge_button = ttk.Button(self.master, text="파일 병합", command=self.start_merge)
        merge_button.pack(pady=10)

        # 키보드 단축키 바인딩
        self.master.bind("<Control-a>", self.select_all)
        self.master.bind("<Control-A>", self.select_all)  # Shift+Ctrl+A

    def browse_path(self):
        path = filedialog.askdirectory()
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)
            self.refresh_tree()

    def should_exclude(self, path, exclude_patterns):
        name = os.path.basename(path)
        return any(fnmatch.fnmatch(name, pattern) for pattern in exclude_patterns)

    def refresh_tree(self):
        # Treeview 초기화
        for i in self.tree.get_children():
            self.tree.delete(i)

        path = self.path_entry.get()
        include_pattern = self.extension_entry.get()
        exclude_patterns = [item.strip() for item in self.exclude_entry.get().split(",")]

        if not path or not os.path.exists(path):
            return

        for root, dirs, files in os.walk(path):
            # 제외 폴더 제거
            dirs[:] = [d for d in dirs if not self.should_exclude(d, exclude_patterns)]

            for file in files:
                full_path = os.path.join(root, file)
                # 포함 패턴 & 제외 패턴 검사
                if (fnmatch.fnmatch(file, include_pattern)
                        and not self.should_exclude(full_path, exclude_patterns)):
                    size = os.path.getsize(full_path)
                    modified = os.path.getmtime(full_path)
                    modified_date = datetime.fromtimestamp(modified).strftime('%Y-%m-%d %H:%M:%S')
                    # 체크박스(✓) 표시를 기본값으로
                    self.tree.insert('', 'end',
                                     text=full_path,
                                     values=("✓", f"{size / 1024:.2f} KB", modified_date),
                                     tags=('checked',))

    def toggle_check(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            if column == "#1":  # 체크박스 열(첫 번째 데이터 열)
                item = self.tree.identify_row(event.y)
                tags = self.tree.item(item, "tags")
                if "checked" in tags:
                    self.tree.item(item, tags=("unchecked",), values=("", *self.tree.item(item, "values")[1:]))
                else:
                    self.tree.item(item, tags=("checked",), values=("✓", *self.tree.item(item, "values")[1:]))

    def select_all(self, event=None):
        for item in self.tree.get_children():
            self.tree.item(item, tags=("checked",), values=("✓", *self.tree.item(item, "values")[1:]))

    def deselect_all(self):
        for item in self.tree.get_children():
            self.tree.item(item, tags=("unchecked",), values=("", *self.tree.item(item, "values")[1:]))

    def start_merge(self):
        selected_items = [item for item in self.tree.get_children() if "checked" in self.tree.item(item, "tags")]
        if not selected_items:
            messagebox.showwarning("경고", "선택된 파일이 없습니다.")
            return

        self.stop_thread.clear()
        self.progress_var.set(0)
        self.status_label.config(text="병합 중...")

        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"result_{current_time}.txt"
        result_folder = "result"
        if not os.path.exists(result_folder):
            os.makedirs(result_folder)
        file_path = os.path.join(result_folder, filename)

        # 작업 큐에 선택된 파일들 삽입
        for item in selected_items:
            self.file_queue.put(self.tree.item(item, 'text'))

        # 병합 작업을 별도 스레드에서 실행
        threading.Thread(target=self.merge_files, args=(file_path, len(selected_items)), daemon=True).start()

    def merge_files(self, file_path, total_files):
        with open(file_path, "wb") as result_file:
            processed_files = 0
            while not self.file_queue.empty() and not self.stop_thread.is_set():
                path = self.file_queue.get()
                # 각 파일 시작 표시
                result_file.write(f"\n--- File: {path} ---\n".encode('utf-8'))

                try:
                    with open(path, "rb") as file:
                        raw_content = file.read()
                        # 파일 인코딩을 모를 경우, 안전하게 utf-8로 디코딩(에러 무시)
                        content = raw_content.decode("utf-8", errors="ignore")
                        result_file.write(content.encode('utf-8'))
                except Exception as e:
                    error_message = f"Error reading file {path}: {str(e)}\n"
                    result_file.write(error_message.encode('utf-8'))

                processed_files += 1
                progress = (processed_files / total_files) * 100
                self.progress_var.set(progress)
                self.master.update_idletasks()

        self.master.after(0, self.finish_merge, file_path)

    def finish_merge(self, file_path):
        self.progress_var.set(100)
        self.status_label.config(text="병합 완료")
        messagebox.showinfo("성공", f"파일이 성공적으로 병합되었습니다.\n결과 파일: {file_path}")


if __name__ == "__main__":
    root = tk.Tk()
    app = FileMerger(root)
    root.mainloop()
