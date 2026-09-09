import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import json
import os
import threading
import queue
import pygame
from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, GiftEvent, CommentEvent

CONFIG_FILE = "config.json"

# สร้างคิวสำหรับส่งข้อความระหว่างบอทกับ GUI
log_queue = queue.Queue()

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"username": "", "sound_path": ""}

def save_config(username, sound_path):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"username": username, "sound_path": sound_path}, f)

# ฟังก์ชันบอท (รันเบื้องหลัง)
def start_bot(username, sound_path):
    try:
        # เริ่มระบบเสียง
        pygame.mixer.init()
        # โหลดไฟล์เสียง (ถ้ามีการเลือกไฟล์ไว้)
        if sound_path and os.path.exists(sound_path):
            gift_sound = pygame.mixer.Sound(sound_path)
        else:
            gift_sound = None
        
        client = TikTokLiveClient(unique_id=username)

        @client.on(ConnectEvent)
        async def on_connect(event: ConnectEvent):
            log_queue.put(f"✅ เชื่อมต่อกับช่อง {event.unique_id} สำเร็จ!")

        @client.on(CommentEvent)
        async def on_comment(event: CommentEvent):
            log_queue.put(f"💬 {event.user.nickname}: {event.comment}")

        @client.on(GiftEvent)
        async def on_gift(event: GiftEvent):
            # ป้องกันการอ่านซ้ำซ้อนตอนผู้ชมส่งของขวัญรัวๆ (คอมโบ)
            if event.gift.streakable and not event.gift.streaking_finished:
                return
            
            log_queue.put(f"🎁 {event.user.nickname} ส่ง {event.gift.info.name} จำนวน {event.gift.count} ชิ้น!")
            
            # เล่นเสียงถ้ามีไฟล์เสียง
            if gift_sound:
                gift_sound.play()

        client.run()
    except Exception as e:
        log_queue.put(f"❌ เกิดข้อผิดพลาด: {e}")

# ฟังก์ชันอัปเดต GUI จากคิว
def process_queue():
    while not log_queue.empty():
        msg = log_queue.get_nowait()
        chat_box.insert(tk.END, msg + "\n")
        chat_box.see(tk.END) # เลื่อนหน้าจอลงมาบรรทัดล่างสุดอัตโนมัติ
    
    # สั่งให้ฟังก์ชันนี้เรียกตัวเองซ้ำทุกๆ 100 มิลลิวินาที
    root.after(100, process_queue)

# --- ส่วนตั้งค่าหน้าต่าง Tkinter ---
def browse_file():
    filename = filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav *.mp3")])
    if filename:
        sound_entry.delete(0, tk.END)
        sound_entry.insert(0, filename)

def run_app():
    username = user_entry.get().strip()
    sound_path = sound_entry.get().strip()

    if not username:
        messagebox.showwarning("แจ้งเตือน", "กรุณาใส่ชื่อช่อง TikTok")
        return

    save_config(username, sound_path)
    start_btn.config(state=tk.DISABLED, text="กำลังดึงข้อมูล...")
    
    # เคลียร์ข้อความเก่า
    chat_box.delete(1.0, tk.END)
    chat_box.insert(tk.END, "กำลังเชื่อมต่อ...\n")
    
    bot_thread = threading.Thread(target=start_bot, args=(username, sound_path), daemon=True)
    bot_thread.start()

# สร้างหน้าต่างหลัก
root = tk.Tk()
root.title("TikTok Live Monitor")
root.geometry("500x450")

config_data = load_config()

# ส่วนตั้งค่าด้านบน
frame_top = tk.Frame(root)
frame_top.pack(pady=10)

tk.Label(frame_top, text="ชื่อช่อง TikTok:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
user_entry = tk.Entry(frame_top, width=30)
user_entry.insert(0, config_data["username"])
user_entry.grid(row=0, column=1, padx=5, pady=2)

tk.Label(frame_top, text="ไฟล์เสียง:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
sound_entry = tk.Entry(frame_top, width=30)
sound_entry.insert(0, config_data["sound_path"])
sound_entry.grid(row=1, column=1, padx=5, pady=2)
tk.Button(frame_top, text="เลือกไฟล์", command=browse_file).grid(row=1, column=2, padx=5, pady=2)

start_btn = tk.Button(root, text="เริ่มเชื่อมต่อ", command=run_app, bg="green", fg="white", width=20)
start_btn.pack(pady=5)

# กล่องแสดงข้อความ
chat_box = scrolledtext.ScrolledText(root, width=55, height=15, state='normal')
chat_box.pack(pady=10, padx=10)

# เริ่มการทำงานของระบบเช็คคิว
root.after(100, process_queue)

root.mainloop()