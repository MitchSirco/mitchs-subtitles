import sys
import re
import argparse
from bisect import bisect_right
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QVBoxLayout, QWidget,
    QLabel, QDoubleSpinBox, QComboBox, QPushButton, QGroupBox, QHBoxLayout, QMessageBox,
    QStatusBar, QSlider, QToolBar, QAction
)
from PyQt5.QtCore import Qt, QPointF, QTimer, QRectF
from PyQt5.QtGui import QPainterPath, QPen, QColor, QBrush, QKeySequence, QWheelEvent, QPainter

def time_str_to_seconds(time_str):
    parts = time_str.split(':')
    if len(parts) == 3:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds_part = parts[2]
    elif len(parts) == 2:
        hours = 0
        minutes = int(parts[0])
        seconds_part = parts[1]
    else:
        hours = 0
        minutes = 0
        seconds_part = parts[0]
    
    if '.' in seconds_part:
        sec, ms = seconds_part.split('.')
        seconds = int(sec)
        ms = int(ms.ljust(2, '0')[:2])
    else:
        seconds = int(seconds_part)
        ms = 0
        
    return hours * 3600 + minutes * 60 + seconds + ms / 100.0

def seconds_to_ass_time(total_seconds):
    total_hundredths = round(total_seconds * 100)
    hours = total_hundredths // 360000
    remaining = total_hundredths % 360000
    minutes = remaining // 6000
    remaining_sec = remaining % 6000
    seconds = remaining_sec // 100
    hundredths = remaining_sec % 100
    return f"{hours}:{minutes:02d}:{seconds:02d}.{hundredths:02d}"

def interpolate_linear(p0, p1, t):
    return (
        p0[0] + (p1[0] - p0[0]) * t,
        p0[1] + (p1[1] - p0[1]) * t
    )

def interpolate_bezier(p0, p1, p2, p3, t):
    t2 = t * t
    t3 = t2 * t
    return (
        0.5 * (2 * p1[0] + t * (-p0[0] + p2[0]) + t2 * (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) + t3 * (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0])),
        0.5 * (2 * p1[1] + t * (-p0[1] + p2[1]) + t2 * (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) + t3 * (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]))
    )

class AnchorPoint:
    def __init__(self, x, y, time, text, index, style, actor):
        self.x = x
        self.y = y
        self.time = time
        self.text = text
        self.index = index
        self.style = style
        self.actor = actor
        self.original_x = x
        self.original_y = y

