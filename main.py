import sys
import os
import pyphen
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QTextEdit,
    QPushButton, QLabel, QFileDialog, QHBoxLayout, QComboBox
)
from PyQt5.QtCore import Qt, QTimer

class Slide:
    def __init__(self, text):
        self.text = text
        self.words = self.text.split()

class SlideManager:
    def __init__(self, text):
        slide_texts = text.split('<---pagebreak--->')
        self.slides = [Slide(t.strip()) for t in slide_texts]
        self.current_slide = 0

    def next_slide(self):
        if self.current_slide < len(self.slides) - 1:
            self.current_slide += 1

    def previous_slide(self):
        if self.current_slide > 0:
            self.current_slide -= 1

    def get_current_slide(self):
        return self.slides[self.current_slide]

    def get_remaining_slides(self):
        return self.slides[self.current_slide + 1:]

class SpeechTimer:
    def __init__(self, language='en'):
        self.pyphen_dic = pyphen.Pyphen(lang=language)
        self.average_syllable_duration = 0.2  # Avg. human speech ~5 syllables/sec
        self.speed_factor = 1.0

    def estimate_word_time(self, word):
        syllables = self.pyphen_dic.inserted(word).count('-') + 1
        base_time = syllables * self.average_syllable_duration
        if word.endswith(('.', ',')):
            base_time += 0.2  # Additional pause for punctuation
        return base_time / self.speed_factor

    def estimate_text_time(self, words):
        return sum(self.estimate_word_time(word) for word in words)

