from PySide6.QtWidgets import (QMainWindow, QGraphicsView, QGraphicsScene, 
                                QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsLineItem,
                                QGraphicsItem,
                                QDockWidget, QCheckBox, QVBoxLayout, QWidget,
                                QToolBar, QApplication, QMenuBar, QMenu, QFileDialog,
                                QColorDialog, QDialog, QLabel, QPushButton, QComboBox,
                                QHBoxLayout, QDialogButtonBox)
from PySide6.QtCore import Qt, QTimer, QPoint, QEvent
from PySide6.QtGui import QPen, QColor, QIcon, QAction, QFontMetrics, QMouseEvent
from .spfparser import SPFParser
import sys
import os
import time

class ThumbnailView(QGraphicsView):
    """Custom QGraphicsView for thumbnail that always fits in view and disables all interactions."""
    
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self._always_fit = True
    
    def wheelEvent(self, event):
        """Disable wheel zoom in thumbnail."""
        event.ignore()
    
    def mousePressEvent(self, event):
        """Disable mouse interactions in thumbnail."""
        event.ignore()
    
    def mouseMoveEvent(self, event):
        """Disable mouse move in thumbnail."""
        event.ignore()
    
    def mouseReleaseEvent(self, event):
        """Disable mouse release in thumbnail."""
        event.ignore()
    
    def resizeEvent(self, event):
        """Automatically fit in view when resized."""
        super().resizeEvent(event)
        if self._always_fit and self.scene() and self.scene().items():
            bounding_rect = self.scene().itemsBoundingRect()
            if not bounding_rect.isEmpty():
                self.fitInView(bounding_rect, Qt.KeepAspectRatio)
    
    def setAlwaysFit(self, always_fit):
        """Set whether to always fit in view."""
        self._always_fit = always_fit
        if always_fit and self.scene() and self.scene().items():
            bounding_rect = self.scene().itemsBoundingRect()
            if not bounding_rect.isEmpty():
                self.fitInView(bounding_rect, Qt.KeepAspectRatio)

class PanGraphicsView(QGraphicsView):
    """Custom QGraphicsView with mouse drag to pan functionality."""
    
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self._panning = False
        self._pan_start_pos = QPoint()
        self._space_pressed = False
    
    def mousePressEvent(self, event):
        """Handle mouse press events for panning."""
        # Enable panning with middle mouse button or space + left mouse button
        if event.button() == Qt.MiddleButton or \
           (event.button() == Qt.LeftButton and self._space_pressed):
            self._panning = True
            self._pan_start_pos = event.position().toPoint()
            button_name = "Middle" if event.button() == Qt.MiddleButton else "Left (with Space)"
            print(f"[DRAG] Start panning with {button_name} button at view pos: ({self._pan_start_pos.x()}, {self._pan_start_pos.y()})")
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move events for panning."""
        if self._panning:
            delta = event.position().toPoint() - self._pan_start_pos
            old_h = self.horizontalScrollBar().value()
            old_v = self.verticalScrollBar().value()
            self.horizontalScrollBar().setValue(old_h - delta.x())
            self.verticalScrollBar().setValue(old_v - delta.y())
            new_h = self.horizontalScrollBar().value()
            new_v = self.verticalScrollBar().value()
            print(f"[DRAG] Move: delta=({delta.x()}, {delta.y()}), "
                  f"scroll: H({old_h}->{new_h}), V({old_v}->{new_v})")
            self._pan_start_pos = event.position().toPoint()
            event.accept()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events for panning."""
        if self._panning:
            final_pos = event.position().toPoint()
            total_delta = final_pos - self._pan_start_pos
            print(f"[DRAG] End panning at view pos: ({final_pos.x()}, {final_pos.y()}), "
                  f"total delta: ({total_delta.x()}, {total_delta.y()})")
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)
    
    def keyPressEvent(self, event):
        """Handle key press events to enable space+click panning."""
        if event.key() == Qt.Key_Space:
            self._space_pressed = True
            self.setCursor(Qt.OpenHandCursor)
        super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event):
        """Handle key release events."""
        if event.key() == Qt.Key_Space:
            self._space_pressed = False
            if not self._panning:
                self.setCursor(Qt.ArrowCursor)
        super().keyReleaseEvent(event)
    
    def contextMenuEvent(self, event):
        """Handle right-click context menu events."""
        # Get the parent RCViewer to create the context menu
        parent = self.parent()
        while parent and not isinstance(parent, QMainWindow):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'show_context_menu'):
            # Convert view coordinates to scene coordinates
            view_pos = event.pos()
            scene_pos = self.mapToScene(view_pos)
            parent.show_context_menu(event.globalPos(), scene_pos)
        else:
            super().contextMenuEvent(event)

