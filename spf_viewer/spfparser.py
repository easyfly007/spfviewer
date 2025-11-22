from spf_viewer.node import Node
from spf_viewer.rcelem import RCElement
from spf_viewer.net import Net
import re

class SPFParser:
    """
    A simple SPF / DSPF parser.
    Parses nodes, resistors (R), and capacitors (C) from a SPF/DSPF file.
    """
    """
    example00.spf:
    .subckt example_netlist VDD GND

    *|NET N1
    *|I N1 X=0.0 Y=0.0
    *|P N2 X=10.0 Y=0.0
    R1 N1 N2 100 llx=0.0 lly=0.0 urx=10.0 ury=10.0 layer=M1
    C1 N1 GND 0.5

    *|NET N2
    *|I N2 X=10.0 Y=0.0
    *|P N3 X=20.0 Y=0.0
    *|S N4 X=10.0 Y=10.0
    R2 N2 N3 200 llx=10.0 lly=0.0 urx=20.0 ury=10.0 layer=M1
    R3 N2 N4 50 llx=10.0 lly=0.0 urx=10.0 ury=10.0 layer=M2
    C2 N2 GND 0.8

    *|NET N3
    *|I N3 X=20.0 Y=0.0
    *|P N5 X=30.0 Y=0.0
    R4 N3 N5 150 llx=20.0 lly=0.0 urx=30.0 ury=10.0 layer=M1
    C3 N3 GND 0.3

    .ends example_netlist
    """
    def __init__(self, file_path):
        self.file_path = file_path
        self.nets = {}
        self.parse()

    def parse(self):
        """Parse the file and populate the nodes and elements dictionaries."""

        with open(self.file_path, 'r') as f:
            subckt = None
            current_net = None
            for line in f :
                line = line.strip()    # Remove whitespace and comments
                if not line or line.startswith('#'):    # Skip empty lines and comments
                    continue
                if line.lower().startswith('.subckt'):
                    tokens = line.split()
                    subckt = tokens[1]
                    continue
                if line.startswith('.ends'):
                    subckt = None
                    continue

                if line.startswith('*|NET'):
                    tokens = line.split()
                    net_id = tokens[1]
                    current_net = Net(net_id, net_id)
                    self.nets[net_id] = current_net
                    continue
                
                # node line
                if line.startswith('*|I') or line.startswith('*|P') or line.startswith('*|S'):
                    tokens = line.split()
                    if tokens[0] == '*|I':
                        nodetype = 'I'
                    elif tokens[0] == '*|P':
                        nodetype = 'P'
                    elif tokens[0] == '*|S':
                        nodetype = 'S'
                    else:
                        assert False, "Invalid node type"
                    nodename = tokens[1]
                    layer = None    # default layer is None if not specified
                    x = None
                    y = None
                    for tok in tokens[2:]:
                        if tok.lower().startswith('x='):
                            # ignore case sensitivity for X= and x=
                            x = float(tok.split('=')[1])
                        elif tok.lower().startswith('y='):
                            y = float(tok.split('=')[1])
                        elif tok.lower().startswith('layer='):
                            layer = tok.split('=')[1]
                        else:
                            assert False, "Invalid token"
                    node = Node(nodename, x, y, nodetype, layer)
                    current_net.add_node(node)
                    continue

                # Resistor line
                if line.startswith('R') or line.startswith('C') or line.startswith('L'):
                    tokens = line.split()
                    elem_name = tokens[0]
                    if elem_name.startswith('R'):
                        elem_type = 'R'
                    elif elem_name.startswith('C'):
                        elem_type = 'C'
                    elif elem_name.startswith('L'):
                        elem_type = 'L'
                    else:
                        assert False, "Invalid element type"
                    if elem_type == 'C' or elem_type == 'L':
                        continue
                    # ignore other element types except R
                    n1_name = tokens[1]
                    n2_name = tokens[2]
                    value = tokens[3]
                    elem_id = elem_name
                    if len(tokens) >= 5:
                        assert tokens[4] == '$', "Invalid layer token" + str(tokens[4])   
                    tokens = tokens[5:]
                    llx = None
                    lly = None
                    urx = None
                    ury = None
                    for token in tokens:
                        if token.lower().startswith('llx='):
                            llx = float(token.split('=')[1])
                        elif token.lower().startswith('lly='):
                            lly = float(token.split('=')[1])
                        elif token.lower().startswith('urx='):
                            urx = float(token.split('=')[1])
                        elif token.lower().startswith('ury='):
                            ury = float(token.split('=')[1])
                        elif token.lower().startswith('layer='):
                            layer = token.split('=')[1]
                        else:
                            assert False, "Invalid token" + str(token)
                    n1 = current_net.get_node(n1_name)
                    n2 = current_net.get_node(n2_name)
                    elem = RCElement(elem_id, n1.id, n2.id, float(value), llx, lly, urx, ury, layer, elem_type)
                    current_net.add_element(elem)
                    continue

    def summary(self):
        """Print a summary of parsed nodes and RC elements."""
        print(f"Parsed {len(self.nets)} nets.")
        print("Nets (sample):", list(self.nets.keys())[:1])
        return self.nets

if __name__ == "__main__":
    spffile = "examples/example1.spf"
    parser = SPFParser(spffile)
    parser.summary()