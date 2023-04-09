from PySide6.QtWidgets import (
    QHBoxLayout,
    QWidget,
    QTextEdit,
)
from PySide6.QtCore import Slot, Qt
from PySide6.QtGui import QTextCursor


class AddrWidget(QTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.LineWrapMode.FixedColumnWidth)
        self.setLineWrapColumnOrWidth(6)
        self.setFontFamily("Courier New")
        self.setFontPointSize(14)
        self.setFixedWidth(76)

    def set_bytes(self, raw_bytes):
        text = ""
        for i in range(0, len(raw_bytes), 16):
            text += format(i, "06X")

        self.setPlainText(text)


class HexWidget(QTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.LineWrapMode.FixedColumnWidth)
        self.setLineWrapColumnOrWidth(49)
        self.setFontFamily("Courier New")
        self.setFontPointSize(14)
        self.setFixedWidth(538)

    def set_bytes(self, raw_bytes):
        text = ""
        for i, b in enumerate(raw_bytes):
            text += format(b, "02X")
            text += " "
            if ((i + 1) % 8) == 0 and ((i + 1) % 16) != 0:
                text += " "

        self.setPlainText(text.rstrip())

    def raw_index_to_start(self, idx):
        line, idx = idx // 16, idx % 16

        return line * 49 + idx * 3 + (idx // 8)

    def raw_index_to_end(self, idx):
        return self.raw_index_to_start(idx) + 2

    def to_raw_index(self, idx):
        line, idx = idx // 49, idx % 49

        return line * 16 + (idx - (idx // 24)) // 3


class AsciiWidget(QTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.LineWrapMode.FixedColumnWidth)
        self.setLineWrapColumnOrWidth(17)
        self.setFontFamily("Courier New")
        self.setFontPointSize(14)
        self.setFixedWidth(214)

    def set_bytes(self, raw_bytes):
        text = ""
        for i, b in enumerate(raw_bytes):
            if 0x21 <= b <= 0x7E:
                text += chr(b)
            else:
                text += "."

            if ((i + 1) % 8) == 0 and ((i + 1) % 16) != 0:
                text += " "

        self.setPlainText(text)

    def raw_index_to_start(self, idx):
        line, idx = idx // 16, idx % 16

        return line * 17 + idx + (idx // 8)

    def raw_index_to_end(self, idx):
        return self.raw_index_to_start(idx) + 1

    def to_raw_index(self, idx):
        line, idx = idx // 17, idx % 17

        return line * 16 + idx - (idx // 8)


def set_selection(widget, start, end, cursor_idx):
    if len(widget.toPlainText()) == 0:
        return

    cursor = widget.textCursor()

    start_idx = widget.raw_index_to_start(start)
    end_idx = widget.raw_index_to_end(end)

    if cursor_idx == end:
        cursor.setPosition(start_idx)
        cursor.setPosition(end_idx, QTextCursor.MoveMode.KeepAnchor)
    else:
        cursor.setPosition(end_idx)
        cursor.setPosition(start_idx, QTextCursor.MoveMode.KeepAnchor)

    widget.setTextCursor(cursor)


class GbxHexEditor(QWidget):
    def __init__(self, on_select, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # addr
        self.addr_widget = AddrWidget()

        # hex
        self.hex_widget = HexWidget()

        # ascii
        self.ascii_widget = AsciiWidget()

        # layout
        layout = QHBoxLayout()
        layout.addWidget(self.addr_widget)
        layout.addWidget(self.hex_widget)
        layout.addWidget(self.ascii_widget)

        self.addr_widget.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.hex_widget.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.hex_widget.setVerticalScrollBar(self.addr_widget.verticalScrollBar())
        self.ascii_widget.setVerticalScrollBar(self.hex_widget.verticalScrollBar())

        # inspector

        # manage selection

        @Slot()
        def hex_cursor_pos_changed():
            cursor = self.hex_widget.textCursor()

            start_idx = self.hex_widget.to_raw_index(cursor.selectionStart())
            end_idx = self.hex_widget.to_raw_index(cursor.selectionEnd())
            cursor_idx = self.hex_widget.to_raw_index(cursor.position())

            set_selection(self.hex_widget, start_idx, end_idx, cursor_idx)
            set_selection(self.ascii_widget, start_idx, end_idx, cursor_idx)

            on_select(
                self.raw_bytes[min(start_idx, end_idx) :],
                self.raw_bytes[min(start_idx, end_idx) : max(start_idx, end_idx)],
            )

        self.hex_widget.cursorPositionChanged.connect(hex_cursor_pos_changed)

        # root

        self.setLayout(layout)
        self.setFixedWidth(860)

    def set_bytes(self, raw_bytes):
        if len(raw_bytes) >= 10000:
            print(f"too many bytes {len(raw_bytes)}")
            raw_bytes = raw_bytes[:10000]
        self.raw_bytes = raw_bytes

        self.addr_widget.set_bytes(raw_bytes)
        self.hex_widget.set_bytes(raw_bytes)
        self.ascii_widget.set_bytes(raw_bytes)

        set_selection(self.hex_widget, 0, 0, 0)
        set_selection(self.ascii_widget, 0, 0, 0)
