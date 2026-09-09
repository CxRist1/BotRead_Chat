import customtkinter as ctk
from tkinter import filedialog, messagebox
import json
import os
import threading
import queue
import pygame
import time
import io
from gtts import gTTS
from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, GiftEvent, CommentEvent, FollowEvent

CONFIG_FILE = "config.json"

log_queue = queue.Queue()
tts_queue = queue.Queue()

active_settings = {"speed": 150, "volume": 100, "max_len": 3000}

# ==========================================
# เริ่มระบบเสียงและ Theme พื้นฐาน
# ==========================================
pygame.mixer.init() # ย้ายมาเปิดระบบเสียงตั้งแต่เริ่มแอปเพื่อให้ปุ่ม Test ใช้งานได้
ctk.set_appearance_mode("Light")  
ctk.set_default_color_theme("blue")

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
                            "follow_sound_path": "", 
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
    while True:
        text = tts_queue.get()
        if text is None: break
        
        if len(text) > active_settings["max_len"]:
            text = text[:active_settings["max_len"]]
            
        try:
            tts = gTTS(text=text, lang='th')
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            
            pygame.mixer.music.load(fp)
            pygame.mixer.music.set_volume(active_settings["volume"] / 100.0)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
        except Exception as e:
            print(f"TTS Error: {e}")

# ==========================================
# ฟังก์ชันปุ่ม Test
# ==========================================
def test_system():
    confirm_settings() # อัปเดตความดังล่าสุดก่อนเทสต์
    log_queue.put("🔧 ระบบ: กำลังทดสอบเสียง...")
    tts_queue.put("สวัสดีครับ ทดสอบระบบเสียงสิริและการแจ้งเตือนครับ")
    
    # ดึงไฟล์เสียงมาทดสอบเล่น
    gift_path = gift_sound_entry.get().strip()
    follow_path = follow_sound_entry.get().strip()
    
    def play_test_fx():
        if follow_path and os.path.exists(follow_path):
            pygame.mixer.Sound(follow_path).play()
        time.sleep(1.5) # เว้นจังหวะให้เสียง Follow เล่นก่อนค่อยเล่น Gift
        if gift_path and os.path.exists(gift_path):
            pygame.mixer.Sound(gift_path).play()
            
    threading.Thread(target=play_test_fx, daemon=True).start()

def start_bot(username, gift_sound_path, follow_sound_path):
    try:
        gift_sound = pygame.mixer.Sound(gift_sound_path) if gift_sound_path and os.path.exists(gift_sound_path) else None
        follow_sound = pygame.mixer.Sound(follow_sound_path) if follow_sound_path and os.path.exists(follow_sound_path) else None
        
        client = TikTokLiveClient(unique_id=username)

        @client.on(ConnectEvent)
        async def on_connect(event: ConnectEvent):
            log_queue.put(f"✅ เชื่อมต่อกับช่อง {event.unique_id} สำเร็จ!")

        @client.on(CommentEvent)
        async def on_comment(event: CommentEvent):
            log_queue.put(f"💬 {event.user.nickname}: {event.comment}")
            tts_queue.put(f"{event.user.nickname} พูดว่า {event.comment}")

        @client.on(GiftEvent)
        async def on_gift(event: GiftEvent):
            if event.gift.streakable and not event.gift.streaking_finished:
                return
            log_queue.put(f"🎁 {event.user.nickname} ส่ง {event.gift.info.name} จำนวน {event.gift.count} ชิ้น!")
            if gift_sound:
                gift_sound.play()

        @client.on(FollowEvent)
        async def on_follow(event: FollowEvent):
            log_queue.put(f"👤 {event.user.nickname} เริ่มติดตามคุณ!")
            if follow_sound:
                follow_sound.play()

        client.run()
    except Exception as e:
        log_queue.put(f"❌ เกิดข้อผิดพลาด: {e}")

def process_queue():
    while not log_queue.empty():
        msg = log_queue.get_nowait() + "\n"
        chat_box.insert("end", msg)
        chat_box.see("end")
    root.after(100, process_queue)

def save_current_account():
    username = user_combo.get().strip()
    if not username:
        messagebox.showwarning("แจ้งเตือน", "กรุณาพิมพ์ชื่อช่องก่อนกดจดจำบัญชี")
        return
        
    config_data["accounts"][username] = {
        "sound_path": gift_sound_entry.get().strip(),
        "follow_sound_path": follow_sound_entry.get().strip(),
        "tts_speed": get_int(speed_entry, 150),
        "tts_volume": get_int(vol_entry, 100),
        "tts_max_len": get_int(len_entry, 3000)
    }
    config_data["last_used"] = username
    user_combo.configure(values=list(config_data["accounts"].keys()))
    
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f)
        
    messagebox.showinfo("สำเร็จ", f"💾 จดจำการตั้งค่าบัญชีเรียบร้อย!")

