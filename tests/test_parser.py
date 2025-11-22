import sys
import os

# Add parent directory to path to import spf_viewer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from spf_viewer.spfparser import SPFParser


def test_parser_basic():
    """Test basic parsing functionality."""
    # Use example00.spf for testing
    test_file = os.path.join(os.path.dirname(__file__), '..', 'examples', 'example00.spf')
    
    parser = SPFParser(test_file)
    
    # Test that nets are parsed
    assert len(parser.nets) > 0, "Should parse at least one net"
    print(f"✓ Parsed {len(parser.nets)} nets")
    
    # Test specific nets from example00.spf
    assert 'N1' in parser.nets, "Should have net N1"
    assert 'N2' in parser.nets, "Should have net N2"
    assert 'N3' in parser.nets, "Should have net N3"
    print("✓ All expected nets found")
    
    return parser


def test_net_n1():
    """Test parsing of net N1."""
    test_file = os.path.join(os.path.dirname(__file__), '..', 'examples', 'example00.spf')
    parser = SPFParser(test_file)
    
    net_n1 = parser.nets['N1']
    
    # Test nodes in N1
    nodes = list(net_n1.get_nodes())
    assert len(nodes) >= 2, f"Net N1 should have at least 2 nodes, got {len(nodes)}"
    print(f"✓ Net N1 has {len(nodes)} nodes")
    
    # Test node properties
    node_ids = [node.id for node in nodes]
    assert 'N1#1' in node_ids, "Should have node N1#1"
    assert 'N1#2' in node_ids, "Should have node N1#2"
    print("✓ Expected nodes found in N1")
    
    # Test node coordinates
    n1_node = net_n1.get_node('N1#1')
    assert n1_node is not None, "Should find node N1#1"
    assert n1_node.x == 0.0, f"Node N1#1 x should be 0.0, got {n1_node.x}"
    assert n1_node.y == 0.0, f"Node N1#1 y should be 0.0, got {n1_node.y}"
    print("✓ Node coordinates correct")
    
    # Test elements in N1
    elements = list(net_n1.get_elements())
    assert len(elements) >= 1, f"Net N1 should have at least 1 element, got {len(elements)}"
    print(f"✓ Net N1 has {len(elements)} elements")
    
    # Test R1 resistor
    r1 = net_n1.get_element('R1')
    assert r1 is not None, "Should have element R1"
    assert r1.type == 'R', f"R1 should be type R, got {r1.type}"
    assert r1.value == 100.0, f"R1 value should be 100.0, got {r1.value}"
    assert r1.node1 == 'N1#1', f"R1 node1 should be N1#1, got {r1.node1}"
    assert r1.node2 == 'N1#2', f"R1 node2 should be N1#2, got {r1.node2}"
    assert r1.layer == 'M1', f"R1 layer should be M1, got {r1.layer}"
    assert r1.llx == 0.0, f"R1 llx should be 0.0, got {r1.llx}"
    assert r1.lly == 0.0, f"R1 lly should be 0.0, got {r1.lly}"
    assert r1.urx == 10.0, f"R1 urx should be 10.0, got {r1.urx}"
    assert r1.ury == 10.0, f"R1 ury should be 10.0, got {r1.ury}"
    print("✓ R1 element properties correct")


def test_net_n2():
    """Test parsing of net N2."""
    test_file = os.path.join(os.path.dirname(__file__), '..', 'examples', 'example00.spf')
    parser = SPFParser(test_file)
    
    net_n2 = parser.nets['N2']
    
    # Test nodes in N2
    nodes = list(net_n2.get_nodes())
    assert len(nodes) >= 3, f"Net N2 should have at least 3 nodes, got {len(nodes)}"
    print(f"✓ Net N2 has {len(nodes)} nodes")
    
    # Test node types
    node_ids = [node.id for node in nodes]
    assert 'N2#1' in node_ids, "Should have node N2#1"
    assert 'N2' in node_ids, "Should have node N2"
    assert 'N2#3' in node_ids, "Should have node N2#3"
    print("✓ Expected nodes found in N2")
    
    # Test node types
    n2_1 = net_n2.get_node('N2#1')
    assert n2_1.type == 'I', f"N2#1 should be type I, got {n2_1.type}"
    
    n2_main = net_n2.get_node('N2')
    assert n2_main.type == 'P', f"N2 should be type P, got {n2_main.type}"
    
    n2_3 = net_n2.get_node('N2#3')
    assert n2_3.type == 'S', f"N2#3 should be type S, got {n2_3.type}"
    print("✓ Node types correct")
    
    # Test elements in N2
    elements = list(net_n2.get_elements())
    assert len(elements) >= 2, f"Net N2 should have at least 2 elements, got {len(elements)}"
    print(f"✓ Net N2 has {len(elements)} elements")
    
    # Test R2 resistor
    r2 = net_n2.get_element('R2')
    assert r2 is not None, "Should have element R2"
    assert r2.value == 200.0, f"R2 value should be 200.0, got {r2.value}"
    assert r2.layer == 'M1', f"R2 layer should be M1, got {r2.layer}"
    print("✓ R2 element properties correct")
    
    # Test R3 resistor
    r3 = net_n2.get_element('R3')
    assert r3 is not None, "Should have element R3"
    assert r3.value == 50.0, f"R3 value should be 50.0, got {r3.value}"
    assert r3.layer == 'M2', f"R3 layer should be M2, got {r3.layer}"
    print("✓ R3 element properties correct")


def test_net_n3():
    """Test parsing of net N3."""
    test_file = os.path.join(os.path.dirname(__file__), '..', 'examples', 'example00.spf')
    parser = SPFParser(test_file)
    
    net_n3 = parser.nets['N3']
    
    # Test nodes in N3
    nodes = list(net_n3.get_nodes())
    assert len(nodes) >= 2, f"Net N3 should have at least 2 nodes, got {len(nodes)}"
    print(f"✓ Net N3 has {len(nodes)} nodes")
    
    # Test R4 resistor
    r4 = net_n3.get_element('R4')
    assert r4 is not None, "Should have element R4"
    assert r4.value == 150.0, f"R4 value should be 150.0, got {r4.value}"
    assert r4.layer == 'M1', f"R4 layer should be M1, got {r4.layer}"
    print("✓ R4 element properties correct")


def test_all_nets_summary():
    """Test summary of all parsed nets."""
    test_file = os.path.join(os.path.dirname(__file__), '..', 'examples', 'example00.spf')
    parser = SPFParser(test_file)
    
    total_nodes = 0
    total_elements = 0
    
    for net_id, net in parser.nets.items():
        nodes = list(net.get_nodes())
        elements = list(net.get_elements())
        total_nodes += len(nodes)
        total_elements += len(elements)
        print(f"  Net {net_id}: {len(nodes)} nodes, {len(elements)} elements")
    
    print(f"✓ Total: {len(parser.nets)} nets, {total_nodes} nodes, {total_elements} elements")
    assert total_nodes > 0, "Should have parsed some nodes"
    assert total_elements > 0, "Should have parsed some elements"


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Running SPF Parser Tests")
    print("=" * 60)
    
    try:
        print("\n1. Testing basic parsing...")
        parser = test_parser_basic()
        
        print("\n2. Testing net N1...")
        test_net_n1()
        
        print("\n3. Testing net N2...")
        test_net_n2()
        
        print("\n4. Testing net N3...")
        test_net_n3()
        
        print("\n5. Testing all nets summary...")
        test_all_nets_summary()
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        return True
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