class ZoomableGraphicsView(QGraphicsView):
    def __init__(self, width, height, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setSceneRect(0, 0, width, height)
        self.width = width
        self.height = height
        self.anchor_points = []
        self.path_points = []
        self.animation_index = 0
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.animate_snake)
        self.animation_speed = 50  # ms per frame
        self.animation_running = False
        self.zoom_level = 1.0
        
        # Set up scene with a reasonable default view
        self.fitInView(QRectF(0, 0, width, height), Qt.KeepAspectRatio)
        
    def set_anchor_points(self, anchor_points):
        self.anchor_points = anchor_points
        self.draw_scene()
        
    def set_path_points(self, path_points):
        self.path_points = path_points
        
    def draw_scene(self):
        self.scene.clear()
        
        # Draw grid
        grid_pen = QPen(QColor(80, 80, 80))
        grid_pen.setWidth(1)

        
        # Draw only major grid lines (every 500 units)
        for x in range(0, self.width + 1, 500):
            self.scene.addLine(x, 0, x, self.height, grid_pen)
            text = self.scene.addText(str(x))
            text.setPos(x - 10, self.height - 30)
            text.setDefaultTextColor(QColor(200, 200, 200))
            text.setZValue(10)
        
        for y in range(0, self.height + 1, 500):
            self.scene.addLine(0, y, self.width, y, grid_pen)
            text = self.scene.addText(str(y))
            text.setPos(10, y - 15)
            text.setDefaultTextColor(QColor(200, 200, 200))
            text.setZValue(10)
            
        
        # Draw origin
        origin = self.scene.addRect(0, 0, 5, 5, QPen(Qt.NoPen), QBrush(QColor(255, 100, 100)))
        origin.setZValue(10)
        
        # Draw path if we have points
        if self.path_points:
            path = QPainterPath()
            path.moveTo(self.path_points[0][0], self.path_points[0][1])
            
            for i in range(1, len(self.path_points)):
                path.lineTo(self.path_points[i][0], self.path_points[i][1])
            
            self.scene.addPath(path, QPen(QColor(0, 200, 255), 2))
        
        # Draw anchor points
        for point in self.anchor_points:
            # Draw original position
            orig = self.scene.addEllipse(
                point.original_x - 3, 
                point.original_y - 3, 
                6, 6, 
                QPen(Qt.NoPen), 
                QBrush(QColor(100, 100, 100, 150)))
            orig.setZValue(5)
            
            # Draw current position
            curr = self.scene.addEllipse(
                point.x - 5, 
                point.y - 5, 
                10, 10, 
                QPen(Qt.NoPen), 
                QBrush(QColor(255, 87, 51, 200)))
            curr.setZValue(10)
            
            # Draw connection line
            line = self.scene.addLine(
                point.original_x, 
                point.original_y, 
                point.x, 
                point.y, 
                QPen(QColor(255, 200, 0), 1))
            line.setZValue(1)
            
            # Draw text label
            text = self.scene.addText(f"{point.index+1} ({point.x},{point.y}): {point.text} ")
            text.setPos(point.x + 10, point.y - 15)
            text.setDefaultTextColor(QColor(255, 255, 255))
            text.setDefaultTextColor(Qt.black)
            text.setZValue(10)
            
        # Draw current animation position if running
        if self.animation_running and self.path_points:
            x, y = self.path_points[self.animation_index][:2]
            anim = self.scene.addEllipse(
                x - 8, 
                y - 8, 
                16, 16, 
                QPen(Qt.NoPen), 
                QBrush(QColor(0, 255, 100, 200)))
            anim.setZValue(15)
            
            text = self.scene.addText(f"Frame: {self.animation_index+1}/{len(self.path_points)}")
            text.setPos(20, 20)
            text.setDefaultTextColor(QColor(0, 255, 100))
            text.setZValue(15)
            
    def wheelEvent(self, event: QWheelEvent):
        zoom_factor = 1.2
        if event.angleDelta().y() > 0:
            # Zoom in
            self.zoom_level *= zoom_factor
            self.scale(zoom_factor, zoom_factor)
        else:
            # Zoom out
            self.zoom_level /= zoom_factor
            self.scale(1/zoom_factor, 1/zoom_factor)
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_R:
            self.fitInView(QRectF(0, 0, self.width, self.height), Qt.KeepAspectRatio)
            self.zoom_level = 1.0
        super().keyPressEvent(event)
        
    def start_animation(self):
        if self.path_points:
            self.animation_index = 0
            self.animation_running = True
            self.animation_timer.start(self.animation_speed)
            
    def stop_animation(self):
        self.animation_running = False
        self.animation_timer.stop()
        self.draw_scene()

    def animate_snake(self):
        if self.animation_index < len(self.path_points) - 1:
            self.animation_index += 1
            self.draw_scene()
        else:
            self.stop_animation()


