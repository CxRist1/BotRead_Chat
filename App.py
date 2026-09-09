import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, LabelFrame
from tkinter import ttk
import json
import os
import threading
import queue
import pygame
import pyttsx3
from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, GiftEvent, CommentEvent

CONFIG_FILE = "config.json"

log_queue = queue.Queue()
tts_queue = queue.Queue()

# ตัวแปรเก็บการตั้งค่าเสียงปัจจุบัน (เพื่อให้เปลี่ยนค่าได้ทันทีขณะบอทรันอยู่)
active_settings = {
    "speed": 150,
    "volume": 100,
    "max_len": 3000
}

def get_int(entry_widget, default_value):
    try:
        return int(entry_widget.get().strip())
    except ValueError:
        return default_value

def load_config():
    default_config = {"last_used": "", "accounts": {}}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if "username" in saved and "accounts" not in saved:
                    username = saved["username"]
                    default_config["last_used"] = username
                    if username:
                        default_config["accounts"][username] = {
                            "sound_path": saved.get("sound_path", ""),
                            "tts_speed": saved.get("tts_speed", 150),
                            "tts_volume": saved.get("tts_volume", 100),
                            "tts_max_len": saved.get("tts_max_len", 3000)
                        }
                else:
                    default_config.update(saved)
        except:
            pass
    return default_config

def tts_worker():
    engine = pyttsx3.init()
    
    while True:
        text = tts_queue.get()
        if text is None: break
        
        # ดึงค่าล่าสุดมาใช้เสมอ ทำให้ปรับความเร็ว/ความดังระหว่างไลฟ์ได้ทันที
        engine.setProperty('rate', active_settings["speed"])
        engine.setProperty('volume', active_settings["volume"] / 100.0)
        
        if len(text) > active_settings["max_len"]:
            text = text[:active_settings["max_len"]]
            
        try:
            engine.say(text)
            engine.runAndWait()
        except:
            pass

def start_bot(username, sound_path):
    try:
        pygame.mixer.init()
        gift_sound = pygame.mixer.Sound(sound_path) if sound_path and os.path.exists(sound_path) else None
        
        # รันระบบเสียง
        threading.Thread(target=tts_worker, daemon=True).start()
        client = TikTokLiveClient(unique_id=username)

        @client.on(ConnectEvent)
        async def on_connect(event: ConnectEvent):
            log_queue.put(f"✅ เชื่อมต่อกับช่อง {event.unique_id} สำเร็จ!")

        @client.on(CommentEvent)
        async def on_comment(event: CommentEvent):
            log_queue.put(f"💬 {event.user.nickname}: {event.comment}")
            tts_queue.put(event.comment)

        @client.on(GiftEvent)
        async def on_gift(event: GiftEvent):
            if event.gift.streakable and not event.gift.streaking_finished:
                return
            log_queue.put(f"🎁 {event.user.nickname} ส่ง {event.gift.info.name} จำนวน {event.gift.count} ชิ้น!")
            if gift_sound:
                gift_sound.play()

        client.run()
    except Exception as e:
        log_queue.put(f"❌ เกิดข้อผิดพลาด: {e}")

def process_queue():
    while not log_queue.empty():
        chat_box.insert(tk.END, log_queue.get_nowait() + "\n")
        chat_box.see(tk.END)
    root.after(100, process_queue)

def save_current_account():
    username = user_combo.get().strip()
    if not username:
        messagebox.showwarning("แจ้งเตือน", "กรุณาพิมพ์ชื่อช่องก่อนกดจดจำบัญชี")
        return
        
    config_data["accounts"][username] = {
        "sound_path": sound_entry.get().strip(),
        "tts_speed": get_int(speed_entry, 150),
        "tts_volume": get_int(vol_entry, 100),
        "tts_max_len": get_int(len_entry, 3000)
    }
    config_data["last_used"] = username
    user_combo['values'] = list(config_data["accounts"].keys())
    
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f)
        
    messagebox.showinfo("สำเร็จ", f"💾 จดจำการตั้งค่าของช่อง '{username}' เรียบร้อยแล้ว!")

def confirm_settings():
    # อัปเดตตัวแปรระบบเสียงให้มีผลทันที
    active_settings["volume"] = get_int(vol_entry, 100)
    active_settings["speed"] = get_int(speed_entry, 150)
    active_settings["max_len"] = get_int(len_entry, 3000)
    
    # จัดตัวเลขในกล่องข้อความให้สวยงาม (เผื่อผู้ใช้พิมพ์ผิด)
    vol_entry.delete(0, tk.END); vol_entry.insert(0, active_settings["volume"])
    speed_entry.delete(0, tk.END); speed_entry.insert(0, active_settings["speed"])
    len_entry.delete(0, tk.END); len_entry.insert(0, active_settings["max_len"])
    
    # ถ้ามีชื่อช่องอยู่ ให้เซฟค่าลงไฟล์ด้วย
    username = user_combo.get().strip()
    if username:
        if username not in config_data["accounts"]:
            config_data["accounts"][username] = {}
        config_data["accounts"][username]["tts_volume"] = active_settings["volume"]
        config_data["accounts"][username]["tts_speed"] = active_settings["speed"]
        config_data["accounts"][username]["tts_max_len"] = active_settings["max_len"]
        
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f)
            
    messagebox.showinfo("ยืนยัน", "✔️ อัปเดตการตั้งค่าเสียงเรียบร้อย (มีผลทันที)")

