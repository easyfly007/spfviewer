class Net:
    def __init__(self, net_id, name, type = None):
        self.id = net_id
        self.name = name
        self.type = type
        self.nodes = {}
        self.elements = {}
        self._element_counter = 0  # Counter for assigning indices to elements in this net
    def __repr__(self):
        return f"Net(id={self.id}, name={self.name}, type={self.type}, nodes={self.nodes})"
    def __str__(self):
        return f"Net(id={self.id}, name={self.name}, type={self.type}, nodes={self.nodes})"
    def add_node(self, node):
        self.nodes[node.id] = node
    def add_element(self, element):
        self.elements[element.id] = element
        # Assign index to element within this net (starting from 0)
        element.index = self._element_counter
        self._element_counter += 1
    def get_element(self, element_id):
        return self.elements.get(element_id)
    def get_nodes(self):
        return self.nodes.values()
    def get_elements(self):
        return self.elements.values()
    def get_node(self, node_id):
        return self.nodes.get(node_id)