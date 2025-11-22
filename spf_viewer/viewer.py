from PySide6.QtWidgets import (QMainWindow, QGraphicsView, QGraphicsScene, 
                                QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsLineItem,
                                QGraphicsItem,
                                QDockWidget, QCheckBox, QVBoxLayout, QWidget,
                                QToolBar, QAction)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPen, QColor, QIcon
from PySide6.QtWidgets import QApplication
from .spfparser import SPFParser
import sys
import os

class RCViewer(QMainWindow):
    NODE_RADIUS = 1
    
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.setWindowTitle("SPF/DSPF Viewer")
        self.setGeometry(100, 100, 800, 600)
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        # no qt please, use numpy and matplotlib instead
        self.view.setBackgroundBrush(QColor(255, 255, 255))
        self.setCentralWidget(self.view)
        self.parser = SPFParser(self.file_path)
        
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
        self.collect_layers()
        self.collect_nets()
        # Initialize layer color mapping
        self.init_layer_colors()
        # Create net panel first so it appears above layer panel
        self.create_net_panel()
        self.create_layer_panel()
        
        # Create toolbar
        self.create_toolbar()
        
        self.render_nodes()
        self.render_elements()
        
        # Connect scene selection changed signal
        self.scene.selectionChanged.connect(self.on_selection_changed)
    
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
    
    def zoom_out(self):
        """Zoom out the view."""
        self.view.scale(1.0 / 1.2, 1.0 / 1.2)
    
    def fit_to_view(self):
        """Fit all items to the view."""
        if self.scene.items():
            self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
    
    def reset_zoom(self):
        """Reset zoom to 1:1."""
        self.view.resetTransform()
    
    def clear_selection(self):
        """Clear current selection and highlights."""
        self.scene.clearSelection()
        self.clear_highlight()
    
    def create_layer_panel(self):
        """Create a dock widget with layer selection checkboxes."""
        self.layer_dock = QDockWidget("Layer Selection", self)
        self.layer_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Create checkboxes for each layer
        self.layer_checkboxes = {}
        for layer in self.all_layers:
            layer_name = str(layer) if layer is not None else "None"
            checkbox = QCheckBox(layer_name)
            checkbox.setChecked(True)  # All layers visible by default
            # Use a lambda that captures the checkbox object to get the actual state
            checkbox.stateChanged.connect(lambda checked, l=layer, cb=checkbox: self.on_layer_toggled(l, cb.isChecked()))
            self.layer_checkboxes[layer] = checkbox
            layout.addWidget(checkbox)
        
        layout.addStretch()
        self.layer_dock.setWidget(widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.layer_dock)
        # Split the dock widgets vertically so net panel is above layer panel
        self.splitDockWidget(self.net_dock, self.layer_dock, Qt.Vertical)
        # Make sure the dock widget is visible
        self.layer_dock.setVisible(True)
    
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
        """渲染节点，使用图层对应的颜色""" 
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

    def render_elements(self): 
        """渲染 RC 元素""" 
        # Build a node lookup from all nets
        all_nodes = {}
        for net in self.parser.nets.values():
            for node in net.get_nodes():
                all_nodes[node.id] = node
        
        for net_id, net in self.parser.nets.items():
            for elem in net.get_elements(): 
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
                
                # 电阻有边界框就用矩形显示 
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
                    
                    # 填充浅色 
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
                    # 没有 bbox 就用节点连线 
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
        self.render_nodes_for_elements()
        # also render the nodes for the elements
    

    def render_nodes_for_elements(self):
        """渲染节点，使用图层对应的颜色"""
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
        
        # Force update
        self.view.update()
        self.scene.update()
    
    def wheelEvent(self, event):
        zoom_factor = 1.15 
        if event.angleDelta().y() > 0: 
            self.view.scale(zoom_factor, zoom_factor) 
        else: 
            self.view.scale(1 / zoom_factor, 1 / zoom_factor)

    def show(self):
        #self.render_nodes()
        self.render_elements()
        super().show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = RCViewer("examples/example1.spf")
    viewer.show()
    sys.exit(app.exec())