class SnakeGeneratorUI(QMainWindow):
    def __init__(self, input_file, output_file, width=2560, height=1440):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.width = width
        self.height = height
        self.anchor_points = []
        self.path_points = []
        self.path_segments_data = []
        
        self.setWindowTitle("Snake Subtitle Generator")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create toolbar
        toolbar = QToolBar("Tools")
        self.addToolBar(toolbar)
        
        # Zoom actions
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcut(QKeySequence.ZoomIn)
        zoom_in_action.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcut(QKeySequence.ZoomOut)
        zoom_out_action.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_action)
        
        reset_zoom_action = QAction("Reset View", self)
        reset_zoom_action.setShortcut("R")
        reset_zoom_action.triggered.connect(self.reset_view)
        toolbar.addAction(reset_zoom_action)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Create main layout
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        
        # Create preview area
        preview_group = QGroupBox("Preview (Drag to pan, Mouse wheel to zoom)")
        preview_layout = QVBoxLayout()
        self.preview = ZoomableGraphicsView(self.width, self.height)
        preview_layout.addWidget(self.preview)
        preview_group.setLayout(preview_layout)
        
        # Create controls area
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout()
        
        # Resolution settings
        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("Width:"))
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(100, 10000)
        self.width_spin.setValue(self.width)
        self.width_spin.valueChanged.connect(self.update_resolution)
        res_layout.addWidget(self.width_spin)
        
        res_layout.addWidget(QLabel("Height:"))
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(100, 10000)
        self.height_spin.setValue(self.height)
        self.height_spin.valueChanged.connect(self.update_resolution)
        res_layout.addWidget(self.height_spin)
        controls_layout.addLayout(res_layout)
        
        # Interpolation settings
        controls_layout.addWidget(QLabel("Interpolation:"))
        self.interpolation_combo = QComboBox()
        self.interpolation_combo.addItems(["Linear", "Bézier"])
        self.interpolation_combo.setCurrentIndex(1)
        self.interpolation_combo.currentIndexChanged.connect(self.update_path)
        controls_layout.addWidget(self.interpolation_combo)
        
        # Step size
        controls_layout.addWidget(QLabel("Step Size (seconds):"))
        self.step_spin = QDoubleSpinBox()
        self.step_spin.setRange(0.01, 1.0)
        self.step_spin.setValue(0.1)
        self.step_spin.setSingleStep(0.01)
        self.step_spin.valueChanged.connect(self.update_path)
        controls_layout.addWidget(self.step_spin)
        
        # Display mode
        controls_layout.addWidget(QLabel("Display Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Sequential (each point disappears)", 
            "Persistent (points remain visible)"
        ])
        controls_layout.addWidget(self.mode_combo)
        
        # Point duration
        controls_layout.addWidget(QLabel("Point Duration (seconds):"))
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.01, 1.0)
        self.duration_spin.setValue(0.1)
        self.duration_spin.setSingleStep(0.01)
        controls_layout.addWidget(self.duration_spin)
        
        # Text mode
        controls_layout.addWidget(QLabel("Text Mode:"))
        self.text_mode_combo = QComboBox()
        self.text_mode_combo.addItems([
            "Use first point's text for all", 
            "Use each point's individual text"
        ])
        controls_layout.addWidget(self.text_mode_combo)
        
        # Buttons
        self.preview_btn = QPushButton("Preview Animation")
        self.preview_btn.clicked.connect(self.preview_animation)
        controls_layout.addWidget(self.preview_btn)
        
        self.generate_btn = QPushButton("Generate ASS File")
        self.generate_btn.clicked.connect(self.generate_ass)
        controls_layout.addWidget(self.generate_btn)
        
        self.reload_btn = QPushButton("Reload Input file")
        self.reload_btn.clicked.connect(self.reload_input_file)
        controls_layout.addWidget(self.reload_btn)
        
        
        self.reset_btn = QPushButton("Reset Positions")
        self.reset_btn.clicked.connect(self.reset_positions)
        controls_layout.addWidget(self.reset_btn)
        
        controls_group.setLayout(controls_layout)
        
        # Add to main layout
        main_layout.addWidget(preview_group, 3)
        main_layout.addWidget(controls_group, 1)
        
        self.setCentralWidget(main_widget)
        
        # Load input file
        self.load_input_file()
        
    def zoom_in(self):
        self.preview.zoom_level *= 1.2
        self.preview.scale(1.2, 1.2)
        self.update_status()
        
    def zoom_out(self):
        self.preview.zoom_level /= 1.2
        self.preview.scale(1/1.2, 1/1.2)
        self.update_status()
        
    def reset_view(self):
        self.preview.fitInView(QRectF(0, 0, self.preview.width, self.preview.height), Qt.KeepAspectRatio)
        self.preview.zoom_level = 1.0
        self.update_status()
        
    def update_status(self):
        self.status_bar.showMessage(f"Zoom: {self.preview.zoom_level:.1f}x | Press R to reset view")
        
    def update_resolution(self):
        self.width = int(self.width_spin.value())
        self.height = int(self.height_spin.value())
        self.preview.width = self.width
        self.preview.height = self.height
        self.preview.setSceneRect(0, 0, self.width, self.height)
        self.reset_view()
        self.update_path()
        
    def load_input_file(self):
        events = []
        other_lines = []
        anchor_times = []

        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("Dialogue: "):
                        content = line[len("Dialogue: "):]
                        parts = content.split(',', 9)
                        if len(parts) < 10:
                            other_lines.append(line)
                            continue
                        
                        layer, start_str, end_str, style, name, marginL, marginR, marginV, effect, text = parts
                        
                        match = re.search(r'\\pos\((\d+),(\d+)\)', text)
                        if match:
                            x, y = map(int, match.groups())
                            clean_text = re.sub(r'\\pos\(\d+,\d+\)', '', text).strip()
                            
                            start_sec = time_str_to_seconds(start_str)
                            
                            events.append({
                                'layer': layer,
                                'start_sec': start_sec,
                                'end_sec': time_str_to_seconds(end_str),
                                'x': x, 'y': y,
                                'style': style,
                                'name': name,
                                'marginL': marginL,
                                'marginR': marginR,
                                'marginV': marginV,
                                'effect': effect,
                                'text': clean_text,
                                'original_line': line
                            })
                            anchor_times.append(start_sec)
                            continue
                    other_lines.append(line)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load input file:\n{str(e)}")
            return
        
        if len(events) < 2:
            QMessageBox.warning(self, "Warning", "Need at least 2 anchor points")
            return
        
        # Create AnchorPoint objects
        self.anchor_points = []
        for i, event in enumerate(events):
            self.anchor_points.append(AnchorPoint(
                event['x'], 
                event['y'], 
                event['start_sec'], 
                event['text'], 
                i,
                event['style'],
                event['name']

            ))
        self.other_lines = other_lines
        # Update preview
        self.update_path()
        
    def update_path(self):
        if len(self.anchor_points) < 2:
            return
            
        # Sort anchor points by time
        sorted_anchors = sorted(
            [p for p in self.anchor_points if p.actor != "noAnim"], key=lambda p: p.time)

        # Identify path segments based on "start" and "end" actors
        path_segments = []
        current_segment = []
        in_segment = False

        # Default to a single path if no start/end markers
        if not any(p.actor in ["start", "end"] for p in sorted_anchors):
            path_segments.append(sorted_anchors)
        else:
            for point in sorted_anchors:
                if point.actor == "start":
                    if in_segment: # End previous segment if a new one starts
                        path_segments.append(current_segment)
                    current_segment = [point]
                    in_segment = True
                elif point.actor == "end" and in_segment:
                    current_segment.append(point)
                    path_segments.append(current_segment)
                    current_segment = []
                    in_segment = False
                elif in_segment:
                    current_segment.append(point)

        # Calculate path points for each segment
        self.path_points = []
        self.path_segments_data = [] # Store data for generation
        use_bezier = self.interpolation_combo.currentText() == "Bézier"
        step = self.step_spin.value()

        for segment in path_segments:
            if len(segment) < 2:
                continue

            segment_points = []
            total_start = segment[0].time
            total_end = segment[-1].time
            current_time = total_start

            while current_time <= total_end:
                # Find current sub-segment within the larger segment
                segment_index = None
                for i in range(len(segment) - 1):
                    if segment[i].time <= current_time <= segment[i+1].time:
                        segment_index = i
                        break
                
                if segment_index is None:
                    segment_index = len(segment) - 2

                if not use_bezier:
                    # Linear interpolation
                    t0 = segment[segment_index].time
                    t1 = segment[segment_index+1].time
                    frac = (current_time - t0) / (t1 - t0) if t1 != t0 else 0.0
                    x0, y0 = segment[segment_index].x, segment[segment_index].y
                    x1, y1 = segment[segment_index+1].x, segment[segment_index+1].y
                    x, y = interpolate_linear((x0, y0), (x1, y1), frac)
                    segment_points.append((x, y, current_time))
                else:
                    # Bézier interpolation
                    i = segment_index
                    p0 = segment[i-1] if i > 0 else segment[i]
                    p1 = segment[i]
                    p2 = segment[i+1]
                    p3 = segment[i+2] if i+2 < len(segment) else segment[i+1]
                    
                    t0 = p1.time
                    t1 = p2.time
                    t_local = (current_time - t0) / (t1 - t0) if t1 != t0 else 0.0
                    
                    x, y = interpolate_bezier(
                        (p0.x, p0.y),
                        (p1.x, p1.y),
                        (p2.x, p2.y),
                        (p3.x, p3.y),
                        t_local
                    )
                    segment_points.append((x, y, current_time))
                
                current_time += step
            
            self.path_points.extend(segment_points)
            self.path_segments_data.append({
                "points": segment_points,
                "anchors": segment
            })

        # Update preview
        self.preview.set_anchor_points(self.anchor_points)
        self.preview.set_path_points(self.path_points)
        self.preview.draw_scene()
        self.update_status()
        
    def preview_animation(self):
        if not self.path_points:
            self.update_path()
            
        if self.preview.animation_running:
            self.preview.stop_animation()
            self.preview_btn.setText("Preview Animation")
        else:
            self.preview.start_animation()
            self.preview_btn.setText("Stop Animation")
            
    def reset_positions(self):
        for point in self.anchor_points:
            point.x = point.original_x
            point.y = point.original_y
        self.update_path()
        
    def generate_ass(self):
        if not self.anchor_points or not self.path_segments_data:
            self.update_path()
            
        try:
            # Prepare anchor events
            anchor_lines = []
            for point in self.anchor_points:
                # Reconstruct the original event with new position
                text = f"{{\\pos({int(point.x)},{int(point.y)})}}{point.text}"
                # Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
                anchor_lines.append(f"Dialogue: 0,{seconds_to_ass_time(point.time)},{seconds_to_ass_time(point.time+0.1)},{point.style},,0,0,0,,{text}")
            
            # Prepare snake events
            snake_lines = []
            for segment_data in self.path_segments_data:
                segment_anchors = segment_data["anchors"]
                segment_points = segment_data["points"]
                
                if not segment_anchors:
                    continue

                uniform_text = segment_anchors[0].text
                last_time = segment_anchors[-1].time + 0.1  # Small offset
                
                for x, y, time_sec in segment_points:
                    start_time = seconds_to_ass_time(time_sec)
                    style = "style"
                    # Determine end time
                    if self.mode_combo.currentIndex() == 0:  # Sequential
                        end_time = seconds_to_ass_time(time_sec + self.duration_spin.value())
                    else:  # Persistent
                        end_time = seconds_to_ass_time(last_time)
                    
                    # Determine text
                    if self.text_mode_combo.currentIndex() == 0:  # Uniform
                        text_content = uniform_text
                    else:  # Per point
                        # Find the closest anchor point in the current segment
                        closest_idx = 0
                        min_diff = float('inf')
                        for j, anchor in enumerate(segment_anchors):
                            diff = abs(anchor.time - time_sec)
                            if diff < min_diff:
                                min_diff = diff
                                closest_idx = j
                        style = segment_anchors[closest_idx].style
                        text_content = segment_anchors[closest_idx].text
                    
                    # Create event
                    text = f"{{\\pos({int(x)},{int(y)})}}{text_content}"
                    snake_lines.append(f"Dialogue: 0,{start_time},{end_time},{style},,0,0,0,,{text}")
            
            # Write to output file
            with open(self.output_file, 'w', encoding='utf-8') as f:
                for line in self.other_lines:
                    f.write(line+"\n")
                f.write("\n".join(snake_lines))

            QMessageBox.information(self, "Success", f"Generated {self.output_file} successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not generate output file:\n{str(e)}")

    def reload_input_file(self):
        # 1. Stop any running animation
        self.preview.stop_animation()
        
        # 2. Clear current anchor points
        self.anchor_points = []
        self.path_segments_data = []
        
        # 3. Re-run the file loading process
        self.load_input_file()  # Existing function
        
        # 4. Update the path
        self.update_path()


def main():
    parser = argparse.ArgumentParser(description='Snake Subtitle Generator with UI')
    parser.add_argument('input_file', help='Input ASS subtitle file')
    parser.add_argument('output_file', help='Output ASS subtitle file')
    parser.add_argument('--width', type=int, default=2560, help='Canvas width')
    parser.add_argument('--height', type=int, default=1440, help='Canvas height')
    
    #args = parser.parse_args()
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    #window = SnakeGeneratorUI(args.input_file, args.output_file, args.width, args.height)
    #debugging specific way, because debugger doesn't support args
    window = SnakeGeneratorUI("./input.ass", "./output.ass", 2560, 1440)
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