def confirm_settings():
    active_settings["volume"] = get_int(vol_entry, 100)
    active_settings["speed"] = get_int(speed_entry, 150)
    active_settings["max_len"] = get_int(len_entry, 3000)
    
    vol_entry.delete(0, "end"); vol_entry.insert(0, active_settings["volume"])
    speed_entry.delete(0, "end"); speed_entry.insert(0, active_settings["speed"])
    len_entry.delete(0, "end"); len_entry.insert(0, active_settings["max_len"])
    
    username = user_combo.get().strip()
    if username and username in config_data["accounts"]:
        config_data["accounts"][username]["tts_volume"] = active_settings["volume"]
        config_data["accounts"][username]["tts_speed"] = active_settings["speed"]
        config_data["accounts"][username]["tts_max_len"] = active_settings["max_len"]
        
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f)

def run_app():
    username = user_combo.get().strip()
    if not username:
        messagebox.showwarning("แจ้งเตือน", "กรุณาใส่ชื่อช่อง TikTok")
        return

    confirm_settings()
    
    config_data["last_used"] = username
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f)
    
    start_btn.configure(state="disabled", text="กำลังเชื่อมต่อ...")
    chat_box.delete("1.0", "end")
    chat_box.insert("end", f"กำลังเชื่อมต่อช่อง: {username}...\n")
    
    bot_thread = threading.Thread(
        target=start_bot, 
        args=(username, gift_sound_entry.get().strip(), follow_sound_entry.get().strip()),
        daemon=True
    )
    bot_thread.start()

def on_account_select(choice):
    if choice in config_data["accounts"]:
        acc = config_data["accounts"][choice]
        
        gift_sound_entry.delete(0, "end")
        gift_sound_entry.insert(0, acc.get("sound_path", ""))
        
        follow_sound_entry.delete(0, "end")
        follow_sound_entry.insert(0, acc.get("follow_sound_path", ""))
        
        vol_entry.delete(0, "end")
        vol_entry.insert(0, acc.get("tts_volume", 100))
        
        speed_entry.delete(0, "end")
        speed_entry.insert(0, acc.get("tts_speed", 150))
        
        len_entry.delete(0, "end")
        len_entry.insert(0, acc.get("tts_max_len", 3000))
        
        active_settings["volume"] = acc.get("tts_volume", 100)
        active_settings["speed"] = acc.get("tts_speed", 150)
        active_settings["max_len"] = acc.get("tts_max_len", 3000)

def browse_gift_file():
    filepath = filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav *.mp3")])
    if filepath:
        gift_sound_entry.delete(0, "end")
        gift_sound_entry.insert(0, filepath)

def browse_follow_file():
    filepath = filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav *.mp3")])
    if filepath:
        follow_sound_entry.delete(0, "end")
        follow_sound_entry.insert(0, filepath)

# ==========================================
# สร้างหน้าต่างหลัก CTk
# ==========================================
root = ctk.CTk()
root.title("TikTok Live Studio - Dashboard")
root.geometry("1020x730") 
root.configure(fg_color="#F0F2F5")

config_data = load_config()

title_font = ctk.CTkFont(family="Helvetica", size=18, weight="bold")
header_font = ctk.CTkFont(family="Helvetica", size=14, weight="bold")
body_font = ctk.CTkFont(family="Helvetica", size=13)

# ------------------------------------------
# ส่วนซ้าย: Sidebar
# ------------------------------------------
sidebar_frame = ctk.CTkFrame(root, width=330, corner_radius=0, fg_color="#FFFFFF")
sidebar_frame.pack(side="left", fill="y", padx=0, pady=0)
sidebar_frame.pack_propagate(False) 

ctk.CTkLabel(sidebar_frame, text="⚙️ Control Panel", font=title_font, text_color="#1C1E21").pack(pady=(20, 10))

acc_card = ctk.CTkFrame(sidebar_frame, fg_color="#F7F8FA", corner_radius=8)
acc_card.pack(fill="x", padx=15, pady=(0, 10))

ctk.CTkLabel(acc_card, text="บัญชี & การเชื่อมต่อ", font=header_font, text_color="#4B4F56").pack(anchor="w", padx=15, pady=(10, 5))

ctk.CTkLabel(acc_card, text="ชื่อช่อง TikTok (@):", font=body_font).pack(anchor="w", padx=15)
user_combo = ctk.CTkComboBox(acc_card, values=list(config_data["accounts"].keys()), command=on_account_select, font=body_font, width=250, border_color="#CCD0D5")
user_combo.pack(padx=15, pady=(0, 10))

btn_save = ctk.CTkButton(acc_card, text="💾 บันทึกบัญชีนี้", command=save_current_account, fg_color="#3B82F6", text_color="white", hover_color="#2563EB", font=body_font, width=250)
btn_save.pack(padx=15, pady=(0, 10))

