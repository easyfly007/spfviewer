from PySide6.QtWidgets import (QMainWindow, QGraphicsView, QGraphicsScene, 
                                QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsLineItem,
                                QDockWidget, QCheckBox, QVBoxLayout, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPen, QColor
from PySide6.QtWidgets import QApplication
from .spfparser import SPFParser
import sys
import os

class RCViewer(QMainWindow):
    NODE_RADIUS = 2.0
    
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
        
        # Collect all layers and create layer selection panel
        self.collect_layers()
        self.create_layer_panel()
        
        self.render_nodes()
        self.render_elements()
    
    def collect_layers(self):
        """Collect all unique layers from nodes and elements."""
        layers = set()
        for net in self.parser.nets.values():
            for node in net.get_nodes():
                if node.layer:
                    layers.add(node.layer)
            for elem in net.get_elements():
                if elem.layer:
                    layers.add(elem.layer)
        # Add None layer for items without layer
        self.all_layers = sorted([l for l in layers if l is not None]) + [None]
        self.selected_layers = set(self.all_layers)  # All layers selected by default
    
    def create_layer_panel(self):
        """Create a dock widget with layer selection checkboxes."""
        dock = QDockWidget("Layer Selection", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Create checkboxes for each layer
        self.layer_checkboxes = {}
        for layer in self.all_layers:
            layer_name = str(layer) if layer is not None else "None"
            checkbox = QCheckBox(layer_name)
            checkbox.setChecked(True)  # All layers visible by default
            checkbox.stateChanged.connect(lambda state, l=layer: self.on_layer_toggled(l, state))
            self.layer_checkboxes[layer] = checkbox
            layout.addWidget(checkbox)
        
        layout.addStretch()
        dock.setWidget(widget)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
    
    def on_layer_toggled(self, layer, state):
        """Handle layer visibility toggle."""
        if state == Qt.Checked:
            self.selected_layers.add(layer)
        else:
            self.selected_layers.discard(layer)
        self.update_layer_visibility()
    
    def update_layer_visibility(self):
        """Update visibility of graphics items based on selected layers."""
        for layer, items in self.layer_items.items():
            visible = layer in self.selected_layers
            for item in items:
                item.setVisible(visible)
    
    def add_item_to_layer(self, item, layer):
        """Add a graphics item to the layer tracking dictionary."""
        if layer not in self.layer_items:
            self.layer_items[layer] = []
        self.layer_items[layer].append(item)
    
    def render_nodes(self):
        """渲染节点为蓝色圆点""" 
        for net in self.parser.nets.values():
            for node in net.get_nodes():
                ellipse = QGraphicsEllipseItem(
                    node.x - self.NODE_RADIUS, 
                    node.y - self.NODE_RADIUS, 
                    2 * self.NODE_RADIUS, 
                    2 * self.NODE_RADIUS ) 
                ellipse.setBrush(QColor("blue")) 
                ellipse.setToolTip(f"Node: {node.id}\nLayer: {node.layer}") 
                self.scene.addItem(ellipse)
                self.add_item_to_layer(ellipse, node.layer)

    def render_elements(self): 
        """渲染 RC 元素""" 
        # Build a node lookup from all nets
        all_nodes = {}
        for net in self.parser.nets.values():
            for node in net.get_nodes():
                all_nodes[node.id] = node
        
        for net in self.parser.nets.values():
            for elem in net.get_elements(): 
                # 设置颜色 
                color = QColor("red") 
                if elem.type == 'R':
                    pass
                else:
                    color = QColor("green") 
                pen = QPen(color) 
                pen.setWidth(1) 
                
                # 电阻有边界框就用矩形显示 
                if elem.llx is not None and elem.lly is not None and elem.urx is not None and elem.ury is not None: 
                    rect = QGraphicsRectItem(
                        elem.llx, 
                        elem.lly, 
                        elem.urx - elem.llx, 
                        elem.ury - elem.lly) 
                    rect.setPen(pen) 
                    rect.setBrush(QColor(color).lighter(170)) 
                    
                    # 填充浅色 
                    rect.setToolTip(
                        f"{elem.type} {elem.id}\nValue: {elem.value}\nLayer: {elem.layer}") 
                    self.scene.addItem(rect)
                    self.add_item_to_layer(rect, elem.layer)
                else: 
                    # 没有 bbox 就用节点连线 
                    n1 = all_nodes.get(elem.node1) 
                    n2 = all_nodes.get(elem.node2) 
                    if not n1 or not n2: 
                        continue 
                    line = self.scene.addLine(n1.x, n1.y, n2.x, n2.y, pen) 
                    line.setToolTip(f"{elem.type} {elem.id}\nValue: {elem.value}\nLayer: {elem.layer}") 
                    self.scene.addItem(line)
                    self.add_item_to_layer(line, elem.layer) 

    def wheelEvent(self, event):
        zoom_factor = 1.15 
        if event.angleDelta().y() > 0: 
            self.view.scale(zoom_factor, zoom_factor) 
        else: 
            self.view.scale(1 / zoom_factor, 1 / zoom_factor)

    def show(self):
        self.render_nodes()
        self.render_elements()
        super().show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = RCViewer("examples/example1.spf")
    viewer.show()
    sys.exit(app.exec())