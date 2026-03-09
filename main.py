'''
import sys
import os
import datetime

if getattr(sys, 'frozen', False):
    app_base_dir = os.path.dirname(sys.executable)
else:
    app_base_dir = os.path.dirname(os.path.abspath(__file__))

log_dir = os.path.join(app_base_dir, "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_file_path = os.path.join(log_dir, f"Romasha_Log_{current_time}.txt")

class StreamToLogger(object):
    def __init__(self, filename):
        self.log = open(filename, "a", encoding="utf-8")

    def write(self, message):
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.log.flush()

sys.stdout = StreamToLogger(log_file_path)
sys.stderr = sys.stdout
# =====================================================================
'''


import memory_manager                               
import sys
import os
import re
import datetime
import random
import queue
import base64
import requests
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal, QTimer, QRect
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QMessageBox
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtGui import QRegion, QCursor                   

import llm_brain
import motion_manager
import outfit_manager


class BrainWorker(QThread):
    chunk_received = pyqtSignal(str)
    task_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.task_queue = queue.Queue()
        self.is_cancelled = False
        self.running = True

    def run(self):
        while self.running:
            try:
                task = self.task_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            user_text, interrupted_text = task

            if user_text == "/SYSTEM_RESET_MEMORY":
                try:
                                             
                    memory_manager.clear_all_memories()
                                           
                    llm_brain.chat_history.clear()
                                                            
                    llm_brain.config["intimacy"] = 0
                    llm_brain.save_config()
                    print("💔 [记忆消散]: 曾经相处的点滴如沙般流逝，你们回到了最初相遇时的陌生与戒备。\n")

                except Exception as e:
                    print(f"⚠️ [命运纠缠]: 过去的痕迹似乎难以抹除 ({e})")
                self.task_queue.task_done()
                continue

            self.is_cancelled = False
            try:
                llm_brain.stream_chat_with_romasha(user_text, interrupted_text, self)
            except Exception as e:
                print(f"⚠️ [思绪迷茫]: 她的思绪似乎被某种未知的烦恼打断了 ({e})")

            if not self.is_cancelled:
                self.task_finished.emit()

            self.task_queue.task_done()

    def interrupt_and_submit(self, user_text, interrupted_text):
        self.is_cancelled = True
        with self.task_queue.mutex:
            self.task_queue.queue.clear()
        self.task_queue.put((user_text, interrupted_text))


