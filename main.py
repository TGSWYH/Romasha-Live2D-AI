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
'''


import memory_manager
import sys
import os
import re
import datetime
import random
import queue
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
                    print("💔 [世界线变动]: 亲密度已重置为0。一切回到了原点。\n")

                except Exception as e:
                    print(f"内存重置异常: {e}")
                self.task_queue.task_done()
                continue

            self.is_cancelled = False
            try:
                llm_brain.stream_chat_with_romasha(user_text, interrupted_text, self)
            except Exception as e:
                print(f"⚠️ 思考线程内部错误: {e}")

            if not self.is_cancelled:
                self.task_finished.emit()

            self.task_queue.task_done()

    def interrupt_and_submit(self, user_text, interrupted_text):
        self.is_cancelled = True
        with self.task_queue.mutex:
            self.task_queue.queue.clear()
        self.task_queue.put((user_text, interrupted_text))


class RomashaDesktop(QMainWindow):
    def __init__(self):
        super().__init__()

        self.accumulated_text = ""
        self.processed_tags = set()

        self.current_context_html = ""
        self.target_display_text = ""
        self.current_display_text = ""

        self.current_idle_motion = motion_manager.get_motion_index('talk')
        self.motion_revert_timer = QTimer(self)
        self.motion_revert_timer.setSingleShot(True)
        self.motion_revert_timer.timeout.connect(self.revert_to_idle_motion)

        self.typewriter_timer = QTimer(self)
        self.typewriter_timer.timeout.connect(self.typewriter_tick)
        self.typewriter_timer.start(40)

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

        self.brain_worker = BrainWorker()
        self.brain_worker.chunk_received.connect(self.handle_stream_chunk)
        self.brain_worker.task_finished.connect(self.on_task_finished)
        self.brain_worker.start()

        self.is_tracking_enabled = True
        self.is_touch_enabled = True

        self.mouse_timer = QTimer(self)
        self.mouse_timer.timeout.connect(self.track_global_mouse)
        #self.mouse_timer.start(50)

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
        # self.setGeometry(100, 100, 400, 1000)

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

        self.time_check_timer = QTimer(self)
        self.time_check_timer.timeout.connect(self.check_routine_outfit)
        self.time_check_timer.start(60000)

    def silently_save_config(self):
        llm_brain.save_config()
        # print("💾 [后台守护]: 缩放与位置已自动存档。")

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
        self.thought_idle_seconds = 0
        self.vision_idle_seconds = 0
        self.vision_sleep_count = 0
        self.next_idle_trigger_minutes = 3
        self.current_idle_target_seconds = 180

        if self.is_tracking_enabled:
            self.browser.page().runJavaScript("window.toggleTracking(true);")
        self.trigger_motion('BaseMotions', self.current_idle_motion)

    def idle_tick(self):
        self.thought_idle_seconds += 1
        self.vision_idle_seconds += 1

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
        bubble_html = self.current_context_html + "<span style='color:#888; font-size:12px;'><i>(独处思考中...)</i></span>"
        safe_html = bubble_html.replace("'", "\\'")
        self.browser.page().runJavaScript(f"window.showBubble('{safe_html}');")

        self.start_new_thought(sys_prompt)

    def resolve_static_mood(self):
        if self.vision_idle_seconds < 300:
            sys_prompt = "[系统机制：你刚才已经维持静止发呆或小声嘀咕 15 秒了。请根据你此刻的情绪，决定切换回正常的动态常态动作（如 mood_talk, mood_talk_alc 等）。你可以小声嘟囔一句话、说一两句心声，也可以什么都不说只输出动作标签。]"

            self.current_context_html = f"<span style='color:#ccc;'><i>(短暂的定格后，她似乎有了动作...)</i></span><br>"
            bubble_html = self.current_context_html + "<span style='color:#888; font-size:12px;'><i>(调整状态...)</i></span>"
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

        if is_holiday:
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
            target_outfit = "uniform_dress"
        else:
            target_outfit = "uniform_tight"

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

            params = outfit_manager.get_outfit_params(target_outfit)
            for param_id, val in params.items():
                self.set_parameter(param_id, val)

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
            except Exception as e:
                print(f"状态恢复异常: {e}")

            self.mouse_timer.start(50)
            self.idle_timer.start(1000)
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
                    self.browser.page().runJavaScript("window.showBubble('<i>(记忆已被重置，迎来了崭新的初见...)</i>');")

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
                bubble_html = f"<span style='color:#888; font-size:12px;'><i>({bubble_desc})</i></span>"
                self.browser.page().runJavaScript(f"window.showBubble(\"{bubble_html}\");")
                return

            if user_text.startswith('/touch '):
                state_val = user_text.split(' ')[1]
                state_bool = state_val != "0"
                self.is_touch_enabled = state_bool
                state_str = "false" if not state_bool else "true"
                self.browser.page().runJavaScript(f"window.toggleTouch({state_str});")

                llm_brain.config["touch_enabled"] = state_bool
                llm_brain.save_config()

                action_desc = "解除了物理屏障，能真切感受到你的温度" if state_bool else "展开了隔绝的屏障，如同隔着一层不可触及的玻璃"
                print(f"\n👆 [无声羁绊]: 你们之间{action_desc}。")

                bubble_desc = "实体触碰感应已恢复..." if state_bool else "实体触碰屏障已屏蔽..."
                bubble_html = f"<span style='color:#888; font-size:12px;'><i>({bubble_desc})</i></span>"
                self.browser.page().runJavaScript(f"window.showBubble(\"{bubble_html}\");")
                return

            self.current_context_html = f"<span style='color:#48a1fa;'>你: {user_text}</span><br>"
            bubble_html = self.current_context_html + "<span style='color:#888; font-size:12px;'><i>(思考中...)</i></span>"
            safe_html = bubble_html.replace("'", "\\'")
            self.browser.page().runJavaScript(f"window.showBubble('{safe_html}');")

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
            bubble_html = self.current_context_html + "<span style='color:#888; font-size:12px;'><i>(感受中...)</i></span>"
            safe_html = bubble_html.replace("'", "\\'")
            self.browser.page().runJavaScript(f"window.showBubble('{safe_html}');")

            self.start_new_thought(action_text)

    def start_new_thought(self, prompt_text):
        self.static_mood_timer.stop()
        if prompt_text.startswith("[系统机制"):
            print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] 🍃 [时光流逝]: {prompt_text[6:18]}...")
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
        self.brain_worker.interrupt_and_submit(prompt_text, interrupted_text)

    def recover_taol_fall(self):
        sys_prompt = "[系统机制：距离刚才浴巾意外滑落已经过去了整整10秒。你现在急忙蹲下重新捡起并紧紧裹好了浴巾。请必须输出 [wear_towel] 标签，并伴随极其娇羞、甚至带有哭腔或羞愤的动作（如 [mood_talk_ero]）与慌乱的话语/心声。]"

        self.current_context_html = "<span style='color:#fd92a1;'><i>(短暂的慌乱后，她急急忙忙重新裹好了浴巾...)</i></span><br>"
        bubble_html = self.current_context_html + "<span style='color:#888; font-size:12px;'><i>(满脸通红手忙脚乱中...)</i></span>"
        safe_html = bubble_html.replace("'", "\\'")
        self.browser.page().runJavaScript(f"window.showBubble('{safe_html}');")

        self.start_new_thought(sys_prompt)

    def on_task_finished(self):
        if self.accumulated_text.strip():
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 🌸 Romasha: {self.accumulated_text}")

        self.accumulated_text = ""

    def handle_stream_chunk(self, chunk):
        self.accumulated_text += chunk

        tags = re.findall(r'\[(.*?)\]', self.accumulated_text)
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower not in self.processed_tags:
                self.processed_tags.add(tag_lower)
                self.execute_tag(tag_lower)

        clean_text = re.sub(r'\[.*?\]', '', self.accumulated_text)
        self.target_display_text = re.sub(r'\[[^\]]*$', '', clean_text).strip()

    def typewriter_tick(self):
        if self.current_display_text != self.target_display_text:
            if not self.target_display_text.startswith(self.current_display_text):
                self.current_display_text = self.target_display_text
            else:
                next_char_index = len(self.current_display_text)
                if next_char_index < len(self.target_display_text):
                    self.current_display_text += self.target_display_text[next_char_index]

            safe_text = self.current_display_text.replace("\\", "\\\\").replace("\n", "<br>")
            final_html = self.current_context_html + safe_text
            safe_html = final_html.replace("'", "\\'")

            self.browser.page().runJavaScript(f"window.showBubble('{safe_html}');")

    def execute_tag(self, tag):
        if tag.startswith('intimacy_'):
            try:
                val_str = tag.split('_', 1)[1]
                change_val = int(val_str)
                current_int = llm_brain.config.get("intimacy", 0)
                new_int = max(-100, min(100, current_int + change_val))

                llm_brain.config["intimacy"] = new_int
                llm_brain.save_config()

                symbol = "+" if change_val > 0 else ""
                print(f"💖 [关系动态]: 亲密度 {symbol}{change_val} (当前总计: {new_int}/100)")

                color = "#ffb6c1" if change_val > 0 else "#a8d8ea"
                bubble_html = f"<span style='color:{color}; font-size:12px;'><i>[亲密度 {symbol}{change_val}]</i></span><br>"
                self.browser.page().runJavaScript(f"window.showBubble(\"{bubble_html}\");")
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
            # if mood_name in ['wait', 'wait_haji']:
            #     mood_name = 'neutral'
            try:
                idx = motion_manager.get_motion_index(mood_name)
                if idx is not None:
                    self.current_idle_motion = idx
                    if not self.motion_revert_timer.isActive():
                        self.trigger_motion('BaseMotions', idx)
                    if mood_name in ['neutral', 'wait', 'wait_haji']:
                        self.static_mood_timer.start(15000)  # 15秒后触发破冰
                    else:
                        self.static_mood_timer.stop()
            except Exception as e:
                pass


        elif tag.startswith('act_'):
            action_name = tag.split('_', 1)[1]
            if action_name == 'taol_fall':
                print("\n💦 [物理引擎]: 浴巾意外滑落！启动 10 秒重新穿戴倒计时...")
                self.taol_recover_timer.start(10000)  # 10000 毫秒 = 10 秒
            try:
                idx = motion_manager.get_motion_index(action_name)
                if idx is not None:
                    self.trigger_motion('BaseMotions', idx)
                    self.motion_revert_timer.start(4500)
            except Exception as e:
                pass

    def trigger_motion(self, group, index):
        self.browser.page().runJavaScript(f"window.playRomashaMotion('{group}', {index});")

    def set_parameter(self, param_id, value):
        self.browser.page().runJavaScript(f"window.setRomashaParam('{param_id}', {value});")

    def closeEvent(self, event):
        self.brain_worker.running = False
        self.brain_worker.wait()

        llm_brain.save_config()
        print("\n💾 [系统]: 物理坐标与缩放状态已归档。")

        event.accept()


if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("🧠 [系统启动中] 正在唤醒 Romasha 的海马体记忆中枢...")
    print("   (正在加载底层数据库与嵌入模型，这可能需要十几秒，请耐心等待)")

    try:
        memory_manager.retrieve_relevant_memories("系统底层自检唤醒")
        print("✨ [系统启动中] 记忆库唤醒成功！神经链接已完全就绪。")
    except Exception as e:
        print(f"⚠️ [系统启动中] 记忆库加载可能存在异常，但程序将继续运行: {e}")

    print("=" * 50 + "\n")

    app = QApplication(sys.argv)
    romasha = RomashaDesktop()
    romasha.show()
    sys.exit(app.exec_())