def run_app():
    username = user_combo.get().strip()
    if not username:
        messagebox.showwarning("แจ้งเตือน", "กรุณาใส่ชื่อช่อง TikTok")
        return

    # เรียกใช้ฟังก์ชันยืนยันการตั้งค่าก่อนเริ่ม
    confirm_settings()
    
    config_data["last_used"] = username
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f)
    
    start_btn.config(state=tk.DISABLED, text="กำลังดึงข้อมูล...")
    chat_box.delete(1.0, tk.END)
    chat_box.insert(tk.END, "กำลังเชื่อมต่อ...\n")
    
    bot_thread = threading.Thread(
        target=start_bot, 
        args=(username, sound_entry.get().strip()),
        daemon=True
    )
    bot_thread.start()

def on_account_select(event=None):
    selected = user_combo.get()
    if selected in config_data["accounts"]:
        acc = config_data["accounts"][selected]
        
        sound_entry.delete(0, tk.END)
        sound_entry.insert(0, acc.get("sound_path", ""))
        
        vol_entry.delete(0, tk.END)
        vol_entry.insert(0, acc.get("tts_volume", 100))
        
        speed_entry.delete(0, tk.END)
        speed_entry.insert(0, acc.get("tts_speed", 150))
        
        len_entry.delete(0, tk.END)
        len_entry.insert(0, acc.get("tts_max_len", 3000))
        
        # อัปเดตค่าให้ระบบเสียงทันทีเมื่อเปลี่ยน Profile
        active_settings["volume"] = acc.get("tts_volume", 100)
        active_settings["speed"] = acc.get("tts_speed", 150)
        active_settings["max_len"] = acc.get("tts_max_len", 3000)

# --- สร้างหน้าต่าง GUI ---
root = tk.Tk()
root.title("TikTok Live Bot")
root.geometry("540x650")
config_data = load_config()

frame_top = LabelFrame(root, text=" ⚙️ ตั้งค่าบัญชีและการเชื่อมต่อ ", padx=10, pady=10)
frame_top.pack(pady=10, fill="x", padx=20)

tk.Label(frame_top, text="ชื่อช่อง TikTok:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
user_combo = ttk.Combobox(frame_top, width=22)
user_combo.grid(row=0, column=1, pady=5, sticky="w")
user_combo['values'] = list(config_data["accounts"].keys())
user_combo.bind("<<ComboboxSelected>>", on_account_select)

btn_save = tk.Button(frame_top, text="💾 จดจำบัญชีนี้", command=save_current_account, bg="#17a2b8", fg="white")
btn_save.grid(row=0, column=2, padx=5, sticky="w")

tk.Label(frame_top, text="เสียงแจ้งเตือน:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
sound_entry = tk.Entry(frame_top, width=25)
sound_entry.grid(row=1, column=1, pady=5, sticky="w")
tk.Button(frame_top, text="เลือกไฟล์", command=lambda: sound_entry.insert(0, filedialog.askopenfilename()) if sound_entry.delete(0, tk.END) == None else None).grid(row=1, column=2, padx=5, sticky="w")

tts_frame = LabelFrame(root, text=" 🎙️ ตั้งค่าเสียงอ่านแชท (Text-to-Speech) ", padx=10, pady=10)
tts_frame.pack(fill="x", padx=20, pady=5)

tk.Label(tts_frame, text="ความดัง (%):").grid(row=0, column=0, sticky="e", pady=5)
vol_entry = tk.Entry(tts_frame, width=10)
vol_entry.grid(row=0, column=1, sticky="w", padx=5)

tk.Label(tts_frame, text="ความเร็ว (ปกติ 150):").grid(row=0, column=2, sticky="e", pady=5)
speed_entry = tk.Entry(tts_frame, width=10)
speed_entry.grid(row=0, column=3, sticky="w", padx=5)

tk.Label(tts_frame, text="อ่านข้อความยาวสุด:").grid(row=1, column=0, sticky="e", pady=5)
len_entry = tk.Entry(tts_frame, width=10)
len_entry.grid(row=1, column=1, sticky="w", padx=5)
tk.Label(tts_frame, text="(ตัวอักษร)").grid(row=1, column=2, sticky="w")

# เพิ่มปุ่มยืนยันการตั้งค่า
btn_confirm = tk.Button(tts_frame, text="✔️ ยืนยันการตั้งค่า", command=confirm_settings, bg="#ffc107", fg="black")
btn_confirm.grid(row=1, column=3, padx=5, sticky="w")

# เติมค่าเริ่มต้น
vol_entry.insert(0, "100")
speed_entry.insert(0, "150")
len_entry.insert(0, "3000")

if config_data["last_used"]:
    user_combo.set(config_data["last_used"])
    on_account_select()

start_btn = tk.Button(root, text="▶ เริ่มเชื่อมต่อไลฟ์สด", command=run_app, bg="#28a745", fg="white", font=("Arial", 11, "bold"), width=20)
start_btn.pack(pady=10)

chat_box = scrolledtext.ScrolledText(root, width=60, height=14)
chat_box.pack(padx=20, pady=5)

root.after(100, process_queue)
root.mainloop()