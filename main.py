import sys
import pyttsx3
import sounddevice as sd
import threading
import time
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QDialog, QGridLayout, QStatusBar, QMessageBox, QComboBox, QSpinBox, QFormLayout,
    QLineEdit, QListWidget, QListWidgetItem, QCheckBox, QTextEdit
)
from PyQt5.QtCore import Qt, QTimer, QTime
from PyQt5.QtGui import QFont

# ---------------- Announcement class ----------------
class Announcement:
    def __init__(self, text_template, play_time: datetime, repeat=None, voice_id=0, priority=0, variables=None):
        """
        :param text_template: str, text with placeholders, e.g. "Train {train_no} arriving at platform {platform}"
        :param play_time: datetime of scheduled announcement
        :param repeat: None or 'daily', 'weekly' for recurring
        :param voice_id: index of pyttsx3 voice
        :param priority: int, higher interrupts lower (live=10, scheduled=1)
        :param variables: dict of placeholders to fill in text_template
        """
        self.text_template = text_template
        self.play_time = play_time
        self.repeat = repeat
        self.voice_id = voice_id
        self.priority = priority
        self.variables = variables or {}

    def get_text(self):
        try:
            return self.text_template.format(**self.variables)
        except Exception as e:
            return self.text_template  # fallback if variables missing

    def is_due(self, now):
        return now >= self.play_time

    def reschedule(self):
        """Reschedule for next occurrence if repeating."""
        if self.repeat == "daily":
            self.play_time += timedelta(days=1)
        elif self.repeat == "weekly":
            self.play_time += timedelta(weeks=1)

# ---------------- Queue Manager ----------------
class AnnouncementQueue:
    def __init__(self, engine, voices, status_bar):
        self.queue = []
        self.current_announcement = None
        self.engine = engine
        self.voices = voices
        self.status_bar = status_bar
        self.lock = threading.Lock()
        self.playing_thread = None
        self.interrupted = False

    def add_announcement(self, announcement: Announcement):
        with self.lock:
            self.queue.append(announcement)
            # Sort by priority descending and play_time ascending
            self.queue.sort(key=lambda a: (-a.priority, a.play_time))
        self.status_bar.showMessage(f"Announcement queued: {announcement.get_text()}")
        self._try_play_next()

    def interrupt_with_live(self, announcement: Announcement):
        with self.lock:
            # Interrupt current announcement
            if self.playing_thread and self.playing_thread.is_alive():
                self.interrupted = True
                self.engine.stop()  # stop current TTS immediately
            # Put live announcement at front of queue
            self.queue.insert(0, announcement)
        self.status_bar.showMessage("Live announcement started...")
        self._try_play_next()

    def _try_play_next(self):
        if self.playing_thread and self.playing_thread.is_alive():
            return  # Already playing
        if not self.queue:
            return
        next_ann = self.queue.pop(0)
        self.current_announcement = next_ann
        self.interrupted = False
        self.playing_thread = threading.Thread(target=self._play_announcement, args=(next_ann,), daemon=True)
        self.playing_thread.start()

    def _play_announcement(self, announcement):
        try:
            self.engine.setProperty('voice', self.voices[announcement.voice_id].id)
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 1.0)
            text = announcement.get_text()
            self.status_bar.showMessage(f"Playing: {text}")
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            self.status_bar.showMessage(f"Error playing announcement: {e}")
        finally:
            # After playing, if repeating, reschedule and re-add
            if announcement.repeat:
                announcement.reschedule()
                self.add_announcement(announcement)
            # Play next announcement
            self.current_announcement = None
            self._try_play_next()

# ---------------- Schedule Manager Dialog ----------------
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem,
    QMessageBox, QLabel, QGroupBox, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

