import sys
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTreeWidget, QTreeWidgetItem, QLabel, QInputDialog, QMessageBox,
    QGroupBox, QSplitter, QStatusBar, QShortcut, QAbstractItemView,
    QHeaderView,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QKeySequence, QIcon, QFont, QColor

import monitor_info
import window_manager
import layout_store
from hotkey_manager import SimpleHotkeyManager


STYLESHEET = """
QMainWindow {
    background-color: #1e1e2e;
}
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #45475a;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
    color: #89b4fa;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 5px;
    padding: 7px 16px;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #45475a;
    border-color: #89b4fa;
}
QPushButton:pressed {
    background-color: #585b70;
}
QPushButton#btnSave {
    background-color: #a6e3a1;
    color: #1e1e2e;
    border: none;
    font-weight: bold;
}
QPushButton#btnSave:hover {
    background-color: #94e2d5;
}
QPushButton#btnRestore {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    font-weight: bold;
}
QPushButton#btnRestore:hover {
    background-color: #74c7ec;
}
QPushButton#btnDelete {
    background-color: #f38ba8;
    color: #1e1e2e;
    border: none;
    font-weight: bold;
}
QPushButton#btnDelete:hover {
    background-color: #eba0ac;
}
QTreeWidget {
    background-color: #181825;
    border: 1px solid #45475a;
    border-radius: 4px;
    alternate-background-color: #1e1e2e;
    outline: none;
}
QTreeWidget::item {
    padding: 4px 0;
    border-bottom: 1px solid #313244;
}
QTreeWidget::item:selected {
    background-color: #45475a;
    color: #cdd6f4;
}
QTreeWidget::item:hover {
    background-color: #313244;
}
QHeaderView::section {
    background-color: #313244;
    color: #89b4fa;
    padding: 6px;
    border: none;
    border-bottom: 2px solid #45475a;
    font-weight: bold;
}
QStatusBar {
    background-color: #181825;
    color: #a6adc8;
    border-top: 1px solid #313244;
}
QLabel#monitorTag {
    background-color: #313244;
    border: 1px solid #585b70;
    border-radius: 4px;
    padding: 6px 12px;
}
QLabel#titleTag {
    font-size: 18px;
    font-weight: bold;
    color: #cba6f7;
}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.hotkey_mgr = SimpleHotkeyManager()
        self._init_ui()
        self._refresh_monitors()
        self._refresh_layouts()
        self._register_hotkeys_from_store()

        self._monitor_timer = QTimer(self)
        self._monitor_timer.timeout.connect(self._refresh_monitors)
        self._monitor_timer.start(5000)

    def _init_ui(self):
        self.setWindowTitle("多显示器窗口布局管理器")
        self.setMinimumSize(900, 600)
        self.resize(1000, 680)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 8)
        main_layout.setSpacing(10)

        title_label = QLabel("🖥  多显示器窗口布局管理器")
        title_label.setObjectName("titleTag")
        main_layout.addWidget(title_label)

        monitor_group = QGroupBox("当前显示器")
        monitor_layout = QHBoxLayout(monitor_group)
        monitor_layout.setContentsMargins(12, 20, 12, 12)
        self._monitor_container = monitor_layout
        main_layout.addWidget(monitor_group)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(2)

        layout_group = QGroupBox("布局方案")
        layout_vbox = QVBoxLayout(layout_group)
        layout_vbox.setContentsMargins(8, 20, 8, 8)

        self._layout_tree = QTreeWidget()
        self._layout_tree.setHeaderLabels(["方案名称", "窗口数", "快捷键", "更新时间"])
        self._layout_tree.setColumnCount(4)
        self._layout_tree.setAlternatingRowColors(True)
        self._layout_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self._layout_tree.setRootIsDecorated(False)
        header = self._layout_tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._layout_tree.itemDoubleClicked.connect(self._on_layout_double_clicked)
        layout_vbox.addWidget(self._layout_tree)

        btn_row = QHBoxLayout()
        btn_save = QPushButton("💾 保存当前布局")
        btn_save.setObjectName("btnSave")
        btn_save.clicked.connect(self._on_save_layout)
        btn_row.addWidget(btn_save)

        btn_restore = QPushButton("🔄 恢复选中布局")
        btn_restore.setObjectName("btnRestore")
        btn_restore.clicked.connect(self._on_restore_layout)
        btn_row.addWidget(btn_restore)

        btn_delete = QPushButton("🗑 删除选中布局")
        btn_delete.setObjectName("btnDelete")
        btn_delete.clicked.connect(self._on_delete_layout)
        btn_row.addWidget(btn_delete)
        layout_vbox.addLayout(btn_row)

        btn_row2 = QHBoxLayout()
        btn_rename = QPushButton("✏️ 重命名")
        btn_rename.clicked.connect(self._on_rename_layout)
        btn_row2.addWidget(btn_rename)

        btn_hotkey = QPushButton("⌨️ 设置快捷键")
        btn_hotkey.clicked.connect(self._on_set_hotkey)
        btn_row2.addWidget(btn_hotkey)

        btn_refresh = QPushButton("🔍 刷新窗口列表")
        btn_refresh.clicked.connect(self._refresh_layouts)
        btn_row2.addWidget(btn_refresh)
        layout_vbox.addLayout(btn_row2)

        splitter.addWidget(layout_group)

        window_group = QGroupBox("当前窗口")
        window_vbox = QVBoxLayout(window_group)
        window_vbox.setContentsMargins(8, 20, 8, 8)

        self._window_tree = QTreeWidget()
        self._window_tree.setHeaderLabels(["窗口标题", "进程", "位置", "大小"])
        self._window_tree.setColumnCount(4)
        self._window_tree.setAlternatingRowColors(True)
        self._window_tree.setSelectionMode(QAbstractItemView.NoSelection)
        self._window_tree.setRootIsDecorated(False)
        w_header = self._window_tree.header()
        w_header.setSectionResizeMode(0, QHeaderView.Stretch)
        w_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        w_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        w_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        btn_refresh_win = QPushButton("🔄 刷新窗口")
        btn_refresh_win.clicked.connect(self._refresh_windows)
        window_vbox.addWidget(self._window_tree)
        window_vbox.addWidget(btn_refresh_win)

        splitter.addWidget(window_group)
        splitter.setSizes([450, 550])
        main_layout.addWidget(splitter, 1)

        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("就绪")

        self.setStyleSheet(STYLESHEET)

    def _refresh_monitors(self):
        monitors = monitor_info.get_monitor_details()
        layout = self._monitor_container
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for m in monitors:
            tag = QLabel(f"🖥 {m['name']}  {m['resolution']}  ({m['left']},{m['top']})")
            tag.setObjectName("monitorTag")
            layout.addWidget(tag)
        layout.addStretch()

    def _refresh_windows(self):
        self._window_tree.clear()
        windows = window_manager.enumerate_windows()
        for w in windows:
            pos_str = f"({w['left']}, {w['top']})"
            size_str = f"{w['width']} × {w['height']}"
            item = QTreeWidgetItem([
                w["title"],
                w.get("process_name", ""),
                pos_str,
                size_str,
            ])
            self._window_tree.addTopLevelItem(item)
        self._statusbar.showMessage(f"检测到 {len(windows)} 个可见窗口")

    def _refresh_layouts(self):
        self._layout_tree.clear()
        layouts = layout_store.list_layouts()
        for l in layouts:
            hotkey = l.get("hotkey", "") or "无"
            item = QTreeWidgetItem([
                l["name"],
                str(l["window_count"]),
                hotkey,
                l.get("updated_at", ""),
            ])
            self._layout_tree.addTopLevelItem(item)

    def _get_selected_layout_name(self):
        items = self._layout_tree.selectedItems()
        if not items:
            return None
        return items[0].text(0)

    def _on_save_layout(self):
        name, ok = QInputDialog.getText(self, "保存布局", "请输入布局方案名称：")
        if not ok or not name.strip():
            return
        name = name.strip()
        windows = window_manager.capture_layout()
        monitors = monitor_info.get_monitor_details()
        layout_store.save_layout(name, windows, monitors)
        self._refresh_layouts()
        self._register_hotkeys_from_store()
        self._statusbar.showMessage(f"布局「{name}」已保存，包含 {len(windows)} 个窗口")

    def _on_restore_layout(self):
        name = self._get_selected_layout_name()
        if not name:
            QMessageBox.warning(self, "提示", "请先选择一个布局方案")
            return
        self._do_restore(name)

    def _on_layout_double_clicked(self, item, _col):
        name = item.text(0)
        self._do_restore(name)

    def _do_restore(self, name):
        layout = layout_store.get_layout(name)
        if not layout:
            QMessageBox.warning(self, "错误", f"找不到布局「{name}」")
            return
        windows = layout.get("windows", [])
        restored, skipped = window_manager.restore_layout(windows)
        self._statusbar.showMessage(
            f"布局「{name}」已恢复：{restored} 个窗口成功，{skipped} 个窗口跳过（未运行）"
        )

    def _on_delete_layout(self):
        name = self._get_selected_layout_name()
        if not name:
            QMessageBox.warning(self, "提示", "请先选择一个布局方案")
            return
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除布局「{name}」吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            layout_store.delete_layout(name)
            self._refresh_layouts()
            self._register_hotkeys_from_store()
            self._statusbar.showMessage(f"布局「{name}」已删除")

    def _on_rename_layout(self):
        name = self._get_selected_layout_name()
        if not name:
            QMessageBox.warning(self, "提示", "请先选择一个布局方案")
            return
        new_name, ok = QInputDialog.getText(
            self, "重命名布局", "新名称：", text=name,
        )
        if not ok or not new_name.strip() or new_name.strip() == name:
            return
        layout_store.rename_layout(name, new_name.strip())
        self._refresh_layouts()
        self._register_hotkeys_from_store()
        self._statusbar.showMessage(f"布局已重命名为「{new_name.strip()}」")

    def _on_set_hotkey(self):
        name = self._get_selected_layout_name()
        if not name:
            QMessageBox.warning(self, "提示", "请先选择一个布局方案")
            return
        layout = layout_store.get_layout(name)
        current = layout.get("hotkey", "") if layout else ""
        hotkey, ok = QInputDialog.getText(
            self, "设置快捷键",
            "请输入快捷键（格式如 <ctrl>+<alt>+1, <ctrl>+<shift>+2 等）：\n"
            "修饰键: <ctrl> <alt> <shift> <cmd>\n"
            "字母/数字直接输入，如 a, 1, F1",
            text=current,
        )
        if not ok:
            return
        hotkey = hotkey.strip()
        layout_store.update_hotkey(name, hotkey)
        self._refresh_layouts()
        self._register_hotkeys_from_store()
        if hotkey:
            self._statusbar.showMessage(f"布局「{name}」快捷键已设置为 {hotkey}")
        else:
            self._statusbar.showMessage(f"布局「{name}」快捷键已清除")

    def _register_hotkeys_from_store(self):
        self.hotkey_mgr.clear_all()
        hotkey_map = layout_store.get_hotkey_map()
        registrations = {}
        for name, hk in hotkey_map.items():
            if hk:
                registrations[hk] = lambda n=name: self._do_restore(n)
        if registrations:
            self.hotkey_mgr.register_multiple(registrations)
        self.hotkey_mgr.start()

    def closeEvent(self, event):
        self.hotkey_mgr.stop()
        self._monitor_timer.stop()
        event.accept()