class PresentationApp(QMainWindow):
    def __init__(self, slide_manager, timer):
        super().__init__()

        self.slide_manager = slide_manager
        self.timer = timer
        self.current_word_index = 0
        self.is_playing = False

        self.init_ui()

        self.update_slide_display()

    def init_ui(self):
        self.setWindowTitle('Presentation Timer')
        self.setGeometry(200, 200, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.layout = QVBoxLayout()
        central_widget.setLayout(self.layout)

        self.slide_label = QLabel('Slide 1/1')
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.mouseDoubleClickEvent = self.double_click_event

        self.current_font_size = 12  # Starting default font size
        self.text_display.setStyleSheet(f'font-size: {self.current_font_size}pt;')

        self.time_label = QLabel('Remaining time: 0.0s')
        self.total_time_label = QLabel('Total remaining time: 0.0s')


        control_layout = QHBoxLayout()

        self.play_pause_button = QPushButton('Play')
        self.play_pause_button.clicked.connect(self.toggle_play_pause)

        self.prev_button = QPushButton('Previous Slide')
        self.prev_button.clicked.connect(self.prev_slide)

        self.next_button = QPushButton('Next Slide')
        self.next_button.clicked.connect(self.next_slide)

        self.speed_selector = QComboBox()
        self.speed_selector.addItems(['-20%', '-10%', '0%', '+10%', '+20%'])
        self.speed_selector.setCurrentIndex(2)
        self.speed_selector.currentIndexChanged.connect(self.update_speed)

        control_layout.addWidget(self.prev_button)
        control_layout.addWidget(self.play_pause_button)
        control_layout.addWidget(self.next_button)
        control_layout.addWidget(QLabel('Speed:'))
        control_layout.addWidget(self.speed_selector)

        # self.layout.addWidget(self.slide_label)
        self.instruction_label = QLabel('Ctrl+Scroll: Font Size | Space: Play/Pause after starting')
        self.instruction_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Create a horizontal layout for top labels
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.slide_label)
        top_layout.addWidget(self.instruction_label)

        # Replace previous line self.layout.addWidget(self.slide_label) with:
        self.layout.addLayout(top_layout)
        self.layout.addWidget(self.text_display)
        time_layout = QHBoxLayout()
        time_layout.addWidget(self.time_label)
        time_layout.addWidget(self.total_time_label, alignment=Qt.AlignRight)
        self.layout.addLayout(time_layout)

        self.layout.addLayout(control_layout)

        self.word_timer = QTimer()
        self.word_timer.timeout.connect(self.advance_word)

    def update_speed(self):
        speed_mapping = {'-20%': 0.8, '-10%': 0.9, '0%': 1.0, '+10%': 1.1, '+20%': 1.2}
        self.timer.speed_factor = speed_mapping[self.speed_selector.currentText()]
        self.update_remaining_time()

    def double_click_event(self, event):
        cursor = self.text_display.cursorForPosition(event.pos())
        cursor.select(cursor.WordUnderCursor)
        selected_word = cursor.selectedText()

        slide = self.slide_manager.get_current_slide()
        if selected_word in slide.words:
            self.current_word_index = slide.words.index(selected_word)
            self.highlight_words()
            self.update_remaining_time()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            if not self.is_playing:
                # If not playing, always reset the word_timer and start from current position
                self.toggle_play_pause()
            else:
                self.toggle_play_pause()

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            delta = event.angleDelta().y() / 120  # 1 step = 120 units
            self.current_font_size += int(delta)
            self.current_font_size = max(5, min(20, self.current_font_size))  # limits font size between 5 and 20 pt
            self.text_display.setStyleSheet(f'font-size: {self.current_font_size}pt;')
            event.accept()
        else:
            super().wheelEvent(event)

    def update_slide_display(self):
        self.current_word_index = 0
        self.slide_label.setText(f'Slide {self.slide_manager.current_slide + 1}/{len(self.slide_manager.slides)}')
        self.highlight_words()
        self.update_remaining_time()

    def highlight_words(self):
        slide = self.slide_manager.get_current_slide()
        words = slide.words

        highlighted_text = ""
        for idx, word in enumerate(words):
            if idx == self.current_word_index:
                highlighted_text += f'<span style="background-color: yellow;">{word}</span> '
            else:
                highlighted_text += word + ' '

        self.text_display.setHtml(highlighted_text.strip())

    def update_remaining_time(self):
        slide = self.slide_manager.get_current_slide()
        remaining_words = slide.words[self.current_word_index:]
        remaining_slide_time = self.timer.estimate_text_time(remaining_words)
        self.time_label.setText(f'Remaining slide time: {remaining_slide_time:.1f}s')

        remaining_slides_time = sum(
            self.timer.estimate_text_time(s.words) for s in self.slide_manager.get_remaining_slides()
        )
        total_remaining_time = remaining_slide_time + remaining_slides_time

        minutes = int(total_remaining_time // 60)
        seconds = int(total_remaining_time % 60)
        self.total_time_label.setText(f'Total remaining time: {minutes:02d}:{seconds:02d}')

    def advance_word(self):
        slide = self.slide_manager.get_current_slide()
        if self.current_word_index < len(slide.words) - 1:
            self.current_word_index += 1
            self.highlight_words()
            self.update_remaining_time()
            duration_ms = int(self.timer.estimate_word_time(slide.words[self.current_word_index]) * 1000)
            self.word_timer.start(duration_ms)
        else:
            self.word_timer.stop()
            self.is_playing = False
            self.play_pause_button.setText('Play')

    def toggle_play_pause(self):
        if not self.is_playing:
            self.is_playing = True
            self.play_pause_button.setText('Pause')
            self.advance_word()
        else:
            self.word_timer.stop()
            self.is_playing = False
            self.play_pause_button.setText('Play')

    def next_slide(self):
        self.slide_manager.next_slide()
        self.update_slide_display()

    def prev_slide(self):
        self.slide_manager.previous_slide()
        self.update_slide_display()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    files, _ = QFileDialog.getOpenFileName(None, 'Select Slide File', os.getenv('HOME'), "Text files (*.txt)")
    if files:
        text = open(files, 'r', encoding='utf-8').read()
        window = PresentationApp(SlideManager(text), SpeechTimer())
        window.show()
    sys.exit(app.exec_())