class TTSWorker(QThread):
                                  
    audio_ready = pyqtSignal(str, bool, str)                  

    def __init__(self):
        super().__init__()
        self.task_queue = queue.Queue()
        self.running = True

                 
    def translate_to_japanese(self, text):
        try:
            api_type = llm_brain.config.get("api_type", "openai").lower()
            messages = [
                {"role": "system", "content": "你是一个精准的中译日翻译器，请将用户的中文台词精准直译翻译成对应的日文。【极其重要】：如果文本中包含形如 [quick_breath]、[sigh] 等英文控制标签，你必须原样保留它们，并将它们插入到日文中合理的位置。绝对不要翻译这些方括号内的标签！只需要输出最终的日文结果，不要任何解释。"},
                {"role": "user", "content": text}
            ]
            if api_type == "openai":
                response = llm_brain.client.chat.completions.create(
                    model=llm_brain.TARGET_MODEL,
                    messages=messages,
                    temperature=0.3
                )
                return response.choices[0].message.content.strip()
            elif api_type == "ollama":
                base_url = llm_brain.config.get("base_url", "").rstrip('/')
                if not base_url.endswith('/api/chat'):
                    base_url = f"{base_url}/api/chat"
                payload = {"model": llm_brain.TARGET_MODEL, "messages": messages, "stream": False, "options": {"temperature": 0.3}}
                headers = {"Content-Type": "application/json"}
                api_key = llm_brain.config.get("api_key", "")
                if api_key: headers["Authorization"] = f"Bearer {api_key}"
                resp = requests.post(base_url, json=payload, headers=headers, timeout=30.0)
                resp.raise_for_status()
                return resp.json().get("message", {}).get("content", text).strip()
        except Exception as e:
            print(f"\n⚠️ [意识干扰]: 那种古老的语调在脑海中变得模糊，你只能靠直觉去理解她想表达的意思...")
            print(f"   (🛠️ 隐秘线索: 思绪转译受阻，已回退至熟悉的语言 - {str(e)[:50]})")
            return text

    def run(self):
        while self.running:
            try:
                text = self.task_queue.get(timeout=0.5)
            except queue.Empty:
                continue

                                    
                                           
                                                                       
            clean_text = re.sub(r'\[(act_|mood_|intimacy_|wear_|hair_).*?\]', '', text)
            clean_text = re.sub(r'（内心：.*?）', '', clean_text)
            clean_text = clean_text.strip()

            if not clean_text:
                                                          
                                    
                self.audio_ready.emit("", True, "empty")
                self.task_queue.task_done()
                continue

                                                   
            instruct_text = ""
            match = re.match(r'^([\w\u4e00-\u9fa5]+)<\|endofprompt\|>(.*)$', clean_text)
            if match:
                instruct_text = match.group(1)            
                clean_text = match.group(2).strip()                                 

                                                   
            if llm_brain.config.get("tts_translate_to_ja", False) and clean_text:
                print("\n🌐 [古老回音]: 她的嘴唇微动，吐出的似乎是前文明遗留下的某种古老而温柔的语调...")
                clean_text = self.translate_to_japanese(clean_text)
                print(f"   (✨ 呢喃: {clean_text})")

            try:
                tts_engine = llm_brain.config.get("tts_engine", "cosyvoice")
                                                                
                proxies = {"http": None, "https": None}

                if tts_engine == "cosyvoice":
                                               
                    final_tts_text = clean_text
                    url = llm_brain.config.get("cosy_url", "")
                    payload = {
                        "text": final_tts_text,
                        "character_name": llm_brain.config.get("cosy_character", ""),
                        "mode": llm_brain.config.get("cosy_mode", ""),
                        "instruct_text": instruct_text,                
                        "speed": 1.0
                    }
                    response = requests.post(url, json=payload, proxies=proxies, timeout=60.0)

                    if response.status_code == 200:
                        b64_audio = base64.b64encode(response.content).decode('utf-8')
                        self.audio_ready.emit(b64_audio, True, "success")
                    else:
                                                        
                        print(
                            f"\n🔇 [感官剥离]: 也许是基地的磁场干扰，或者是她太过紧张，她的声音细若游丝，瞬间消散在冰冷的空气中...")
                        print(f"   (🛠️ 隐秘线索: 发声器官(CosyVoice)共振失败，状态码 {response.status_code})")
                        self.audio_ready.emit("", False, "api_error")

                else:
                                               
                                                 
                    sovits_text = re.sub(r'^.*?<\|endofprompt\|>', '', clean_text)
                                                               
                    sovits_text = re.sub(r'\[.*?\]', '', sovits_text).strip()
                    url = llm_brain.config.get("sovits_url", "")
                                                              
                                                                     
                                                   
                                                      
                    params = {
                        "refer_wav_path": llm_brain.config.get("sovits_ref_audio", ""),
                        "prompt_text": llm_brain.config.get("sovits_ref_text", ""),
                        "prompt_language": llm_brain.config.get("sovits_ref_lang", ""),         
                        "text":sovits_text,             
                        "text_language": llm_brain.config.get("sovits_target_lang", "")
                    }

                                                                 
                    response = requests.get(url, params=params, proxies=proxies, timeout=30.0)

                    if response.status_code == 200:
                                              
                        b64_audio = base64.b64encode(response.content).decode('utf-8')
                        self.audio_ready.emit(b64_audio, True, "success")
                    else:
                        print(f"\n🔇 [听觉迷雾]: 她的声音似乎被某种无形的屏障阻挡了...")
                        print(
                            f"   (🛠️ 隐秘线索: API拒绝了请求，状态码 {response.status_code}，原因: {response.text[:100]})")
                        self.audio_ready.emit("", False, "api_error")

            except requests.exceptions.ConnectionError:
                                                  
                print(f"\n🔇 [听觉迷雾]: 周围的环境有些嘈杂，你只能看着她微动的双唇，却听不清声音。")
                print(f"   (🛠️ 隐秘线索: GPT-SoVITS/CosyVoice API未启动或端口错误，已瞬间触发防卡死保护！)")
                self.audio_ready.emit("", False, "connection_error")
            except requests.exceptions.ProxyError:
                print(f"\n🔇 [听觉迷雾]: 一阵莫名的耳鸣让你短暂失聪，无法听清她的话语...")
                print(f"   (🛠️ 隐秘线索: 网络代理干扰了本地连接，尝试关闭代理软件)")
                self.audio_ready.emit("", False, "proxy_error")
            except requests.exceptions.Timeout:
                print(f"\n🔇 [听觉迷雾]: 她似乎在犹豫，声音卡在了喉咙里，过了好一会都没能发出声来...")
                print(
                    f"   (🛠️ 隐秘线索: 处理超过了 30 秒。因为电脑配置较差，显卡可能仍在加载模型，请耐心再跟她聊一句试试)")
                self.audio_ready.emit("", False, "timeout")
            except Exception as e:
                print(f"\n🔇 [听觉迷雾]: 也许是太紧张了，她的声音细若游丝，几乎无法捕捉...")
                print(f"   (🛠️ 隐秘线索: 底层连接失败，错误详情: {str(e)[:150]})")
                self.audio_ready.emit("", False, "unknown_error")

            self.task_queue.task_done()


