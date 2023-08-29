from struct import unpack_from, calcsize

from PySide6.QtWidgets import QHBoxLayout, QWidget, QTextEdit, QFormLayout, QLabel
from PySide6.QtCore import Slot, Qt
from PySide6.QtGui import QTextCursor

# from src.gbx_structs import GbxVec3Tenb


class AInspector(QHBoxLayout):
    def __init__(self, nb_labels, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.labels = []
        for _ in range(nb_labels):
            self.labels.append(QLabel())
            self.addWidget(self.labels[-1])


class Hex_Inspector(AInspector):
    def inspect(self, raw_bytes):
        for i in range(len(self.labels)):
            text = ""
            for b in raw_bytes[i * 4 : (i + 1) * 4][::-1]:
                text += format(b, "02X")

            self.labels[i].setText(text)


class Count_Inspector(AInspector):
    def inspect(self, raw_bytes):
        self.labels[0].setText(str(len(raw_bytes) + 1))


# class Vec3_tenb_Inspector(AInspector):
#     def inspect(self, raw_bytes):
#         for label in self.labels:
#             label.setText("")

#         if len(raw_bytes) >= 4:
#             for i in range(0, len(raw_bytes) // 4):
#                 if i >= len(self.labels):
#                     break

#                 x = GbxVec3Tenb.parse(raw_bytes[i * 4 : (i + 1) * 4])
#                 self.labels[i].setText(str(x))


def inspector_from_format(format, nb_labels):
    format_size = calcsize(format)

    class _Inspector(QHBoxLayout):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            self.labels = []
            for _ in range(nb_labels):
                self.labels.append(QLabel())
                self.addWidget(self.labels[-1])

        def inspect(self, raw_bytes):
            for label in self.labels:
                label.setText("")

            if len(raw_bytes) >= format_size:
                for i in range(0, len(raw_bytes) // format_size):
                    if i >= len(self.labels):
                        break

                    (x,) = unpack_from(format, raw_bytes, i * format_size)
                    self.labels[i].setText(str(x))

    return _Inspector()


class Inspector(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.count_inspector = Count_Inspector(1)
        self.hex_inspector = Hex_Inspector(4)
        self.uint8_widget = inspector_from_format("<B", 16)
        self.int8_widget = inspector_from_format("<b", 16)
        self.uint16_widget = inspector_from_format("<H", 8)
        self.uint32_widget = inspector_from_format("<I", 4)
        self.int16_widget = inspector_from_format("<h", 8)
        self.int32_widget = inspector_from_format("<i", 4)
        self.float16_widget = inspector_from_format("<e", 4)
        self.float32_widget = inspector_from_format("<f", 4)
        self.uint64_widget = inspector_from_format("<Q", 2)
        self.int64_widget = inspector_from_format("<q", 2)
        # self.vec_tenb_widget = Vec3_tenb_Inspector(4)

        layout = QFormLayout()
        layout.addRow("count", self.count_inspector)
        layout.addRow("hex", self.hex_inspector)
        layout.addRow("UInt16", self.uint16_widget)
        layout.addRow("Int16", self.int16_widget)
        layout.addRow("UInt32", self.uint32_widget)
        layout.addRow("Int32", self.int32_widget)
        layout.addRow("float16", self.float16_widget)
        layout.addRow("float32", self.float32_widget)
        layout.addRow("UInt64", self.uint64_widget)
        layout.addRow("Int64", self.int64_widget)
        layout.addRow("UInt8", self.uint8_widget)
        layout.addRow("Int8", self.int8_widget)
        # layout.addRow("Vec3_tenb", self.vec_tenb_widget)
        self.setLayout(layout)

    def inspect(self, raw_bytes, selection):
        self.count_inspector.inspect(selection)
        self.hex_inspector.inspect(raw_bytes)
        self.uint16_widget.inspect(raw_bytes)
        self.int16_widget.inspect(raw_bytes)
        self.uint32_widget.inspect(raw_bytes)
        self.int32_widget.inspect(raw_bytes)
        self.float16_widget.inspect(raw_bytes)
        self.float32_widget.inspect(raw_bytes)
        self.uint64_widget.inspect(raw_bytes)
        self.int64_widget.inspect(raw_bytes)
        self.uint8_widget.inspect(raw_bytes)
        self.int8_widget.inspect(raw_bytes)
        # self.vec_tenb_widget.inspect(raw_bytes)
