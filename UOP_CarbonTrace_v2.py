import sys
import numpy as np
from math import log10
import matplotlib.pyplot as plt
import matplotlib as mpl

# --- FIX 1: Safely disable shortcuts (Prevents "keymap" crashes) ---
keys_to_disable = ['keymap.yscale', 'keymap.xscale', 'keymap.all_axes']
for key in keys_to_disable:
    try:
        mpl.rcParams[key] = []
    except KeyError:
        pass 

# UI Imports
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QGroupBox, QPushButton, QLabel, 
                               QLineEdit, QRadioButton, QFileDialog, QFormLayout,
                               QFrame, QMessageBox, QScrollArea, QSizePolicy, QButtonGroup)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QCursor

# Matplotlib Integration
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MplCanvas(FigureCanvas):
    """A canvas that integrates matplotlib into Qt."""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        self.axes.axis('off')
        super().__init__(self.fig)

class CarbonTraceWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UOP CarbonTrace - Graph Digitizer")
        self.resize(1200, 800)

        # -- Data State --
        self.img = None
        self.calibration = {
            'x_min': {'pixel': None, 'val': None, 'name': 'X Min'},
            'x_max': {'pixel': None, 'val': None, 'name': 'X Max'},
            'y_min': {'pixel': None, 'val': None, 'name': 'Y Min'},
            'y_max': {'pixel': None, 'val': None, 'name': 'Y Max'}
        }
        self.data_points = [] 
        self.current_state = None 

        # -- Scale State --
        self.x_scale_type = 'linear'
        self.y_scale_type = 'linear'

        # -- UI Setup --
        self.init_ui()
        self.apply_carbon_theme()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # 1. Sidebar
        sidebar = QScrollArea()
        sidebar.setWidgetResizable(True)
        sidebar.setFixedWidth(320)
        sidebar_content = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_content)
        sidebar_layout.setAlignment(Qt.AlignTop)

        # Header
        lbl_header = QLabel("UOP CarbonTrace")
        lbl_header.setStyleSheet("font-size: 18px; font-weight: bold; color: #00E676; margin-bottom: 10px;")
        lbl_header.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(lbl_header)

        # -- Load Section --
        grp_load = QGroupBox("1. Source Image")
        l_load = QVBoxLayout()
        self.btn_load = QPushButton("Load Graph Image")
        self.btn_load.clicked.connect(self.load_image)
        l_load.addWidget(self.btn_load)
        grp_load.setLayout(l_load)
        sidebar_layout.addWidget(grp_load)

        # -- Calibration Section --
        grp_cal = QGroupBox("2. Calibration")
        l_cal = QFormLayout()
        
        self.btn_xmin = QPushButton("Set X Min")
        self.in_xmin = QLineEdit(""); self.in_xmin.setPlaceholderText("Value...")
        self.lbl_xmin_stat = QLabel("❌")
        
        self.btn_xmax = QPushButton("Set X Max")
        self.in_xmax = QLineEdit(""); self.in_xmax.setPlaceholderText("Value...")
        self.lbl_xmax_stat = QLabel("❌")
        
        self.btn_ymin = QPushButton("Set Y Min")
        self.in_ymin = QLineEdit(""); self.in_ymin.setPlaceholderText("Value...")
        self.lbl_ymin_stat = QLabel("❌")
        
        self.btn_ymax = QPushButton("Set Y Max")
        self.in_ymax = QLineEdit(""); self.in_ymax.setPlaceholderText("Value...")
        self.lbl_ymax_stat = QLabel("❌")

        # Connect buttons
        self.btn_xmin.clicked.connect(lambda: self.start_calibration('x_min'))
        self.btn_xmax.clicked.connect(lambda: self.start_calibration('x_max'))
        self.btn_ymin.clicked.connect(lambda: self.start_calibration('y_min'))
        self.btn_ymax.clicked.connect(lambda: self.start_calibration('y_max'))

        l_cal.addRow(self.btn_xmin, self.create_row(self.in_xmin, self.lbl_xmin_stat))
        l_cal.addRow(self.btn_xmax, self.create_row(self.in_xmax, self.lbl_xmax_stat))
        l_cal.addRow(self.btn_ymin, self.create_row(self.in_ymin, self.lbl_ymin_stat))
        l_cal.addRow(self.btn_ymax, self.create_row(self.in_ymax, self.lbl_ymax_stat))

        # --- FIX 2: Strict Button Groups (Prevents "Disappearing Dot") ---
        # We group the radio buttons so one MUST always be active.
        
        # X Scale
        self.bg_x = QButtonGroup(self) # Create strict group
        self.rad_x_lin = QRadioButton("X Linear")
        self.rad_x_log = QRadioButton("X Log")
        self.bg_x.addButton(self.rad_x_lin)
        self.bg_x.addButton(self.rad_x_log)
        self.rad_x_lin.setChecked(True) # Force initial state
        self.bg_x.buttonClicked.connect(self.set_x_scale_type)

        # Y Scale
        self.bg_y = QButtonGroup(self) # Create strict group
        self.rad_y_lin = QRadioButton("Y Linear")
        self.rad_y_log = QRadioButton("Y Log")
        self.bg_y.addButton(self.rad_y_lin)
        self.bg_y.addButton(self.rad_y_log)
        self.rad_y_lin.setChecked(True) # Force initial state
        self.bg_y.buttonClicked.connect(self.set_y_scale_type)
        
        # Layout
        scale_row = QHBoxLayout()
        scale_row.addWidget(self.rad_x_lin); scale_row.addWidget(self.rad_x_log)
        l_cal.addRow("X Scale:", scale_row)
        scale_row2 = QHBoxLayout()
        scale_row2.addWidget(self.rad_y_lin); scale_row2.addWidget(self.rad_y_log)
        l_cal.addRow("Y Scale:", scale_row2)
        
        grp_cal.setLayout(l_cal)
        sidebar_layout.addWidget(grp_cal)

        # -- Digitization Section --
        grp_dig = QGroupBox("3. Capture Data")
        l_dig = QVBoxLayout()
        
        self.btn_pick = QPushButton("Manual Trace")
        self.btn_pick.setCheckable(True)
        self.btn_pick.clicked.connect(self.toggle_picking)
        
        self.btn_color = QPushButton("Auto-Trace by Color")
        self.btn_color.clicked.connect(self.select_by_color)

        color_layout = QFormLayout()
        self.in_r = QLineEdit("0"); self.in_g = QLineEdit("0"); self.in_b = QLineEdit("0")
        self.in_tol = QLineEdit("10")
        color_layout.addRow("R (0-255):", self.in_r)
        color_layout.addRow("G (0-255):", self.in_g)
        color_layout.addRow("B (0-255):", self.in_b)
        color_layout.addRow("Tol (%):", self.in_tol)
        
        self.btn_clear = QPushButton("Clear Traces")
        self.btn_clear.clicked.connect(self.clear_points)

        l_dig.addWidget(self.btn_pick)
        l_dig.addWidget(self.btn_color)
        l_dig.addLayout(color_layout)
        l_dig.addWidget(self.btn_clear)
        grp_dig.setLayout(l_dig)
        sidebar_layout.addWidget(grp_dig)

        # -- Export Section --
        grp_out = QGroupBox("4. Export")
        l_out = QVBoxLayout()
        self.btn_save = QPushButton("Save Data (CSV)")
        self.btn_save.clicked.connect(self.save_data)
        l_out.addWidget(self.btn_save)
        grp_out.setLayout(l_out)
        sidebar_layout.addWidget(grp_out)

        # Status Label
        self.lbl_hint = QLabel("Ready. Load a graph to begin.")
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setStyleSheet("font-weight: bold; color: #00E676; margin-top: 10px;")
        sidebar_layout.addWidget(self.lbl_hint)

        sidebar.setWidget(sidebar_content)
        layout.addWidget(sidebar)

        # 2. Plot Area
        plot_container = QWidget()
        plot_layout = QVBoxLayout(plot_container)
        
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        plot_layout.addWidget(self.canvas)
        layout.addWidget(plot_container)

        self.cid_click = self.canvas.mpl_connect('button_press_event', self.on_canvas_click)

    def create_row(self, widget1, widget2):
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(0,0,0,0)
        l.addWidget(widget1)
        l.addWidget(widget2)
        return w

    def apply_carbon_theme(self):
        style = """
        QMainWindow { background-color: #212121; }
        QLabel { color: #f5f5f5; font-family: 'Segoe UI', sans-serif; font-size: 13px; }
        QGroupBox { 
            color: #00E676; font-weight: bold; border: 1px solid #616161; 
            margin-top: 20px; border-radius: 4px; padding-top: 10px; 
            background-color: #2b2b2b;
        }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        QPushButton { 
            background-color: #424242; color: white; border: 1px solid #757575; 
            padding: 8px; border-radius: 4px; font-weight: bold;
        }
        QPushButton:hover { background-color: #616161; border: 1px solid #00E676; }
        QPushButton:checked { background-color: #00E676; color: black; border: 1px solid #00E676; }
        QLineEdit { 
            background-color: #333333; color: #00E676; border: 1px solid #616161; 
            padding: 6px; border-radius: 4px; font-size: 13px;
        }
        QRadioButton { color: #f5f5f5; }
        QScrollArea { border: none; background-color: #212121; }
        """
        self.setStyleSheet(style)

    # -- Explicit Scale Handlers --
    def set_x_scale_type(self):
        if self.rad_x_lin.isChecked():
            self.x_scale_type = 'linear'
        elif self.rad_x_log.isChecked():
            self.x_scale_type = 'log'

    def set_y_scale_type(self):
        if self.rad_y_lin.isChecked():
            self.y_scale_type = 'linear'
        elif self.rad_y_log.isChecked():
            self.y_scale_type = 'log'

    # -- Logic --
    def load_image(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open Graph", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if not filename: return
        self.img = plt.imread(filename)
        self.canvas.axes.clear()
        self.canvas.axes.imshow(self.img)
        self.canvas.axes.axis('off')
        self.canvas.draw()
        self.lbl_hint.setText("Graph loaded. Please calibrate axes.")

    def start_calibration(self, key):
        if self.img is None:
            self.lbl_hint.setText("Please load an image first.")
            return
        self.current_state = key
        self.lbl_hint.setText(f"Click the location for {key}.")
        self.canvas.setCursor(Qt.ArrowCursor)

    def toggle_picking(self):
        if self.btn_pick.isChecked():
            self.current_state = 'picking_points'
            self.lbl_hint.setText("Click to trace points. Right-click to undo.")
            self.canvas.setCursor(Qt.CrossCursor)
        else:
            self.current_state = None
            self.lbl_hint.setText("Tracing paused.")
            self.canvas.setCursor(Qt.ArrowCursor)

    def on_canvas_click(self, event):
        if event.inaxes != self.canvas.axes: return
        
        if self.current_state in self.calibration:
            key = self.current_state
            if key.startswith('x'): self.calibration[key]['pixel'] = event.xdata
            else: self.calibration[key]['pixel'] = event.ydata
            
            getattr(self, f"lbl_{key.replace('_','')}_stat").setText("✅")
            self.lbl_hint.setText(f"{key} set. Input the value on the left.")
            
            self.canvas.axes.plot(event.xdata, event.ydata, 'x', color='#00E676', markersize=12, markeredgewidth=2)
            self.canvas.draw()
            self.current_state = None
            self.canvas.setCursor(Qt.ArrowCursor)
        
        elif self.current_state == 'picking_points':
            if event.button == 1: 
                self.data_points.append((event.xdata, event.ydata))
                self.canvas.axes.plot(event.xdata, event.ydata, '.', color='#00E676', markersize=8)
                self.canvas.draw()
                self.canvas.setCursor(Qt.CrossCursor)
            elif event.button == 3: 
                if self.data_points:
                    self.data_points.pop()
                    self.redraw_plot()
                    self.canvas.setCursor(Qt.CrossCursor)

    def select_by_color(self):
        if self.img is None: return
        try:
            r, g, b = int(self.in_r.text()), int(self.in_g.text()), int(self.in_b.text())
            tol = float(self.in_tol.text()) / 100.0
        except ValueError:
            self.lbl_hint.setText("Invalid color inputs.")
            return

        target = np.array([r, g, b]) / 255.0
        img_rgb = self.img[:, :, :3] 
        dist = np.linalg.norm(img_rgb - target, axis=2)
        y_idx, x_idx = np.where(dist < tol)
        
        unique_x = np.unique(x_idx)
        new_points = []
        for ux in unique_x:
            uy = np.mean(y_idx[x_idx == ux])
            new_points.append((ux, uy))
        
        self.data_points.extend(new_points)
        x_plot = [p[0] for p in new_points]
        y_plot = [p[1] for p in new_points]
        self.canvas.axes.plot(x_plot, y_plot, '.', color='#00E676', markersize=2, alpha=0.5)
        self.canvas.draw()
        self.lbl_hint.setText(f"Auto-traced {len(new_points)} points.")

    def clear_points(self):
        self.data_points = []
        self.redraw_plot()

    def redraw_plot(self):
        if self.img is None: return
        self.canvas.axes.clear()
        self.canvas.axes.imshow(self.img)
        self.canvas.axes.axis('off')
        
        for key, data in self.calibration.items():
            if data['pixel'] is not None:
                color = '#00E676'
                if key.startswith('x'): self.canvas.axes.axvline(data['pixel'], color=color, linestyle='--', alpha=0.5)
                else: self.canvas.axes.axhline(data['pixel'], color=color, linestyle='--', alpha=0.5)

        if self.data_points:
            xs, ys = zip(*self.data_points)
            self.canvas.axes.plot(xs, ys, '.', color='#00E676', markersize=8)
        self.canvas.draw()

    def save_data(self):
        # Validation
        missing_cal = []
        for key, data in self.calibration.items():
            if data['pixel'] is None:
                missing_cal.append(data['name'])
        
        if missing_cal:
            msg = "You forgot to set the location for:\n" + "\n".join(f"- {m}" for m in missing_cal)
            QMessageBox.warning(self, "Calibration Missing", msg)
            return

        if not self.data_points:
            QMessageBox.warning(self, "Data Error", "No trace data points found.")
            return

        try:
            if not self.in_xmin.text() or not self.in_xmax.text() or not self.in_ymin.text() or not self.in_ymax.text():
                 QMessageBox.warning(self, "Input Error", "Please enter values for all 4 axes limits.")
                 return

            cal = self.calibration
            cal['x_min']['val'] = float(self.in_xmin.text())
            cal['x_max']['val'] = float(self.in_xmax.text())
            cal['y_min']['val'] = float(self.in_ymin.text())
            cal['y_max']['val'] = float(self.in_ymax.text())
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Axes values must be valid numbers.")
            return

        real_data = []
        x1_px, x2_px = cal['x_min']['pixel'], cal['x_max']['pixel']
        x1_val, x2_val = cal['x_min']['val'], cal['x_max']['val']
        y1_px, y2_px = cal['y_min']['pixel'], cal['y_max']['pixel']
        y1_val, y2_val = cal['y_min']['val'], cal['y_max']['val']

        if self.x_scale_type == 'log':
            x1_val, x2_val = log10(x1_val), log10(x2_val)
        
        if self.y_scale_type == 'log':
            y1_val, y2_val = log10(y1_val), log10(y2_val)

        for px, py in self.data_points:
            x_res = x1_val + (px - x1_px) * (x2_val - x1_val) / (x2_px - x1_px)
            y_res = y1_val + (py - y1_px) * (y2_val - y1_val) / (y2_px - y1_px)
            
            if self.x_scale_type == 'log': x_res = 10**x_res
            if self.y_scale_type == 'log': y_res = 10**y_res
            real_data.append((x_res, y_res))

        path, _ = QFileDialog.getSaveFileName(self, "Export Data - Enter Filename", "", "CSV Files (*.csv)")
        
        if path:
            with open(path, 'w') as f:
                f.write("x,y\n")
                for x, y in real_data:
                    f.write(f"{x},{y}\n")
            self.lbl_hint.setText(f"Export successful: {path}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CarbonTraceWindow()
    window.show()
    sys.exit(app.exec())