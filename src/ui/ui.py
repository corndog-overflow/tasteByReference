import sys
import os
import sqlite3
from PySide6 import QtCore, QtWidgets, QtGui
import re 

try:
    from config import DB_NAME
except ImportError:
    DB_NAME = "recipes.db"

BG         = "#3D1F1B"
BG_DARK    = "#1E0E0C"
BG_PANEL   = "#2E1714"
ACCENT     = "#E8DEC8"
ACCENT_DIM = "#A89880"
BORDER     = "#C4B49A"

QSS = f"""
QWidget {{
    background-color: {BG};
    color: {ACCENT};
    font-family: "Courier New";
    font-size: 13px;
}}
QFrame#panel {{
    background-color: {BG_PANEL};
    border: 2px solid {BORDER};
}}
QLabel#panel-title {{
    color: {ACCENT_DIM};
    font-size: 11px;
    letter-spacing: 2px;
    border-bottom: 1px solid {ACCENT_DIM};
    padding-bottom: 4px;
}}
QTextEdit {{
    background-color: {BG_PANEL};
    color: {ACCENT};
    border: none;
    font-family: "Courier New";
    font-size: 13px;
    selection-background-color: {ACCENT_DIM};
    selection-color: {BG_DARK};
}}
QListWidget {{
    background-color: {BG_DARK};
    color: {ACCENT};
    border: 2px solid {BORDER};
    font-family: "Courier New";
    font-size: 12px;
    outline: none;
}}
QListWidget::item {{
    padding: 5px 10px;
    border-bottom: 1px solid {BG_PANEL};
}}
QListWidget::item:selected {{
    background-color: {BG_PANEL};
    color: {ACCENT};
    border-left: 3px solid {ACCENT_DIM};
}}
QListWidget::item:hover {{ background-color: {BG_PANEL}; }}
QLineEdit {{
    background-color: {BG_DARK};
    color: {ACCENT};
    border: 2px solid {BORDER};
    padding: 6px 10px;
    font-family: "Courier New";
    font-size: 12px;
}}
QLineEdit:focus    {{ border: 2px solid {ACCENT}; }}
QLineEdit::placeholder {{ color: {ACCENT_DIM}; }}
QPushButton {{
    background-color: {BG_DARK};
    color: {ACCENT};
    border: 2px solid {BORDER};
    padding: 6px 14px;
    font-family: "Courier New";
    font-size: 12px;
    letter-spacing: 1px;
}}
QPushButton:hover    {{ background-color: {ACCENT};     color: {BG_DARK}; }}
QPushButton:pressed  {{ background-color: {ACCENT_DIM}; color: {BG_DARK}; }}
QPushButton:disabled {{ color: {ACCENT_DIM}; border-color: {BG_PANEL}; }}
QPushButton#go-btn   {{ font-weight: bold; letter-spacing: 2px; min-width: 60px; }}

QPushButton#status {{  /* --- NEW: make status look like a label --- */
    border: none;
    text-align: left;
    padding: 0px;
}}

QLabel#header {{
    font-size: 26px;
    letter-spacing: 4px;
    color: {ACCENT};
    border-bottom: 2px solid {ACCENT_DIM};
    padding-bottom: 8px;
}}
QLabel#subheader {{ font-size: 11px; color: {ACCENT_DIM}; letter-spacing: 2px; }}

QScrollBar:vertical {{ background: {BG_DARK}; width: 8px; border: none; }}
QScrollBar::handle:vertical {{ background: {ACCENT_DIM}; min-height: 20px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""


def query_db(ingredient="", time_val="", cuisine="", query="") -> list[dict]:
    if not os.path.exists(DB_NAME):
        return []
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row

    clauses, params = [], []
    if ingredient:
        clauses.append("main_ingredient LIKE ?");  params.append(f"%{ingredient}%")
    if cuisine:
        clauses.append("cuisine LIKE ?");           params.append(f"%{cuisine}%")
    if time_val:
        clauses.append("total_time LIKE ?");        params.append(f"%{time_val}%")
    if query:
        clauses.append("(instructions LIKE ? OR source_url LIKE ?)")
        params.extend([f"%{query}%", f"%{query}%"])

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows  = conn.execute(f"SELECT * FROM meshi {where} LIMIT 50", params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def build_left_panel_text(row: dict) -> str:
    raw_ingredients = row.get("ingredients") or "no ingredients found."

    formatted_ingredients = re.sub(r"\s*(\d+\.)\s*", r"\n\1 ", raw_ingredients).strip()

    lines = [
        f"title:  {row.get('title') or 'n/a'}",
        f"author:           {row.get('author') or 'n/a'}",
        f"time:             {row.get('total_time') or 'n/a'} (minutes)",
        f"cuisine:          {row.get('cuisine') or 'n/a'}",
        "",
        "ingredients:",
        formatted_ingredients,  
        "",
        "source:",
        f"{row.get('source_url') or 'n/a'}",
    ]

    nutrition = (row.get("nutritional_info") or "").strip()
    if nutrition and nutrition.lower() not in ("unknown", "null", "none", ""):
        lines += ["", "─" * 32, "nutritional info:", nutrition]

    return "\n".join(lines)

def result_label(row: dict) -> str:
    ingredient = row.get("title") or "?"
    cuisine    = row.get("cuisine") or ""
    time_raw   = (row.get("total_time")+" minutes" or "").strip()
    time_part  = f"({time_raw} min)" if time_raw and time_raw.lower() != "unknown" else ""
    return "  ·  ".join(p for p in [ingredient, cuisine, time_part] if p)


def make_panel(title: str):
    frame = QtWidgets.QFrame()
    frame.setObjectName("panel")
    layout = QtWidgets.QVBoxLayout(frame)

    lbl = QtWidgets.QLabel(title.upper())
    lbl.setObjectName("panel-title")
    layout.addWidget(lbl)

    area = QtWidgets.QTextEdit()
    area.setReadOnly(True)
    layout.addWidget(area)

    return frame, area


class RecipeWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("taste by reference")
        self.resize(960, 660)
        self._results = []
        self._build_ui()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)

        root.addWidget(self._make_header())

        self.results_list = QtWidgets.QListWidget()
        self.results_list.setMaximumHeight(130)
        self.results_list.setVisible(False)
        self.results_list.currentRowChanged.connect(self._on_result_selected)
        root.addWidget(self.results_list)

        panels = QtWidgets.QHBoxLayout()
        self.left_panel, self.left_area = make_panel("Ingredients & Info")
        self.right_panel, self.right_area = make_panel("Instructions")
        panels.addWidget(self.left_panel)
        panels.addWidget(self.right_panel)
        root.addLayout(panels, stretch=1)

        self.status_btn = QtWidgets.QPushButton("")
        self.status_btn.setObjectName("status")
        self.status_btn.setFlat(True)
        self.status_btn.clicked.connect(self._toggle_results)
        root.addWidget(self.status_btn)

        root.addWidget(self._make_search_bar())

    def _make_header(self):
        box = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(box)

        title = QtWidgets.QLabel("taste by reference")
        title.setStyleSheet("font-weight: bold;")
        title.setObjectName("header")
        title.setAlignment(QtCore.Qt.AlignCenter)

        sub = QtWidgets.QLabel("> search by ingredient, cuisine, or time.")
        sub.setObjectName("subheader")
        sub.setAlignment(QtCore.Qt.AlignCenter)

        lay.addWidget(title)
        lay.addWidget(sub)
        return box

    def _make_search_bar(self):
        box = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(box)

        fields = [("main ingredient", 3), ("time", 1), ("cuisine", 1), ("search...", 4)]
        self.inputs = {}

        for placeholder, stretch in fields:
            f = QtWidgets.QLineEdit()
            f.setPlaceholderText(placeholder)
            f.returnPressed.connect(self.on_search)
            self.inputs[placeholder] = f
            lay.addWidget(f, stretch=stretch)

        go = QtWidgets.QPushButton("GO")
        go.clicked.connect(self.on_search)
        lay.addWidget(go)

        return box

    def _toggle_results(self):
        if self._results:
            visible = not self.results_list.isVisible()
            self.results_list.setVisible(visible)

    def on_search(self):
        ingredient = self.inputs["main ingredient"].text().strip()
        time_val   = self.inputs["time"].text().strip()
        cuisine    = self.inputs["cuisine"].text().strip()
        query      = self.inputs["search..."].text().strip()

        if not any([ingredient, time_val, cuisine, query]):
            self.status_btn.setText("> enter at least one search term.")
            return

        self._results = query_db(ingredient, time_val, cuisine, query)

        if not self._results:
            self.status_btn.setText("> no results found.")
            self.results_list.setVisible(False)
            self.left_area.clear()
            self.right_area.clear()
            return

        self.status_btn.setText(f"> {len(self._results)} result(s) found. (click to toggle)")

        self.results_list.clear()
        for row in self._results:
            self.results_list.addItem(result_label(row))

        self.results_list.setVisible(True)
        self.results_list.setCurrentRow(0)

    def _on_result_selected(self, index: int):
        if index < 0 or index >= len(self._results):
            return

        row = self._results[index]
        self.left_area.setPlainText(build_left_panel_text(row))

        raw_instructions = row.get("instructions") or "no instructions found."

        formatted = re.sub(r"\s*(\d+\.)\s*", r"\n\1 ", raw_instructions).strip()

        self.right_area.setPlainText(formatted)
        self.results_list.setVisible(False)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(QSS)

    widget = RecipeWidget()
    widget.show()

    sys.exit(app.exec())