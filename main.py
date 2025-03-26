import sys
import os
import pyphen
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QTextEdit,
    QPushButton, QLabel, QFileDialog, QHBoxLayout
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

class SpeechTimer:
    def __init__(self, language='en'):
        self.pyphen_dic = pyphen.Pyphen(lang=language)
        self.average_syllable_duration = 0.2  # Avg. human speech ~5 syllables/sec

    def estimate_word_time(self, word):
        syllables = self.pyphen_dic.inserted(word).count('-') + 1
        return syllables * self.average_syllable_duration

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

        self.time_label = QLabel('Remaining time: 0.0s')

        control_layout = QHBoxLayout()

        self.play_pause_button = QPushButton('Play')
        self.play_pause_button.clicked.connect(self.toggle_play_pause)

        self.prev_button = QPushButton('Previous Slide')
        self.prev_button.clicked.connect(self.prev_slide)

        self.next_button = QPushButton('Next Slide')
        self.next_button.clicked.connect(self.next_slide)

        control_layout.addWidget(self.prev_button)
        control_layout.addWidget(self.play_pause_button)
        control_layout.addWidget(self.next_button)

        self.layout.addWidget(self.slide_label)
        self.layout.addWidget(self.text_display)
        self.layout.addWidget(self.time_label)
        self.layout.addLayout(control_layout)

        self.word_timer = QTimer()
        self.word_timer.timeout.connect(self.advance_word)

    def double_click_event(self, event):
        cursor = self.text_display.cursorForPosition(event.pos())
        cursor.select(cursor.WordUnderCursor)
        selected_word = cursor.selectedText()

        slide = self.slide_manager.get_current_slide()
        if selected_word in slide.words:
            self.current_word_index = slide.words.index(selected_word)
            self.highlight_words()
            self.update_remaining_time()

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
        remaining_time = self.timer.estimate_text_time(remaining_words)
        self.time_label.setText(f'Remaining time: {remaining_time:.1f}s')

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
            slide = self.slide_manager.get_current_slide()
            if self.current_word_index >= len(slide.words):
                self.current_word_index = 0
            duration_ms = int(self.timer.estimate_word_time(slide.words[self.current_word_index]) * 1000)
            self.word_timer.start(duration_ms)
            self.is_playing = True
            self.play_pause_button.setText('Pause')
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
