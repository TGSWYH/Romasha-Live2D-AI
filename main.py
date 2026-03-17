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
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QMessageBox,
                             QDialog, QTextBrowser, QPushButton, QProgressBar, QLineEdit,
                             QHBoxLayout, QLabel, QScrollArea, QInputDialog, QSizePolicy, QComboBox)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtGui import QRegion, QCursor, QFont, QColor, QTextCursor, QIcon                   

import llm_brain
import motion_manager
import outfit_manager
import story_manager
import lorebook_manager


                                            
                           
                                            
class NameEditDialog(QDialog):
    def __init__(self, current_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle('命运观测终端 - 玩家档案')
                            
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.resize(320, 160)
        self.setStyleSheet("background-color: #f8f9fa; color: #333; border-radius: 8px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        label = QLabel("请输入你在这个世界中的名字：")
        label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        layout.addWidget(label)

        self.name_input = QLineEdit(self)
        self.name_input.setText(current_name)
        self.name_input.setFont(QFont("Microsoft YaHei", 11))
        self.name_input.setStyleSheet("border: 2px solid #ffb6c1; padding: 6px; border-radius: 6px; background: white;")
        layout.addWidget(self.name_input)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("确认修改")
        self.save_btn.setStyleSheet("QPushButton { background: #ffb6c1; color: white; border-radius: 5px; padding: 8px; font-weight: bold;} QPushButton:hover { background: #ff99ab; }")
        self.save_btn.clicked.connect(self.accept)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet("QPushButton { background: #ddd; color: #333; border-radius: 5px; padding: 8px; font-weight: bold;} QPushButton:hover { background: #ccc; }")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def get_name(self):
        return self.name_input.text().strip()

class StoryWindow(QWidget):
                                    
    choice_made = pyqtSignal(str)
    name_changed = pyqtSignal(str)               

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Princess Synergy - 命运观测终端")
                  
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web/favicon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.resize(1000, 750)
                        
                                                           
        self.setWindowFlags(Qt.Window)
        self.setStyleSheet("background-color: #f8f9fa; color: #333; border-radius: 10px;")

             
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)

                               
        top_bar = QHBoxLayout()
        title_label = QLabel("📖 命运世界线推演日志")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        title_label.setStyleSheet("color: #666;")

                         
        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))

        current_name = llm_brain.config.get("player_name", "未命名")
                         
        self.name_btn = QPushButton(f"👤 当前玩家: {current_name}")
        self.name_btn.setFixedWidth(180)
        self.name_btn.setStyleSheet("""
                            QPushButton { background: #ffb6c1; color: white; border-radius: 5px; padding: 6px; font-weight: bold;}
                            QPushButton:hover { background: #ff99ab; }
                        """)
        self.name_btn.clicked.connect(self.edit_player_name)

                         
                                     
        self.is_generating_story = True
        self.action_btn = QPushButton("🛑 停止推演")
        self.action_btn.setFixedWidth(120)
        self.action_btn.setStyleSheet("""
                    QPushButton { background: #e74c3c; color: white; border-radius: 5px; padding: 6px; font-weight: bold;}
                    QPushButton:hover { background: #c0392b; }
                """)
        self.action_btn.clicked.connect(self.toggle_generation)

                       
        self.exit_btn = QPushButton("🚪 退出推演")
        self.exit_btn.setFixedWidth(100)
        self.exit_btn.setStyleSheet("""
                    QPushButton { background: #95a5a6; color: white; border-radius: 5px; padding: 6px; font-weight: bold;}
                    QPushButton:hover { background: #7f8c8d; }
                """)
                                                                
        self.exit_btn.clicked.connect(self.close)

                       
        self.level_combo = QComboBox()
        self.level_combo.addItems(["参与度 0", "参与度 1", "参与度 2", "参与度 3"])
        self.level_combo.setCurrentIndex(2)            
        self.level_combo.setStyleSheet("""
                    QComboBox { background: rgba(255,255,255,0.9); border: 1px solid #ffb6c1; border-radius: 5px; padding: 4px 18px 4px 8px; font-size: 12px; color: #6031e2; font-weight: bold; }
                    QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 15px; border-left: none; }
                    QComboBox::down-arrow { width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #6031e2; margin-right: 4px; }
                """)

        top_bar.addWidget(title_label)
        top_bar.addWidget(self.status_label)
        top_bar.addStretch()
        top_bar.addWidget(self.level_combo)           
        top_bar.addWidget(self.name_btn)
        top_bar.addWidget(self.action_btn)           
        top_bar.addWidget(self.exit_btn)            
        self.layout.addLayout(top_bar)

                                  
        self.history_browser = QTextBrowser()
        self.history_browser.setFont(QFont("Microsoft YaHei", 11))
        self.history_browser.setStyleSheet("""
                    QTextBrowser {
                        background-color: #f1f3f5; 
                        border: 1px solid #ddd; 
                        border-radius: 8px; 
                        padding: 10px;
                    }
                    /* 专属滚动条美化 */
                    QScrollBar:vertical {
                        border: none; background: #e9ecef; width: 12px; margin: 2px 2px 2px 0; border-radius: 6px;
                    }
                    QScrollBar::handle:vertical {
                        background: #ffb6c1; min-height: 40px; border-radius: 6px;
                    }
                    QScrollBar::handle:vertical:hover {
                        background: #ff99ab;
                    }
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                        border: none; background: none;
                    }
                """)
        self.layout.addWidget(self.history_browser, stretch=5)

                                  
        self.current_browser = QTextBrowser()
        self.current_browser.setFont(QFont("Microsoft YaHei", 12))
        self.current_browser.setStyleSheet("""
                    QTextBrowser {
                        background-color: #ffffff; 
                        border: 2px solid #ffb6c1; 
                        border-radius: 8px; 
                        padding: 10px;
                    }
                    /* 专属滚动条美化 */
                    QScrollBar:vertical {
                        border: none; background: transparent; width: 12px; margin: 2px 2px 2px 0; border-radius: 6px;
                    }
                    QScrollBar::handle:vertical {
                        background: #ffb6c1; min-height: 40px; border-radius: 6px;
                    }
                    QScrollBar::handle:vertical:hover {
                        background: #ff99ab;
                    }
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                        border: none; background: none;
                    }
                """)
        self.layout.addWidget(self.current_browser, stretch=3)

                          
        self.options_widget = QWidget()
                                                              
                                                   
        self.options_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.options_main_layout = QVBoxLayout(self.options_widget)
        self.options_main_layout.setContentsMargins(0, 0, 0, 0)
        self.options_main_layout.setSpacing(12)               
                                                                             
                                   

                               
        self.buttons_container = QWidget()
        self.buttons_layout = QVBoxLayout(self.buttons_container)
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.buttons_layout.setSpacing(8)
        self.options_main_layout.addWidget(self.buttons_container)

                            
        self.custom_input_container = QWidget()
        self.custom_input_layout = QHBoxLayout(self.custom_input_container)
        self.custom_input_layout.setContentsMargins(0, 0, 0, 0)
        self.custom_input_layout.setSpacing(8)

        self.custom_choice_input = QLineEdit()
        self.custom_choice_input.setPlaceholderText("或者...不满意选项？亲自输入你期望的走向！(按回车发送)")
        self.custom_choice_input.setFont(QFont("Microsoft YaHei", 10))
        self.custom_choice_input.setStyleSheet(
            "border: 1px solid #ffb6c1; border-radius: 5px; padding: 8px; background: white;")
                                       
        self.custom_choice_input.textChanged.connect(self.pause_countdown)
        self.custom_choice_input.returnPressed.connect(self.send_custom_choice)

        self.custom_send_btn = QPushButton("发送抉择")
        self.custom_send_btn.setFixedWidth(100)
        self.custom_send_btn.setStyleSheet(
            "QPushButton { background: #ffb6c1; color: white; border-radius: 5px; padding: 8px; font-weight: bold;} QPushButton:hover { background: #ff99ab; }")
        self.custom_send_btn.clicked.connect(self.send_custom_choice)

        self.custom_input_layout.addWidget(self.custom_choice_input)
        self.custom_input_layout.addWidget(self.custom_send_btn)
        self.options_main_layout.addWidget(self.custom_input_container)

        self.layout.addWidget(self.options_widget, 0)
        self.options_widget.hide()

                          
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(600)                      
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet(
            "QProgressBar { border: none; background-color: #e9ecef; border-radius: 3px; } QProgressBar::chunk { background-color: #ffb6c1; }")
        self.layout.addWidget(self.progress_bar, 0)          
        self.progress_bar.hide()

                
        self.target_text = ""
        self.current_text = ""
        self.pending_options = []
        self.time_left = 600                     

                                     
        self.typewriter_timer = QTimer(self)
        self.typewriter_timer.timeout.connect(self.typewriter_tick)

                  
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.countdown_tick)

                            
        scrollbar_style = """
                    QScrollBar:vertical {
                        border: none;
                        background: #f1f3f5;
                        width: 12px;
                        border-radius: 6px;
                    }
                    QScrollBar::handle:vertical {
                        background: #ffb6c1;
                        min-height: 30px;
                        border-radius: 6px;
                    }
                    QScrollBar::handle:vertical:hover {
                        background: #ff99ab;
                    }
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                        border: none;
                        background: none;
                    }
                    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                        background: none;
                    }
                """
                           
        self.setStyleSheet(self.styleSheet() + scrollbar_style)

    def edit_player_name(self):
        current_name = llm_brain.config.get("player_name", "")
                       
        dialog = NameEditDialog(current_name, self)
        if dialog.exec_() == QDialog.Accepted:
            new_name = dialog.get_name()
            if new_name:
                self.name_changed.emit(new_name)
                            
                self.name_btn.setText(f"👤 当前玩家: {new_name}")

    def toggle_generation(self):
        if self.is_generating_story:
                           
            self.typewriter_timer.stop()
            self.countdown_timer.stop()
            self.is_generating_story = False
            self.action_btn.setText("▶ 继续推演")
            self.action_btn.setStyleSheet("""
                QPushButton { background: #2ecc71; color: white; border-radius: 5px; padding: 6px; font-weight: bold;}
                QPushButton:hover { background: #27ae60; }
            """)

                        
            self.status_label.setText(" 已暂停")
            self.status_label.setStyleSheet("color: #d35400;")      

            self.choice_made.emit("/CANCEL_GENERATION")
        else:
                            
            self.countdown_timer.stop()
            self.options_widget.hide()
            self.progress_bar.hide()

                                
            self.status_label.setText(" 推演中...")
            self.status_label.setStyleSheet("color: #e74c3c;")
            self.is_generating_story = True
            self.action_btn.setText("🛑 停止推演")
            self.action_btn.setStyleSheet("""
                                    QPushButton { background: #e74c3c; color: white; border-radius: 5px; padding: 6px; font-weight: bold;}
                                    QPushButton:hover { background: #c0392b; }
                                """)

            self.choice_made.emit("*(顺应局势，继续推进剧情)*")

    def prepare_new_chapter(self, prompt_desc=""):
        self.is_generating_story = True
        self.action_btn.setText("🛑 停止推演")
        self.action_btn.setStyleSheet("""
                    QPushButton { background: #e74c3c; color: white; border-radius: 5px; padding: 6px; font-weight: bold;}
                    QPushButton:hover { background: #c0392b; }
                """)

                        
        self.status_label.setText(" 推演中...")
        self.status_label.setStyleSheet("color: #e74c3c;")      

        self.current_browser.clear()
        self.current_text = ""
        self.target_text = ""
        self.options_widget.hide()
        self.progress_bar.hide()
                         
        for i in reversed(range(self.buttons_layout.count())):
            widget = self.buttons_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()              

                                 
        self.custom_choice_input.clear()

        if prompt_desc:
            self.history_browser.append(f"<span style='color:#6031e2;'><b>{prompt_desc}</b></span><br>")

        self.show()
        self.typewriter_timer.start(20)              

    def update_streaming_text(self, text):
        self.target_text = text

    def typewriter_tick(self):
        if self.current_text != self.target_text:
            next_idx = len(self.current_text)
            self.current_text += self.target_text[next_idx:next_idx + 4]                
                                                       
            self.current_browser.setText(self.current_text.replace("\n", "<br>"))
            cursor = self.current_browser.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.current_browser.setTextCursor(cursor)

                                   
    def finalize_chapter(self, final_text, options):
        try:
            self.typewriter_timer.stop()

                                        
            self.is_generating_story = False
            self.action_btn.setText("▶ 继续推演")
            self.action_btn.setStyleSheet("""
                        QPushButton { background: #2ecc71; color: white; border-radius: 5px; padding: 6px; font-weight: bold;}
                        QPushButton:hover { background: #27ae60; }
                    """)

                                                             
            safe_text = final_text.replace("\n", "<br>")
            self.current_browser.setText(safe_text)
                             
            self.history_browser.append(f"<span style='color:#333;'>{safe_text}</span><br><br>")

                    
            self.pending_options = options
            if self.pending_options:
                                          
                self.status_label.setText(" 请抉择...")
                self.status_label.setStyleSheet("color: #2ecc71;")

                for opt_text in self.pending_options:
                    btn = QPushButton(opt_text)
                    btn.setFont(QFont("Microsoft YaHei", 10))
                    btn.setStyleSheet(
                        "QPushButton { background-color: #fff; border: 1px solid #ddd; border-radius: 5px; padding: 10px; text-align: left; } QPushButton:hover { background-color: #fff0f5; border: 1px solid #ffb6c1; }")
                    btn.clicked.connect(lambda checked, text=opt_text: self.on_option_clicked(text))
                    self.buttons_layout.addWidget(btn)

                self.options_widget.show()
                self.time_left = 600
                self.progress_bar.setMaximum(600)                
                self.progress_bar.setValue(600)
                                   
                self.progress_bar.setStyleSheet(
                    "QProgressBar { border: none; background-color: #e9ecef; border-radius: 3px; } QProgressBar::chunk { background-color: #ffb6c1; }")
                self.progress_bar.show()
                self.countdown_timer.start(100)

        except Exception as e:
            print(f"⚠️ [UI渲染警告]: 选项渲染受阻 -> {e}")

    def update_chapter_text(self, final_text):
        try:
            self.typewriter_timer.stop()
            self.is_generating_story = False
            self.action_btn.setText("▶ 继续推演")
            self.action_btn.setStyleSheet("""
                        QPushButton { background: #2ecc71; color: white; border-radius: 5px; padding: 6px; font-weight: bold;}
                        QPushButton:hover { background: #27ae60; }
                    """)
            safe_text = final_text.replace("\n", "<br>")
            self.current_browser.setText(safe_text)
            self.history_browser.append(f"<span style='color:#333;'>{safe_text}</span><br><br>")
        except Exception as e:
            print(f"⚠️ [UI渲染警告]: 文本渲染受阻 -> {e}")

    def show_options(self, options):
        try:
            self.pending_options = options
            if self.pending_options:
                                          
                self.status_label.setText(" 请抉择...")
                self.status_label.setStyleSheet("color: #2ecc71;")

                                 
                for i in reversed(range(self.buttons_layout.count())):
                    widget = self.buttons_layout.itemAt(i).widget()
                    if widget is not None:
                        widget.deleteLater()              

                for opt_text in self.pending_options:
                    btn = QPushButton(opt_text)
                    btn.setFont(QFont("Microsoft YaHei", 10))
                    btn.setStyleSheet(
                        "QPushButton { background-color: #fff; border: 1px solid #ddd; border-radius: 5px; padding: 10px; text-align: left; } QPushButton:hover { background-color: #fff0f5; border: 1px solid #ffb6c1; }")
                    btn.clicked.connect(lambda checked, text=opt_text: self.on_option_clicked(text))
                    self.buttons_layout.addWidget(btn)

                self.options_widget.show()
                self.time_left = 600
                self.progress_bar.setMaximum(600)                
                self.progress_bar.setValue(600)
                                    
                self.progress_bar.setStyleSheet(
                    "QProgressBar { border: none; background-color: #e9ecef; border-radius: 3px; } QProgressBar::chunk { background-color: #ffb6c1; }")
                self.progress_bar.show()
                self.countdown_timer.start(100)
        except Exception as e:
            print(f"⚠️ [UI渲染警告]: 选项渲染受阻 -> {e}")

    def countdown_tick(self):
        self.time_left -= 1
        self.progress_bar.setValue(self.time_left)
        if self.time_left <= 0:
            self.countdown_timer.stop()
            self.on_option_clicked("*(沉默不语。请顺应局势自动推进)*")

    def on_option_clicked(self, choice_text):
        self.countdown_timer.stop()
        self.options_widget.hide()
        self.progress_bar.hide()

                         
        self.status_label.setText(" 推演中...")
        self.status_label.setStyleSheet("color: #e74c3c;")
        self.is_generating_story = True
        self.action_btn.setText("🛑 停止推演")
        self.action_btn.setStyleSheet("""
                            QPushButton { background: #e74c3c; color: white; border-radius: 5px; padding: 6px; font-weight: bold;}
                            QPushButton:hover { background: #c0392b; }
                        """)

        self.choice_made.emit(choice_text)

    def pause_countdown(self, text):
        if text.strip() and self.countdown_timer.isActive():
            self.countdown_timer.stop()
            self.status_label.setText(" 抉择中 (输入中...)")
            self.status_label.setStyleSheet("color: #f39c12;")           
                                
            self.progress_bar.setStyleSheet(
                "QProgressBar { border: none; background-color: #e9ecef; border-radius: 3px; } QProgressBar::chunk { background-color: #f39c12; }")

    def send_custom_choice(self):
        choice_text = self.custom_choice_input.text().strip()
        if choice_text:
            self.custom_choice_input.clear()            
                                 
            self.on_option_clicked(f"*(玩家亲自干涉)*: {choice_text}")

    def closeEvent(self, event):
                                  
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle('结束推演')
        msg_box.setText(
            "确定要彻底结束本次命运推演，让她回归日常模式吗？\n（当前的推演进度将不会保留在面板上，但已存入本地小说日志）")
        msg_box.setIcon(QMessageBox.Question)

                         
        yes_btn = msg_box.addButton("确定", QMessageBox.YesRole)
        no_btn = msg_box.addButton("取消", QMessageBox.NoRole)

                              
        msg_box.setDefaultButton(no_btn)

                     
        msg_box.exec_()

                      
        if msg_box.clickedButton() == yes_btn:
            self.countdown_timer.stop()
            self.typewriter_timer.stop()
            self.choice_made.emit("/EXIT_STORY_MODE")

                         
                                       
                                                        
            self.status_label.setText("")
            self.hide()

                                         
        event.ignore()


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
            self.is_cancelled = False

            if user_text == "/SYSTEM_RESET_MEMORY":
                try:
                                             
                    memory_manager.clear_all_memories()
                                           
                    llm_brain.chat_history.clear()
                                         
                    story_manager.clear_summary()
                                                
                    lorebook_manager.clear_dynamic_lore()
                                                
                    story_manager.archive_novel_log()
                                                            
                    llm_brain.config["intimacy"] = 0
                                            
                    llm_brain.config["player_name"] = ""
                                               
                    llm_brain.config["current_location"] = "罗玛莎的房间门口"
                    llm_brain.config["current_chapter"] = 1
                    llm_brain.config["is_first_encounter"] = True                          
                    llm_brain.save_config()
                    print("💔 [记忆消散]: 曾经相处的点滴如沙般流逝，你们回到了最初相遇时的陌生与戒备。\n")

                except Exception as e:
                    print(f"⚠️ [命运纠缠]: 过去的痕迹似乎难以抹除 ({e})")
                self.task_queue.task_done()
                continue

                              
            if user_text.startswith("/STORY_TICK_"):
                try:
                                                 
                                                
                    parts = user_text.split("_", 3)
                    level = parts[2]
                    choice_text = parts[3] if len(parts) > 3 else ""

                    llm_brain.stream_story_with_romasha(level, choice_text, self)
                except Exception as e:
                    print(f"⚠️ [命运纠缠]: 故事线推演失败 ({e})")

                if not self.is_cancelled:
                    self.task_finished.emit()
                self.task_queue.task_done()
                continue

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
        self.is_cancelled = False             

                 
    def translate_to_japanese(self, text):
        try:
            api_type = llm_brain.config.get("api_type", "openai").lower()
            messages = [
                {"role": "system", "content": "你是一个精准的中译日翻译器，请将玩家的中文台词精准直译翻译成对应的日文。【极其重要】：如果文本中包含形如 [quick_breath]、[sigh] 等英文控制标签，你必须原样保留它们，并将它们插入到日文中合理的位置。绝对不要翻译这些方括号内的标签！只需要输出最终的日文结果，不要任何解释。"},
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

            self.is_cancelled = False              

                                    
                                           
                                                                       
            clean_text = re.sub(r'\[(act_|mood_|intimacy_|wear_|hair_|set_name_).*?\]', '', text)
            clean_text = re.sub(r'（内心：.*?）', '', clean_text)
            clean_text = clean_text.strip()

            if not clean_text:
                                                          
                                    
                self.audio_ready.emit("", True, "empty")
                self.task_queue.task_done()
                continue

                                                   
            instruct_text = ""
                                               
            match = re.match(r'^(.*?)<\|endofprompt\|>(.*)$', clean_text, re.DOTALL)
            if match:
                raw_instruct = match.group(1)          
                                                   
                instruct_text = re.sub(r'[^\w\u4e00-\u9fa5]', '', raw_instruct)
                clean_text = match.group(2).strip()                                
                                   
                clean_text = clean_text.replace("<|endofprompt|>", "")

                                                   
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

                                                                  
                    if self.is_cancelled:
                        print("🔇 [底层拦截]: 语音生成完毕，但已被玩家的最新举动打断，该语音包作废。")
                        self.task_queue.task_done()
                        continue

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

                                                                 
                    response = requests.get(url, params=params, proxies=proxies, timeout=60.0)

                                                              
                    if self.is_cancelled:
                        print("🔇 [底层拦截]: SoVITS语音生成完毕，但已被玩家打断，作废。")
                        self.task_queue.task_done()
                        continue

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
                    f"   (🛠️ 隐秘线索: 处理超过了 60 秒。因为电脑配置较差，显卡可能仍在加载模型，请耐心再跟她聊一句试试)")
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

                                     
        self.last_text_finish_time = datetime.datetime.now()

                             
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

                            
        self.story_window = StoryWindow()
        self.story_window.choice_made.connect(self.handle_story_choice)
        self.story_window.name_changed.connect(self.update_player_name)

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
                                   
        settings.setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, False)
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

    def update_player_name(self, new_name):
        llm_brain.config["player_name"] = new_name
        llm_brain.save_config()
                    
        self.show_system_notification(
            f"<span style='color:#6031e2; font-size: var(--sub-font-size);'><i>(玩家名字已更新为：{new_name})</i></span>",
            2000)

    def handle_story_choice(self, choice_text):
        """接收来自剧情窗口的选择"""
        if choice_text == "/CANCEL_GENERATION":
                                     
            self.brain_worker.is_cancelled = True
            self.story_window.current_browser.append(
                "<br><br><span style='color:#e74c3c;'><b>[系统]: ⚠️ 推演已被手动强行中止。你可以直接在下方做出抉择。</b></span>")
                             
            self.flush_pending_tags()
            self.is_waiting_for_voice = False
            return

        if choice_text == "/EXIT_STORY_MODE":
            self.is_story_mode = False
                                                   
            self.brain_worker.is_cancelled = True

                                           
            self.flush_pending_tags()
            self.is_waiting_for_voice = False

            self.show_system_notification(
                "<span style='color:#e74c3c; font-size: var(--sub-font-size);'><i>(命运观测终端已关闭，切回日常模式...)</i></span>",
                3000)
            print("\n💻 [系统]: 玩家关闭了剧情窗口，回归日常陪伴。")
            return

                      
        print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] ⚖️ 命运抉择: {choice_text}")

                        
        self.show_system_notification("<span style='color:#6031e2; font-size: var(--sub-font-size);'><i>(正在推演下个阶段的未来...)</i></span>", 4000)

                                                 
        current_level = str(self.story_window.level_combo.currentIndex())
        self.start_new_thought(f"/STORY_TICK_{current_level}_{choice_text}")


    def restore_bubble_state(self):
        """恢复被指令打断的对话气泡"""
        self.is_showing_notification = False

                                                    
        if getattr(self, 'is_story_mode', False):
            bubble_html = "<span style='color:#6031e2; font-size: var(--sub-font-size);'><i>(正在进行世界线深度推演，请在日志面板查看...)</i></span>"
            self.browser.page().runJavaScript(f"window.showBubble(\"{bubble_html}\", true);")
            return
                  

                                        
        if self.is_waiting_for_voice:
            bubble_html = self.current_context_html + "<span style='color:#888; font-size: var(--sub-font-size);'><i>(微启双唇，正在酝酿要说的话...)</i></span>"
            safe_html = bubble_html.replace("'", "\\'")
            self.browser.page().runJavaScript(f"window.showBubble('{safe_html}', true);")

                       
        elif self.current_display_text != self.target_display_text:
                                                 
                                             
            pass

                                      
        else:
                                                      
            safe_text = self.current_display_text.replace("\\", "\\\\").replace("\n", "<br>")
            final_html = self.current_context_html + safe_text

                                                        
            clean_text_len = len(re.sub(r'<[^>]+>', '', final_html))
            display_time_seconds = max(5.0, clean_text_len * 0.3)

                               
            elapsed = (datetime.datetime.now() - getattr(self, 'last_text_finish_time',
                                                         datetime.datetime.now())).total_seconds()

            if elapsed < display_time_seconds:
                                 
                safe_html = final_html.replace("'", "\\'")
                self.browser.page().runJavaScript(f"window.showBubble('{safe_html}', false);")
            else:
                                      
                self.browser.page().runJavaScript("document.getElementById('chat-bubble').style.opacity = 0;")

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
                                                                         
                      
            self.set_idle_motion(self.current_idle_motion)

    def idle_tick(self):
                                          
        if getattr(self, 'is_story_mode', False):
            return

                                                       
        is_generating = (not self.brain_worker.task_queue.empty()) or self.is_waiting_for_voice or getattr(self,
                                                                                                           'is_typing',
                                                                                                           False)

        self.vision_idle_seconds += 1                               
                                 
        if not is_generating:
            self.thought_idle_seconds += 1

                                     
        if self.vision_idle_seconds == 300:
            self.browser.page().runJavaScript("window.toggleTracking(false);")
                                                                                             
                                         
            self.set_idle_motion(motion_manager.get_motion_index('wait_haji'))

                                
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

                                 
        self.current_context_html = f"<span style='color:#ccc; font-size: var(--sub-font-size);'><i>(漫长的安静中，Romasha 似乎在想些什么...)</i></span><br>"
        bubble_html = self.current_context_html + "<span style='color:#888; font-size: var(--sub-font-size);'><i>(独处思考中...)</i></span>"
        safe_html = bubble_html.replace("'", "\\'")
        self.browser.page().runJavaScript(f"window.showBubble('{safe_html}');")

        self.start_new_thought(sys_prompt)

    def resolve_static_mood(self):
                                          
        if getattr(self, 'is_story_mode', False):
            return

                                             
        if self.vision_idle_seconds < 300:
                                            
            sys_prompt = "[系统机制：你刚才已经维持静止发呆或小声嘀咕 15 秒了。请根据你此刻的情绪，决定切换回正常的动态常态动作（如 mood_talk, mood_talk_alc 等）。你可以小声嘟囔一句话、说一两句心声，也可以什么都不说只输出动作标签。]"

            self.current_context_html = f"<span style='color:#ccc; font-size: var(--sub-font-size);'><i>(短暂的定格后，她似乎有了动作...)</i></span><br>"
            bubble_html = self.current_context_html + "<span style='color:#888; font-size: var(--sub-font-size);'><i>(调整状态...)</i></span>"
            safe_html = bubble_html.replace("'", "\\'")
            self.browser.page().runJavaScript(f"window.showBubble('{safe_html}');")

            self.start_new_thought(sys_prompt)

    def revert_to_idle_motion(self):
        self.set_parameter('ParamCheek', 0.0)
        self.set_parameter('angry', 0.0)
                                                                     
                         
        self.set_idle_motion(self.current_idle_motion)

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

                                              
            if getattr(self, 'manual_outfit_lock', False):
                if new_time_period == "day":
                                                
                    self.manual_outfit_lock = False
                else:
                                                  
                    return

                               
            if target_outfit and target_outfit != outfit_manager._current_outfit:
                if target_outfit == "towel":
                    print(f"\n👗 [观察]: 夜深了，听到浴室传来隐约的水声后，Romasha裹着浴巾走了出来。")
                elif target_outfit == "sleepwear":
                    print(f"\n👗 [观察]: 留意到时间的推移，Romasha默默换上了轻薄的睡衣。")
                else:
                    print(f"\n👗 [观察]: 留意到时间的推移，Romasha默默换了一身适合现在的衣服。")

                               
            bubble_html = "<span style='color:#ccc; font-size: var(--sub-font-size);'><i>(一阵轻微的窸窣声后，她换好了一身衣服...)</i></span><br>"
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

                                     
            if llm_brain.config.get("is_first_encounter", True):
                intro_text = "故事刚刚开始：她刚刚击败龙人少女，又遭遇了迪亚德的羞辱与监控，正一个人在房间里心力交瘁、极度迷茫……(试着对她搭话来开启命运的齿轮吧)"

                                         
                def show_delayed_intro():
                    print(f"\n🌟 [命运指引]: {intro_text}")
                                             
                    bubble_html = f"<span style='color:#6031e2; font-weight:bold; font-size: var(--sub-font-size);'>🌟 {intro_text}</span>"
                    self.show_system_notification(bubble_html, 10000)

                                                           
                QTimer.singleShot(2000, show_delayed_intro)

                                               
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
                                                           
                    self.brain_worker.is_cancelled = True
                    with self.brain_worker.task_queue.mutex:
                        self.brain_worker.task_queue.queue.clear()

                                            
                    self.tts_worker.is_cancelled = True

                    with self.tts_worker.task_queue.mutex:
                        self.tts_worker.task_queue.queue.clear()

                    self.is_waiting_for_voice = False
                    self.browser.page().runJavaScript(
                        "if(typeof window.stopRomashaVoice === 'function') window.stopRomashaVoice();")
                    self.pending_tags.clear()

                                   
                    self.brain_worker.task_queue.put(("/SYSTEM_RESET_MEMORY", ""))

                            
                    self.current_context_html = ""
                    self.current_display_text = ""
                    self.target_display_text = ""
                    self.accumulated_text = ""            

                    self.show_system_notification("<span style='color:#888; font-size: var(--sub-font-size);'><i>(记忆已被重置，迎来了崭新的初见...)</i></span>", 3000)
                                               
                    self.story_window.name_btn.setText("👤 当前玩家: 未命名")
                    self.manual_outfit_lock = False             


                                                                
                                          
                                                                
                                            
                    self.set_parameter('ParamCheek', 0.0)
                    self.set_parameter('angry', 0.0)

                                                                          
                    idx = motion_manager.get_motion_index('talk')
                    if idx is not None:
                        self.current_idle_motion = idx
                                                                
                                                                
                                                            
                        self.set_idle_motion(idx)

                                                       
                                                            
                    llm_brain.config["intimacy"] = 0
                    self.apply_initial_state()

                return

            if user_text.startswith('/auto '):
                                    
                player_name = llm_brain.config.get("player_name", "")
                if not player_name:
                    dialog = NameEditDialog("", self)
                    if dialog.exec_() == QDialog.Accepted and dialog.get_name():
                        name = dialog.get_name()
                        llm_brain.config["player_name"] = name
                        llm_brain.save_config()
                        self.story_window.name_btn.setText(f"👤 当前玩家: {name}")
                    else:
                        self.show_system_notification("<span style='color:#e74c3c; font-size: var(--sub-font-size);'><i>(取消了推演...)</i></span>", 1500)
                        return

                level = user_text.split(' ')[1].strip()
                if level in ["0", "1", "2", "3"]:
                    self.is_story_mode = True             
                    self.story_window.level_combo.setCurrentIndex(int(level))                     
                    self.story_level = level
                                            
                    llm_brain.chat_history = [msg for msg in llm_brain.chat_history if
                                              not msg.get("content", "").startswith("[系统机制")]
                    self.show_system_notification(
                        f"<span style='color:#6031e2; font-size: var(--sub-font-size);'><i>(已切入世界线推演模式，参与度: {level}...)</i></span>",
                        3000)

                                                       
                    self.start_new_thought(f"/STORY_TICK_{level}_")
                return

            if user_text.startswith('/choice ') and getattr(self, 'is_story_mode', False):
                choice_text = user_text.replace('/choice ', '').strip()
                                           
                llm_brain.chat_history = [msg for msg in llm_brain.chat_history if
                                          not msg.get("content", "").startswith("[系统机制")]
                                    
                current_level = str(self.story_window.level_combo.currentIndex())
                self.start_new_thought(f"/STORY_TICK_{current_level}_{choice_text}")
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

                                     
            if user_text.startswith('/chapter '):
                try:
                    chap_val = int(user_text.split(' ')[1].strip())
                    if chap_val >= 1:
                        llm_brain.config["current_chapter"] = chap_val
                        llm_brain.save_config()

                                 
                        print(f"\n📖 [命运流转]: 世界的齿轮已拨动，当前推演时间线跃迁至：第 {chap_val} 章。")

                                
                        bubble_html = f"<span style='color:#6031e2; font-size: var(--sub-font-size);'><i>(时间的刻度跳动了，你们来到了新的阶段：第 {chap_val} 章...)</i></span>"
                        self.show_system_notification(bubble_html, 2000)
                except Exception:
                    print("⚠️ 指令错误，正确格式为: /chapter 2")
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

                                     
                       
            self.current_context_html = f"<span style='color:#48a1fa; font-size: var(--main-font-size);'>你: {user_text}</span><br>"
            self.last_text_finish_time = datetime.datetime.now()                    
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

                                         
            self.current_context_html = f"<span style='color:#fd92a1; font-size: var(--main-font-size);'>{action_text}</span><br>"
            bubble_html = self.current_context_html + "<span style='color:#888; font-size: var(--sub-font-size);'><i>(感受中...)</i></span>"
            safe_html = bubble_html.replace("'", "\\'")
                          
            self.browser.page().runJavaScript(f"window.showBubble('{safe_html}', true);")

            self.start_new_thought(action_text)

    def start_new_thought(self, prompt_text):
                                               
                                 
        self.static_mood_timer.stop()
        self.speech_end_timer.stop()                               

                              
        if prompt_text.startswith("/STORY_TICK_"):
                        
            parts = prompt_text.split("_", 3)
            level = parts[2]
            choice_text = parts[3] if len(parts) > 3 and parts[3] else "开启世界线推演"
            print(
                f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] 📖 [命运编织]: 世界线正在向新的分歧点推演 (参与度: {level})...")
                                        
            self.story_window.prepare_new_chapter(f"▶ 抉择: {choice_text} (参与度: {level})")
                              
        elif prompt_text.startswith("[系统机制"):
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

                                     
        self.tts_worker.is_cancelled = True
        with self.tts_worker.task_queue.mutex:
            self.tts_worker.task_queue.queue.clear()
                                                       

        self.brain_worker.interrupt_and_submit(prompt_text, interrupted_text)

    def recover_taol_fall(self):
                               
        if getattr(self, 'is_story_mode', False):
            return

                                      
        sys_prompt = "[系统机制：距离刚才浴巾意外滑落已经过去了整整10秒。你现在急忙蹲下重新捡起并紧紧裹好了浴巾。请必须输出 [wear_towel] 标签，并伴随极其娇羞、甚至带有哭腔或羞愤的动作（如 [mood_talk_ero]）与慌乱的话语/心声。]"

                      
                                       
        self.current_context_html = "<span style='color:#fd92a1; font-size: var(--main-font-size);'><i>(短暂的慌乱后，她急急忙忙重新裹好了浴巾...)</i></span><br>"
        bubble_html = self.current_context_html + "<span style='color:#888; font-size: var(--sub-font-size);'><i>(满脸通红手忙脚乱中...)</i></span>"
        safe_html = bubble_html.replace("'", "\\'")
        self.browser.page().runJavaScript(f"window.showBubble('{safe_html}');")

                                 
        self.start_new_thought(sys_prompt)

    def on_task_finished(self):
        if self.accumulated_text.strip():
                                                        
                                    
                                                        
            if getattr(self, 'is_story_mode', False):
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 🌸 剧情推演结束，处理分支中...")
                full_text = self.accumulated_text

                                                                        
                                                                            
                                             
                options_match = re.search(r'[<＜]\s*options\s*[>＞](.*?)([<＜]/\s*options\s*[>＞]|$)', full_text,
                                          flags=re.DOTALL | re.IGNORECASE)
                self.pending_story_options = []
                options_raw = ""
                fallback_match = None

                if options_match:
                    options_raw = options_match.group(1).strip()
                else:
                                                                        
                    fallback_match = re.search(r'(1\.\s*.*)$', full_text, re.DOTALL)
                    if fallback_match:
                        options_raw = fallback_match.group(1).strip()
                        options_raw = re.sub(r'[<＜]/?\s*options\s*[>＞]?', '', options_raw, flags=re.IGNORECASE).strip()

                if options_raw:
                                                   
                                                        
                                                         
                    if re.search(r'\d+\.', options_raw):
                        opts = re.split(r'\d+\.\s*', options_raw)
                    elif re.search(r'[-*]\s+', options_raw):
                        opts = re.split(r'[-*]\s+', options_raw)
                    else:
                        opts = options_raw.split('\n')

                    self.pending_story_options = [opt.strip() for opt in opts if opt.strip()]

                                           
                print(
                    f"🎯 [系统诊断]: 成功提取到 {len(self.pending_story_options)} 个选项 -> {self.pending_story_options}")

                                              
                display_text = re.sub(r'[<＜]\s*options\s*[>＞].*?([<＜]/\s*options\s*[>＞]|$)', '', full_text,
                                      flags=re.DOTALL | re.IGNORECASE)
                                                            
                if not options_match and fallback_match:
                    display_text = display_text.replace(fallback_match.group(1), "").strip()

                display_text = re.sub(r'\[(act_|mood_|wear_|hair_).*?\]', '', display_text)

                                
                                          
                                                        
                say_matches = re.findall(r'\[say:\s*"(.*?)"\]', full_text, re.DOTALL)
                tts_text = "。".join(say_matches)

                if tts_text:
                            
                    clean_tts_print = re.sub(r'^.*?<\|endofprompt\|>', '', tts_text)
                                                               
                    clean_tts_print = re.sub(r'\[.*?\]', '', clean_tts_print).strip()
                    print(f"\n🗣️ [剧情高光台词]: {clean_tts_print}")

                                                               
                    bubble_html = f"<span style='color:#fd92a1; font-weight:bold; font-size: var(--main-font-size);'>「{clean_tts_print}」</span><br>"
                                                                                            
                    safe_html = bubble_html.replace("'", "\\'").replace("\n", "<br>")
                    self.browser.page().runJavaScript(f"window.showBubble('{safe_html}', true);")

                                                    
                display_text = re.sub(r'\[say:\s*"[^"]*?<\|endofprompt\|>(.*?)"\]', r'“\1”', display_text,
                                      flags=re.DOTALL)
                display_text = re.sub(r'\[say:\s*"(.*?)"\]', r'“\1”', display_text, flags=re.DOTALL)
                                             
                display_text = re.sub(r'\[.*?\]', '', display_text).strip()

                                    
                                                        
                                                                                             
                self.story_window.update_chapter_text(display_text)

                novel_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "world_data", "novel_log.txt")
                os.makedirs(os.path.dirname(novel_path), exist_ok=True)
                with open(novel_path, "a", encoding="utf-8") as f:
                    f.write(f"\n\n--- 【记录时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}】 ---\n")
                                  
                    f.write(self.story_window.target_text)

                         
                                  
                if self.is_waiting_for_voice:
                    if tts_text:
                        self.tts_worker.task_queue.put(tts_text)
                    else:
                        self.is_waiting_for_voice = False
                        self.speech_end_timer.start(2000)
                                                
                else:
                                                  
                                             
                                           
                    duration_ms = 2000
                    self.speech_end_timer.start(duration_ms)

                                                        
                                  
                                                        
            else:
                                                
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
                elif tag_lower.startswith('set_name_'):                  
                    self.execute_tag(tag)                                
                                   
                elif tag_lower.startswith('move_to_'):
                    self.execute_tag(tag)               
                                         
                elif tag_lower.startswith('sys_chapter_up'):
                    self.execute_tag(tag_lower)
                                                      
                                                            
                elif tag_lower.startswith(('act_', 'mood_', 'wear_', 'hair_')):
                                                               
                                                        
                    if getattr(self, 'is_story_mode', False):
                        self.execute_tag(tag_lower)
                    else:
                        self.pending_tags.append(tag_lower)                       

                                                    
                                  
                                                    
                     
        clean_text = re.sub(r'<options>.*?(</options>|$)', '', self.accumulated_text, flags=re.DOTALL)

                                        
        voice_tags = r'breath|quick_breath|laughter|cough|clucking|accent|noise|hissing|sigh|vocalized-noise|lipsmack|mn'
        regex_pattern = fr'\[(act_|mood_|wear_|hair_|intimacy_|set_name_|move_to_|sys_chapter_up|{voice_tags}).*?\]'
        clean_text = re.sub(regex_pattern, '', clean_text, flags=re.IGNORECASE)

                                                     
        clean_text = re.sub(r'\[say:\s*"[^"]*?<\|endofprompt\|>(.*?)"\]', r'“\1”', clean_text)
        clean_text = re.sub(r'\[say:\s*"(.*?)"\]', r'“\1”', clean_text)

                                             
        clean_text = re.sub(r'^.*?<\|endofprompt\|>', '', clean_text)

                             
        final_text = re.sub(r'\[[^\]]*$', '', clean_text).strip()

                                  
                                               
                                                                   
                                                           
                                                                    
                                                                      
                                                                             

                                                    
                                
                                                    
        if getattr(self, 'is_story_mode', False):
                                
            self.story_window.update_streaming_text(final_text)

                              
            bubble_html = "<span style='color:#6031e2; font-size: var(--sub-font-size);'><i>(正在进行世界线深度推演，请在日志面板查看...)</i></span>"
            self.browser.page().runJavaScript(f"window.showBubble(\"{bubble_html}\", true);")

        else:
                             
            self.final_clean_text = final_text

                                                  
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
                self.last_text_finish_time = datetime.datetime.now()
                safe_text = self.current_display_text.replace("\\", "\\\\").replace("\n", "<br>")
                final_html = self.current_context_html + safe_text
                safe_html = final_html.replace("'", "\\'")
                                     
                self.browser.page().runJavaScript(f"window.showBubble('{safe_html}', false);")

                                 
    def execute_tag(self, tag):
                        
        if tag.lower().startswith('set_name_'):
            new_name = tag[9:].strip()                       
            if new_name:
                llm_brain.config["player_name"] = new_name
                llm_brain.save_config()
                print(f"\n📝 [羁绊铭记]: 已将你的称呼更新为：{new_name}")

                                     
                bubble_html = f"<span style='color:#6031e2; font-size: var(--sub-font-size);'><i>(她在心里默默记下了你的名字：{new_name})</i></span><br>"
                self.current_context_html += bubble_html
            return

                                 
        if tag.lower().startswith('move_to_'):
            new_loc = tag[8:].strip()                      
            if new_loc:
                llm_brain.config["current_location"] = new_loc
                llm_brain.save_config()
                print(f"\n🚶‍♀️ [空间转移]: 伴随着脚步声，Romasha 前往了【{new_loc}】。")

                                     
                bubble_html = f"<span style='color:#6031e2; font-size: var(--sub-font-size);'><i>(她改变了位置，现在来到了：{new_loc}...)</i></span><br>"
                self.current_context_html += bubble_html

                                     
                                    
                sys_bubble_html = f"<span style='color:#3498db; font-weight:bold; font-size: var(--main-font-size);'>🚶‍♀️ 场景转移：前往【{new_loc}】...</span>"
                self.show_system_notification(sys_bubble_html, 4000)
            return

                                 
        if tag.lower().startswith('sys_chapter_up'):
            current_chap = llm_brain.config.get("current_chapter", 1)
                           
            if current_chap < 5:
                next_chap = current_chap + 1
                llm_brain.config["current_chapter"] = next_chap
                llm_brain.save_config()

                print(f"\n🌌 [命运回响]:剧本弧光完成，命运齿轮转动，已自动推进至【第 {next_chap} 章】的推演节点。")

                                             
                bubble_html = f"<span style='color:#6031e2; font-size: var(--sub-font-size);'><i>(命运的篇章已翻过，进入：第 {next_chap} 章...)</i></span><br>"
                self.current_context_html += bubble_html

                                     
                sys_bubble_html = f"<span style='color:#6031e2; font-weight:bold; font-size: var(--main-font-size);'> 🌌 命运的齿轮转动，已自动进入第 {next_chap} 阶段...</span>"
                self.show_system_notification(sys_bubble_html, 4000)
            return

                          
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

                color = "#ffb6c1" if change_val >= 0 else "#6031e2"
                                                                 
                                            
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

                                                           
                    self.manual_outfit_lock = True
            except Exception as e:
                pass


        elif tag.startswith('mood_'):
            mood_name = tag.split('_', 1)[1]
                                                   
                                                    
                                       

                               
            if getattr(self, 'is_story_mode', False):
                print(f"🎬 [物理引擎]: 罗玛莎情绪切换 -> {mood_name}")

            try:
                idx = motion_manager.get_motion_index(mood_name)
                if idx is not None:
                    self.current_idle_motion = idx
                                                            
                                                         
                    self.set_idle_motion(idx)
                                         
                    if mood_name in ['neutral', 'wait', 'wait_haji']:
                        self.is_current_mood_static = True
                    else:
                        self.is_current_mood_static = False
                                                                 
            except Exception as e:
                pass


        elif tag.startswith('act_'):
            action_name = tag.split('_', 1)[1]

                               
            if getattr(self, 'is_story_mode', False):
                print(f"🎬 [物理引擎]: 罗玛莎触发瞬间动作 -> {action_name}")

                           
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
        for tag in self.pending_tags:
            self.execute_tag(tag)
        self.pending_tags.clear()
                                               

    def on_speech_finished(self):
        self.revert_to_idle_motion()

        if getattr(self, 'is_current_mood_static', False):
                                                       
            delay_ms = 5000 if llm_brain.config.get("voice_enabled", True) else 8000
            self.static_mood_timer.start(delay_ms)

                                            
        if getattr(self, 'is_story_mode', False) and hasattr(self,
                                                                 'pending_story_options') and self.pending_story_options:
            self.story_window.show_options(self.pending_story_options)
            self.pending_story_options = []

    def trigger_motion(self, group, index):
        self.browser.page().runJavaScript(f"window.playRomashaMotion('{group}', {index});")

                            
    def set_idle_motion(self, index):
        self.browser.page().runJavaScript(f"window.setRomashaIdleMotion({index});")

    def set_parameter(self, param_id, value):
        self.browser.page().runJavaScript(f"window.setRomashaParam('{param_id}', {value});")

    def closeEvent(self, event):
        self.brain_worker.running = False
        self.brain_worker.wait()

                                            
        self.motion_revert_timer.stop()
        self.typewriter_timer.stop()
        self.notification_timer.stop()
        self.static_mood_timer.stop()
        self.taol_recover_timer.stop()
        self.auto_save_timer.stop()
        self.speech_end_timer.stop()
        self.idle_timer.stop()
        self.time_check_timer.stop()
        self.mouse_timer.stop()

                                                    
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

                                                    
                               
                                                    
        if getattr(self, 'is_story_mode', False):
                                        
                                                      
            unlock_js = """
                if(window.bubbleTimeout) clearTimeout(window.bubbleTimeout); 
                window.bubbleTimeout = setTimeout(() => { document.getElementById('chat-bubble').style.opacity = 0; }, 6000);
                """
            self.browser.page().runJavaScript(unlock_js)
        else:
                                         
                                                     
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
                             
                                                         
        current_int = llm_brain.config.get("intimacy", 0)              
        memory_manager.retrieve_relevant_memories("初次相遇的预热", current_int)             
        print(f"✨ [{time_tag}] 她慢慢睁开了眼睛，你看到了她的身影。")
    except Exception as e:
        print(f"⚠️ [{time_tag}] 刚醒来似乎有些头晕，但并不影响你们的相遇: {e}")

    print("=" * 50 + "\n")

    app = QApplication(sys.argv)
    romasha = RomashaDesktop()
    romasha.show()
    sys.exit(app.exec_())
