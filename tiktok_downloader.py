import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import requests
import subprocess
import threading
import os
import time
import re 

# --- CẤU HÌNH CỤ THỂ ---
# Đảm bảo lệnh 'yt-dlp' và 'ffmpeg' có trong biến môi trường PATH
YT_DLP_COMMAND = 'yt-dlp' 
FFMPEG_COMMAND = 'ffmpeg'

# Cải thiện tốc độ tải: Số lượng luồng tải đồng thời cho mỗi video (Mặc định: 1)
CONCURRENT_FRAGMENTS = 8 # Điều chỉnh số này để tối ưu tốc độ tải (4, 8, 16 là phổ biến)

class DownloaderApp:
    def __init__(self, master):
        self.master = master
        master.title("Video Downloader (TikTok, YouTube & Facebook)")
        
        # Thiết lập Style/Theme cho ttk
        s = ttk.Style()
        s.theme_use('clam') # Chủ đề hiện đại hơn
        
        # Định nghĩa Styles cho các nút màu sắc
        s.configure('Success.TButton', foreground='black', background='#28a745', font=('Arial', 10, 'bold')) # Xanh lá
        s.map('Success.TButton', background=[('active', '#218838')])
        
        s.configure('Danger.TButton', foreground='white', background='#dc3545', font=('Arial', 10, 'bold')) # Đỏ
        s.map('Danger.TButton', background=[('active', '#c82333')])
        
        s.configure('Info.TButton', foreground='white', background='#17a2b8', font=('Arial', 10, 'bold')) # Xanh dương nhạt (Quét/Chuyển đổi)
        s.map('Info.TButton', background=[('active', '#138496')])
        
        s.configure('Primary.TButton', foreground='white', background='#007bff', font=('Arial', 10, 'bold')) # Xanh dương (TikTok/Youtube)
        s.map('Primary.TButton', background=[('active', '#0056b3')])
        
        s.configure('Secondary.TButton', foreground='white', background='#6c757d', font=('Arial', 10)) # Xám (Kiểm tra FFmpeg)
        s.map('Secondary.TButton', background=[('active', '#5a6268')])
        
        # Biến trạng thái chung
        self.is_downloading = False
        self.download_session = None
        self.start_time = None 
        self.process = None 
        
        # Khởi tạo giao diện Notebook (Tabs)
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(pady=10, padx=10, expand=True, fill="both")

        # Khung cho chức năng Đơn lẻ
        self.tab_single = ttk.Frame(self.notebook, padding="10 10 10 10")
        self.notebook.add(self.tab_single, text="Tải Đơn lẻ (FLV/MP4)")
        self._create_single_download_widgets(self.tab_single)

        # Khung cho chức năng TikTok Hàng loạt
        self.tab_batch_tiktok = ttk.Frame(self.notebook, padding="10 10 10 10")
        self.notebook.add(self.tab_batch_tiktok, text="Tải Hàng loạt TikTok")
        self._create_batch_tiktok_widgets(self.tab_batch_tiktok)
        
        # Khung cho chức năng YouTube Shorts
        self.tab_batch_youtube = ttk.Frame(self.notebook, padding="10 10 10 10")
        self.notebook.add(self.tab_batch_youtube, text="Tải YouTube Shorts")
        self._create_batch_youtube_widgets(self.tab_batch_youtube)
        
        # Khung cho chức năng Facebook Reels (MỚI)
        self.tab_batch_facebook = ttk.Frame(self.notebook, padding="10 10 10 10")
        self.notebook.add(self.tab_batch_facebook, text="Tải Facebook Reels")
        self._create_batch_facebook_widgets(self.tab_batch_facebook)
        
        # Biến trạng thái Hàng loạt
        self.tiktok_total_videos = 0
        self.tiktok_downloaded_count = 0
        self.youtube_total_videos = 0
        self.youtube_downloaded_count = 0
        self.facebook_total_videos = 0 # MỚI
        self.facebook_downloaded_count = 0 # MỚI


    # =================================================================
    #                      CÁC HÀM CHUNG/TIỆN ÍCH (KHÔNG ĐỔI)
    # =================================================================
    def update_status(self, label, message, color="blue"):
        # Sử dụng widget tk.Label để dễ dàng đổi màu foreground (fg)
        self.master.after(0, label.config, {"text": message, "fg": color})
        
    def update_progress_label(self, label, downloaded, total):
        self.master.after(0, label.config, {"text": f"{downloaded} / {total}"})
    
    def find_ffmpeg(self):
        """Tìm FFmpeg trong nhiều vị trí khác nhau"""
        possible_paths = [
            'ffmpeg',  # Trong PATH
            'ffmpeg.exe',  # Windows với .exe
            r'C:\ffmpeg\bin\ffmpeg.exe',  # Vị trí phổ biến 1
            r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',  # Vị trí phổ biến 2
            r'C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe',  # 32-bit version
            os.path.join(os.path.expanduser('~'), 'ffmpeg', 'bin', 'ffmpeg.exe'),  # User home
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg.exe'),  # Cùng thư mục
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bin', 'ffmpeg.exe'),  # Subfolder bin
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run([path, '-version'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return path
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError, subprocess.CalledProcessError):
                continue
        
        return None
    
    def download_ffmpeg_suggestion(self):
        """Hướng dẫn tải FFmpeg cho Windows"""
        suggestion = """💡 HƯỚNG DẪN CÀI ĐẶT FFMPEG:

📥 CÁCH 1 - Tải về thủ công (KHUYÊN DÙNG):
1. Vào: https://www.gyan.dev/ffmpeg/builds/
2. Tải "release builds" → ffmpeg-release-essentials.zip
3. Giải nén vào thư mục: C:\\ffmpeg\\
4. Đảm bảo có file: C:\\ffmpeg\\bin\\ffmpeg.exe

🔧 CÁCH 2 - Thêm vào PATH:
1. Sau khi giải nén FFmpeg
2. Thêm "C:\\ffmpeg\\bin" vào PATH hệ thống
3. Khởi động lại ứng dụng

⚡ CÁCH 3 - Copy trực tiếp:
1. Tải ffmpeg.exe về
2. Copy vào cùng thư mục với ứng dụng này
3. Chạy lại ứng dụng

🔍 Kiểm tra: Nhấn nút "Kiểm tra FFmpeg" để test"""
        
        return suggestion


    # =================================================================
    #                      CHỨC NĂNG TẢI ĐƠN LẺ (TAB 1) - GIAO DIỆN MỚI
    # =================================================================
    
    def _create_single_download_widgets(self, master):
        # Khung Input (Link và Đường dẫn)
        input_frame = ttk.LabelFrame(master, text="Thông tin Tải xuống", padding="10 10 10 10")
        input_frame.pack(padx=5, pady=5, fill="x")
        
        # Cấu hình grid cho input_frame (cột giữa mở rộng)
        input_frame.columnconfigure(1, weight=1)

        # 1. Link Live Stream
        ttk.Label(input_frame, text="Link Livestream (.flv):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.url_entry = ttk.Entry(input_frame)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew", columnspan=2)
        self.url_entry.insert(0, "https://pull-flv-l11-va01.tiktokcdn.com/...")

        # 2. Đường dẫn lưu file
        ttk.Label(input_frame, text="Đường dẫn lưu File FLV:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.path_entry = ttk.Entry(input_frame)
        self.path_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(input_frame, text="Duyệt...", command=self.browse_save_path).grid(row=1, column=2, sticky="e", padx=5, pady=5)
        
        # Khung Điều khiển (Nút chức năng)
        control_frame = ttk.Frame(master, padding="10 10 10 10")
        control_frame.pack(padx=5, pady=5, fill="x")

        # 3. Nút chức năng
        self.single_download_button = ttk.Button(control_frame, text="Bắt đầu Tải về", command=self.start_download, style='Success.TButton')
        self.single_download_button.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.single_stop_button = ttk.Button(control_frame, text="Dừng Tải về", command=self.stop_download, state=tk.DISABLED, style='Danger.TButton')
        self.single_stop_button.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.convert_button = ttk.Button(control_frame, text="Chuyển đổi sang MP4 (FFmpeg)", command=self.start_convert, state=tk.DISABLED, style='Info.TButton')
        self.convert_button.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        
        # Nút kiểm tra FFmpeg
        self.check_ffmpeg_button = ttk.Button(control_frame, text="🔍 Kiểm tra FFmpeg", command=self.check_ffmpeg, style='Secondary.TButton')
        self.check_ffmpeg_button.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        # Khung Trạng thái
        status_frame = ttk.LabelFrame(master, text="Trạng thái Tải xuống", padding="10 10 10 10")
        status_frame.pack(padx=5, pady=5, fill="x")
        status_frame.columnconfigure(1, weight=1)

        # 4. Khu vực Trạng thái
        ttk.Label(status_frame, text="Trạng thái:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        # Giữ lại tk.Label để dễ dàng đổi màu trạng thái (fg)
        self.single_status_label = tk.Label(status_frame, text="Sẵn sàng", fg="blue", wraplength=450, justify=tk.LEFT)
        self.single_status_label.grid(row=0, column=1, sticky="w", padx=5, pady=5)

    # (Các hàm logic tải đơn lẻ không đổi)
    def browse_save_path(self):
        default_filename = "tiktok_live_video.flv"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".flv",
            filetypes=[("FLV Video", "*.flv")],
            initialfile=default_filename
        )
        if save_path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, save_path)

    def start_download(self):
        url = self.url_entry.get().strip()
        save_path = self.path_entry.get().strip()
        if not url or not save_path:
            messagebox.showerror("Lỗi", "Vui lòng điền đầy đủ Link Livestream và Đường dẫn lưu File.")
            return
        self.update_status(self.single_status_label, "Đang chuẩn bị tải về...", "orange")
        self.single_download_button.config(state=tk.DISABLED)
        self.single_stop_button.config(state=tk.NORMAL)
        self.convert_button.config(state=tk.DISABLED)
        self.is_downloading = True
        self.download_thread = threading.Thread(target=self._download_flv, args=(url, save_path))
        self.download_thread.start()

    def stop_download(self):
        self.is_downloading = False
        if self.download_session: self.download_session.close() 
        elapsed_time_formatted = time.strftime("%H:%M:%S", time.gmtime(time.time() - self.start_time)) if self.start_time else "00:00:00"
        self.update_status(self.single_status_label, f"Đã dừng tải về (File có thể bị thiếu). Thời gian: {elapsed_time_formatted}", "red")
        self.single_download_button.config(state=tk.NORMAL)
        self.single_stop_button.config(state=tk.DISABLED)
        if os.path.exists(self.path_entry.get()): self.convert_button.config(state=tk.NORMAL)

    def _download_flv(self, url, save_path):
        self.start_time = time.time()
        try:
            self.download_session = requests.Session()
            with self.download_session.get(url, stream=True) as r:
                r.raise_for_status() 
                total_size = int(r.headers.get('content-length', 0))
                downloaded_size = 0
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192): 
                        if not self.is_downloading: break
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        elapsed_seconds = time.time() - self.start_time
                        elapsed_time_formatted = time.strftime("%H:%M:%S", time.gmtime(elapsed_seconds))
                        progress = downloaded_size / total_size * 100 if total_size else 0
                        status_message = (f"Đang tải: {downloaded_size} bytes ({progress:.2f}%) | Đã trôi qua: {elapsed_time_formatted}")
                        self.master.after(0, self.update_status, self.single_status_label, status_message, "orange")
                
                final_time_message = time.strftime("%H:%M:%S", time.gmtime(time.time() - self.start_time))
                if self.is_downloading:
                    self.master.after(0, self.update_status, self.single_status_label, f"Tải về HOÀN TẤT. Kích thước: {downloaded_size} bytes. Thời gian: {final_time_message}", "green")
                else:
                    self.master.after(0, self.update_status, self.single_status_label, f"Tải về ĐÃ DỪNG. Kích thước: {downloaded_size} bytes. Thời gian: {final_time_message}", "red")

        except requests.exceptions.RequestException as e:
            self.master.after(0, messagebox.showerror, "Lỗi Tải xuống", f"Lỗi kết nối hoặc URL không hợp lệ: {e}")
            self.master.after(0, self.update_status, self.single_status_label, "Lỗi khi tải về.", "red")
        finally:
            self.is_downloading = False
            self.download_session = None
            self.start_time = None
            self.master.after(0, self.single_download_button.config, {"state": tk.NORMAL})
            self.master.after(0, self.single_stop_button.config, {"state": tk.DISABLED})
            if os.path.exists(save_path): self.master.after(0, self.convert_button.config, {"state": tk.NORMAL})

    def check_ffmpeg(self):
        """Kiểm tra và hiển thị trạng thái FFmpeg"""
        ffmpeg_path = self.find_ffmpeg()
        
        if ffmpeg_path:
            try:
                result = subprocess.run([ffmpeg_path, '-version'], 
                                      capture_output=True, text=True, timeout=10)
                version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown version"
                
                success_msg = f"✅ FFMPEG SẴN SÀNG!\n\n"
                success_msg += f"📍 Vị trí: {ffmpeg_path}\n"
                success_msg += f"📄 Phiên bản: {version_line}\n\n"
                success_msg += "🎉 Bạn có thể sử dụng chức năng chuyển đổi video!"
                
                messagebox.showinfo("FFmpeg OK", success_msg)
                self.update_status(self.single_status_label, "✅ FFmpeg sẵn sàng", "green")
                
            except Exception as e:
                messagebox.showerror("Lỗi FFmpeg", f"Tìm thấy FFmpeg nhưng không thể chạy:\n{e}")
                self.update_status(self.single_status_label, "❌ FFmpeg lỗi", "red")
        else:
            # Hiển thị hướng dẫn chi tiết
            error_msg = "❌ KHÔNG TÌM THẤY FFMPEG!\n\n"
            error_msg += self.download_ffmpeg_suggestion()
            
            messagebox.showerror("Cần cài FFmpeg", error_msg)
            self.update_status(self.single_status_label, "❌ Cần cài FFmpeg", "red")

    def start_convert(self):
        input_path = self.path_entry.get().strip()
        if not input_path or not os.path.exists(input_path): 
            messagebox.showerror("Lỗi", "Vui lòng chọn file FLV để chuyển đổi!")
            return
            
        # Kiểm tra FFmpeg trước khi chuyển đổi
        ffmpeg_path = self.find_ffmpeg()
        if not ffmpeg_path:
            error_msg = "❌ KHÔNG TÌM THẤY FFMPEG!\n\n"
            error_msg += self.download_ffmpeg_suggestion()
            messagebox.showerror("Cần cài FFmpeg", error_msg)
            return
            
        base, ext = os.path.splitext(input_path)
        output_path = base + ".mp4"
        
        # Kiểm tra file output đã tồn tại
        if os.path.exists(output_path):
            response = messagebox.askyesno("File tồn tại", 
                                         f"File {os.path.basename(output_path)} đã tồn tại.\n\nGhi đè?")
            if not response:
                return
        
        self.update_status(self.single_status_label, "🔄 Đang chuyển đổi FLV sang MP4...", "orange")
        self.convert_button.config(state=tk.DISABLED)
        convert_thread = threading.Thread(target=self._convert_flv_to_mp4, args=(input_path, output_path, ffmpeg_path))
        convert_thread.start()

    def _convert_flv_to_mp4(self, input_path, output_path, ffmpeg_path):
        ffmpeg_command = [ffmpeg_path, '-i', input_path, '-c', 'copy', '-y', output_path]  # -y để overwrite
        
        try:
            self.master.after(0, self.update_status, self.single_status_label, 
                            f"⚙️ Đang xử lý với FFmpeg: {os.path.basename(ffmpeg_path)}", "blue")
            
            result = subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)
            
            # Kiểm tra file output
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                file_size = os.path.getsize(output_path) / (1024*1024)  # MB
                success_msg = f"✅ CHUYỂN ĐỔI THÀNH CÔNG!\n"
                success_msg += f"📁 File: {os.path.basename(output_path)}\n"
                success_msg += f"📊 Kích thước: {file_size:.1f} MB"
                
                self.master.after(0, self.update_status, self.single_status_label, success_msg, "green")
                
                # Hỏi có muốn mở thư mục không
                self.master.after(0, self._ask_open_folder, os.path.dirname(output_path))
            else:
                self.master.after(0, self.update_status, self.single_status_label, 
                                "❌ Chuyển đổi thất bại - File output không hợp lệ", "red")
                
        except subprocess.CalledProcessError as e:
            error_detail = e.stderr if e.stderr else "Lỗi không xác định"
            self.master.after(0, messagebox.showerror, "Lỗi Chuyển đổi", 
                            f"FFmpeg thất bại:\n{error_detail[:300]}")
            self.master.after(0, self.update_status, self.single_status_label, "❌ Lỗi khi chuyển đổi", "red")
        except Exception as e:
            self.master.after(0, messagebox.showerror, "Lỗi", f"Lỗi không xác định: {str(e)}")
            self.master.after(0, self.update_status, self.single_status_label, "❌ Lỗi không xác định", "red")
        finally:
            self.master.after(0, self.convert_button.config, {"state": tk.NORMAL})
    
    def _ask_open_folder(self, folder_path):
        """Hỏi có muốn mở thư mục chứa file đã chuyển đổi"""
        response = messagebox.askyesno("Mở thư mục", "Chuyển đổi thành công!\n\nMở thư mục chứa file MP4?")
        if response:
            try:
                if os.name == 'nt':  # Windows
                    subprocess.run(['explorer', folder_path])
                elif os.name == 'posix':  # macOS/Linux
                    subprocess.run(['open' if 'darwin' in os.uname().sysname.lower() else 'xdg-open', folder_path])
            except Exception as e:
                messagebox.showinfo("Thông báo", f"Không thể mở thư mục tự động.\nVị trí file: {folder_path}")


    # =================================================================
    #                      CHỨC NĂNG TẢI HÀNG LOẠT TIKTOK (TAB 2) - GIAO DIỆN MỚI
    # =================================================================
    def _create_batch_tiktok_widgets(self, master):
        # Khung Cấu hình
        config_frame = ttk.LabelFrame(master, text="Cấu hình Tải hàng loạt TikTok", padding="10 10 10 10")
        config_frame.pack(padx=5, pady=5, fill="x")
        config_frame.columnconfigure(1, weight=1) # Cột giữa mở rộng

        # 1. Input Cookie
        ttk.Label(config_frame, text="Đường dẫn file Cookies (.txt):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.tiktok_cookie_path_entry = ttk.Entry(config_frame)
        self.tiktok_cookie_path_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(config_frame, text="Duyệt...", command=self.browse_tiktok_cookies).grid(row=0, column=2, sticky="e", padx=5, pady=5)

        # 2. Input Link TikTok
        ttk.Label(config_frame, text="Link Trang TikTok (@username):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.tiktok_url_entry = ttk.Entry(config_frame)
        self.tiktok_url_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5, columnspan=2)

        # 3. Nút Quét và Số lượng Video
        self.tiktok_scan_button = ttk.Button(config_frame, text="Quét Tổng Video", command=self.start_tiktok_scan, style='Info.TButton')
        self.tiktok_scan_button.grid(row=2, column=0, padx=5, pady=10, sticky="w")
        
        ttk.Label(config_frame, text="Số lượng Video muốn tải:").grid(row=2, column=1, sticky="e", padx=5, pady=10)
        self.tiktok_max_videos_entry = ttk.Entry(config_frame, width=10)
        self.tiktok_max_videos_entry.insert(0, "Tất cả")
        self.tiktok_max_videos_entry.grid(row=2, column=2, sticky="e", padx=5, pady=10)

        # 4. Đường dẫn lưu
        ttk.Label(config_frame, text="Thư mục Lưu File:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.tiktok_batch_dir_entry = ttk.Entry(config_frame)
        self.tiktok_batch_dir_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(config_frame, text="Duyệt...", command=self.browse_tiktok_download_dir).grid(row=3, column=2, sticky="e", padx=5, pady=5)

        # Khung Điều khiển & Trạng thái
        status_control_frame = ttk.LabelFrame(master, text="Tiến trình Tải xuống", padding="10 10 10 10")
        status_control_frame.pack(padx=5, pady=5, fill="x")
        status_control_frame.columnconfigure(1, weight=1) 

        # 5. Nút Bắt đầu Tải
        self.tiktok_batch_download_button = ttk.Button(status_control_frame, text="BẮT ĐẦU TẢI HÀNG LOẠT", command=self.start_tiktok_batch_download, style='Primary.TButton', state=tk.DISABLED)
        self.tiktok_batch_download_button.grid(row=0, column=0, padx=5, pady=10, sticky="w")
        
        self.tiktok_batch_stop_button = ttk.Button(status_control_frame, text="Dừng Tải Hàng loạt", command=self.stop_tiktok_batch_download, style='Danger.TButton', state=tk.DISABLED)
        self.tiktok_batch_stop_button.grid(row=0, column=2, padx=5, pady=10, sticky="e")

        # 6. Khu vực Trạng thái
        ttk.Label(status_control_frame, text="Trạng thái:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.tiktok_batch_status_label = tk.Label(status_control_frame, text="Chờ quét...", fg="blue", wraplength=400, justify=tk.LEFT)
        self.tiktok_batch_status_label.grid(row=1, column=1, columnspan=2, sticky="w", padx=5, pady=5)
        
        ttk.Label(status_control_frame, text="Tiến trình:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.tiktok_progress_label = tk.Label(status_control_frame, text="0/0", fg="purple")
        self.tiktok_progress_label.grid(row=2, column=1, columnspan=2, sticky="w", padx=5, pady=5)

    # (Các hàm logic tải TikTok không đổi)
    def browse_tiktok_cookies(self):
        cookie_path = filedialog.askopenfilename(defaultextension=".txt", filetypes=[("Cookies File", "*.txt")])
        if cookie_path: self.tiktok_cookie_path_entry.delete(0, tk.END); self.tiktok_cookie_path_entry.insert(0, cookie_path)

    def browse_tiktok_download_dir(self):
        download_dir = filedialog.askdirectory()
        if download_dir: self.tiktok_batch_dir_entry.delete(0, tk.END); self.tiktok_batch_dir_entry.insert(0, download_dir)

    def start_tiktok_scan(self):
        url = self.tiktok_url_entry.get().strip()
        cookie_path = self.tiktok_cookie_path_entry.get().strip()
        if not url: messagebox.showerror("Lỗi", "Vui lòng nhập Link Trang TikTok."); return
        if not os.path.exists(cookie_path) and cookie_path: messagebox.showwarning("Cảnh báo", "File cookies không tồn tại. Tiếp tục quét mà không có cookies.");
        
        self.update_status(self.tiktok_batch_status_label, "Đang quét trang TikTok để đếm video...", "orange")
        self.tiktok_scan_button.config(state=tk.DISABLED)
        self.tiktok_batch_download_button.config(state=tk.DISABLED)
        
        threading.Thread(target=self._scan_tiktok_videos, args=(url, cookie_path)).start()

    def _scan_tiktok_videos(self, url, cookie_path):
        scan_command = [YT_DLP_COMMAND, "--flat-playlist", "--skip-download", "--print-json", url]
        if os.path.exists(cookie_path): scan_command.extend(["--cookies", cookie_path])
        
        try:
            result = subprocess.run(scan_command, capture_output=True, text=True, check=False)
            video_lines = [line for line in result.stdout.splitlines() if line.strip().startswith('{')]
            self.tiktok_total_videos = len(video_lines)
            self.tiktok_downloaded_count = 0
            
            if self.tiktok_total_videos > 0:
                self.master.after(0, self.update_status, self.tiktok_batch_status_label, f"QUÉT HOÀN TẤT. Tìm thấy {self.tiktok_total_videos} video.", "green")
                self.master.after(0, self.tiktok_batch_download_button.config, {"state": tk.NORMAL})
            else:
                self.master.after(0, self.update_status, self.tiktok_batch_status_label, f"Quét thất bại/Không có video. Kiểm tra URL/Cookies.", "red")
                self.master.after(0, self.tiktok_batch_download_button.config, {"state": tk.DISABLED})
        except FileNotFoundError:
            self.master.after(0, self.update_status, self.tiktok_batch_status_label, "Lỗi Quét: Không tìm thấy yt-dlp.", "red")

        self.master.after(0, self.update_progress_label, self.tiktok_progress_label, self.tiktok_downloaded_count, self.tiktok_total_videos)
        self.master.after(0, self.tiktok_scan_button.config, {"state": tk.NORMAL})
    
    def start_tiktok_batch_download(self):
        url = self.tiktok_url_entry.get().strip()
        cookie_path = self.tiktok_cookie_path_entry.get().strip()
        download_dir = self.tiktok_batch_dir_entry.get().strip()
        max_videos_str = self.tiktok_max_videos_entry.get().strip()
        if not download_dir or not os.path.isdir(download_dir): messagebox.showerror("Lỗi", "Vui lòng chọn thư mục lưu trữ hợp lệ."); return
        try: max_videos = int(max_videos_str) if max_videos_str.lower() != "tất cả" else None
        except ValueError: messagebox.showerror("Lỗi", "Số lượng video không hợp lệ."); return

        self.update_status(self.tiktok_batch_status_label, "Đang bắt đầu tải hàng loạt...", "purple")
        self.tiktok_scan_button.config(state=tk.DISABLED)
        self.tiktok_batch_download_button.config(state=tk.DISABLED)
        self.tiktok_batch_stop_button.config(state=tk.NORMAL)
        self.is_downloading = True
        self.tiktok_downloaded_count = 0
        self.update_progress_label(self.tiktok_progress_label, self.tiktok_downloaded_count, self.tiktok_total_videos)
        
        self.download_thread = threading.Thread(target=self._batch_download_logic, args=(url, cookie_path, download_dir, max_videos, self.tiktok_batch_status_label, self.tiktok_progress_label, "tiktok"))
        self.download_thread.start()

    def stop_tiktok_batch_download(self):
        self._stop_batch_download_logic(self.tiktok_batch_status_label, self.tiktok_scan_button, self.tiktok_batch_download_button, self.tiktok_batch_stop_button, self.tiktok_downloaded_count, self.tiktok_total_videos)
        
    
    # =================================================================
    #                      CHỨC NĂNG TẢI YOUTUBE SHORTS (TAB 3) - GIAO DIỆN MỚI
    # =================================================================

    def _create_batch_youtube_widgets(self, master):
        # Khung Cấu hình
        config_frame = ttk.LabelFrame(master, text="Cấu hình Tải hàng loạt YouTube Shorts", padding="10 10 10 10")
        config_frame.pack(padx=5, pady=5, fill="x")
        config_frame.columnconfigure(1, weight=1) # Cột giữa mở rộng

        # 1. Input Link YouTube Kênh
        ttk.Label(config_frame, text="Link Kênh YouTube (@username):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.youtube_url_entry = ttk.Entry(config_frame)
        self.youtube_url_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5, columnspan=2)

        # 2. Nút Quét và Số lượng Video
        self.youtube_scan_button = ttk.Button(config_frame, text="Quét Tổng Shorts (<60s)", command=self.start_youtube_scan, style='Info.TButton')
        self.youtube_scan_button.grid(row=1, column=0, padx=5, pady=10, sticky="w")
        
        ttk.Label(config_frame, text="Số lượng Shorts muốn tải:").grid(row=1, column=1, sticky="e", padx=5, pady=10)
        self.youtube_max_videos_entry = ttk.Entry(config_frame, width=10)
        self.youtube_max_videos_entry.insert(0, "Tất cả")
        self.youtube_max_videos_entry.grid(row=1, column=2, sticky="e", padx=5, pady=10)

        # 3. Đường dẫn lưu
        ttk.Label(config_frame, text="Thư mục Lưu File:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.youtube_batch_dir_entry = ttk.Entry(config_frame)
        self.youtube_batch_dir_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(config_frame, text="Duyệt...", command=self.browse_youtube_download_dir).grid(row=2, column=2, sticky="e", padx=5, pady=5)

        # Khung Điều khiển & Trạng thái
        status_control_frame = ttk.LabelFrame(master, text="Tiến trình Tải xuống", padding="10 10 10 10")
        status_control_frame.pack(padx=5, pady=5, fill="x")
        status_control_frame.columnconfigure(1, weight=1) 

        # 4. Nút Bắt đầu Tải
        self.youtube_batch_download_button = ttk.Button(status_control_frame, text="BẮT ĐẦU TẢI SHORTS", command=self.start_youtube_batch_download, style='Primary.TButton', state=tk.DISABLED)
        self.youtube_batch_download_button.grid(row=0, column=0, padx=5, pady=10, sticky="w")
        
        self.youtube_batch_stop_button = ttk.Button(status_control_frame, text="Dừng Tải Shorts", command=self.stop_youtube_batch_download, style='Danger.TButton', state=tk.DISABLED)
        self.youtube_batch_stop_button.grid(row=0, column=2, padx=5, pady=10, sticky="e")

        # 5. Khu vực Trạng thái
        ttk.Label(status_control_frame, text="Trạng thái:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.youtube_batch_status_label = tk.Label(status_control_frame, text="Chờ quét...", fg="blue", wraplength=400, justify=tk.LEFT)
        self.youtube_batch_status_label.grid(row=1, column=1, columnspan=2, sticky="w", padx=5, pady=5)
        
        ttk.Label(status_control_frame, text="Tiến trình:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.youtube_progress_label = tk.Label(status_control_frame, text="0/0", fg="purple")
        self.youtube_progress_label.grid(row=2, column=1, columnspan=2, sticky="w", padx=5, pady=5)

    # (Các hàm logic tải Youtube không đổi)
    def browse_youtube_download_dir(self):
        download_dir = filedialog.askdirectory()
        if download_dir: self.youtube_batch_dir_entry.delete(0, tk.END); self.youtube_batch_dir_entry.insert(0, download_dir)

    def start_youtube_scan(self):
        url = self.youtube_url_entry.get().strip()
        if not url: messagebox.showerror("Lỗi", "Vui lòng nhập Link Kênh YouTube."); return
        
        self.update_status(self.youtube_batch_status_label, "Đang quét kênh YouTube để đếm Shorts...", "orange")
        self.youtube_scan_button.config(state=tk.DISABLED)
        self.youtube_batch_download_button.config(state=tk.DISABLED)
        
        threading.Thread(target=self._scan_youtube_videos, args=(url,)).start()

    def _scan_youtube_videos(self, url):
        scan_command = [
            YT_DLP_COMMAND, 
            "--flat-playlist", 
            "--skip-download", 
            "--print-json", 
            "--match-filter", "duration <= 60", 
            "--ignore-errors", 
            url
        ]
        
        try:
            result = subprocess.run(scan_command, capture_output=True, text=True, check=False)
            video_lines = [line for line in result.stdout.splitlines() if line.strip().startswith('{')]
            self.youtube_total_videos = len(video_lines)
            self.youtube_downloaded_count = 0
            
            if self.youtube_total_videos > 0:
                self.master.after(0, self.update_status, self.youtube_batch_status_label, f"QUÉT HOÀN TẤT. Tìm thấy {self.youtube_total_videos} Shorts.", "green")
                self.master.after(0, self.youtube_batch_download_button.config, {"state": tk.NORMAL})
            else:
                self.master.after(0, self.update_status, self.youtube_batch_status_label, f"Quét thất bại/Không có Shorts. Kiểm tra URL.", "red")
                self.master.after(0, self.youtube_batch_download_button.config, {"state": tk.DISABLED})
        except FileNotFoundError:
            self.master.after(0, self.update_status, self.youtube_batch_status_label, "Lỗi Quét: Không tìm thấy yt-dlp.", "red")

        self.master.after(0, self.update_progress_label, self.youtube_progress_label, self.youtube_downloaded_count, self.youtube_total_videos)
        self.master.after(0, self.youtube_scan_button.config, {"state": tk.NORMAL})

    def start_youtube_batch_download(self):
        url = self.youtube_url_entry.get().strip()
        download_dir = self.youtube_batch_dir_entry.get().strip()
        max_videos_str = self.youtube_max_videos_entry.get().strip()
        
        if not download_dir or not os.path.isdir(download_dir): messagebox.showerror("Lỗi", "Vui lòng chọn thư mục lưu trữ hợp lệ."); return
        try: max_videos = int(max_videos_str) if max_videos_str.lower() != "tất cả" else None
        except ValueError: messagebox.showerror("Lỗi", "Số lượng video không hợp lệ."); return

        self.update_status(self.youtube_batch_status_label, "Đang bắt đầu tải Shorts...", "purple")
        self.youtube_scan_button.config(state=tk.DISABLED)
        self.youtube_batch_download_button.config(state=tk.DISABLED)
        self.youtube_batch_stop_button.config(state=tk.NORMAL)
        self.is_downloading = True
        self.youtube_downloaded_count = 0
        self.update_progress_label(self.youtube_progress_label, self.youtube_downloaded_count, self.youtube_total_videos)
        
        self.download_thread = threading.Thread(target=self._batch_download_logic, args=(url, None, download_dir, max_videos, self.youtube_batch_status_label, self.youtube_progress_label, "youtube"))
        self.download_thread.start()

    def stop_youtube_batch_download(self):
        self._stop_batch_download_logic(self.youtube_batch_status_label, self.youtube_scan_button, self.youtube_batch_download_button, self.youtube_batch_stop_button, self.youtube_downloaded_count, self.youtube_total_videos)

    # =================================================================
    #                      CHỨC NĂNG TẢI FACEBOOK REELS (TAB 4 - MỚI) - GIAO DIỆN MỚI
    # =================================================================
    
    def _create_batch_facebook_widgets(self, master):
        # Khung Cấu hình
        config_frame = ttk.LabelFrame(master, text="Cấu hình Tải hàng loạt Facebook Reels", padding="10 10 10 10")
        config_frame.pack(padx=5, pady=5, fill="x")
        config_frame.columnconfigure(1, weight=1) # Cột giữa mở rộng

        # 1. Input Cookie (Rất quan trọng cho Facebook)
        ttk.Label(config_frame, text="Đường dẫn file Cookies (.txt):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.facebook_cookie_path_entry = ttk.Entry(config_frame)
        self.facebook_cookie_path_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(config_frame, text="Duyệt...", command=self.browse_facebook_cookies).grid(row=0, column=2, sticky="e", padx=5, pady=5)

        # 2. Input Link Trang Facebook
        ttk.Label(config_frame, text="Link Trang/Hồ sơ Facebook:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.facebook_url_entry = ttk.Entry(config_frame)
        self.facebook_url_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5, columnspan=2)

        # 3. Nút Quét và Số lượng Video
        self.facebook_scan_button = ttk.Button(config_frame, text="Quét Tổng Reels", command=self.start_facebook_scan, style='Info.TButton')
        self.facebook_scan_button.grid(row=2, column=0, padx=5, pady=10, sticky="w")
        
        ttk.Label(config_frame, text="Số lượng Reels muốn tải:").grid(row=2, column=1, sticky="e", padx=5, pady=10)
        self.facebook_max_videos_entry = ttk.Entry(config_frame, width=10)
        self.facebook_max_videos_entry.insert(0, "Tất cả")
        self.facebook_max_videos_entry.grid(row=2, column=2, sticky="e", padx=5, pady=10)

        # 4. Đường dẫn lưu
        ttk.Label(config_frame, text="Thư mục Lưu File:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.facebook_batch_dir_entry = ttk.Entry(config_frame)
        self.facebook_batch_dir_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(config_frame, text="Duyệt...", command=self.browse_facebook_download_dir).grid(row=3, column=2, sticky="e", padx=5, pady=5)

        # Khung Điều khiển & Trạng thái
        status_control_frame = ttk.LabelFrame(master, text="Tiến trình Tải xuống", padding="10 10 10 10")
        status_control_frame.pack(padx=5, pady=5, fill="x")
        status_control_frame.columnconfigure(1, weight=1) 

        # 5. Nút Bắt đầu Tải
        self.facebook_batch_download_button = ttk.Button(status_control_frame, text="BẮT ĐẦU TẢI REELS", command=self.start_facebook_batch_download, style='Primary.TButton', state=tk.DISABLED)
        self.facebook_batch_download_button.grid(row=0, column=0, padx=5, pady=10, sticky="w")
        
        self.facebook_batch_stop_button = ttk.Button(status_control_frame, text="Dừng Tải Reels", command=self.stop_facebook_batch_download, style='Danger.TButton', state=tk.DISABLED)
        self.facebook_batch_stop_button.grid(row=0, column=2, padx=5, pady=10, sticky="e")

        # 6. Khu vực Trạng thái
        ttk.Label(status_control_frame, text="Trạng thái:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.facebook_batch_status_label = tk.Label(status_control_frame, text="Chờ quét...", fg="blue", wraplength=400, justify=tk.LEFT)
        self.facebook_batch_status_label.grid(row=1, column=1, columnspan=2, sticky="w", padx=5, pady=5)
        
        ttk.Label(status_control_frame, text="Tiến trình:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.facebook_progress_label = tk.Label(status_control_frame, text="0/0", fg="purple")
        self.facebook_progress_label.grid(row=2, column=1, columnspan=2, sticky="w", padx=5, pady=5)

    # (Các hàm logic tải Facebook không đổi)
    def browse_facebook_cookies(self):
        cookie_path = filedialog.askopenfilename(defaultextension=".txt", filetypes=[("Cookies File", "*.txt")])
        if cookie_path: self.facebook_cookie_path_entry.delete(0, tk.END); self.facebook_cookie_path_entry.insert(0, cookie_path)

    def browse_facebook_download_dir(self):
        download_dir = filedialog.askdirectory()
        if download_dir: self.facebook_batch_dir_entry.delete(0, tk.END); self.facebook_batch_dir_entry.insert(0, download_dir)
    
    def start_facebook_scan(self):
        url = self.facebook_url_entry.get().strip()
        cookie_path = self.facebook_cookie_path_entry.get().strip()
        if not url: messagebox.showerror("Lỗi", "Vui lòng nhập Link Trang Facebook."); return
        if not os.path.exists(cookie_path): messagebox.showwarning("Cảnh báo", "File cookies không tồn tại. Rất có thể việc quét sẽ thất bại.");
        
        self.update_status(self.facebook_batch_status_label, "Đang quét Trang Facebook để đếm Reels...", "orange")
        self.facebook_scan_button.config(state=tk.DISABLED)
        self.facebook_batch_download_button.config(state=tk.DISABLED)
        
        threading.Thread(target=self._scan_facebook_videos, args=(url, cookie_path)).start()

    def _scan_facebook_videos(self, url, cookie_path):
        # KHUYÊN DÙNG: Yêu cầu URL Trang chính (ví dụ: https://www.facebook.com/caulong.official)
        
        scan_command = [
            YT_DLP_COMMAND, 
            "--flat-playlist",            # Chỉ lấy thông tin mà không tải
            "--dump-json",                # In ra cấu trúc JSON của playlist
            "--ignore-errors",            # Bỏ qua các lỗi video đơn lẻ
            "--sleep-requests", "1",      # Giảm tốc độ yêu cầu (khuyên dùng cho FB)
            url
        ]
        
        # Thêm cookie nếu có
        if os.path.exists(cookie_path): 
            scan_command.extend(["--cookies", cookie_path])
        
        try:
            self.update_status(self.facebook_batch_status_label, "Đang quét Trang Facebook để đếm Reels...", "orange")
            result = subprocess.run(scan_command, capture_output=True, text=True, check=False, timeout=60) # Thêm timeout
            
            # Phân tích đầu ra: Chỉ cần đếm số lượng các mục JSON hợp lệ
            video_lines = [line for line in result.stdout.splitlines() if line.strip().startswith('{')]
            
            if not video_lines and result.stderr:
                 self.master.after(0, self.update_status, self.facebook_batch_status_label, f"Quét thất bại. Lỗi: {result.stderr.strip()[:150]}", "red")
                 self.master.after(0, self.facebook_batch_download_button.config, {"state": tk.DISABLED})
                 self.master.after(0, self.facebook_scan_button.config, {"state": tk.NORMAL})
                 return

            self.facebook_total_videos = len(video_lines)
            self.facebook_downloaded_count = 0
            
            if self.facebook_total_videos > 0:
                self.master.after(0, self.update_status, self.facebook_batch_status_label, f"QUÉT HOÀN TẤT. Tìm thấy {self.facebook_total_videos} Reels/Bài đăng.", "green")
                self.master.after(0, self.facebook_batch_download_button.config, {"state": tk.NORMAL})
            else:
                self.master.after(0, self.update_status, self.facebook_batch_status_label, f"Quét thất bại/Không có video. Vui lòng kiểm tra lại URL và COOKIES.", "red")
                self.master.after(0, self.facebook_batch_download_button.config, {"state": tk.DISABLED})
        
        except FileNotFoundError:
            self.master.after(0, self.update_status, self.facebook_batch_status_label, "Lỗi Quét: Không tìm thấy yt-dlp.", "red")
        except subprocess.TimeoutExpired:
            self.master.after(0, self.update_status, self.facebook_batch_status_label, "Lỗi Quét: Hết thời gian chờ (60s). Cookies/URL có thể sai.", "red")


        self.master.after(0, self.update_progress_label, self.facebook_progress_label, self.facebook_downloaded_count, self.facebook_total_videos)
        self.master.after(0, self.facebook_scan_button.config, {"state": tk.NORMAL})

    def start_facebook_batch_download(self):
        url = self.facebook_url_entry.get().strip()
        cookie_path = self.facebook_cookie_path_entry.get().strip()
        download_dir = self.facebook_batch_dir_entry.get().strip()
        max_videos_str = self.facebook_max_videos_entry.get().strip()
        
        if not download_dir or not os.path.isdir(download_dir): messagebox.showerror("Lỗi", "Vui lòng chọn thư mục lưu trữ hợp lệ."); return
        try: max_videos = int(max_videos_str) if max_videos_str.lower() != "tất cả" else None
        except ValueError: messagebox.showerror("Lỗi", "Số lượng video không hợp lệ."); return

        self.update_status(self.facebook_batch_status_label, "Đang bắt đầu tải Reels...", "purple")
        self.facebook_scan_button.config(state=tk.DISABLED)
        self.facebook_batch_download_button.config(state=tk.DISABLED)
        self.facebook_batch_stop_button.config(state=tk.NORMAL)
        self.is_downloading = True
        self.facebook_downloaded_count = 0
        self.update_progress_label(self.facebook_progress_label, self.facebook_downloaded_count, self.facebook_total_videos)
        
        self.download_thread = threading.Thread(target=self._batch_download_logic, args=(url, cookie_path, download_dir, max_videos, self.facebook_batch_status_label, self.facebook_progress_label, "facebook"))
        self.download_thread.start()

    def stop_facebook_batch_download(self):
        self._stop_batch_download_logic(self.facebook_batch_status_label, self.facebook_scan_button, self.facebook_batch_download_button, self.facebook_batch_stop_button, self.facebook_downloaded_count, self.facebook_total_videos)

    # =================================================================
    #                      LOGIC CHUNG CHO TẢI HÀNG LOẠT (KHÔNG ĐỔI)
    # =================================================================
    def _stop_batch_download_logic(self, status_label, scan_btn, download_btn, stop_btn, downloaded_count, total_videos):
        self.is_downloading = False
        if self.process and self.process.poll() is None:
            self.process.terminate()
        # Chờ một lát cho quá trình con kết thúc
        if self.process:
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
                
        self.update_status(status_label, f"ĐÃ DỪNG TẢI. Đã tải {downloaded_count}/{total_videos}.", "red")
        
        self.master.after(0, scan_btn.config, {"state": tk.NORMAL})
        self.master.after(0, download_btn.config, {"state": tk.NORMAL})
        self.master.after(0, stop_btn.config, {"state": tk.DISABLED})
        
    def _batch_download_logic(self, url, cookie_path, download_dir, max_videos, status_label, progress_label, source):
        # Thiết lập lệnh tải yt-dlp
        command = [
            YT_DLP_COMMAND,
            "-P", download_dir, 
            "-o", "%(title)s.%(ext)s", 
            url
        ]
        
        # ÁP DỤNG CẢI THIỆN TỐC ĐỘ TẢI
        if CONCURRENT_FRAGMENTS > 1:
            command.extend(["-N", str(CONCURRENT_FRAGMENTS)]) 
            self.update_status(status_label, f"Đang sử dụng tải đa luồng: {CONCURRENT_FRAGMENTS} luồng...", "blue")

        current_downloaded = 0
        current_total = 0
        
        # 1. Thiết lập các thông số ban đầu và lấy tổng số video đã quét
        if source == "youtube":
            command.extend(["--match-filter", "duration <= 60", "--ignore-errors"])
            self.youtube_downloaded_count = 0 
            current_total = self.youtube_total_videos
        elif source == "tiktok":
            if cookie_path and os.path.exists(cookie_path): command.extend(["--cookies", cookie_path])
            self.tiktok_downloaded_count = 0 
            current_total = self.tiktok_total_videos
        elif source == "facebook": # LOGIC FACEBOOK
            if cookie_path and os.path.exists(cookie_path): command.extend(["--cookies", cookie_path])
            self.facebook_downloaded_count = 0 
            current_total = self.facebook_total_videos

        # 2. Áp dụng giới hạn tải và điều chỉnh tổng số hiển thị (current_total)
        if max_videos is not None and max_videos > 0:
            command.extend(["--max-downloads", str(max_videos)])
            current_total = min(current_total, max_videos)

        try:
            self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
            
            for line in self.process.stdout:
                if not self.is_downloading: break
                
                # CẬP NHẬT LOGIC BỘ ĐẾM: Sửa lỗi đếm bị nhân đôi
                if re.search(r"Destination: .*|has already been downloaded", line):
                    if source == "youtube": 
                        self.youtube_downloaded_count += 1
                        current_downloaded = self.youtube_downloaded_count
                    elif source == "tiktok": 
                        self.tiktok_downloaded_count += 1
                        current_downloaded = self.tiktok_downloaded_count
                    elif source == "facebook": # LOGIC FACEBOOK
                        self.facebook_downloaded_count += 1
                        current_downloaded = self.facebook_downloaded_count
                    
                    self.update_progress_label(progress_label, current_downloaded, current_total)
                
                self.update_status(status_label, f"Đang tải: {line.strip()[:150]}", "purple")
                
            self.process.wait()

            # Lấy số lượng đã tải cuối cùng
            if source == "youtube": 
                current_downloaded = self.youtube_downloaded_count
            elif source == "tiktok": 
                current_downloaded = self.tiktok_downloaded_count
            elif source == "facebook": # LOGIC FACEBOOK
                current_downloaded = self.facebook_downloaded_count

            # LOGIC KIỂM TRA KẾT THÚC: Sửa lỗi Mã 101
            # Nếu đã đạt số lượng yêu cầu, coi là hoàn tất.
            is_success_by_count = current_total > 0 and current_downloaded >= current_total
            
            if is_success_by_count or self.process.returncode == 0:
                # Cập nhật lại lần cuối
                self.master.after(0, self.update_progress_label, progress_label, current_downloaded, current_total)
                self.update_status(status_label, f"TẢI HOÀN TẤT! Đã tải {current_downloaded}/{current_total} video.", "green")
            
            elif self.is_downloading == False: 
                 self.update_status(status_label, f"ĐÃ DỪNG TẢI bởi người dùng. Đã tải {current_downloaded}/{current_total}.", "red")
            else:
                self.update_status(status_label, f"TẢI THẤT BẠI. Mã lỗi: {self.process.returncode}.", "red")
                
        except FileNotFoundError:
            self.update_status(status_label, "Lỗi Tải: Không tìm thấy yt-dlp.", "red")

        finally:
            self.is_downloading = False
            # Kích hoạt lại các nút sau khi tải xong/lỗi
            if source == "youtube": 
                self.master.after(0, self.youtube_scan_button.config, {"state": tk.NORMAL})
                self.master.after(0, self.youtube_batch_download_button.config, {"state": tk.NORMAL})
                self.master.after(0, self.youtube_batch_stop_button.config, {"state": tk.DISABLED})
            elif source == "tiktok": 
                self.master.after(0, self.tiktok_scan_button.config, {"state": tk.NORMAL})
                self.master.after(0, self.tiktok_batch_download_button.config, {"state": tk.NORMAL})
                self.master.after(0, self.tiktok_batch_stop_button.config, {"state": tk.DISABLED})
            elif source == "facebook": # LOGIC FACEBOOK
                self.master.after(0, self.facebook_scan_button.config, {"state": tk.NORMAL})
                self.master.after(0, self.facebook_batch_download_button.config, {"state": tk.NORMAL})
                self.master.after(0, self.facebook_batch_stop_button.config, {"state": tk.DISABLED})

# --- KHỞI CHẠY ỨNG DỤNG ---
if __name__ == "__main__":
    root = tk.Tk()
    app = DownloaderApp(root)
    root.mainloop()