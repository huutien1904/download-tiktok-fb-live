import tkinter as tk
from tkinter import filedialog, messagebox
import requests
import subprocess
import threading
import os
import time

# --- CÁC HÀM XỬ LÝ CHÍNH ---

class TikTokDownloaderApp:
    def __init__(self, master):
        self.master = master
        master.title("TikTok Live Downloader & Converter")
        
        # Biến để kiểm soát việc tải xuống
        self.is_downloading = False
        self.download_thread = None
        self.download_session = None # Dùng để hủy tải xuống
        
        # Biến để tính toán thời gian video
        self.download_start_time = None
        self.estimated_bitrate = 1000000  # 1 Mbps mặc định (125 KB/s)

        # Khởi tạo giao diện
        self._create_widgets(master)

    def _create_widgets(self, master):
        # 1. Link Live Stream
        tk.Label(master, text="Link Livestream (.flv):").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.url_entry = tk.Entry(master, width=60)
        self.url_entry.grid(row=0, column=1, padx=10, pady=5)
        # Điền link mẫu
        self.url_entry.insert(0, "https://pull-flv-l11-va01.tiktokcdn.com/game/stream-3000480683892146276.flv?...")

        # 2. Đường dẫn lưu file
        tk.Label(master, text="Đường dẫn lưu File FLV:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.path_entry = tk.Entry(master, width=50)
        self.path_entry.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        
        # Nút Duyệt thư mục
        tk.Button(master, text="Duyệt...", command=self.browse_save_path).grid(row=1, column=1, sticky="e", padx=10, pady=5)
        
        # 3. Nút chức năng
        self.download_button = tk.Button(master, text="Bắt đầu Tải về", command=self.start_download, bg="green", fg="white")
        self.download_button.grid(row=2, column=0, padx=10, pady=10)
        
        self.stop_button = tk.Button(master, text="Dừng Tải về", command=self.stop_download, state=tk.DISABLED, bg="red", fg="white")
        self.stop_button.grid(row=2, column=1, sticky="w", padx=10, pady=10)

        self.convert_button = tk.Button(master, text="Chuyển đổi sang MP4", command=self.start_convert, state=tk.DISABLED)
        self.convert_button.grid(row=2, column=1, sticky="e", padx=10, pady=10)

        # 4. Khu vực Trạng thái
        tk.Label(master, text="Trạng thái:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.status_label = tk.Label(master, text="Sẵn sàng", fg="blue")
        self.status_label.grid(row=3, column=1, sticky="w", padx=10, pady=5)
        
        # 5. Hiển thị thời gian video đã tải
        tk.Label(master, text="Thời gian video:").grid(row=4, column=0, sticky="w", padx=10, pady=5)
        self.video_time_label = tk.Label(master, text="00:00:00", fg="green")
        self.video_time_label.grid(row=4, column=1, sticky="w", padx=10, pady=5)

    def browse_save_path(self):
        # Mở hộp thoại để chọn nơi lưu và tên file
        default_filename = "tiktok_live_video.flv"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".flv",
            filetypes=[("FLV Video", "*.flv")],
            initialfile=default_filename
        )
        if save_path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, save_path)
            
    def update_status(self, message, color="blue"):
        self.status_label.config(text=message, fg=color)
    
    def format_time(self, seconds):
        """Chuyển đổi giây thành định dạng HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def update_video_time(self, downloaded_bytes):
        """Cập nhật thời gian video dựa trên dung lượng đã tải"""
        if downloaded_bytes > 0:
            # Tính thời gian video dựa trên bitrate ước tính
            # Bitrate tính bằng bits per second, downloaded_bytes tính bằng bytes
            estimated_seconds = (downloaded_bytes * 8) / self.estimated_bitrate
            time_str = self.format_time(estimated_seconds)
            self.video_time_label.config(text=time_str)
        else:
            self.video_time_label.config(text="00:00:00")

    def start_download(self):
        # 1. Kiểm tra đầu vào
        url = self.url_entry.get().strip()
        save_path = self.path_entry.get().strip()

        if not url or not save_path:
            messagebox.showerror("Lỗi", "Vui lòng điền đầy đủ Link Livestream và Đường dẫn lưu File.")
            return

        self.update_status("Đang chuẩn bị tải về...", "orange")
        self.download_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.convert_button.config(state=tk.DISABLED)
        self.is_downloading = True
        
        # Reset thời gian video
        self.update_video_time(0)
        self.download_start_time = time.time()

        # 2. Chạy tải xuống trong một luồng mới
        self.download_thread = threading.Thread(target=self._download_flv, args=(url, save_path))
        self.download_thread.start()

    def stop_download(self):
        self.is_downloading = False
        # Nếu đang trong quá trình request (chưa bắt đầu tải) thì có thể dừng
        if self.download_session:
             self.download_session.close() # Ngắt kết nối
        self.update_status("Đã dừng tải về (Có thể file bị thiếu dữ liệu).", "red")
        self.download_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        # Cho phép convert (nếu người dùng muốn thử chuyển đổi file chưa hoàn chỉnh)
        if os.path.exists(self.path_entry.get()):
            self.convert_button.config(state=tk.NORMAL)

    def _download_flv(self, url, save_path):
        try:
            self.download_session = requests.Session()
            # Stream=True để tải từng phần (chunk)
            with self.download_session.get(url, stream=True) as r:
                r.raise_for_status() # Báo lỗi nếu mã trạng thái không phải 200
                total_size = int(r.headers.get('content-length', 0))
                downloaded_size = 0
                chunk_size = 8192 # 8KB
                
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=chunk_size): 
                        if not self.is_downloading:
                            break
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Cập nhật bitrate ước tính dựa trên tốc độ tải thực tế
                        if self.download_start_time:
                            elapsed_time = time.time() - self.download_start_time
                            if elapsed_time > 5:  # Sau 5 giây mới bắt đầu ước tính để có dữ liệu chính xác hơn
                                current_bitrate = (downloaded_size * 8) / elapsed_time  # bits per second
                                # Làm mượt bitrate bằng cách lấy trung bình với giá trị cũ
                                self.estimated_bitrate = (self.estimated_bitrate + current_bitrate) / 2
                        
                        # Cập nhật trạng thái và thời gian video
                        progress = downloaded_size / total_size * 100 if total_size else 0
                        self.master.after(0, self.update_status, f"Đang tải về: {downloaded_size} bytes ({progress:.2f}%)", "orange")
                        self.master.after(0, self.update_video_time, downloaded_size)
                
                # Hoàn tất hoặc bị dừng
                if self.is_downloading:
                    self.master.after(0, self.update_status, f"Tải về HOÀN TẤT. Kích thước: {downloaded_size} bytes.", "green")
                else:
                    self.master.after(0, self.update_status, f"Tải về ĐÃ DỪNG. Kích thước: {downloaded_size} bytes.", "red")

        except requests.exceptions.RequestException as e:
            self.master.after(0, messagebox.showerror, "Lỗi Tải xuống", f"Lỗi kết nối hoặc URL không hợp lệ: {e}")
            self.master.after(0, self.update_status, "Lỗi khi tải về.", "red")
        finally:
            self.is_downloading = False
            self.download_session = None
            self.download_start_time = None
            self.master.after(0, self.download_button.config, {"state": tk.NORMAL})
            self.master.after(0, self.stop_button.config, {"state": tk.DISABLED})
            if os.path.exists(save_path):
                self.master.after(0, self.convert_button.config, {"state": tk.NORMAL})


    def start_convert(self):
        input_path = self.path_entry.get().strip()
        
        if not input_path or not os.path.exists(input_path):
            messagebox.showerror("Lỗi", "Vui lòng tải file FLV về trước hoặc kiểm tra đường dẫn file.")
            return

        if not input_path.lower().endswith(".flv"):
             messagebox.showerror("Lỗi", "File đầu vào phải có định dạng .flv")
             return

        # Tạo tên file MP4 đầu ra
        base, ext = os.path.splitext(input_path)
        output_path = base + ".mp4"
        
        self.update_status("Đang chuyển đổi FLV sang MP4 (Yêu cầu FFmpeg)...", "purple")
        self.convert_button.config(state=tk.DISABLED)

        # Chạy chuyển đổi trong một luồng mới
        convert_thread = threading.Thread(target=self._convert_flv_to_mp4, args=(input_path, output_path))
        convert_thread.start()

    def _convert_flv_to_mp4(self, input_path, output_path):
        # Lệnh FFmpeg: -i là input, -c copy là copy stream (nhanh)
        # Nếu muốn mã hóa lại để tương thích hơn, dùng: -c:v libx264 -c:a aac
        FFMPEG_EXE_PATH = 'C:/ffmpeg/bin/ffmpeg.exe'
        ffmpeg_command = [
            FFMPEG_EXE_PATH, 
            '-i', input_path, 
            '-c', 'copy', # Sao chép luồng video/audio mà không mã hóa lại (RẤT NHANH)
            output_path
        ]
        
        try:
            # Chạy FFmpeg
            subprocess.run(ffmpeg_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.master.after(0, self.update_status, f"Chuyển đổi HOÀN TẤT. File MP4: {output_path}", "green")
        except FileNotFoundError:
             self.master.after(0, messagebox.showerror, "Lỗi FFmpeg", "Không tìm thấy lệnh 'ffmpeg'. Vui lòng cài đặt FFmpeg và thêm nó vào biến môi trường PATH.")
             self.master.after(0, self.update_status, "Lỗi khi chuyển đổi (Không tìm thấy FFmpeg).", "red")
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.decode('utf-8', errors='ignore')
            self.master.after(0, messagebox.showerror, "Lỗi Chuyển đổi", f"FFmpeg thất bại. Lỗi: \n{error_output[-500:]}")
            self.master.after(0, self.update_status, "Lỗi khi chuyển đổi.", "red")
        except Exception as e:
            self.master.after(0, messagebox.showerror, "Lỗi Không xác định", f"Đã xảy ra lỗi: {e}")
            self.master.after(0, self.update_status, "Lỗi không xác định.", "red")
        finally:
            self.master.after(0, self.convert_button.config, {"state": tk.NORMAL})

# --- KHỞI CHẠY ỨNG DỤNG ---
root = tk.Tk()
app = TikTokDownloaderApp(root)
root.mainloop()