class RCViewer(QMainWindow):
    NODE_RADIUS = 0.5
    
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.setWindowTitle("SPF/DSPF Viewer")
        self.setGeometry(100, 100, 800, 600)
        # Initialize file name label for status bar
        self.file_name_label = None
        self.scene = QGraphicsScene()
        # Thumbnail scene and view
        self.thumbnail_scene = None
        self.thumbnail_view = None
        self.viewport_rect = None
        self.view = PanGraphicsView(self.scene)
        # no qt please, use numpy and matplotlib instead
        self.view.setBackgroundBrush(QColor(255, 255, 255))
        self.setCentralWidget(self.view)
        
        # Time statistics
        print("=" * 60)
        print("Starting to load and render SPF file...")
        print("=" * 60)
        
        # Debug: File information
        print(f"[DEBUG] SPF file path: {self.file_path}")
        if os.path.exists(self.file_path):
            file_size = os.path.getsize(self.file_path)
            print(f"[DEBUG] File exists, size: {file_size:,} bytes ({file_size / 1024:.2f} KB)")
        else:
            print(f"[DEBUG] WARNING: File does not exist!")
        
        # Parse SPF file
        print(f"[DEBUG] Starting to parse SPF file...")
        parse_start = time.time()
        self.parser = SPFParser(self.file_path)
        parse_end = time.time()
        parse_time = parse_end - parse_start
        print(f"[Time Stats] Parse SPF file: {parse_time:.4f} seconds")
        
        # Debug: Parse results
        total_nets = len(self.parser.nets)
        total_nodes = sum(len(net.get_nodes()) for net in self.parser.nets.values())
        total_elements = sum(len(net.get_elements()) for net in self.parser.nets.values())
        print(f"[DEBUG] Parsed results:")
        print(f"  - Total nets: {total_nets}")
        print(f"  - Total nodes: {total_nodes}")
        print(f"  - Total elements: {total_elements}")
        
        # Debug: Count by element type
        element_types = {}
        for net in self.parser.nets.values():
            for elem in net.get_elements():
                elem_type = elem.type if hasattr(elem, 'type') else 'Unknown'
                element_types[elem_type] = element_types.get(elem_type, 0) + 1
        if element_types:
            print(f"[DEBUG] Element types breakdown:")
            for elem_type, count in sorted(element_types.items()):
                print(f"  - {elem_type}: {count}")
        
        # Debug: Sample net IDs
        if total_nets > 0:
            sample_nets = list(self.parser.nets.keys())[:5]
            print(f"[DEBUG] Sample net IDs (first 5): {sample_nets}")
        
        # Store graphics items by layer for visibility control
        self.layer_items = {}  # {layer_name: [list of graphics items]}
        # Store graphics items by net for visibility control
        self.net_items = {}  # {net_id: [list of graphics items]}
        # Map each graphics item to its net for quick lookup
        self.item_to_net = {}  # {graphics_item: net_id}
        # Map each graphics item to its layer for quick lookup
        self.item_to_layer = {}  # {graphics_item: layer}
        # Map graphics items to RCElements and Nodes for selection
        self.item_to_element = {}  # {graphics_item: RCElement}
        self.item_to_node = {}  # {graphics_item: Node}
        # Map node_id to list of elements that use this node
        self.node_to_elements = {}  # {node_id: [list of RCElements]}
        # Map graphics items for elements (to check visibility)
        self.element_graphics_items = {}  # {RCElement: [list of graphics items]}
        # Store original styles for highlighting
        self.item_original_pen = {}  # {graphics_item: QPen}
        self.item_original_brush = {}  # {graphics_item: QBrush}
        self.item_original_zvalue = {}  # {graphics_item: float}
        # Currently selected element
        self.selected_element = None
        self.selected_element_items = []  # Graphics items for selected element
        self.selected_node_items = []  # Graphics items for selected nodes
        
        # Collect all layers and nets, then create selection panels
        print(f"[DEBUG] Collecting layers and nets...")
        self.collect_layers()
        self.collect_nets()
        print(f"[DEBUG] Collected {len(self.all_layers)} layers, {len(self.all_nets)} nets")
        print(f"[DEBUG] Layers: {[str(l) if l is not None else 'None' for l in self.all_layers]}")
        # Initialize layer color mapping
        self.init_layer_colors()
        # Create net panel first so it appears above layer panel
        self.create_net_panel()
        self.create_layer_panel()
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create status bar (with two lines: selection info and SPF file name)
        self.create_status_bar()
        
        # Render graphics
        print(f"[DEBUG] Starting to render graphics...")
        render_start = time.time()
        self.render_nodes()
        render_nodes_time = time.time() - render_start
        print(f"[Time Stats] Render nodes: {render_nodes_time:.4f} seconds")
        
        render_elements_start = time.time()
        self.render_elements()
        render_elements_time = time.time() - render_elements_start
        print(f"[Time Stats] Render elements: {render_elements_time:.4f} seconds")
        
        # Debug: Render results
        total_graphics_items = len(self.scene.items())
        print(f"[DEBUG] Total graphics items in scene: {total_graphics_items}")
        print(f"[DEBUG] Graphics items by type:")
        ellipse_count = sum(1 for item in self.scene.items() if isinstance(item, QGraphicsEllipseItem))
        rect_count = sum(1 for item in self.scene.items() if isinstance(item, QGraphicsRectItem))
        line_count = sum(1 for item in self.scene.items() if isinstance(item, QGraphicsLineItem))
        print(f"  - Ellipses (nodes): {ellipse_count}")
        print(f"  - Rectangles: {rect_count}")
        print(f"  - Lines: {line_count}")
        
        # Update thumbnail after rendering
        QTimer.singleShot(200, self.update_thumbnail)
        
        total_render_time = render_nodes_time + render_elements_time
        total_time = parse_time + total_render_time
        print(f"[Time Stats] Total render time: {total_render_time:.4f} seconds")
        print(f"[Time Stats] Total time: {total_time:.4f} seconds")
        print("=" * 60)
        
        # Connect scene selection changed signal
        self.scene.selectionChanged.connect(self.on_selection_changed)
        
        # Schedule fit to view after window is shown
        QTimer.singleShot(100, self.fit_to_view)
    
    def collect_layers(self):
        """Collect all unique layers from nodes and elements."""
        layers = set()
        for net in self.parser.nets.values():
            # no need to show the layers in the layer panel for nodes, because nodes seems to be part of the resistors or capacitors
            # only show the layers in the layer panel for resistors or capacitors
            for elem in net.get_elements():
                if elem.layer:
                    layers.add(elem.layer)
        # Add None layer for items without layer
        self.all_layers = sorted([l for l in layers if l is not None]) + [None]
        self.selected_layers = set(self.all_layers)  # All layers selected by default
    
    def collect_nets(self):
        """Collect all nets from the parser."""
        self.all_nets = sorted(self.parser.nets.keys())
        self.selected_nets = set(self.all_nets)  # All nets selected by default
    
    def init_layer_colors(self):
        """Initialize color mapping for each layer."""
        # Predefined color palette for layers
        color_palette = [
            QColor(255, 0, 0),      # Red
            QColor(0, 255, 0),      # Green
            QColor(0, 0, 255),      # Blue
            QColor(255, 165, 0),    # Orange
            QColor(255, 0, 255),    # Magenta
            QColor(0, 255, 255),    # Cyan
            QColor(255, 192, 203),  # Pink
            QColor(128, 0, 128),    # Purple
            QColor(255, 255, 0),    # Yellow
            QColor(0, 128, 0),      # Dark Green
            QColor(128, 128, 128),  # Gray
            QColor(255, 140, 0),    # Dark Orange
            QColor(75, 0, 130),     # Indigo
            QColor(255, 20, 147),   # Deep Pink
            QColor(0, 191, 255),    # Deep Sky Blue
        ]
        
        self.layer_colors = {}
        for i, layer in enumerate(self.all_layers):
            if layer is None:
                # Use gray for items without layer
                self.layer_colors[layer] = QColor(128, 128, 128)
            else:
                # Assign color from palette, cycling if needed
                self.layer_colors[layer] = color_palette[i % len(color_palette)]
        
        print(f"[DEBUG] Layer colors initialized: {[(str(l) if l is not None else 'None', c.name()) for l, c in self.layer_colors.items()]}")
    
    def get_layer_color(self, layer):
        """Get the color for a given layer."""
        return self.layer_colors.get(layer, QColor(128, 128, 128))  # Default to gray if layer not found
    
    def set_layer_color(self):
        """Open a dialog to set color for a layer."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Set Layer Color")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        dialog.setLayout(layout)
        
        # Layer selection
        layer_label = QLabel("Select Layer:")
        layout.addWidget(layer_label)
        
        layer_combo = QComboBox()
        for layer in self.all_layers:
            layer_name = str(layer) if layer is not None else "None"
            layer_combo.addItem(layer_name, layer)
        layout.addWidget(layer_combo)
        
        # Current color display
        color_label = QLabel("Current Color:")
        layout.addWidget(color_label)
        
        color_preview = QLabel()
        color_preview.setMinimumHeight(30)
        color_preview.setStyleSheet(f"background-color: {self.get_layer_color(self.all_layers[0]).name()}; border: 1px solid black;")
        layout.addWidget(color_preview)
        
        # Update preview when layer changes
        def update_color_preview():
            selected_layer = layer_combo.currentData()
            current_color = self.get_layer_color(selected_layer)
            color_preview.setStyleSheet(f"background-color: {current_color.name()}; border: 1px solid black;")
        
        layer_combo.currentIndexChanged.connect(update_color_preview)
        update_color_preview()
        
        # Color picker button
        color_button = QPushButton("Choose Color...")
        layout.addWidget(color_button)
        
        selected_color = [None]  # Use list to allow modification in nested function
        
        def choose_color():
            selected_layer = layer_combo.currentData()
            current_color = self.get_layer_color(selected_layer)
            color = QColorDialog.getColor(current_color, dialog, "Choose Layer Color")
            if color.isValid():
                selected_color[0] = color
                color_preview.setStyleSheet(f"background-color: {color.name()}; border: 1px solid black;")
        
        color_button.clicked.connect(choose_color)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec() == QDialog.Accepted:
            selected_layer = layer_combo.currentData()
            if selected_color[0] is not None:
                # Update layer color
                self.layer_colors[selected_layer] = selected_color[0]
                print(f"[DEBUG] Set color for layer {selected_layer}: {selected_color[0].name()}")
                
                # Update all graphics items with this layer
                self.update_layer_colors(selected_layer, selected_color[0])
                
                # Update color preview in layer panel
                if selected_layer in self.layer_color_labels:
                    color_label = self.layer_color_labels[selected_layer]
                    color_label.setStyleSheet(f"background-color: {selected_color[0].name()}; border: 1px solid black;")
                    color_label.setToolTip(f"Layer color: {selected_color[0].name()}")
                
                self.update_status_message(f"Color updated for layer: {str(selected_layer) if selected_layer else 'None'}")
            else:
                self.update_status_message("No color selected")
    
    def update_layer_colors(self, layer, color):
        """Update colors for all graphics items with the specified layer."""
        if layer in self.layer_items:
            for item in self.layer_items[layer]:
                # Skip if item is currently highlighted
                if item in self.selected_element_items or item in self.selected_node_items:
                    continue
                
                # Update node colors (ellipses)
                if isinstance(item, QGraphicsEllipseItem):
                    item.setBrush(color)
                
                # Update element colors (rectangles and lines)
                elif isinstance(item, QGraphicsRectItem):
                    pen_color = color.darker(120)
                    item.setPen(QPen(pen_color))
                    item.setBrush(color.lighter(150))
                elif hasattr(item, 'setPen'):  # For lines
                    pen_color = color.darker(120)
                    item.setPen(QPen(pen_color, 1))
        
        # Force view update
        self.view.update()
        self.scene.update()
    
    def create_net_panel(self):
        """Create a dock widget with net selection checkboxes."""
        self.net_dock = QDockWidget("Net Selection", self)
        self.net_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Create checkboxes for each net
        self.net_checkboxes = {}
        for net_id in self.all_nets:
            checkbox = QCheckBox(net_id)
            checkbox.setChecked(True)  # All nets visible by default
            # Use a lambda that captures the checkbox object to get the actual state
            checkbox.stateChanged.connect(lambda checked, n=net_id, cb=checkbox: self.on_net_toggled(n, cb.isChecked()))
            self.net_checkboxes[net_id] = checkbox
            layout.addWidget(checkbox)
        
        layout.addStretch()
        self.net_dock.setWidget(widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.net_dock)
        # Make sure the dock widget is visible
        self.net_dock.setVisible(True)
    
    def create_status_bar(self):
        """Create a status bar with two lines: selection info (line 1) and SPF file name (line 2)."""
        status_bar = self.statusBar()
        
        # Create a widget to hold two lines of information
        status_widget = QWidget()
        status_layout = QVBoxLayout()
        status_layout.setContentsMargins(5, 2, 5, 2)
        status_layout.setSpacing(2)
        
        # First line: selection info (will be updated by showMessage)
        self.selection_label = QLabel("Ready")
        self.selection_label.setAlignment(Qt.AlignLeft)
        status_layout.addWidget(self.selection_label)
        
        # Second line: SPF file name
        self.file_name_label = QLabel("")
        self.file_name_label.setAlignment(Qt.AlignLeft)
        status_layout.addWidget(self.file_name_label)
        
        status_widget.setLayout(status_layout)
        
        # Add as permanent widget
        status_bar.addPermanentWidget(status_widget, 1)
        
        # Set initial message
        status_bar.showMessage("Ready")
        
        # Update file name if file_path is provided
        if self.file_path:
            file_name = os.path.basename(self.file_path)
            self.update_file_name_display(file_name)
            print(f"[DEBUG] Status bar: Setting file name to {file_name}")
        else:
            self.update_file_name_display("")
            print("[DEBUG] Status bar: No file path provided")
        
        # Force status bar to update
        status_bar.update()
    
    def update_status_message(self, message):
        """Update the first line of status bar (selection info)."""
        self.statusBar().showMessage(message)
        if hasattr(self, 'selection_label'):
            self.selection_label.setText(message)
    
    def update_file_name_display(self, file_name):
        """Update the file name display in status bar (second line)."""
        if self.file_name_label:
            if file_name:
                self.file_name_label.setText(f"SPF File: {file_name}")
                self.file_name_label.setVisible(True)
                print(f"[DEBUG] Status bar: Updated file name label to 'SPF File: {file_name}'")
            else:
                self.file_name_label.setText("")
                self.file_name_label.setVisible(True)  # Keep visible even when empty
                print("[DEBUG] Status bar: Cleared file name label")
        else:
            print("[DEBUG] Status bar: file_name_label is None")
    
    def create_menu_bar(self):
        """Create a menu bar with file menu."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        # Open SPF file action
        open_action = QAction("Open SPF File...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_spf_file)
        file_menu.addAction(open_action)
        
        # Separator
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Preferences menu
        preferences_menu = menubar.addMenu("Preferences")
        
        # Set layer color action
        set_color_action = QAction("Set Layer Color...", self)
        set_color_action.triggered.connect(self.set_layer_color)
        preferences_menu.addAction(set_color_action)
    
    def open_spf_file(self):
        """Open a SPF file dialog and load the selected file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open SPF File",
            "",
            "SPF Files (*.spf *.dspf);;All Files (*)"
        )
        
        if file_path:
            try:
                # Clear current scene
                self.scene.clear()
                
                # Clear thumbnail scene if it exists
                if hasattr(self, 'thumbnail_scene') and self.thumbnail_scene:
                    # Clear all items except viewport rect
                    items_to_remove = []
                    for item in self.thumbnail_scene.items():
                        if item != self.viewport_rect:
                            items_to_remove.append(item)
                    for item in items_to_remove:
                        self.thumbnail_scene.removeItem(item)
                
                # Reset all tracking dictionaries
                self.layer_items = {}
                self.net_items = {}
                self.item_to_net = {}
                self.item_to_layer = {}
                self.item_to_element = {}
                self.item_to_node = {}
                self.node_to_elements = {}
                self.element_graphics_items = {}
                self.item_original_pen = {}
                self.item_original_brush = {}
                self.item_original_zvalue = {}
                self.selected_element = None
                self.selected_element_items = []
                self.selected_node_items = []
                
                # Time statistics for file loading
                print("=" * 60)
                print(f"Starting to load new SPF file: {os.path.basename(file_path)}")
                print("=" * 60)
                
                # Debug: File information
                print(f"[DEBUG] SPF file path: {file_path}")
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    print(f"[DEBUG] File exists, size: {file_size:,} bytes ({file_size / 1024:.2f} KB)")
                else:
                    print(f"[DEBUG] WARNING: File does not exist!")
                
                # Update file path and parse new file
                self.file_path = file_path
                print(f"[DEBUG] Starting to parse SPF file...")
                parse_start = time.time()
                self.parser = SPFParser(file_path)
                parse_time = time.time() - parse_start
                print(f"[Time Stats] Parse SPF file: {parse_time:.4f} seconds")
                
                # Debug: Parse results
                total_nets = len(self.parser.nets)
                total_nodes = sum(len(net.get_nodes()) for net in self.parser.nets.values())
                total_elements = sum(len(net.get_elements()) for net in self.parser.nets.values())
                print(f"[DEBUG] Parsed results:")
                print(f"  - Total nets: {total_nets}")
                print(f"  - Total nodes: {total_nodes}")
                print(f"  - Total elements: {total_elements}")
                
                # Debug: Count by element type
                element_types = {}
                for net in self.parser.nets.values():
                    for elem in net.get_elements():
                        elem_type = elem.type if hasattr(elem, 'type') else 'Unknown'
                        element_types[elem_type] = element_types.get(elem_type, 0) + 1
                if element_types:
                    print(f"[DEBUG] Element types breakdown:")
                    for elem_type, count in sorted(element_types.items()):
                        print(f"  - {elem_type}: {count}")
                
                # Debug: Sample net IDs
                if total_nets > 0:
                    sample_nets = list(self.parser.nets.keys())[:5]
                    print(f"[DEBUG] Sample net IDs (first 5): {sample_nets}")
                
                # Update window title (first line)
                self.setWindowTitle("SPF/DSPF Viewer")
                
                # Update file name display in status bar (second line)
                self.update_file_name_display(os.path.basename(file_path))
                
                # Recollect layers and nets
                print(f"[DEBUG] Collecting layers and nets...")
                collect_start = time.time()
                self.collect_layers()
                self.collect_nets()
                print(f"[DEBUG] Collected {len(self.all_layers)} layers, {len(self.all_nets)} nets")
                print(f"[DEBUG] Layers: {[str(l) if l is not None else 'None' for l in self.all_layers]}")
                
                # Reinitialize layer colors
                self.init_layer_colors()
                collect_time = time.time() - collect_start
                print(f"[Time Stats] Collect layers and nets: {collect_time:.4f} seconds")
                
                # Recreate panels
                panel_start = time.time()
                if hasattr(self, 'net_dock'):
                    self.removeDockWidget(self.net_dock)
                if hasattr(self, 'layer_dock'):
                    self.removeDockWidget(self.layer_dock)
                if hasattr(self, 'thumbnail_dock'):
                    self.removeDockWidget(self.thumbnail_dock)
                self.create_net_panel()
                self.create_layer_panel()
                self.create_thumbnail_panel()
                panel_time = time.time() - panel_start
                print(f"[Time Stats] Create panels: {panel_time:.4f} seconds")
                
                # Re-render
                print(f"[DEBUG] Starting to render graphics...")
                render_start = time.time()
                self.render_nodes()
                render_nodes_time = time.time() - render_start
                print(f"[Time Stats] Render nodes: {render_nodes_time:.4f} seconds")
                
                render_elements_start = time.time()
                self.render_elements()
                render_elements_time = time.time() - render_elements_start
                print(f"[Time Stats] Render elements: {render_elements_time:.4f} seconds")
                
                # Debug: Render results
                total_graphics_items = len(self.scene.items())
                print(f"[DEBUG] Total graphics items in scene: {total_graphics_items}")
                print(f"[DEBUG] Graphics items by type:")
                ellipse_count = sum(1 for item in self.scene.items() if isinstance(item, QGraphicsEllipseItem))
                rect_count = sum(1 for item in self.scene.items() if isinstance(item, QGraphicsRectItem))
                line_count = sum(1 for item in self.scene.items() if isinstance(item, QGraphicsLineItem))
                print(f"  - Ellipses (nodes): {ellipse_count}")
                print(f"  - Rectangles: {rect_count}")
                print(f"  - Lines: {line_count}")
                
                # Update thumbnail after rendering new file
                QTimer.singleShot(200, self.update_thumbnail)
                
                total_render_time = render_nodes_time + render_elements_time
                total_time = parse_time + collect_time + panel_time + total_render_time
                print(f"[Time Stats] Total render time: {total_render_time:.4f} seconds")
                print(f"[Time Stats] Total time: {total_time:.4f} seconds")
                print("=" * 60)
                
                # Fit to view after loading
                QTimer.singleShot(100, self.fit_to_view)
                
                # Update status bar
                self.update_status_message(f"Loaded: {os.path.basename(file_path)}")
                
                print(f"[DEBUG] Opened SPF file: {file_path}")
                
            except Exception as e:
                self.update_status_message(f"Error loading file: {str(e)}")
                print(f"[DEBUG] Error loading file: {e}")
                import traceback
                traceback.print_exc()
    
    def create_toolbar(self):
        """Create a toolbar with common tools."""
        toolbar = QToolBar("Main Toolbar", self)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        
        # Zoom in action
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_action)
        
        # Zoom out action
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_action)
        
        # Fit to view action
        fit_action = QAction("Fit to View", self)
        fit_action.setShortcut("Ctrl+F")
        fit_action.triggered.connect(self.fit_to_view)
        toolbar.addAction(fit_action)
        
        # Reset zoom action
        reset_zoom_action = QAction("Reset Zoom", self)
        reset_zoom_action.setShortcut("Ctrl+0")
        reset_zoom_action.triggered.connect(self.reset_zoom)
        toolbar.addAction(reset_zoom_action)
        
        toolbar.addSeparator()
        
        # Clear selection action
        clear_selection_action = QAction("Clear Selection", self)
        clear_selection_action.setShortcut("Esc")
        clear_selection_action.triggered.connect(self.clear_selection)
        toolbar.addAction(clear_selection_action)
    
    def zoom_in(self):
        """Zoom in the view."""
        self.view.scale(1.2, 1.2)
        self.update_viewport_rect()
    
    def zoom_out(self):
        """Zoom out the view."""
        self.view.scale(1.0 / 1.2, 1.0 / 1.2)
        self.update_viewport_rect()
    
    def fit_to_view(self):
        """Fit all items to the view with 5% margin on left and right sides."""
        if self.scene.items():
            bounding_rect = self.scene.itemsBoundingRect()
            if not bounding_rect.isEmpty():
                # Calculate 5% margin on both left and right sides
                margin_ratio = 0.05  # 5% margin
                width = bounding_rect.width()
                height = bounding_rect.height()
                
                # Expand the bounding rect by 5% on each side (total 10% width increase)
                margin_width = width * margin_ratio
                expanded_rect = bounding_rect.adjusted(-margin_width, 0, margin_width, 0)
                
                self.view.fitInView(expanded_rect, Qt.KeepAspectRatio)
                QTimer.singleShot(50, self.update_viewport_rect)
    
    def reset_zoom(self):
        """Reset zoom to 1:1."""
        self.view.resetTransform()
        self.update_viewport_rect()
    
    def clear_selection(self):
        """Clear current selection and highlights."""
        self.scene.clearSelection()
        self.clear_highlight()
    
    def create_layer_panel(self):
        """Create a dock widget with layer selection checkboxes and color previews."""
        self.layer_dock = QDockWidget("Layer Selection", self)
        self.layer_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Create checkboxes for each layer with color preview
        self.layer_checkboxes = {}
        self.layer_color_labels = {}  # Store color preview labels
        
        # Find the maximum checkbox width to align color blocks
        # Calculate maximum width needed using font metrics
        font_metrics = QFontMetrics(self.font())
        max_checkbox_width = 0
        for layer in self.all_layers:
            layer_name = str(layer) if layer is not None else "None"
            # Approximate width: checkbox + text + some padding
            text_width = font_metrics.horizontalAdvance(layer_name)
            checkbox_width = 20  # Approximate checkbox width
            total_width = checkbox_width + text_width + 10  # 10px padding
            max_checkbox_width = max(max_checkbox_width, total_width)
        
        for layer in self.all_layers:
            layer_name = str(layer) if layer is not None else "None"
            
            # Create a horizontal layout for checkbox and color preview
            layer_widget = QWidget()
            layer_layout = QHBoxLayout()
            layer_widget.setLayout(layer_layout)
            layer_layout.setContentsMargins(0, 0, 0, 0)
            layer_layout.setSpacing(5)
            
            checkbox = QCheckBox(layer_name)
            checkbox.setChecked(True)  # All layers visible by default
            # Use a lambda that captures the checkbox object to get the actual state
            checkbox.stateChanged.connect(lambda checked, l=layer, cb=checkbox: self.on_layer_toggled(l, cb.isChecked()))
            self.layer_checkboxes[layer] = checkbox
            layer_layout.addWidget(checkbox)
            
            # Add a fixed-width spacer to push color blocks to the same position
            # This ensures all color blocks align vertically
            spacer_width = max_checkbox_width - font_metrics.horizontalAdvance(layer_name) - 20 - 5
            if spacer_width > 0:
                spacer = QWidget()
                spacer.setFixedWidth(spacer_width)
                layer_layout.addWidget(spacer)
            
            # Add color preview label - all will be at the same horizontal position
            color_label = QLabel()
            color_label.setFixedSize(20, 20)
            layer_color = self.get_layer_color(layer)
            color_label.setStyleSheet(f"background-color: {layer_color.name()}; border: 1px solid black;")
            color_label.setToolTip(f"Layer color: {layer_color.name()}")
            self.layer_color_labels[layer] = color_label
            layer_layout.addWidget(color_label)
            
            layer_layout.addStretch()
            layout.addWidget(layer_widget)
        
        layout.addStretch()
        self.layer_dock.setWidget(widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.layer_dock)
        # Split the dock widgets vertically so net panel is above layer panel
        self.splitDockWidget(self.net_dock, self.layer_dock, Qt.Vertical)
        # Make sure the dock widget is visible
        self.layer_dock.setVisible(True)
        
        # Create thumbnail overview panel below layer panel
        self.create_thumbnail_panel()
    
    def create_thumbnail_panel(self):
        """Create a thumbnail overview panel showing the entire res map."""
        self.thumbnail_dock = QDockWidget("Overview", self)
        self.thumbnail_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # Create a scene for thumbnail
        self.thumbnail_scene = QGraphicsScene()
        self.thumbnail_view = ThumbnailView(self.thumbnail_scene)
        # Use the same background color as main view (white)
        self.thumbnail_view.setBackgroundBrush(QColor(255, 255, 255))
        self.thumbnail_view.setMinimumSize(200, 200)
        self.thumbnail_view.setMaximumSize(300, 300)
        self.thumbnail_view.setDragMode(QGraphicsView.NoDrag)  # Disable dragging in thumbnail
        self.thumbnail_view.setInteractive(False)  # Disable interaction
        self.thumbnail_view.setAlwaysFit(True)  # Always fit in view, no zoom/pan allowed
        
        # Add viewport rectangle to show current view area
        self.viewport_rect = QGraphicsRectItem()
        self.viewport_rect.setPen(QPen(QColor(255, 0, 0), 2))  # Red rectangle
        self.viewport_rect.setBrush(QColor(255, 0, 0, 50))  # Semi-transparent red
        self.viewport_rect.setZValue(10000)  # Always on top
        self.thumbnail_scene.addItem(self.viewport_rect)
        
        # Connect main view changes to update thumbnail
        self.view.viewport().installEventFilter(self)
        
        # Set widget
        self.thumbnail_dock.setWidget(self.thumbnail_view)
        self.addDockWidget(Qt.RightDockWidgetArea, self.thumbnail_dock)
        
        # Split dock widgets so thumbnail is below layer panel
        self.splitDockWidget(self.layer_dock, self.thumbnail_dock, Qt.Vertical)
        self.thumbnail_dock.setVisible(True)
        
        # Update thumbnail after rendering
        QTimer.singleShot(200, self.update_thumbnail)
    
    def update_thumbnail(self):
        """Update the thumbnail view to show all items and current viewport."""
        if not hasattr(self, 'thumbnail_scene') or not self.thumbnail_scene:
            return
        
        # Clear thumbnail scene (except viewport rect)
        items_to_remove = []
        for item in self.thumbnail_scene.items():
            if item != self.viewport_rect:
                items_to_remove.append(item)
        for item in items_to_remove:
            self.thumbnail_scene.removeItem(item)
        
        # Copy all visible items from main scene to thumbnail scene
        # Ensure exact same colors and styles as main view
        for item in self.scene.items():
            if isinstance(item, (QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsLineItem)):
                # Create a copy for thumbnail with exact same appearance
                if isinstance(item, QGraphicsEllipseItem):
                    copy = QGraphicsEllipseItem(item.rect())
                    # Copy all style properties exactly
                    copy.setBrush(item.brush())
                    copy.setPen(item.pen())
                    copy.setOpacity(item.opacity())
                    copy.setToolTip(item.toolTip())
                elif isinstance(item, QGraphicsRectItem):
                    copy = QGraphicsRectItem(item.rect())
                    # Copy all style properties exactly
                    copy.setBrush(item.brush())
                    copy.setPen(item.pen())
                    copy.setOpacity(item.opacity())
                    copy.setToolTip(item.toolTip())
                elif isinstance(item, QGraphicsLineItem):
                    line = item.line()
                    copy = QGraphicsLineItem(line)
                    # Copy all style properties exactly
                    copy.setPen(item.pen())
                    copy.setOpacity(item.opacity())
                    copy.setToolTip(item.toolTip())
                
                # Copy Z-value to maintain drawing order
                copy.setZValue(item.zValue())
                # Copy visibility state
                copy.setVisible(item.isVisible())
                self.thumbnail_scene.addItem(copy)
        
        # Always fit all items in thumbnail view (no zoom/pan allowed)
        if self.thumbnail_scene.items():
            bounding_rect = self.thumbnail_scene.itemsBoundingRect()
            if not bounding_rect.isEmpty():
                # Always fit in view with a small margin
                margin = 5
                expanded_rect = bounding_rect.adjusted(-margin, -margin, margin, margin)
                self.thumbnail_view.fitInView(expanded_rect, Qt.KeepAspectRatio)
                # Update viewport rect after fitting
                QTimer.singleShot(50, self.update_viewport_rect)
    
    def update_viewport_rect(self):
        """Update the viewport rectangle in thumbnail to show current view area."""
        if not hasattr(self, 'viewport_rect') or not self.viewport_rect:
            return
        if not self.scene.items():
            return
        
        # Get the visible area in scene coordinates
        visible_rect = self.view.mapToScene(self.view.viewport().rect()).boundingRect()
        
        # Get the bounding rect of all items
        scene_rect = self.scene.itemsBoundingRect()
        if scene_rect.isEmpty():
            return
        
        # Calculate scale factor from scene to thumbnail
        thumbnail_rect = self.thumbnail_scene.itemsBoundingRect()
        if thumbnail_rect.isEmpty():
            return
        
        scale_x = thumbnail_rect.width() / scene_rect.width() if scene_rect.width() > 0 else 1
        scale_y = thumbnail_rect.height() / scene_rect.height() if scene_rect.height() > 0 else 1
        
        # Transform visible rect to thumbnail coordinates
        offset_x = visible_rect.x() - scene_rect.x()
        offset_y = visible_rect.y() - scene_rect.y()
        
        thumbnail_x = thumbnail_rect.x() + offset_x * scale_x
        thumbnail_y = thumbnail_rect.y() + offset_y * scale_y
        thumbnail_width = visible_rect.width() * scale_x
        thumbnail_height = visible_rect.height() * scale_y
        
        # Update viewport rectangle
        self.viewport_rect.setRect(thumbnail_x, thumbnail_y, thumbnail_width, thumbnail_height)
        self.thumbnail_scene.update()
    
    def eventFilter(self, obj, event):
        """Event filter to catch viewport changes and update thumbnail."""
        if obj == self.view.viewport():
            if event.type() in (QEvent.Resize, QEvent.Paint):
                # Update viewport rect when view changes
                QTimer.singleShot(10, self.update_viewport_rect)
        return super().eventFilter(obj, event)
    
    def on_layer_toggled(self, layer, is_checked):
        """Handle layer visibility toggle."""
        layer_name = str(layer) if layer is not None else "None"
        print(f"[DEBUG] on_layer_toggled called: layer={layer_name}, is_checked={is_checked}")
        if is_checked:
            self.selected_layers.add(layer)
            print(f"[DEBUG] Layer SELECTED: {layer_name}")
        else:
            self.selected_layers.discard(layer)
            print(f"[DEBUG] Layer UNSELECTED: {layer_name}")
        print(f"[DEBUG] Selected layers: {sorted([str(l) if l is not None else 'None' for l in self.selected_layers])}")
        self.update_visibility()
    
    def on_net_toggled(self, net_id, is_checked):
        """Handle net visibility toggle."""
        print(f"[DEBUG] on_net_toggled called: net_id={net_id}, is_checked={is_checked}")
        if is_checked:
            self.selected_nets.add(net_id)
            print(f"[DEBUG] Net SELECTED: {net_id}")
        else:
            self.selected_nets.discard(net_id)
            print(f"[DEBUG] Net UNSELECTED: {net_id}")
        print(f"[DEBUG] Selected nets: {sorted(self.selected_nets)}")
        # Update visibility for all items to ensure proper display
        self.update_visibility()
        # Force immediate refresh of visualization when net selection changes
        self.view.update()
        self.view.viewport().update()
        self.scene.update()
        self.scene.invalidate()
    
    def update_visibility(self):
        """Update visibility based on both layer and net selections."""
        visible_count = 0
        hidden_count = 0
        visible_res_count = 0
        visible_node_count = 0
        
        # First, update visibility for elements
        element_visibility = {}  # {RCElement: bool}
        visible_elements = set()  # Track unique visible elements
        for net_id, items in self.net_items.items():
            net_visible = net_id in self.selected_nets
            for item in items:
                # Check if this item is an element (not a node)
                element = self.item_to_element.get(item)
                if element:
                    # Get the layer for this item using the mapping
                    layer = self.item_to_layer.get(item)
                    layer_visible = layer in self.selected_layers if layer is not None else True
                    # Element is visible only if both its layer and net are selected
                    is_visible = layer_visible and net_visible
                    item.setVisible(is_visible)
                    # Track element visibility (an element is visible if any of its graphics items is visible)
                    if element not in element_visibility:
                        element_visibility[element] = False
                    element_visibility[element] = element_visibility[element] or is_visible
                    if is_visible:
                        visible_count += 1
                        visible_elements.add(element)
                    else:
                        hidden_count += 1
        
        # Count visible resistors (elements of type 'R')
        for elem in visible_elements:
            if elem.type == 'R':
                visible_res_count += 1
        
        # Then, update visibility for nodes based on element visibility
        visible_nodes = set()  # Track unique visible nodes
        for net_id, items in self.net_items.items():
            net_visible = net_id in self.selected_nets
            for item in items:
                # Check if this item is a node
                node = self.item_to_node.get(item)
                if node:
                    # Get the layer for this item using the mapping
                    layer = self.item_to_layer.get(item)
                    layer_visible = layer in self.selected_layers if layer is not None else True
                    # Check if at least one related element is visible
                    node_has_visible_element = False
                    if node.id in self.node_to_elements:
                        for elem in self.node_to_elements[node.id]:
                            if element_visibility.get(elem, False):
                                node_has_visible_element = True
                                break
                    # Node is visible only if:
                    # 1. Its layer and net are selected
                    # 2. At least one related element is visible
                    is_visible = layer_visible and net_visible and node_has_visible_element
                    item.setVisible(is_visible)
                    if is_visible:
                        visible_count += 1
                        visible_nodes.add(node.id)
                    else:
                        hidden_count += 1
        
        visible_node_count = len(visible_nodes)
        
        print(f"[DEBUG] Visibility updated:")
        print(f"  - Total items: {visible_count} visible, {hidden_count} hidden")
        print(f"  - Resistors (R): {visible_res_count} visible")
        print(f"  - Nodes: {visible_node_count} visible")
        # Force view update/refresh - multiple methods to ensure immediate update
        self.view.update()
        self.view.viewport().update()
        self.scene.update()
        self.scene.invalidate()
    
    def add_item_to_layer(self, item, layer):
        """Add a graphics item to the layer tracking dictionary."""
        if layer not in self.layer_items:
            self.layer_items[layer] = []
        self.layer_items[layer].append(item)
        # Also store the reverse mapping for quick lookup
        self.item_to_layer[item] = layer
    
    def add_item_to_net(self, item, net_id):
        """Add a graphics item to the net tracking dictionary."""
        if net_id not in self.net_items:
            self.net_items[net_id] = []
        self.net_items[net_id].append(item)
        # Also store the reverse mapping for quick lookup
        self.item_to_net[item] = net_id
    
    def render_nodes(self):
        """Render nodes using layer colors"""
        node_count = 0
        for net_id, net in self.parser.nets.items():
            for node in net.get_nodes():
                ellipse = QGraphicsEllipseItem(
                    node.x - self.NODE_RADIUS, 
                    node.y - self.NODE_RADIUS, 
                    2 * self.NODE_RADIUS, 
                    2 * self.NODE_RADIUS ) 
                # Use layer color for nodes
                node_color = self.get_layer_color(node.layer)
                ellipse.setBrush(node_color) 
                ellipse.setToolTip(f"Node: {node.id}\nNet: {net_id}\nLayer: {node.layer}") 
                # Make selectable
                ellipse.setFlag(QGraphicsItem.ItemIsSelectable, True)
                self.scene.addItem(ellipse)
                self.add_item_to_layer(ellipse, node.layer)
                self.add_item_to_net(ellipse, net_id)
                # Map to node for selection
                self.item_to_node[ellipse] = node
                node_count += 1

    def render_elements(self): 
        """Render RC elements"""
        element_count = 0
        # Build a node lookup from all nets
        all_nodes = {}
        for net in self.parser.nets.values():
            for node in net.get_nodes():
                all_nodes[node.id] = node
        
        for net_id, net in self.parser.nets.items():
            for elem in net.get_elements():
                element_count += 1 
                # Track which elements use which nodes
                if elem.node1 not in self.node_to_elements:
                    self.node_to_elements[elem.node1] = []
                if elem.node2 not in self.node_to_elements:
                    self.node_to_elements[elem.node2] = []
                self.node_to_elements[elem.node1].append(elem)
                self.node_to_elements[elem.node2].append(elem)
                
                # Use layer color for elements
                layer_color = self.get_layer_color(elem.layer)
                # For elements, use a slightly darker version for the pen
                pen_color = layer_color.darker(120)  # Make it 20% darker
                pen = QPen(pen_color) 
                pen.setWidth(1) 
                
                # Initialize element graphics items list
                if elem not in self.element_graphics_items:
                    self.element_graphics_items[elem] = []
                
                # If element has bounding box, display as rectangle
                if elem.llx is not None and elem.lly is not None and elem.urx is not None and elem.ury is not None: 
                    rect = QGraphicsRectItem(
                        elem.llx, 
                        elem.lly, 
                        elem.urx - elem.llx, 
                        elem.ury - elem.lly) 
                    rect.setPen(pen) 
                    # Use layer color with lighter fill
                    rect.setBrush(layer_color.lighter(150)) 
                    # Make selectable
                    rect.setFlag(QGraphicsItem.ItemIsSelectable, True)
                    
                    # Fill with light color
                    rect.setToolTip(
                        f"{elem.type} {elem.id}\nNet: {net_id}\nValue: {elem.value}\nLayer: {elem.layer}") 
                    self.scene.addItem(rect)
                    self.add_item_to_layer(rect, elem.layer)
                    self.add_item_to_net(rect, net_id)
                    # Map to element for selection
                    self.item_to_element[rect] = elem
                    # Track graphics items for this element
                    self.element_graphics_items[elem].append(rect)
                else: 
                    # If no bbox, use line connecting nodes
                    n1 = all_nodes.get(elem.node1) 
                    n2 = all_nodes.get(elem.node2) 
                    if not n1 or not n2: 
                        continue 
                    line = self.scene.addLine(n1.x, n1.y, n2.x, n2.y, pen) 
                    # Make selectable
                    line.setFlag(QGraphicsItem.ItemIsSelectable, True)
                    line.setToolTip(f"{elem.type} {elem.id}\nNet: {net_id}\nValue: {elem.value}\nLayer: {elem.layer}") 
                    self.scene.addItem(line)
                    self.add_item_to_layer(line, elem.layer)
                    self.add_item_to_net(line, net_id)
                    # Map to element for selection
                    self.item_to_element[line] = elem
                    # Track graphics items for this element
                    self.element_graphics_items[elem].append(line)
        
        render_nodes_for_elements_start = time.time()
        self.render_nodes_for_elements()
        render_nodes_for_elements_time = time.time() - render_nodes_for_elements_start
        print(f"[Time Stats] Render element nodes: {render_nodes_for_elements_time:.4f} seconds")
        print(f"[Time Stats] Rendered {element_count} elements")
        # also render the nodes for the elements
    

    def render_nodes_for_elements(self):
        """Render nodes for elements using layer colors"""
        element_node_count = 0
        for net_id, net in self.parser.nets.items():
            for elem in net.get_elements():
                n1 = net.get_node(elem.node1)
                n2 = net.get_node(elem.node2)
                if n1:
                    ellipse = QGraphicsEllipseItem(
                        n1.x - self.NODE_RADIUS, 
                        n1.y - self.NODE_RADIUS, 
                        2 * self.NODE_RADIUS, 
                        2 * self.NODE_RADIUS ) 
                    # Use layer color for nodes
                    node_color = self.get_layer_color(n1.layer)
                    ellipse.setBrush(node_color) 
                    ellipse.setToolTip(f"Node: {n1.id}\nNet: {net_id}\nLayer: {n1.layer}") 
                    # Make selectable
                    ellipse.setFlag(QGraphicsItem.ItemIsSelectable, True)
                    self.scene.addItem(ellipse)
                    self.add_item_to_layer(ellipse, n1.layer)
                    self.add_item_to_net(ellipse, net_id)
                    # Map to node for selection
                    self.item_to_node[ellipse] = n1
                    element_node_count += 1
                if n2:
                    ellipse = QGraphicsEllipseItem(
                        n2.x - self.NODE_RADIUS, 
                        n2.y - self.NODE_RADIUS, 
                        2 * self.NODE_RADIUS, 
                        2 * self.NODE_RADIUS ) 
                    # Use layer color for nodes
                    node_color = self.get_layer_color(n2.layer)
                    ellipse.setBrush(node_color) 
                    ellipse.setToolTip(f"Node: {n2.id}\nNet: {net_id}\nLayer: {n2.layer}") 
                    # Make selectable
                    ellipse.setFlag(QGraphicsItem.ItemIsSelectable, True)
                    self.scene.addItem(ellipse)
                    self.add_item_to_layer(ellipse, n2.layer)
                    self.add_item_to_net(ellipse, net_id)
                    # Map to node for selection
                    self.item_to_node[ellipse] = n2
                    element_node_count += 1
    def on_selection_changed(self):
        """Handle selection change in the scene."""
        selected_items = self.scene.selectedItems()
        if selected_items:
            # Get the first selected item
            item = selected_items[0]
            # Check if it's a resistor element
            element = self.item_to_element.get(item)
            if element and element.type == 'R':
                self.highlight_resistor(element)
            else:
                self.clear_highlight()
        else:
            self.clear_highlight()
    
    def highlight_resistor(self, element):
        """Highlight a resistor and its two nodes."""
        # Clear previous highlight
        self.clear_highlight()
        
        self.selected_element = element
        self.selected_element_items = []
        self.selected_node_items = []
        
        # Find and highlight the two nodes
        node1_id = element.node1
        node2_id = element.node2
        
        # Find the net for this element by checking its graphics items
        net_id = None
        net_name = None
        for item, elem in self.item_to_element.items():
            if elem == element:
                net_id = self.item_to_net.get(item)
                if net_id:
                    net = self.parser.nets.get(net_id)
                    if net:
                        net_name = net.name if hasattr(net, 'name') else net_id
                    break
        
        # Debug print: selected resistor, nodes, and net
        print(f"[DEBUG] Selected Resistor: {element.id} (type: {element.type}, value: {element.value})")
        print(f"[DEBUG] Selected Nodes: {node1_id}, {node2_id}")
        print(f"[DEBUG] Net: {net_name if net_name else net_id if net_id else 'Unknown'}")
        
        # Update status bar with resistor information
        status_text = f"Resistor: {element.id} | Type: {element.type} | Value: {element.value} | "
        status_text += f"Nodes: {node1_id}, {node2_id} | "
        status_text += f"Net: {net_name if net_name else net_id if net_id else 'Unknown'}"
        if element.layer:
            status_text += f" | Layer: {element.layer}"
        self.update_status_message(status_text)
        
        # Find all graphics items for this element
        for item, elem in self.item_to_element.items():
            if elem == element:
                self.selected_element_items.append(item)
                # Store original style and Z value
                if item not in self.item_original_pen:
                    self.item_original_pen[item] = item.pen() if hasattr(item, 'pen') else None
                if item not in self.item_original_brush:
                    self.item_original_brush[item] = item.brush() if hasattr(item, 'brush') else None
                if item not in self.item_original_zvalue:
                    self.item_original_zvalue[item] = item.zValue()
                # Highlight the element
                highlight_pen = QPen(QColor("yellow"), 3)
                highlight_brush = QColor("yellow").lighter(150)
                if hasattr(item, 'setPen'):
                    item.setPen(highlight_pen)
                if hasattr(item, 'setBrush'):
                    item.setBrush(highlight_brush)
                # Bring to front by setting high Z value
                item.setZValue(1000)
        
        target_node_ids = {node1_id, node2_id}
        highlighted_node_ids = set()  # Track which nodes have been highlighted
        
        # Find graphics items for the two nodes, but only highlight once per node
        for item, node in self.item_to_node.items():
            if node.id in target_node_ids and node.id not in highlighted_node_ids:
                self.selected_node_items.append(item)
                highlighted_node_ids.add(node.id)  # Mark this node as highlighted
                # Store original style and Z value
                if item not in self.item_original_pen:
                    self.item_original_pen[item] = item.pen() if hasattr(item, 'pen') else None
                if item not in self.item_original_brush:
                    self.item_original_brush[item] = item.brush() if hasattr(item, 'brush') else None
                if item not in self.item_original_zvalue:
                    self.item_original_zvalue[item] = item.zValue()
                # Highlight the node
                highlight_pen = QPen(QColor("orange"), 3)
                highlight_brush = QColor("orange")
                if hasattr(item, 'setPen'):
                    item.setPen(highlight_pen)
                if hasattr(item, 'setBrush'):
                    item.setBrush(highlight_brush)
                # Bring to front by setting high Z value (higher than elements)
                item.setZValue(1001)
        
        # Force update
        self.view.update()
        self.scene.update()
        # Update thumbnail to show selection
        self.update_thumbnail()
    
    def clear_highlight(self):
        """Clear all highlights and restore original styles."""
        # Restore element styles and Z values
        for item in self.selected_element_items:
            if item in self.item_original_pen and self.item_original_pen[item]:
                if hasattr(item, 'setPen'):
                    item.setPen(self.item_original_pen[item])
            if item in self.item_original_brush and self.item_original_brush[item]:
                if hasattr(item, 'setBrush'):
                    item.setBrush(self.item_original_brush[item])
            if item in self.item_original_zvalue:
                item.setZValue(self.item_original_zvalue[item])
        
        # Restore node styles and Z values
        for item in self.selected_node_items:
            if item in self.item_original_pen and self.item_original_pen[item]:
                if hasattr(item, 'setPen'):
                    item.setPen(self.item_original_pen[item])
            if item in self.item_original_brush and self.item_original_brush[item]:
                if hasattr(item, 'setBrush'):
                    item.setBrush(self.item_original_brush[item])
            if item in self.item_original_zvalue:
                item.setZValue(self.item_original_zvalue[item])
        
        self.selected_element = None
        self.selected_element_items = []
        self.selected_node_items = []
        
        # Clear status bar
        self.update_status_message("Ready")
        
        # Force update
        self.view.update()
        self.scene.update()
        # Update thumbnail
        self.update_thumbnail()
    
    def wheelEvent(self, event):
        zoom_factor = 1.15 
        if event.angleDelta().y() > 0: 
            self.view.scale(zoom_factor, zoom_factor) 
        else: 
            self.view.scale(1 / zoom_factor, 1 / zoom_factor)
        self.update_viewport_rect()
        self.update_viewport_rect()
    
    def show_context_menu(self, global_pos, scene_pos):
        """Show context menu at the right-click position."""
        menu = QMenu(self)
        
        # Find item at the clicked position
        item_at_pos = self.scene.itemAt(scene_pos, self.view.transform())
        
        if item_at_pos:
            # Menu for items (resistors or nodes)
            if item_at_pos in self.item_to_element:
                # Right-clicked on a resistor
                element = self.item_to_element[item_at_pos]
                menu.addAction(f"Resistor: {element.id}", lambda: self._select_element(element))
                menu.addSeparator()
                # Find net for this element using item_to_net mapping
                net_id = self.item_to_net.get(item_at_pos)
                if net_id:
                    menu.addAction(f"Net: {net_id}", lambda: self._select_net(net_id))
                if element.layer:
                    menu.addAction(f"Layer: {element.layer}", lambda: self._select_layer(element.layer))
            elif item_at_pos in self.item_to_node:
                # Right-clicked on a node
                node = self.item_to_node[item_at_pos]
                menu.addAction(f"Node: {node.id}", lambda: self._select_node(node))
                menu.addSeparator()
                if node.layer:
                    menu.addAction(f"Layer: {node.layer}", lambda: self._select_layer(node.layer))
                # Find net for this node
                net_id = self.item_to_net.get(item_at_pos)
                if net_id:
                    menu.addAction(f"Net: {net_id}", lambda: self._select_net(net_id))
            
            menu.addSeparator()
        
        # Common menu items
        menu.addAction("Zoom In", self.zoom_in)
        menu.addAction("Zoom Out", self.zoom_out)
        menu.addAction("Fit to View", self.fit_to_view)
        menu.addAction("Reset Zoom", self.reset_zoom)
        menu.addSeparator()
        menu.addAction("Clear Selection", self.clear_selection)
        
        # Show menu
        menu.exec(global_pos)
    
    def _select_element(self, element):
        """Select and highlight an element."""
        # Clear current selection
        self.scene.clearSelection()
        # Find and select the graphics items for this element
        if element in self.element_graphics_items:
            for item in self.element_graphics_items[element]:
                item.setSelected(True)
        self.on_selection_changed()
    
    def _select_node(self, node):
        """Select and highlight a node."""
        # Clear current selection
        self.scene.clearSelection()
        # Find and select the graphics item for this node
        for item, n in self.item_to_node.items():
            if n == node:
                item.setSelected(True)
                break
        self.on_selection_changed()
    
    def _select_net(self, net_id):
        """Select all items in a net."""
        # Clear current selection
        self.scene.clearSelection()
        # Select all items in this net
        if net_id in self.net_items:
            for item in self.net_items[net_id]:
                item.setSelected(True)
        self.on_selection_changed()
    
    def _select_layer(self, layer):
        """Select all items in a layer."""
        # Clear current selection
        self.scene.clearSelection()
        # Select all items in this layer
        if layer in self.layer_items:
            for item in self.layer_items[layer]:
                item.setSelected(True)
        self.on_selection_changed()

    def show(self):
        #self.render_nodes()
        self.render_elements()
        super().show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = RCViewer("examples/example1.spf")
    viewer.show()
    sys.exit(app.exec())