class RomashaDesktop(QMainWindow):
    def __init__(self):
        super().__init__()

        self.accumulated_text = ""
        self.processed_tags = set()

                              
        self.current_context_html = ""                         
        self.target_display_text = ""                     
        self.current_display_text = ""                      

        self.final_clean_text = ""                  
        self.is_waiting_for_voice = False                  

        self.pending_tags = []                    
        self.is_current_mood_static = False                          

        self.current_idle_motion = motion_manager.get_motion_index('talk')
        self.motion_revert_timer = QTimer(self)
        self.motion_revert_timer.setSingleShot(True)
        self.motion_revert_timer.timeout.connect(self.revert_to_idle_motion)

                                              
        self.typewriter_timer = QTimer(self)
        self.typewriter_timer.timeout.connect(self.typewriter_tick)
        self.typewriter_timer.start(40)

                                    
        self.is_showing_notification = False
        self.notification_timer = QTimer(self)
        self.notification_timer.setSingleShot(True)
        self.notification_timer.timeout.connect(self.restore_bubble_state)

                                
        self.static_mood_timer = QTimer(self)
        self.static_mood_timer.setSingleShot(True)
        self.static_mood_timer.timeout.connect(self.resolve_static_mood)

                           
        self.has_random_taol_fall_triggered = False                     
        self.taol_recover_timer = QTimer(self)
        self.taol_recover_timer.setSingleShot(True)
        self.taol_recover_timer.timeout.connect(self.recover_taol_fall)

                             
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.timeout.connect(self.silently_save_config)

                                                
        self.speech_end_timer = QTimer(self)
        self.speech_end_timer.setSingleShot(True)
        self.speech_end_timer.timeout.connect(self.on_speech_finished)

        self.brain_worker = BrainWorker()
        self.brain_worker.chunk_received.connect(self.handle_stream_chunk)
        self.brain_worker.task_finished.connect(self.on_task_finished)
        self.brain_worker.start()

        self.tts_worker = TTSWorker()
        self.tts_worker.audio_ready.connect(self.play_voice)
        self.tts_worker.start()

                          
        self.is_tracking_enabled = True
        self.is_touch_enabled = True                      

                                        
        self.mouse_timer = QTimer(self)
        self.mouse_timer.timeout.connect(self.track_global_mouse)
                                                 

        self.init_ui()

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

                                      
        screen = QApplication.primaryScreen().geometry()
                                            
        width = int(screen.width())
        height = screen.height() - 1

                
        x = (screen.width() - width) // 2
        y = 0        
        self.setGeometry(x, y, width, height)
                                                               

                                                       
                                
        self.setMask(QRegion(0, 0, 0, 0))

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.browser = QWebEngineView()
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        self.browser.page().setBackgroundColor(Qt.transparent)

        self.browser.titleChanged.connect(self.on_html_signal)

        html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'web', 'index.html'))
        self.browser.load(QUrl.fromLocalFile(html_path))
        layout.addWidget(self.browser)
        self.setCentralWidget(central_widget)

                                       
        self.thought_idle_seconds = 0             
        self.vision_idle_seconds = 0             
        self.vision_sleep_count = 0              
        self.next_idle_trigger_minutes = 3                   
        self.current_idle_target_seconds = 180                  
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self.idle_tick)

                                         
        self.current_time_period = "unknown"

                                     
        self.time_check_timer = QTimer(self)
        self.time_check_timer.timeout.connect(self.check_routine_outfit)
        self.time_check_timer.start(60000)                   

    def silently_save_config(self):
                          
        llm_brain.save_config()
                                           
                                        

    def show_system_notification(self, html_text, duration=1500):
        """显示临时系统通知，并暂停当前的对话气泡"""
        self.is_showing_notification = True
        safe_html = html_text.replace("'", "\\'").replace('"', '\\"')

                                     
        self.browser.page().runJavaScript(f"window.showBubble('{safe_html}', true);")

                                                
        self.notification_timer.start(duration)

    def restore_bubble_state(self):
        """恢复被指令打断的对话气泡"""
        self.is_showing_notification = False

                                        
        if self.is_waiting_for_voice:
            bubble_html = self.current_context_html + "<span style='color:#888; font-size: var(--sub-font-size);'><i>(微启双唇，正在酝酿要说的话...)</i></span>"
            safe_html = bubble_html.replace("'", "\\'")
            self.browser.page().runJavaScript(f"window.showBubble('{safe_html}', true);")

                       
        elif self.current_display_text != self.target_display_text:
                                                 
                                             
            pass

                                      
        else:
                                                      
            safe_text = self.current_display_text.replace("\\", "\\\\").replace("\n", "<br>")
            final_html = self.current_context_html + safe_text
            safe_html = final_html.replace("'", "\\'")
            self.browser.page().runJavaScript(f"window.showBubble('{safe_html}', false);")

    def apply_initial_state(self):
        now = datetime.datetime.now()
        month, day, hour = now.month, now.day, now.hour

                            
        holidays = {
            (1, 1): "元旦", (2, 14): "情人节", (3, 8): "妇女节", (4, 1): "愚人节",
            (5, 1): "劳动节", (5, 4): "青年节", (6, 1): "儿童节", (8, 1): "建军节",
            (9, 10): "教师节", (10, 1): "国庆节", (10, 31): "万圣节", (11, 11): "光棍节",
            (12, 24): "平安夜", (12, 25): "圣诞节", (12, 31): "跨年夜"
        }

        is_holiday = (month, day) in holidays
                                     
        is_cold = month in [10, 11, 12, 1, 2, 3]
        current_intimacy = llm_brain.config.get("intimacy", 0)

                
        if is_holiday:
            holiday_name = holidays[(month, day)]
            print(f"\n🎉 [系统提醒]: 今天是 {holiday_name}！Romasha 换上了节日服装。")
            outfit = "ethnic_cloak" if is_cold else "ethnic_wear"

        elif hour >= 22 or hour <= 6:
                                            
            if current_intimacy >= 60 and random.random() < 0.35:
                print("\n🛁 [系统提醒]: 夜深了，Romasha 似乎刚洗完澡...")
                outfit = "towel"
            else:
                outfit = "sleepwear"
        elif hour >= 19:
            outfit = "uniform_dress"
        else:
            outfit = "uniform_tight"

        params = outfit_manager.get_outfit_params(outfit)
        for param_id, val in params.items():
            self.set_parameter(param_id, val)

    def track_global_mouse(self):
                           
        if self.is_tracking_enabled:
            pos = self.mapFromGlobal(QCursor.pos())
            self.browser.page().runJavaScript(f"window.updateGlobalMouse({pos.x()}, {pos.y()});")

    def reset_afk(self):
                                               
        was_deep_sleeping = (self.vision_idle_seconds >= 300)

                            
        self.thought_idle_seconds = 0
        self.vision_idle_seconds = 0
        self.vision_sleep_count = 0               
        self.next_idle_trigger_minutes = 3
        self.current_idle_target_seconds = 180

                                   
        if self.is_tracking_enabled:
            self.browser.page().runJavaScript("window.toggleTracking(true);")

                    
                                                    
                                                   
        if was_deep_sleeping:
            self.trigger_motion('BaseMotions', self.current_idle_motion)

    def idle_tick(self):
                                                       
        is_generating = (not self.brain_worker.task_queue.empty()) or self.is_waiting_for_voice or getattr(self,
                                                                                                           'is_typing',
                                                                                                           False)

        self.vision_idle_seconds += 1                               
                                 
        if not is_generating:
            self.thought_idle_seconds += 1

                                     
        if self.vision_idle_seconds == 300:
            self.browser.page().runJavaScript("window.toggleTracking(false);")
            self.trigger_motion('BaseMotions', motion_manager.get_motion_index('wait_haji'))

                                
            if self.vision_sleep_count == 0:
                print(f"\n💤 [观察]: 经过一段时间的静默，Romasha收起思绪，沉浸到了自己的世界中。")
            elif self.vision_sleep_count == 1:
                print(f"\n💤 [观察]: 刚才的挪动并没有引起Romasha进一步的注意，她的视线再次移开，继续发呆了。")
            else:
                print(f"\n💤 [观察]: 仿佛已经习惯了这种无声的摆弄，Romasha只是安静地待在新的位置，依然没有看你。")

            self.vision_sleep_count += 1

                                                   
        if self.thought_idle_seconds == self.current_idle_target_seconds:
                          
            current_intimacy = llm_brain.config.get("intimacy", 0)
            if current_intimacy > 90 and outfit_manager._current_outfit == "towel" and not self.has_random_taol_fall_triggered:
                if random.random() < 0.2:
                    self.has_random_taol_fall_triggered = True
                    sys_prompt = "[系统机制：由于长时间的安静，加上你的动作幅度，你身上裹着的浴巾突然意外滑落了！你完全没防备。请立刻输出带有 [act_taol_fall] 标签的动作反应，并伴随一句极其慌乱、娇羞的惊呼或心声。]"
                    self.start_new_thought(sys_prompt)

                                             
                    self.next_idle_trigger_minutes += random.randint(3, 10)
                    self.current_idle_target_seconds = self.thought_idle_seconds + (self.next_idle_trigger_minutes * 60)
                    return

            self.trigger_idle_thought(minutes=self.thought_idle_seconds // 60)

                      
            self.next_idle_trigger_minutes += random.randint(3, 10)

                           
            self.current_idle_target_seconds = self.thought_idle_seconds + (self.next_idle_trigger_minutes * 60)

    def trigger_idle_thought(self, minutes):
        if minutes == 3:
                                      
            sys_prompt = "[系统机制：他已经离开你的身边整整 3 分钟了。请根据你此时的心情，输出一小段自言自语或内心独白（使用括号表示心声）。你可以维持刚才互动时的情绪余温，也可以改变动作。注意：你现在处于独处状态，请做自己的事，绝对不要试图对他搭话。]"
        else:
                                          
            sys_prompt = f"[系统机制：他离开已经有 {minutes} 分钟了，你的视线早已从他原本所在的位置移开，不再看他。此时你可以选择让情绪渐渐平复（切换回talk），或者继续沉浸在自己的世界里小声嘀咕、发呆。请给出一小段心声或自言自语。注意：维持独处状态，不要对他搭话。]"

                                 
        self.current_context_html = f"<span style='color:#ccc;'><i>(漫长的安静中，Romasha 似乎在想些什么...)</i></span><br>"
        bubble_html = self.current_context_html + "<span style='color:#888; font-size: var(--sub-font-size);'><i>(独处思考中...)</i></span>"
        safe_html = bubble_html.replace("'", "\\'")
        self.browser.page().runJavaScript(f"window.showBubble('{safe_html}');")

        self.start_new_thought(sys_prompt)

    def resolve_static_mood(self):
                                             
        if self.vision_idle_seconds < 300:
                                            
            sys_prompt = "[系统机制：你刚才已经维持静止发呆或小声嘀咕 15 秒了。请根据你此刻的情绪，决定切换回正常的动态常态动作（如 mood_talk, mood_talk_alc 等）。你可以小声嘟囔一句话、说一两句心声，也可以什么都不说只输出动作标签。]"

            self.current_context_html = f"<span style='color:#ccc;'><i>(短暂的定格后，她似乎有了动作...)</i></span><br>"
            bubble_html = self.current_context_html + "<span style='color:#888; font-size: var(--sub-font-size);'><i>(调整状态...)</i></span>"
            safe_html = bubble_html.replace("'", "\\'")
            self.browser.page().runJavaScript(f"window.showBubble('{safe_html}');")

            self.start_new_thought(sys_prompt)

    def revert_to_idle_motion(self):
        self.set_parameter('ParamCheek', 0.0)
        self.set_parameter('angry', 0.0)
        self.trigger_motion('BaseMotions', self.current_idle_motion)

    def check_routine_outfit(self):
        now = datetime.datetime.now()
        month, day, hour = now.month, now.day, now.hour

        holidays = {
            (1, 1): "元旦", (2, 14): "情人节", (3, 8): "妇女节", (4, 1): "愚人节",
            (5, 1): "劳动节", (5, 4): "青年节", (6, 1): "儿童节", (8, 1): "建军节",
            (9, 10): "教师节", (10, 1): "国庆节", (10, 31): "万圣节", (11, 11): "光棍节",
            (12, 24): "平安夜", (12, 25): "圣诞节", (12, 31): "跨年夜"
        }

        is_holiday = (month, day) in holidays
        is_cold = month in [10, 11, 12, 1, 2, 3]
        current_intimacy = llm_brain.config.get("intimacy", 0)

        target_outfit = None
        new_time_period = "day"         

                             
        if is_holiday:
            new_time_period = f"holiday_{month}_{day}"
            target_outfit = "ethnic_cloak" if is_cold else "ethnic_wear"
        elif hour >= 22 or hour <= 6:
                                           
                                         
            if outfit_manager._current_outfit not in ["sleepwear", "towel"]:
                if current_intimacy >= 60 and random.random() < 0.35:
                    target_outfit = "towel"
                    print("\n🛁 [时光流转]: 夜深了，Romasha似乎去洗了个澡...")
                else:
                    target_outfit = "sleepwear"
            else:
                                   
                target_outfit = outfit_manager._current_outfit
        elif hour >= 19:
            new_time_period = "evening"
            target_outfit = "uniform_dress"
        else:
            new_time_period = "day"
            target_outfit = "uniform_tight"

                                               
        if getattr(self, 'current_time_period', "unknown") == "unknown":
            self.current_time_period = new_time_period
            return

                                                              
                                                                      
        if new_time_period != self.current_time_period:
            self.current_time_period = new_time_period

                               
            if target_outfit and target_outfit != outfit_manager._current_outfit:
                if target_outfit == "towel":
                    print(f"\n👗 [观察]: 夜深了，听到浴室传来隐约的水声后，Romasha裹着浴巾走了出来。")
                elif target_outfit == "sleepwear":
                    print(f"\n👗 [观察]: 留意到时间的推移，Romasha默默换上了轻薄的睡衣。")
                else:
                    print(f"\n👗 [观察]: 留意到时间的推移，Romasha默默换了一身适合现在的衣服。")

                               
            bubble_html = "<span style='color:#ccc;'><i>(一阵轻微的窸窣声后，她换好了一身衣服...)</i></span><br>"
            self.browser.page().runJavaScript(f"window.showBubble(\"{bubble_html}\");")

                                                     
            QTimer.singleShot(3000, lambda: self._apply_delayed_outfit(target_outfit))

                         
                                                                     
                                                 
                                                  

                       
    def _apply_delayed_outfit(self, target_outfit):
        params = outfit_manager.get_outfit_params(target_outfit)
        for param_id, val in params.items():
            self.set_parameter(param_id, val)

    def on_html_signal(self, title):
        if title == "EVENT:READY":
            self.apply_initial_state()

            try:
                                              
                                 
                scale = float(llm_brain.config.get("scale", 0.25))
                x = float(llm_brain.config.get("pos_x", -1))
                y = float(llm_brain.config.get("pos_y", 100))

                           
                self.is_tracking_enabled = bool(llm_brain.config.get("track_enabled", True))
                self.is_touch_enabled = bool(llm_brain.config.get("touch_enabled", True))

                track_str = "true" if self.is_tracking_enabled else "false"
                touch_str = "true" if self.is_touch_enabled else "false"

                                  
                init_js = f"window.applySavedState({scale}, {x}, {y}, {track_str}, {touch_str});"
                self.browser.page().runJavaScript(init_js)

                                  
                bubble_size = llm_brain.config.get("bubble_size", 1)
                self.browser.page().runJavaScript(f"window.setBubbleSize({bubble_size});")

            except Exception as e:
                print(f"状态恢复异常: {e}")

                                               
            self.mouse_timer.start(50)
            self.idle_timer.start(1000)
            return

                            
        if title == "EVENT:AUDIO_END":
            self.on_speech_finished()
            return

                                  
        if title.startswith("MASK:"):
            rects_data = title.split(":", 1)[1]
            region = QRegion()
            if rects_data:
                                 
                for rect_str in rects_data.split('|'):
                    try:
                        x, y, w, h = map(float, rect_str.split(','))
                                         
                        region = region.united(QRegion(QRect(int(x), int(y), int(w), int(h))))
                    except Exception:
                        pass
                self.setMask(region)
            else:
                                                                
                                               
                                      
                self.setMask(QRegion(0, 0, 0, 0))
            return

                               
        if title.startswith("DRAG_STATE:") or title.startswith("WHEEL_STATE:"):
            try:
                parts = title.split(":")
                              
                llm_brain.config["scale"] = float(parts[1])
                llm_brain.config["pos_x"] = float(parts[2])
                llm_brain.config["pos_y"] = float(parts[3])
                                            
                                                  
                self.auto_save_timer.start(1500)
            except Exception as e:
                pass                

                                       
            if title.startswith("DRAG_STATE:"):
                self.vision_idle_seconds = 0
                if self.is_tracking_enabled:
                    self.browser.page().runJavaScript("window.toggleTracking(true);")
            return

        if title.startswith("CHAT:"):
            user_text = title.split(":", 1)[1]
            self.reset_afk()

            if user_text.strip() == '/reset':
                reply = QMessageBox.warning(
                    self, '「不可逆的抉择：世界线重置」',
                    "真的要让她忘记这一切吗？\n你们将回到最初始的陌生人状态。",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                                   
                    self.brain_worker.task_queue.put(("/SYSTEM_RESET_MEMORY", ""))

                            
                    self.current_context_html = ""
                    self.current_display_text = ""
                    self.target_display_text = ""

                    self.show_system_notification("<span style='color:#888; font-size: var(--sub-font-size);'><i>(记忆已被重置，迎来了崭新的初见...)</i></span>", 3000)

                                                                
                                          
                                                                
                                            
                    self.set_parameter('ParamCheek', 0.0)
                    self.set_parameter('angry', 0.0)

                                                                          
                    idx = motion_manager.get_motion_index('talk')
                    if idx is not None:
                        self.current_idle_motion = idx
                        self.trigger_motion('BaseMotions', idx)

                                                       
                                                            
                    llm_brain.config["intimacy"] = 0
                    self.apply_initial_state()

                return

            if user_text.startswith('/track '):
                state_val = user_text.split(' ')[1]
                state_bool = state_val != "0"
                                 
                self.is_tracking_enabled = state_bool
                state_str = "false" if not state_bool else "true"
                self.browser.page().runJavaScript(f"window.toggleTracking({state_str});")

                                      
                llm_brain.config["track_enabled"] = state_bool
                llm_brain.save_config()

                         
                action_desc = "重新锁定了你的身影" if state_bool else "不再追随你的动作"
                print(f"\n👁️ [空间感知]: Romasha的视线{action_desc}。")

                         
                bubble_desc = "她似乎注意到了你在这边..." if state_bool else "她移开了视线，不再关注你的举动..."
                bubble_html = f"<span style='color:#888; font-size: var(--sub-font-size);'><i>({bubble_desc})</i></span>"
                self.show_system_notification(bubble_html, 1500)                   
                return

                                     
            if user_text.startswith('/touch '):
                state_val = user_text.split(' ')[1]
                state_bool = state_val != "0"
                self.is_touch_enabled = state_bool
                state_str = "false" if not state_bool else "true"
                self.browser.page().runJavaScript(f"window.toggleTouch({state_str});")

                                      
                llm_brain.config["touch_enabled"] = state_bool
                llm_brain.save_config()

                         
                action_desc = "仿佛重新建立起了真实的触感，能感受到彼此的温度" if state_bool else "之间仿佛隔了一层不可触及的空气墙"
                print(f"\n👆 [无声羁绊]: 你们{action_desc}。")

                         
                bubble_desc = "她似乎能真切感受到你的存在..." if state_bool else "触碰的感知似乎被隔绝了..."
                bubble_html = f"<span style='color:#888; font-size: var(--sub-font-size);'><i>({bubble_desc})</i></span>"
                self.show_system_notification(bubble_html, 1500)                   
                return

                                     
            if user_text.startswith('/voice '):
                val = user_text.split(' ')[1].strip().lower()

                if val in ["0", "1"]:
                    state_bool = val == "1"
                    llm_brain.config["voice_enabled"] = state_bool
                    llm_brain.save_config()

                                 
                    if state_bool:
                        print(f"\n💭 [感官羁绊]: 周围安静了下来，你终于又能听见她清晰的声音了。")
                        bubble_desc = "你靠近了一些，试着倾听她的声音..."
                    else:
                        print(f"\n💭 [感官羁绊]: 环境变得嘈杂，你只能通过她的眼神和口型来理解她。")
                        bubble_desc = "周围有些吵闹，你默默注视着她..."

                elif val in ["cosyvoice", "sovits"]:
                    llm_brain.config["tts_engine"] = val
                    llm_brain.config["voice_enabled"] = True               
                    llm_brain.save_config()
                    print(f"\n💭 [灵魂调律]: 冥冥之中，她发声的方式与声线中蕴含的温度，似乎发生了极其微妙的改变。")
                    bubble_desc = f"一阵轻微的恍惚后，她的声音听起来似乎有些不同了：{val}..."
                else:
                    return          

                bubble_html = f"<span style='color:#888; font-size: var(--sub-font-size);'><i>({bubble_desc})</i></span>"
                self.show_system_notification(bubble_html, 1500)                   
                return

                                  
            if user_text.startswith('/size '):
                try:
                    size_val = int(user_text.split(' ')[1].strip())
                    if size_val in [0, 1, 2]:
                        llm_brain.config["bubble_size"] = size_val
                        llm_brain.save_config()
                        self.browser.page().runJavaScript(f"window.setBubbleSize({size_val});")
                        size_desc = ['稍微拉远', '恰到好处', '更加贴近'][size_val]
                        print(f"\n📏 [认知焦距]: 伴随着你注意力的集中，眼前的思绪与话语变得{size_desc}了。")

                        bubble_html = f"<span style='color:#888; font-size: var(--sub-font-size);'><i>(视界已调整为适宜的大小...)</i></span>"
                        self.show_system_notification(bubble_html, 1500)                   
                except Exception:
                    pass
                return

                                    
            if user_text.startswith('/ja '):
                val = user_text.split(' ')[1].strip()
                if val in ["0", "1"]:
                    state_bool = val == "1"
                    llm_brain.config["tts_translate_to_ja"] = state_bool
                    llm_brain.save_config()

                                
                    if state_bool:
                        print(f"\n🌐 [语言中枢]: 她的发声回路切换为了古老的异国语调 (日语翻译已开启)。")
                        bubble_desc = "她的口型似乎在尝试一种古老而优雅的发音..."
                    else:
                        print(f"\n🌐 [语言中枢]: 她的发声回路恢复了你所熟悉的语言 (日语翻译已关闭)。")
                        bubble_desc = "她的语调恢复了正常的频率..."

                    bubble_html = f"<span style='color:#888; font-size: var(--sub-font-size);'><i>({bubble_desc})</i></span>"
                    self.show_system_notification(bubble_html, 1500)                   
                return

                                     
                       
            self.current_context_html = f"<span style='color:#48a1fa;'>你: {user_text}</span><br>"
            bubble_html = self.current_context_html + "<span style='color:#888; font-size: var(--sub-font-size);'><i>(她倾听着你的话语...)</i></span>"
            safe_html = bubble_html.replace("'", "\\'")
                          
            self.browser.page().runJavaScript(f"window.showBubble('{safe_html}', true);")

                            
            self.start_new_thought(user_text)
            return

        if title.startswith("TOUCH:"):
            part = title.split(":")[1]
            self.reset_afk()

            touch_prompts = {
                "head": "*你温柔地摸了摸她的头*",
                "face": "*你轻轻戳了戳她的脸颊*",
                "bust": "*你不小心碰到了她的胸部*",
                "belly": "*你搂住了她的腰*",
                "hip": "*你不小心碰到了她的臀部*",         
                "crotch": "*你不小心碰到了她的隐私部位*",          
                "leg": "*你碰到了她的腿*",
                "hand_right": "*你牵起了她的右手*",          
                "hand_left": "*你握住了她的左手*",          
                "unknown": "*你轻轻碰了碰她*"
            }
            action_text = touch_prompts.get(part, "*你触碰了她*")

                                         
            self.current_context_html = f"<span style='color:#fd92a1;'>{action_text}</span><br>"
            bubble_html = self.current_context_html + "<span style='color:#888; font-size: var(--sub-font-size);'><i>(感受中...)</i></span>"
            safe_html = bubble_html.replace("'", "\\'")
                          
            self.browser.page().runJavaScript(f"window.showBubble('{safe_html}', true);")

            self.start_new_thought(action_text)

    def start_new_thought(self, prompt_text):
                                               
                                 
        self.static_mood_timer.stop()
        self.speech_end_timer.stop()                               
                              
        if prompt_text.startswith("[系统机制"):
            print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] 🍃 [时光流逝]: {prompt_text[6:19]}...")
        else:
            print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] 👤 你: {prompt_text}")

        interrupted_text = ""
        if self.accumulated_text:
            print("💬 [观察]: 她的话音戛然而止，注意力瞬间被你刚才的举动吸引。")
            clean_accumulated = re.sub(r'\[.*?\]', '', self.accumulated_text).strip()
            if len(clean_accumulated) > 2:
                interrupted_text = clean_accumulated

                          
        self.accumulated_text = ""
        self.target_display_text = ""
        self.current_display_text = ""
        self.processed_tags.clear()
        self.pending_tags.clear()              
        self.is_waiting_for_voice = llm_brain.config.get("voice_enabled", True)

                             
        self.browser.page().runJavaScript(
            "if(typeof window.stopRomashaVoice === 'function') window.stopRomashaVoice();")
        self.brain_worker.interrupt_and_submit(prompt_text, interrupted_text)

    def recover_taol_fall(self):
                                      
        sys_prompt = "[系统机制：距离刚才浴巾意外滑落已经过去了整整10秒。你现在急忙蹲下重新捡起并紧紧裹好了浴巾。请必须输出 [wear_towel] 标签，并伴随极其娇羞、甚至带有哭腔或羞愤的动作（如 [mood_talk_ero]）与慌乱的话语/心声。]"

                      
        self.current_context_html = "<span style='color:#fd92a1;'><i>(短暂的慌乱后，她急急忙忙重新裹好了浴巾...)</i></span><br>"
        bubble_html = self.current_context_html + "<span style='color:#888; font-size: var(--sub-font-size);'><i>(满脸通红手忙脚乱中...)</i></span>"
        safe_html = bubble_html.replace("'", "\\'")
        self.browser.page().runJavaScript(f"window.showBubble('{safe_html}');")

                                 
        self.start_new_thought(sys_prompt)

    def on_task_finished(self):
                                        
        if self.accumulated_text.strip():
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 🌸 Romasha: {self.accumulated_text}")
                                      
            if self.is_waiting_for_voice:
                                             
                self.tts_worker.task_queue.put(self.accumulated_text)
            else:
                                     
                self.target_display_text = self.final_clean_text
                self.flush_pending_tags()

                                                        
                duration_ms = max(4000, len(self.final_clean_text) * 250)
                                                                        
                                          
                self.speech_end_timer.start(duration_ms)

        self.accumulated_text = ""

                                              
    def handle_stream_chunk(self, chunk):
        self.accumulated_text += chunk

        tags = re.findall(r'\[(.*?)\]', self.accumulated_text)
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower not in self.processed_tags:
                self.processed_tags.add(tag_lower)
                                                     
                if tag_lower.startswith('intimacy_'):
                    self.execute_tag(tag_lower)
                                                      
                                                            
                elif tag_lower.startswith(('act_', 'mood_', 'wear_', 'hair_')):
                    self.pending_tags.append(tag_lower)                       

                                  
                                               
        clean_text = re.sub(r'\[.*?\]', '', self.accumulated_text)
                                                           
                                                                    
        clean_text = re.sub(r'^.*?<\|endofprompt\|>', '', clean_text)
        self.final_clean_text = re.sub(r'\[[^\]]*$', '', clean_text).strip()

                                              
        if self.is_waiting_for_voice:
                     
            bubble_html = self.current_context_html + "<span style='color:#888; font-size: var(--sub-font-size);'><i>(微启双唇，正在酝酿要说的话...)</i></span>"
            safe_html = bubble_html.replace("'", "\\'")
            self.browser.page().runJavaScript(f"window.showBubble('{safe_html}', true);")
        else:
            self.target_display_text = self.final_clean_text

                                  
    def typewriter_tick(self):
                                         
        if getattr(self, 'is_showing_notification', False):
            return

                            
        if self.current_display_text != self.target_display_text:
            self.is_typing = True
                                 
            if not self.target_display_text.startswith(self.current_display_text):
                self.current_display_text = self.target_display_text
            else:
                                            
                next_char_index = len(self.current_display_text)
                if next_char_index < len(self.target_display_text):
                    self.current_display_text += self.target_display_text[next_char_index]

                                      
            safe_text = self.current_display_text.replace("\\", "\\\\").replace("\n", "<br>")
            final_html = self.current_context_html + safe_text
            safe_html = final_html.replace("'", "\\'")

                                                     
            self.browser.page().runJavaScript(f"window.showBubble('{safe_html}', true);")

        else:
                                  
                                      
            if getattr(self, 'is_typing', False):
                self.is_typing = False
                safe_text = self.current_display_text.replace("\\", "\\\\").replace("\n", "<br>")
                final_html = self.current_context_html + safe_text
                safe_html = final_html.replace("'", "\\'")
                                     
                self.browser.page().runJavaScript(f"window.showBubble('{safe_html}', false);")

                                 
    def execute_tag(self, tag):
                          
        if tag.startswith('intimacy_'):
            try:
                                                
                val_str = tag.split('_', 1)[1]
                change_val = int(val_str)
                current_int = llm_brain.config.get("intimacy", 0)
                                      
                new_int = max(-100, min(100, current_int + change_val))

                llm_brain.config["intimacy"] = new_int
                llm_brain.save_config()

                                  
                symbol = "+" if change_val >= 0 else ""
                print(f"💖 [关系动态]: 亲密度 {symbol}{change_val} (当前: {new_int}/100)")

                color = "#ffb6c1" if change_val >= 0 else "#a8d8ea"
                                                                 
                                            
                intimacy_html = f"<span style='color:{color}; font-size: var(--sub-font-size);'><i>[亲密度 {symbol}{change_val}]</i></span><br>"
                self.current_context_html += intimacy_html
            except Exception as e:
                pass

                    
        if tag.startswith('hair_'):
            hair_style = tag.split('_', 1)[1]
            try:
                                      
                params = outfit_manager.get_outfit_params(outfit_manager._current_outfit, hair_style)
                for param_id, val in params.items():
                    self.set_parameter(param_id, val)
            except Exception as e:
                pass

        elif tag.startswith('wear_'):
            outfit_name = tag.split('_', 1)[1]
            try:
                params = outfit_manager.get_outfit_params(outfit_name)
                for param_id, val in params.items():
                    self.set_parameter(param_id, val)
            except Exception as e:
                pass


        elif tag.startswith('mood_'):
            mood_name = tag.split('_', 1)[1]
                                                   
                                                    
                                       
            try:
                idx = motion_manager.get_motion_index(mood_name)
                if idx is not None:
                    self.current_idle_motion = idx
                    self.trigger_motion('BaseMotions', idx)
                                         
                    if mood_name in ['neutral', 'wait', 'wait_haji']:
                        self.is_current_mood_static = True
                    else:
                        self.is_current_mood_static = False
                                                                 
            except Exception as e:
                pass


        elif tag.startswith('act_'):
            action_name = tag.split('_', 1)[1]
                           
            if action_name == 'taol_fall':
                print("\n💦 [突发状况]: 浴巾好像松开了！她慌乱地试图遮掩...")
                self.taol_recover_timer.start(8000)                   
            try:
                idx = motion_manager.get_motion_index(action_name)
                if idx is not None:
                    self.trigger_motion('BaseMotions', idx)
                                                                  
            except Exception as e:
                pass

    def flush_pending_tags(self):
        """一次性释放所有积攒的动作标签（在声音响起的瞬间调用）"""
        for tag in self.pending_tags:
            self.execute_tag(tag)
        self.pending_tags.clear()

                                    
                                          
                              
                                                           
                                               

    def on_speech_finished(self):
        """精准回调：音频彻底播放结束（或字幕打完）时触发"""
                         
        self.revert_to_idle_motion()

                                    
                                      
        if getattr(self, 'is_current_mood_static', False):
                                                       
            delay_ms = 5000 if llm_brain.config.get("voice_enabled", True) else 8000
            self.static_mood_timer.start(delay_ms)

    def trigger_motion(self, group, index):
        self.browser.page().runJavaScript(f"window.playRomashaMotion('{group}', {index});")

    def set_parameter(self, param_id, value):
        self.browser.page().runJavaScript(f"window.setRomashaParam('{param_id}', {value});")

    def closeEvent(self, event):
        self.brain_worker.running = False
        self.brain_worker.wait()

                                                    
        llm_brain.save_config()
        print("\n💾 [羁绊铭记]: 你们之间的距离与视角，已默默留存在了记忆中，期待下次相遇。")

        event.accept()

    def play_voice(self, b64_audio, success, status=""):
        self.is_waiting_for_voice = False         

                                           
        self.flush_pending_tags()

        if success:
            if b64_audio:
                                                                
                self.browser.page().runJavaScript(f"window.playRomashaVoice('{b64_audio}');")
            else:
                                    
                                                         
                self.speech_end_timer.start(2000)
        else:
                      
            if status == "connection_error":
                                          
                llm_brain.config["voice_enabled"] = False
                llm_brain.save_config()

                print("\n💭 [感官适应]: 你决定不再强求听清每一个字，而是专心注视着她。(若想再次尝试倾听，可对她输入 /voice 1)")
                bubble_html = self.current_context_html + "<span style='color:#e74c3c; font-size: var(--sub-font-size);'><i>(环境有些喧嚣，你注视着她微动的双唇，读懂了她的话语...)</i></span><br>"
            else:
                                  
                bubble_html = self.current_context_html + "<span style='color:#888; font-size: var(--sub-font-size);'><i>(你努力分辨着她微弱的声音...)</i></span><br>"

            safe_html = bubble_html.replace("'", "\\'")
            self.browser.page().runJavaScript(f"window.showBubble('{safe_html}');")
                             
            duration_ms = max(4000, len(self.final_clean_text) * 250)
            self.speech_end_timer.start(duration_ms)

                                                 
        self.target_display_text = self.final_clean_text


if __name__ == '__main__':
                            
    print("\n" + "=" * 50)

                                   
    now_hour = datetime.datetime.now().hour
    if 5 <= now_hour < 12:
        time_tag, time_desc = "晨光微露", "清晨的微光中"
    elif 12 <= now_hour < 18:
        time_tag, time_desc = "午后静谧", "温暖的午后"
    elif 18 <= now_hour < 23:
        time_tag, time_desc = "夜色温柔", "夜幕降临"
    else:
        time_tag, time_desc = "夜半幽静", "深夜的寂静中"

    print(f"🌸 [{time_tag}] {time_desc}，正在等待她慢慢回过神来...")
    print("   (她似乎有些迷糊，需要几秒的时间才能完全清醒，请耐心等待)")

    try:
                             
                                                         
        memory_manager.retrieve_relevant_memories("初次相遇的预热")
        print(f"✨ [{time_tag}] 她慢慢睁开了眼睛，你看到了她的身影。")
    except Exception as e:
        print(f"⚠️ [{time_tag}] 刚醒来似乎有些头晕，但并不影响你们的相遇: {e}")

    print("=" * 50 + "\n")

    app = QApplication(sys.argv)
    romasha = RomashaDesktop()
    romasha.show()
    sys.exit(app.exec_())