ctk.CTkLabel(acc_card, text="🎁 เสียงแจ้งเตือนของขวัญ:", font=body_font).pack(anchor="w", padx=15)
gift_sound_entry = ctk.CTkEntry(acc_card, font=body_font, width=250, border_color="#CCD0D5")
gift_sound_entry.pack(padx=15, pady=(0, 5))
btn_browse_gift = ctk.CTkButton(acc_card, text="📂 ค้นหาไฟล์เสียง", command=browse_gift_file, fg_color="#64748B", text_color="white", hover_color="#475569", font=body_font, width=250)
btn_browse_gift.pack(padx=15, pady=(0, 10))

ctk.CTkLabel(acc_card, text="👤 เสียงแจ้งเตือนคนกดติดตาม:", font=body_font).pack(anchor="w", padx=15)
follow_sound_entry = ctk.CTkEntry(acc_card, font=body_font, width=250, border_color="#CCD0D5")
follow_sound_entry.pack(padx=15, pady=(0, 5))
btn_browse_follow = ctk.CTkButton(acc_card, text="📂 ค้นหาไฟล์เสียง", command=browse_follow_file, fg_color="#64748B", text_color="white", hover_color="#475569", font=body_font, width=250)
btn_browse_follow.pack(padx=15, pady=(0, 10))

tts_card = ctk.CTkFrame(sidebar_frame, fg_color="#F7F8FA", corner_radius=8)
tts_card.pack(fill="x", padx=15, pady=5)

ctk.CTkLabel(tts_card, text="🎙️ เสียงอ่านแชท (Google TTS)", font=header_font, text_color="#4B4F56").pack(anchor="w", padx=15, pady=(10, 5))

row1 = ctk.CTkFrame(tts_card, fg_color="transparent")
row1.pack(fill="x", padx=15, pady=2)
ctk.CTkLabel(row1, text="ความดัง (%):", font=body_font).pack(side="left")
vol_entry = ctk.CTkEntry(row1, width=50, font=body_font, justify="center", border_color="#CCD0D5")
vol_entry.pack(side="right")

row2 = ctk.CTkFrame(tts_card, fg_color="transparent")
row2.pack(fill="x", padx=15, pady=2)
ctk.CTkLabel(row2, text="ความเร็ว (Google ไม่อิงค่านี้):", font=body_font).pack(side="left")
speed_entry = ctk.CTkEntry(row2, width=50, font=body_font, justify="center", border_color="#CCD0D5")
speed_entry.pack(side="right")

row3 = ctk.CTkFrame(tts_card, fg_color="transparent")
row3.pack(fill="x", padx=15, pady=2)
ctk.CTkLabel(row3, text="อ่านยาวสุด (ตัวอักษร):", font=body_font).pack(side="left")
len_entry = ctk.CTkEntry(row3, width=50, font=body_font, justify="center", border_color="#CCD0D5")
len_entry.pack(side="right")

# --- ปุ่มเทสต์ระบบเสียง ---
btn_test = ctk.CTkButton(tts_card, text="🔊 ทดสอบเสียงทั้งหมด", command=test_system, fg_color="#10B981", hover_color="#059669", text_color="white", font=body_font, width=250)
btn_test.pack(padx=15, pady=(10, 5))

btn_confirm = ctk.CTkButton(tts_card, text="✔️ อัปเดตตั้งค่า", command=confirm_settings, fg_color="#8B5CF6", hover_color="#7C3AED", text_color="white", font=body_font, width=250)
btn_confirm.pack(padx=15, pady=(5, 15))

start_btn = ctk.CTkButton(sidebar_frame, text="▶ START LIVE", command=run_app, fg_color="#FE2C55", hover_color="#E62A4D", text_color="white", font=ctk.CTkFont(family="Helvetica", size=16, weight="bold"), height=50, width=290)
start_btn.pack(side="bottom", pady=15)

# ------------------------------------------
# ส่วนขวา: Main Content
# ------------------------------------------
main_frame = ctk.CTkFrame(root, fg_color="transparent")
main_frame.pack(side="right", fill="both", expand=True, padx=20, pady=20)

ctk.CTkLabel(main_frame, text="💬 Live Event Monitor", font=title_font, text_color="#1C1E21").pack(anchor="w", pady=(0, 10))

chat_box = ctk.CTkTextbox(main_frame, font=("Helvetica", 14), corner_radius=10, fg_color="#FFFFFF", text_color="#333333", border_width=1, border_color="#CCD0D5")
chat_box.pack(fill="both", expand=True)

vol_entry.insert(0, "100")
speed_entry.insert(0, "150")
len_entry.insert(0, "3000")

if config_data["last_used"]:
    user_combo.set(config_data["last_used"])
    on_account_select(config_data["last_used"])

# สตาร์ท Thread เสียงอ่านมารอไว้ตั้งแต่เริ่มแอป
threading.Thread(target=tts_worker, daemon=True).start()

root.after(100, process_queue)
root.mainloop()