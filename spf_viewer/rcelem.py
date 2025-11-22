class RCElement:
    """
    this is the basic 
    """
    def __init__(self, element_id, n1, n2, value, llx=None, lly=None, urx=None, ury=None, layer=None, elem_type='R'):
        self.id = element_id
        self.node1 = n1
        self.node2 = n2
        self.value = value
        self.llx = llx
        self.lly = lly
        self.urx = urx
        self.ury = ury
        self.layer = layer
        self.type = elem_type
    def __repr__(self):
        return f"RCElement(id={self.id}, node1={self.node1}, node2={self.node2}, value={self.value}, layer={self.layer}, type={self.type})"
    def __str__(self):
        return f"RCElement(id={self.id}, node1={self.node1}, node2={self.node2}, value={self.value}, layer={self.layer}, type={self.type})"
    def set_node1(self, node):
        self.node1 = node
    def set_node2(self, node):
        self.node2 = node
    def get_node1(self):
        return self.node1
    def get_node2(self):
        return self.node2
    def get_value(self):
        return self.value