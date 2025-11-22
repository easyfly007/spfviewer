import re

class Node:
    def __init__(self, node_id, x=0.0, y=0.0, type='S', layer=None):
        self.id = node_id
        self.x = x
        self.y = y
        self.layer = layer
        self.net = None
        self.type = type
    def __repr__(self): 
        return f"Node(id={self.id}, layer={self.layer}, net={self.net}, type={self.type})"
    def __str__(self):
        return f"Node(id={self.id}, layer={self.layer}, net={self.net}, type={self.type})"
    def set_net(self, net):
        self.net = net
    def get_net(self):
        return self.net
    