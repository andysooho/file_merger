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
        # ────────── 경로 입력 프레임 ──────────
        path_frame = ttk.Frame(self.master, padding="5")
        path_frame.pack(fill=tk.X)

        # 실제 탐색할 경로(entry)
        self.path_entry = ttk.Entry(path_frame, width=50)
        self.path_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

        browse_button = ttk.Button(path_frame, text="경로 선택", command=self.browse_path)
        browse_button.pack(side=tk.RIGHT, padx=5)

        # 베이스 경로 프레임: (병합 시 '--- File:' 표시할 때 제거할 접두어)
        base_path_frame = ttk.Frame(self.master, padding="5")
        base_path_frame.pack(fill=tk.X)

        ttk.Label(base_path_frame, text="베이스 경로(제거할 접두어):").pack(side=tk.LEFT)
        self.base_path_entry = ttk.Entry(base_path_frame, width=50)
        self.base_path_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # ────────── 파일 리스트 프레임 ──────────
        list_frame = ttk.Frame(self.master, padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview 생성
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

        # ────────── 필터 프레임 ──────────
        filter_frame = ttk.Frame(self.master, padding="5")
        filter_frame.pack(fill=tk.X)

        ttk.Label(filter_frame, text="확장자 필터:").pack(side=tk.LEFT)
        self.extension_entry = ttk.Entry(filter_frame, width=10)
        self.extension_entry.pack(side=tk.LEFT, padx=5)
        self.extension_entry.insert(0, "*")

        ttk.Label(filter_frame, text="제외 항목:").pack(side=tk.LEFT)
        self.exclude_entry = ttk.Entry(filter_frame, width=30)
        self.exclude_entry.pack(side=tk.LEFT, padx=5)
        self.exclude_entry.insert(0,
                                  ".cursor,.cursorrules*,.env*,logs,*.csv,*.xlsx,*.pyc,*.log,.idea,.github,.git,.DS_Store,*.json,*.lock,*.md,*.yml,*.yaml,"
                                  "*.erb,*.scss,*.css,*.svg,*.png,*.gif,*.jpg,*.ico,*.woff,*.woff2,*.mp3,*.xlsx,.venv,.gitignore,"
                                  ".env,*.db")

        refresh_button = ttk.Button(filter_frame, text="새로고침", command=self.refresh_tree)
        refresh_button.pack(side=tk.RIGHT, padx=5)

        # ────────── 선택 도구 프레임 ──────────
        select_frame = ttk.Frame(self.master, padding="5")
        select_frame.pack(fill=tk.X)

        select_all_button = ttk.Button(select_frame, text="모두 선택", command=self.select_all)
        select_all_button.pack(side=tk.LEFT, padx=5)

        deselect_all_button = ttk.Button(select_frame, text="모두 해제", command=self.deselect_all)
        deselect_all_button.pack(side=tk.LEFT, padx=5)

        # ────────── 진행 상황 표시 바 ──────────
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.master, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=10, pady=5)

        # 상태 레이블
        self.status_label = ttk.Label(self.master, text="준비")
        self.status_label.pack(pady=5)

        # 병합 버튼
        merge_button = ttk.Button(self.master, text="파일 병합", command=self.start_merge)
        merge_button.pack(pady=10)

        # 키보드 단축키 바인딩 (Ctrl + A)
        self.master.bind("<Control-a>", self.select_all)
        self.master.bind("<Control-A>", self.select_all)

    def browse_path(self):
        """폴더 경로 선택 후, path_entry 및 base_path_entry에 반영."""
        path = filedialog.askdirectory()
        if path:
            # path_entry에 선택된 경로 세팅
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)

            # base_path_entry에 기본적으로 동일 경로 입력(슬래시 붙이기)
            base_path = path
            # OS 별 경로 구분자를 추가
            if not base_path.endswith(os.sep):
                base_path += os.sep
            self.base_path_entry.delete(0, tk.END)
            self.base_path_entry.insert(0, base_path)

            self.refresh_tree()

    def should_exclude(self, path, exclude_patterns):
        name = os.path.basename(path)
        return any(fnmatch.fnmatch(name, pattern) for pattern in exclude_patterns)

    def refresh_tree(self):
        """Treeview의 내용을 현재 path_entry와 필터를 기준으로 갱신."""
        # 기존 리스트 초기화
        for i in self.tree.get_children():
            self.tree.delete(i)

        path = self.path_entry.get().strip()
        if not path or not os.path.exists(path):
            return

        include_pattern = self.extension_entry.get().strip()
        exclude_patterns = [item.strip() for item in self.exclude_entry.get().split(",")]

        for root, dirs, files in os.walk(path):
            # 제외 폴더 제거
            dirs[:] = [d for d in dirs if not self.should_exclude(d, exclude_patterns)]

            for file in files:
                full_path = os.path.join(root, file)
                # 포함 패턴 & 제외 패턴 검사
                if fnmatch.fnmatch(file, include_pattern) and not self.should_exclude(full_path, exclude_patterns):
                    size = os.path.getsize(full_path)
                    modified = os.path.getmtime(full_path)
                    mod_date_str = datetime.fromtimestamp(modified).strftime('%Y-%m-%d %H:%M:%S')
                    # 기본 선택 상태로 보여주기 위해 "checked" 태그 사용
                    self.tree.insert(
                        '',
                        'end',
                        text=full_path,  # 트리의 #0 컬럼(파일 경로)
                        values=("✓", f"{size / 1024:.2f} KB", mod_date_str),
                        tags=('checked',)
                    )

    def toggle_check(self, event):
        """체크박스 열을 클릭하면 토글."""
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            # "#1"은 columns=("Checked", "Size", "Date Modified") 중 첫 번째("Checked")의 인덱스
            if column == "#1":
                item = self.tree.identify_row(event.y)
                tags = self.tree.item(item, "tags")
                current_values = self.tree.item(item, "values")

                if "checked" in tags:
                    # 체크 해제
                    self.tree.item(item, tags=("unchecked",),
                                   values=("", *current_values[1:]))
                else:
                    # 체크
                    self.tree.item(item, tags=("checked",),
                                   values=("✓", *current_values[1:]))

    def select_all(self, event=None):
        """모든 항목 체크박스를 체크 상태로."""
        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            self.tree.item(item, tags=("checked",),
                           values=("✓", *values[1:]))

    def deselect_all(self):
        """모든 항목 체크박스를 해제 상태로."""
        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            self.tree.item(item, tags=("unchecked",),
                           values=("", *values[1:]))

    def start_merge(self):
        """병합 작업 시작 (스레드로 분리)."""
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

        # 작업 큐에 선택된 파일 경로들 삽입
        for item in selected_items:
            full_path = self.tree.item(item, 'text')
            self.file_queue.put(full_path)

        # 병합 작업을 별도 스레드에서 실행 (daemon=True로 백그라운드 스레드 설정)
        threading.Thread(target=self.merge_files, args=(file_path, len(selected_items)), daemon=True).start()

    def merge_files(self, file_path, total_files):
        """병합 로직: file_queue에 들어있는 파일들을 순서대로 병합."""
        prefix_path = self.base_path_entry.get().strip()

        with open(file_path, "wb") as result_file:
            processed_files = 0
            while not self.file_queue.empty() and not self.stop_thread.is_set():
                original_path = self.file_queue.get()

                # 베이스 경로가 있으면 상대 경로로 변환
                if prefix_path:
                    try:
                        short_path = os.path.relpath(original_path, prefix_path)
                    except ValueError:
                        short_path = original_path  # 혹은 경로가 맞지 않을 때는 그대로
                else:
                    short_path = original_path

                # 각 파일 시작 표시
                result_file.write(f"\n--- File: {short_path} ---\n".encode('utf-8'))

                try:
                    with open(original_path, "rb") as file:
                        raw_content = file.read()
                        # UTF-8로 디코딩(에러 무시)
                        content = raw_content.decode("utf-8", errors="ignore")
                        result_file.write(content.encode('utf-8'))

                except Exception as e:
                    error_message = f"Error reading file {original_path}: {str(e)}\n"
                    result_file.write(error_message.encode('utf-8'))

                processed_files += 1
                progress = (processed_files / total_files) * 100
                self.progress_var.set(progress)
                self.master.update_idletasks()

        self.master.after(0, self.finish_merge, file_path)

    def finish_merge(self, file_path):
        """병합 완료 후 UI 업데이트."""
        self.progress_var.set(100)
        self.status_label.config(text="병합 완료")
        messagebox.showinfo("성공", f"파일이 성공적으로 병합되었습니다.\n결과 파일: {file_path}")


if __name__ == "__main__":
    root = tk.Tk()
    app = FileMerger(root)
    root.mainloop()