class ScheduleManagerDialog(QDialog):
    def __init__(self, parent, voices, announcement_queue):
        super().__init__(parent)
        self.setWindowTitle("📅 Smart Schedule Manager")
        self.setWindowIcon(QIcon())  # Optional: set your icon
        self.voices = voices
        self.announcement_queue = announcement_queue
        self.announcements = []
        self.init_ui()
        self.adjust_window_size()

    def scale_font_size(self, base_size=14):
        screen = self.window().screen() or (self.parent().screen() if self.parent() else self.screen())
        dpi = screen.logicalDotsPerInch()
        base_dpi = 96
        scale = dpi / base_dpi
        return max(11, int(base_size * scale))

    def init_ui(self):
        font_size = self.scale_font_size()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Announcements List Group
        list_group = QGroupBox("Scheduled Announcements")
        list_group.setStyleSheet(f"QGroupBox {{ font-weight: bold; font-size: {font_size + 2}px; padding: 10px; }}")
        group_layout = QVBoxLayout()

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"font-size: {font_size}px; padding: 4px;")
        group_layout.addWidget(self.list_widget)

        list_group.setLayout(group_layout)
        main_layout.addWidget(list_group)

        # Buttons Layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        def styled_button(text, bg_color):
            btn = QPushButton(text)
            btn.setFixedWidth(120)
            btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: {font_size}px;
                    padding: 8px;
                    background-color: {bg_color};
                    color: white;
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: #333;
                }}
            """)
            return btn

        add_btn = styled_button("➕ Add", "#4CAF50")
        add_btn.clicked.connect(self.add_announcement)
        btn_layout.addWidget(add_btn)

        edit_btn = styled_button("✏️ Edit", "#2196F3")
        edit_btn.clicked.connect(self.edit_announcement)
        btn_layout.addWidget(edit_btn)

        del_btn = styled_button("🗑️ Delete", "#f44336")
        del_btn.clicked.connect(self.delete_announcement)
        btn_layout.addWidget(del_btn)

        btn_layout.addStretch(1)

        close_btn = styled_button("❌ Close", "#9E9E9E")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        main_layout.addLayout(btn_layout)

        # Status Bar Label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignRight)
        self.status_label.setStyleSheet(f"font-size: {font_size - 2}px; color: #555; padding-top: 5px;")
        main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)
        self.refresh_list()

    def adjust_window_size(self):
        screen = self.window().screen() or (self.parent().screen() if self.parent() else self.screen())
        screen_geom = screen.availableGeometry()
        dpi = screen.logicalDotsPerInch()
        base_dpi = 96
        scale_factor = dpi / base_dpi

        base_width = 900
        base_height = 600

        width = int(base_width * scale_factor)
        height = int(base_height * scale_factor)

        max_width = int(screen_geom.width() * 0.9)
        max_height = int(screen_geom.height() * 0.9)

        width = min(width, max_width)
        height = min(height, max_height)

        self.resize(width, height)
        self.setMinimumSize(int(800 * scale_factor), int(500 * scale_factor))
        self.setMaximumSize(int(screen_geom.width() * 0.95), int(screen_geom.height() * 0.95))

        fg = self.frameGeometry()
        fg.moveCenter(screen_geom.center())
        self.move(fg.topLeft())

    def refresh_list(self):
        self.list_widget.clear()
        for ann in self.announcements:
            repeat_str = f" ({ann.repeat})" if ann.repeat else ""
            item_text = f"{ann.play_time.strftime('%Y-%m-%d %H:%M')} {repeat_str} - {ann.get('text_template')[:50]}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, ann)
            self.list_widget.addItem(item)
        self.status_label.setText(f"Total scheduled: {len(self.announcements)}")

    def add_announcement(self):
        dlg = AnnouncementEditDialog(self, self.voices)
        if dlg.exec_():
            ann = dlg.get_announcement()
            self.announcements.append(ann)
            self.refresh_list()

    def edit_announcement(self):
        selected = self.list_widget.currentItem()
        if not selected:
            QMessageBox.warning(self, "No selection", "Please select an announcement to edit.")
            return
        ann = selected.data(Qt.UserRole)
        dlg = AnnouncementEditDialog(self, self.voices, ann)
        if dlg.exec_():
            updated_ann = dlg.get_announcement()
            idx = self.announcements.index(ann)
            self.announcements[idx] = updated_ann
            self.refresh_list()

    def delete_announcement(self):
        selected = self.list_widget.currentItem()
        if not selected:
            QMessageBox.warning(self, "No selection", "Please select an announcement to delete.")
            return
        ann = selected.data(Qt.UserRole)
        self.announcements.remove(ann)
        self.refresh_list()


# --------------LiveMikeDialog--------------------------

# -------------- Announcement Edit Dialog ---------------

# -------Error when user save the data-----------------
from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QTextEdit, QComboBox, QDateTimeEdit, QSpinBox,
    QHBoxLayout, QPushButton, QMessageBox, QGroupBox, QVBoxLayout, QSpacerItem,
    QScrollArea, QWidget
)
from PyQt5.QtCore import Qt, QDateTime
from PyQt5.QtGui import QIcon, QPalette, QColor
from datetime import datetime

class AnnouncementEditDialog(QDialog):
    def __init__(self, parent, voices, announcement=None):
        super().__init__(parent)
        self.setWindowTitle("Add/Edit Announcement")
        self.setWindowIcon(QIcon())  # Set your icon path here if needed
        self.voices = voices
        self.announcement = announcement
        self.init_ui()
        self.adjust_window_size()

    def scale_font_size(self, base_size=14):
        screen = self.window().screen() or (self.parent().screen() if self.parent() else self.screen())
        dpi = screen.logicalDotsPerInch()
        base_dpi = 96
        scale = dpi / base_dpi
        return max(11, int(base_size * scale))  # minimum font size 11

    def set_light_palette_to_datetimeedit(self, datetime_edit):
        """Force light palette and style on QDateTimeEdit and its calendar popup."""
        light_palette = QPalette()
        light_palette.setColor(QPalette.Base, QColor(255, 255, 255))
        light_palette.setColor(QPalette.Text, Qt.black)
        light_palette.setColor(QPalette.Button, QColor(240, 240, 240))
        light_palette.setColor(QPalette.ButtonText, Qt.black)
        datetime_edit.setPalette(light_palette)

        datetime_edit.setStyleSheet("""
            QDateTimeEdit, QCalendarWidget QWidget {
                background-color: white;
                color: black;
            }
            QCalendarWidget QToolButton {
                background-color: #f0f0f0;
                color: black;
                height: 30px;
                width: 150px;
                qproperty-iconSize: 24px, 24px;
                font-weight: bold;
            }
            QCalendarWidget QMenu {
                background-color: white;
                color: black;
            }
            QCalendarWidget QSpinBox {
                background: white;
                color: black;
                selection-background-color: #0078d7;
                selection-color: white;
            }
            QCalendarWidget QAbstractItemView:enabled {
                font-size: 12pt;
                color: black;
                background-color: white;
                selection-background-color: #0078d7;
                selection-color: white;
            }
        """)

    def init_ui(self):
        font_size = self.scale_font_size()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(20, 20, 20, 20)
        scroll_layout.setSpacing(20)

        # Announcement Text Group
        text_group = QGroupBox("Announcement Text")
        text_group.setStyleSheet(f"QGroupBox {{ font-weight: bold; font-size: {font_size + 2}px; padding: 10px; }}")
        text_layout = QFormLayout()
        self.template_edit = QTextEdit()
        self.template_edit.setPlaceholderText("E.g., Train {train_no} arriving at platform {platform}")
        self.template_edit.setMinimumHeight(150)
        self.template_edit.setStyleSheet(f"font-size: {font_size}px;")
        if self.announcement:
            self.template_edit.setText(self.announcement.text_template)
        else:
            self.template_edit.setText("Train {train_no} arriving at platform {platform}")
        text_layout.addRow("Text Template:", self.template_edit)
        text_group.setLayout(text_layout)

        # Scheduling Group
        schedule_group = QGroupBox("Scheduling")
        schedule_group.setStyleSheet(f"QGroupBox {{ font-weight: bold; font-size: {font_size + 2}px; padding: 10px; }}")
        schedule_layout = QFormLayout()
        self.datetime_edit = QDateTimeEdit()
        self.datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setMinimumWidth(220)
        self.datetime_edit.setStyleSheet(f"font-size: {font_size}px; padding: 4px;")
        self.datetime_edit.setDateTime(QDateTime.currentDateTime() if not self.announcement else QDateTime(self.announcement.play_time))
        self.set_light_palette_to_datetimeedit(self.datetime_edit)  # Apply light theme

        self.repeat_box = QComboBox()
        self.repeat_box.addItems(["None", "Daily", "Weekly"])
        self.repeat_box.setStyleSheet(f"font-size: {font_size}px; padding: 4px;")
        self.repeat_box.setCurrentText(self.announcement.repeat.capitalize() if self.announcement and self.announcement.repeat else "None")

        self.repeat_end_edit = QDateTimeEdit()
        self.repeat_end_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.repeat_end_edit.setCalendarPopup(True)
        self.repeat_end_edit.setMinimumWidth(220)
        self.repeat_end_edit.setStyleSheet(f"font-size: {font_size}px; padding: 4px;")
        self.repeat_end_edit.setEnabled(self.repeat_box.currentText() != "None")
        self.repeat_end_edit.setDateTime(QDateTime.currentDateTime() if not (self.announcement and getattr(self.announcement, 'repeat_end', None)) else QDateTime(self.announcement.repeat_end))
        self.set_light_palette_to_datetimeedit(self.repeat_end_edit)  # Apply light theme

        self.repeat_box.currentTextChanged.connect(self.on_repeat_changed)

        schedule_layout.addRow("Play DateTime:", self.datetime_edit)
        schedule_layout.addRow("Repeat:", self.repeat_box)
        schedule_layout.addRow("Repeat Ends:", self.repeat_end_edit)
        schedule_group.setLayout(schedule_layout)

        # Voice & Priority Group
        options_group = QGroupBox("Voice & Priority")
        options_group.setStyleSheet(f"QGroupBox {{ font-weight: bold; font-size: {font_size + 2}px; padding: 10px; }}")
        options_layout = QFormLayout()

        self.voice_box = QComboBox()
        for v in self.voices:
            self.voice_box.addItem(v.name)
        self.voice_box.setStyleSheet(f"font-size: {font_size}px; padding: 4px;")
        self.voice_box.setCurrentIndex(self.announcement.voice_id if self.announcement else 0)

        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(1, 10)
        self.priority_spin.setStyleSheet(f"font-size: {font_size}px; padding: 4px;")
        self.priority_spin.setValue(self.announcement.priority if self.announcement else 1)

        options_layout.addRow("Voice:", self.voice_box)
        options_layout.addRow("Priority:", self.priority_spin)
        options_group.setLayout(options_layout)

        # Variables Group
        vars_group = QGroupBox("Variables")
        vars_group.setStyleSheet(f"QGroupBox {{ font-weight: bold; font-size: {font_size + 2}px; padding: 10px; }}")
        vars_layout = QFormLayout()

        self.variables_edit = QTextEdit()
        self.variables_edit.setPlaceholderText("key=value format, one per line")
        self.variables_edit.setMinimumHeight(160)
        self.variables_edit.setStyleSheet(f"font-size: {font_size}px;")
        if self.announcement and self.announcement.variables:
            vars_text = "\n".join(f"{k}={v}" for k, v in self.announcement.variables.items())
            self.variables_edit.setText(vars_text)
        else:
            self.variables_edit.setText("train_no=123\nplatform=4")

        vars_layout.addRow(self.variables_edit)
        vars_group.setLayout(vars_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)

        save_btn = QPushButton("✅ Save")
        save_btn.setFixedWidth(110)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: {font_size}px; padding: 8px;
                background-color: #4CAF50; color: white; border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #45a049;
            }}
        """)
        save_btn.clicked.connect(self.on_save)

        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.setFixedWidth(110)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: {font_size}px; padding: 8px;
                background-color: #f44336; color: white; border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #d32f2f;
            }}
        """)
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)

        # Add all groups
        scroll_layout.addWidget(text_group)
        scroll_layout.addWidget(schedule_group)
        scroll_layout.addWidget(options_group)
        scroll_layout.addWidget(vars_group)
        scroll_layout.addSpacerItem(QSpacerItem(20, 20))
        scroll_layout.addLayout(btn_layout)

        scroll.setWidget(scroll_widget)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

    def adjust_window_size(self):
        screen = self.window().screen() or (self.parent().screen() if self.parent() else self.screen())
        screen_geom = screen.availableGeometry()
        dpi = screen.logicalDotsPerInch()
        base_dpi = 96
        scale_factor = dpi / base_dpi

        base_width = 1000
        base_height = 750

        width = int(base_width * scale_factor)
        height = int(base_height * scale_factor)

        max_width = int(screen_geom.width() * 0.9)
        max_height = int(screen_geom.height() * 0.9)

        width = min(width, max_width)
        height = min(height, max_height)

        self.resize(width, height)
        self.setMinimumSize(int(800 * scale_factor), int(600 * scale_factor))
        self.setMaximumSize(int(screen_geom.width() * 0.95), int(screen_geom.height() * 0.95))

        fg = self.frameGeometry()
        fg.moveCenter(screen_geom.center())
        self.move(fg.topLeft())

    def on_repeat_changed(self, text):
        self.repeat_end_edit.setEnabled(text != "None")

    def on_save(self):
        if not self.template_edit.toPlainText().strip():
            QMessageBox.warning(self, "Input Error", "Text Template cannot be empty.")
            return
        if self.repeat_box.currentText() != "None" and self.repeat_end_edit.dateTime() < self.datetime_edit.dateTime():
            QMessageBox.warning(self, "Input Error", "Repeat End date/time must be after Play DateTime.")
            return
        self.accept()

    def get_announcement(self):
        template = self.template_edit.toPlainText().strip()
        play_time = self.datetime_edit.dateTime().toPyDateTime()
        repeat = self.repeat_box.currentText().lower() if self.repeat_box.currentText() != "None" else None
        repeat_end = self.repeat_end_edit.dateTime().toPyDateTime() if repeat else None
        voice_id = self.voice_box.currentIndex()
        priority = self.priority_spin.value()

        variables_text = self.variables_edit.toPlainText()
        variables = {}
        for line in variables_text.splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                variables[k.strip()] = v.strip()

        return {
            "text_template": template,
            "play_time": play_time,
            "repeat": repeat,
            "repeat_end": repeat_end,
            "voice_id": voice_id,
            "priority": priority,
            "variables": variables
        }




# ------------------ Main App --------------------
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QGridLayout,
    QHBoxLayout, QStatusBar, QInputDialog, QDialog
)
from PyQt5.QtCore import Qt, QTimer, QTime
from PyQt5.QtGui import QFont
from datetime import datetime

# Dummy classes (replace with your real implementations)
class Announcement:
    def __init__(self, text, created_at, priority=5):
        self.text = text
        self.created_at = created_at
        self.priority = priority

    def is_due(self, now):
        return True  # for testing


class AnnouncementQueue:
    def __init__(self, engine, voices, status_bar):
        self.queue = []
        self.engine = engine
        self.voices = voices
        self.status_bar = status_bar

    def interrupt_with_live(self, ann):
        self.status_bar.showMessage(f"Live: {ann.text}")

    def add_announcement(self, ann):
        self.queue.append(ann)
        self.status_bar.showMessage(f"Queued: {ann.text}")



# --------------Live Voice Announcemnt-------------------------
import json
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QSlider, QHBoxLayout,
    QFileDialog, QCheckBox, QStatusBar, QComboBox
)
from PyQt5.QtCore import Qt, QThread, QTimer, QTime
import pyaudio
import wave
import numpy as np


CONFIG_FILE = "config.json"


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load config: {e}")
    return {}


def save_config(data):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Failed to save config: {e}")


class MicToSpeaker(QThread):
    def __init__(self, volume=1.0, input_device_index=None, parent=None):
        super().__init__(parent)
        self.running = False
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        self.volume = volume
        self.p = pyaudio.PyAudio()
        self.input_device_index = input_device_index

    def run(self):
        self.stream_input = self.p.open(format=self.format,
                                        channels=self.channels,
                                        rate=self.rate,
                                        input=True,
                                        input_device_index=self.input_device_index,
                                        frames_per_buffer=self.chunk)
        self.stream_output = self.p.open(format=self.format,
                                         channels=self.channels,
                                         rate=self.rate,
                                         output=True)
        self.running = True
        while self.running:
            data = self.stream_input.read(self.chunk, exception_on_overflow=False)
            adjusted_data = self.adjust_volume(data, self.volume)
            self.stream_output.write(adjusted_data)
        self.cleanup()

    def stop(self):
        self.running = False

    def cleanup(self):
        if hasattr(self, 'stream_input'):
            self.stream_input.stop_stream()
            self.stream_input.close()
        if hasattr(self, 'stream_output'):
            self.stream_output.stop_stream()
            self.stream_output.close()
        self.p.terminate()

    def adjust_volume(self, data, volume):
        audio_data = np.frombuffer(data, dtype=np.int16)
        audio_data = (audio_data * volume).clip(-32768, 32767).astype(np.int16)
        return audio_data.tobytes()


class LiveMicDialog(QDialog):
    def __init__(self, parent=None, announcement_queue=None):
        super().__init__(parent)
        self.setWindowTitle("🎙️ Live Mic Announcement")
        self.setGeometry(300, 200, 480, 400)
        self.setStyleSheet("font-size: 15px; font-family: 'Segoe UI';")
        self.announcement_queue = announcement_queue

        # Load config and chime file
        config = load_config()
        self.chime_file = config.get("chime_file", "chime.wav")

        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

        # Microphone device selection
        self.device_label = QLabel("Select Microphone Device:")
        self.layout.addWidget(self.device_label)

        self.device_combo = QComboBox()
        self.layout.addWidget(self.device_combo)
        self.populate_input_devices()

        self.label = QLabel("🎙️ Click 'Start' to use Mic for Announcement")
        self.label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.label)

        self.live_status = QLabel("")
        self.live_status.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.live_status)

        self.start_button = QPushButton("🎙️ Start Live Announcement")
        self.start_button.clicked.connect(self.start_mic)
        self.layout.addWidget(self.start_button)

        self.stop_button = QPushButton("⏹️ Stop Announcement")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_mic)
        self.layout.addWidget(self.stop_button)

        # Volume Control
        volume_layout = QHBoxLayout()
        self.volume_label = QLabel("Volume:")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setMinimum(1)
        self.volume_slider.setMaximum(10)
        self.volume_slider.setValue(5)
        self.volume_slider.setTickInterval(1)
        self.volume_value_label = QLabel("5")
        self.volume_slider.valueChanged.connect(self.update_volume_label)
        volume_layout.addWidget(self.volume_label)
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(self.volume_value_label)
        self.layout.addLayout(volume_layout)

        # Chime on/off checkbox + select chime button
        chime_layout = QHBoxLayout()
        self.chime_checkbox = QCheckBox("Play Chime Before Announcement")
        self.chime_checkbox.setChecked(True)
        chime_layout.addWidget(self.chime_checkbox)

        chime_select_button = QPushButton("🎵 Select Chime")
        chime_select_button.clicked.connect(self.select_chime)
        chime_layout.addWidget(chime_select_button)
        self.layout.addLayout(chime_layout)

        # Status bar with clock
        self.status_bar = QStatusBar()
        self.clock_label = QLabel("")
        self.status_bar.addPermanentWidget(self.clock_label)
        self.layout.addWidget(self.status_bar)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)

        self.mic_thread = None
        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self.blink_live_status)
        self.blink_state = False

    def populate_input_devices(self):
        self.device_combo.clear()
        p = pyaudio.PyAudio()
        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        for i in range(numdevices):
            device_info = p.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                name = device_info.get('name')
                self.device_combo.addItem(name, i)
        p.terminate()

        # Optionally select default device:
        default_index = self.get_default_input_device_index()
        if default_index is not None:
            index = self.device_combo.findData(default_index)
            if index != -1:
                self.device_combo.setCurrentIndex(index)

    def get_default_input_device_index(self):
        try:
            p = pyaudio.PyAudio()
            default_index = p.get_default_input_device_info().get('index')
            p.terminate()
            return default_index
        except Exception:
            return None

    def start_mic(self):
        if self.chime_checkbox.isChecked():
            self.play_chime()

        self.label.setText("🎙️ Live Mic On. Speak now...")
        volume = self.volume_slider.value() / 10.0
        selected_device_index = self.device_combo.currentData()

        self.mic_thread = MicToSpeaker(volume=volume, input_device_index=selected_device_index)
        self.mic_thread.start()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.blink_timer.start(500)

    def stop_mic(self):
        if self.mic_thread:
            self.mic_thread.stop()
            self.mic_thread.wait()
            self.mic_thread = None
        self.label.setText("🎙️ Announcement Stopped.")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.live_status.setText("")
        self.blink_timer.stop()

    def blink_live_status(self):
        if self.blink_state:
            self.live_status.setText("🔴 LIVE")
            self.live_status.setStyleSheet("color: red; font-weight: bold; font-size: 17px;")
        else:
            self.live_status.setText("")
        self.blink_state = not self.blink_state

    def play_chime(self):
        if not os.path.exists(self.chime_file):
            print("Chime file not found:", self.chime_file)
            return
        try:
            wf = wave.open(self.chime_file, 'rb')
            p = pyaudio.PyAudio()
            stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                            channels=wf.getnchannels(),
                            rate=wf.getframerate(),
                            output=True)
            data = wf.readframes(1024)
            while data:
                stream.write(data)
                data = wf.readframes(1024)
            stream.stop_stream()
            stream.close()
            p.terminate()
        except Exception as e:
            print(f"Chime play failed: {e}")

    def select_chime(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Chime Sound", "", "Audio Files (*.wav)")
        if file_path:
            self.chime_file = file_path
            print(f"Permanent chime selected: {self.chime_file}")
            # Save to config immediately
            config = load_config()
            config["chime_file"] = self.chime_file
            save_config(config)

    def update_clock(self):
        current_time = QTime.currentTime().toString("hh:mm:ss AP")
        self.clock_label.setText(f"🕒 {current_time}")

    def update_volume_label(self):
        self.volume_value_label.setText(str(self.volume_slider.value()))

    def closeEvent(self, event):
        # Stop live mic announcement if running before closing
        self.stop_mic()
        event.accept()



class VoiceAnnouncementApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_engine()
        self.init_ui()

        # Announcement queue manager87
        self.announcement_queue = AnnouncementQueue(self.engine, self.voices, self.status_bar)

        # Timer to check scheduled announcements every minute
        self.scheduler_timer = QTimer()
        self.scheduler_timer.timeout.connect(self.check_schedules)
        self.scheduler_timer.start(60000)  # every 60 seconds

        self.schedule_dialog_instance = None

    def init_engine(self):
        import pyttsx3
        self.engine = pyttsx3.init()
        self.voices = self.engine.getProperty('voices')


    def init_ui(self):
        self.setWindowTitle("🚆 Indian Railway Voice Announcement System")
        self.setGeometry(200, 100, 900, 600)

        # Modern gradient background & fonts
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f0f4f7, stop:1 #d9e2ec);
                font-family: 'Arial';
            }
            QLabel#titleLabel {
                color: #2c3e50;
            }
            QStatusBar {
                background-color: #bdc3c7;
                font-size: 14px;
                padding: 5px;
                color: #34495e;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(30)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # Title with objectName for targeted style
        title = QLabel("🚆 Indian Railway Voice Announcement System")
        title.setObjectName("titleLabel")
        title.setFont(QFont("Arial", 30, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Buttons grid layout
        button_layout = QGridLayout()
        button_layout.setHorizontalSpacing(40)
        button_layout.setVerticalSpacing(30)

        live_announce_btn = QPushButton("🎙️ Live Text Announcement")
        live_announce_btn.setStyleSheet(self.button_style())
        live_announce_btn.clicked.connect(self.live_announcement)
        button_layout.addWidget(live_announce_btn, 0, 0)

        live_mic_btn = QPushButton("🎙️ Live Mic Announcement")
        live_mic_btn.setStyleSheet(self.button_style())
        live_mic_btn.clicked.connect(self.open_live_mic_dialog)
        button_layout.addWidget(live_mic_btn, 1, 0)

        schedule_btn = QPushButton("📅 Smart Schedule Manager")
        schedule_btn.setStyleSheet(self.button_style())
        schedule_btn.clicked.connect(self.open_schedule_manager)
        button_layout.addWidget(schedule_btn, 0, 1)

        main_layout.addLayout(button_layout)

        # Status bar and clock layout
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(10, 15, 10, 15)
        status_layout.setSpacing(20)

        self.clock_label = QLabel()
        self.clock_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.clock_label.setStyleSheet("color: #34495e;")
        self.update_clock()
        status_layout.addWidget(self.clock_label, alignment=Qt.AlignLeft)

        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("color: #2c3e50;")
        self.status_bar.showMessage("System Ready.")
        status_layout.addWidget(self.status_bar, stretch=1)

        main_layout.addLayout(status_layout)

        self.setLayout(main_layout)

        # Clock update timer
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)

    def button_style(self):
        return """
            QPushButton {
                background-color: #2980b9;
                color: white;
                padding: 20px 35px;
                font-size: 20px;
                font-weight: bold;
                border-radius: 12px;
                transition: all 0.3s ease;
            }
            QPushButton:hover {
                background-color: #3498db;
                box-shadow: 0 0 10px #2980b9;
            }
            QPushButton:pressed {
                background-color: #1f618d;
            }
        """

    def update_clock(self):
        current_time = QTime.currentTime().toString("hh:mm:ss AP")
        self.clock_label.setText(current_time)

    def live_announcement(self):
        text, ok = QInputDialog.getText(self, "Live Announcement", "Speak your announcement (type here):")
        if ok and text.strip():
            ann = Announcement(text, datetime.now(), priority=10)
            self.announcement_queue.interrupt_with_live(ann)

    def open_live_mic_dialog(self):
        dialog = LiveMicDialog(self, announcement_queue=self.announcement_queue)
        dialog.exec_()

    def open_schedule_manager(self):
        if not self.schedule_dialog_instance:
            self.schedule_dialog_instance = ScheduleManagerDialog(self, self.voices, self.announcement_queue)
        self.schedule_dialog_instance.show()

    def check_schedules(self):
        now = datetime.now()
        for ann in self.schedule_manager_announcements:
            if ann.is_due(now):
                self.announcement_queue.add_announcement(ann)
                if not ann.repeat:
                    self.schedule_manager_announcements.remove(ann)

    @property
    def schedule_manager_announcements(self):
        if self.schedule_dialog_instance:
            return self.schedule_dialog_instance.announcements
        else:
            return []


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VoiceAnnouncementApp()
    window.show()
    sys.exit(app.exec_())

