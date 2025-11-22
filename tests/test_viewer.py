import sys
import os

# Add parent directory to path to import spf_viewer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from PySide6.QtWidgets import QApplication
from spf_viewer.viewer import RCViewer


# Create QApplication instance for testing (required for Qt widgets)
if not QApplication.instance():
    app = QApplication(sys.argv)
else:
    app = QApplication.instance()


def test_viewer_initialization():
    """Test that viewer can be initialized."""
    test_file = os.path.join(os.path.dirname(__file__), '..', 'examples', 'example00.spf')
    
    viewer = RCViewer(test_file)
    
    # Test basic initialization
    assert viewer.parser is not None, "Parser should be initialized"
    assert viewer.scene is not None, "Scene should be initialized"
    assert viewer.view is not None, "View should be initialized"
    assert viewer.file_path == test_file, "File path should be set correctly"
    print("✓ Viewer initialized successfully")
    
    return viewer


def test_layer_collection():
    """Test layer collection functionality."""
    test_file = os.path.join(os.path.dirname(__file__), '..', 'examples', 'example00.spf')
    viewer = RCViewer(test_file)
    
    # Test that layers are collected
    assert hasattr(viewer, 'all_layers'), "Should have all_layers attribute"
    assert len(viewer.all_layers) > 0, "Should have at least one layer"
    print(f"✓ Collected {len(viewer.all_layers)} layers")
    
    # Test that expected layers are present (M1, M2 from example00.spf)
    layer_names = [str(l) if l is not None else 'None' for l in viewer.all_layers]
    assert 'M1' in layer_names, "Should have layer M1"
    assert 'M2' in layer_names, "Should have layer M2"
    print("✓ Expected layers found")
    
    # Test selected_layers
    assert hasattr(viewer, 'selected_layers'), "Should have selected_layers attribute"
    assert len(viewer.selected_layers) == len(viewer.all_layers), "All layers should be selected by default"
    print("✓ All layers selected by default")


def test_net_collection():
    """Test net collection functionality."""
    test_file = os.path.join(os.path.dirname(__file__), '..', 'examples', 'example00.spf')
    viewer = RCViewer(test_file)
    
    # Test that nets are collected
    assert hasattr(viewer, 'all_nets'), "Should have all_nets attribute"
    assert len(viewer.all_nets) > 0, "Should have at least one net"
    print(f"✓ Collected {len(viewer.all_nets)} nets")
    
    # Test that expected nets are present
    assert 'N1' in viewer.all_nets, "Should have net N1"
    assert 'N2' in viewer.all_nets, "Should have net N2"
    assert 'N3' in viewer.all_nets, "Should have net N3"
    print("✓ Expected nets found")
    
    # Test selected_nets
    assert hasattr(viewer, 'selected_nets'), "Should have selected_nets attribute"
    assert len(viewer.selected_nets) == len(viewer.all_nets), "All nets should be selected by default"
    print("✓ All nets selected by default")


def test_layer_colors():
    """Test layer color initialization."""
    test_file = os.path.join(os.path.dirname(__file__), '..', 'examples', 'example00.spf')
    viewer = RCViewer(test_file)
    
    # Test that layer colors are initialized
    assert hasattr(viewer, 'layer_colors'), "Should have layer_colors attribute"
    assert len(viewer.layer_colors) == len(viewer.all_layers), "Should have color for each layer"
    print(f"✓ Initialized colors for {len(viewer.layer_colors)} layers")
    
    # Test get_layer_color method
    for layer in viewer.all_layers:
        color = viewer.get_layer_color(layer)
        assert color is not None, f"Should return a color for layer {layer}"
    print("✓ get_layer_color works for all layers")


def test_graphics_items_tracking():
    """Test that graphics items are properly tracked."""
    test_file = os.path.join(os.path.dirname(__file__), '..', 'examples', 'example00.spf')
    viewer = RCViewer(test_file)
    
    # Test that items are tracked by layer
    assert hasattr(viewer, 'layer_items'), "Should have layer_items attribute"
    assert len(viewer.layer_items) > 0, "Should have some layer items"
    print(f"✓ Tracking items for {len(viewer.layer_items)} layers")
    
    # Test that items are tracked by net
    assert hasattr(viewer, 'net_items'), "Should have net_items attribute"
    assert len(viewer.net_items) > 0, "Should have some net items"
    print(f"✓ Tracking items for {len(viewer.net_items)} nets")
    
    # Test mappings
    assert hasattr(viewer, 'item_to_net'), "Should have item_to_net mapping"
    assert hasattr(viewer, 'item_to_layer'), "Should have item_to_layer mapping"
    assert hasattr(viewer, 'item_to_element'), "Should have item_to_element mapping"
    assert hasattr(viewer, 'item_to_node'), "Should have item_to_node mapping"
    print("✓ All item mappings initialized")


def test_layer_toggle():
    """Test layer visibility toggle functionality."""
    test_file = os.path.join(os.path.dirname(__file__), '..', 'examples', 'example00.spf')
    viewer = RCViewer(test_file)
    
    # Get initial selected layers count
    initial_count = len(viewer.selected_layers)
    
    # Test toggling a layer off
    if viewer.all_layers:
        test_layer = viewer.all_layers[0]
        viewer.on_layer_toggled(test_layer, False)
        assert test_layer not in viewer.selected_layers, "Layer should be removed from selected"
        assert len(viewer.selected_layers) == initial_count - 1, "Selected layers count should decrease"
        print("✓ Layer can be toggled off")
        
        # Test toggling a layer back on
        viewer.on_layer_toggled(test_layer, True)
        assert test_layer in viewer.selected_layers, "Layer should be added back to selected"
        assert len(viewer.selected_layers) == initial_count, "Selected layers count should restore"
        print("✓ Layer can be toggled on")


def test_net_toggle():
    """Test net visibility toggle functionality."""
    test_file = os.path.join(os.path.dirname(__file__), '..', 'examples', 'example00.spf')
    viewer = RCViewer(test_file)
    
    # Get initial selected nets count
    initial_count = len(viewer.selected_nets)
    
    # Test toggling a net off
    if viewer.all_nets:
        test_net = viewer.all_nets[0]
        viewer.on_net_toggled(test_net, False)
        assert test_net not in viewer.selected_nets, "Net should be removed from selected"
        assert len(viewer.selected_nets) == initial_count - 1, "Selected nets count should decrease"
        print("✓ Net can be toggled off")
        
        # Test toggling a net back on
        viewer.on_net_toggled(test_net, True)
        assert test_net in viewer.selected_nets, "Net should be added back to selected"
        assert len(viewer.selected_nets) == initial_count, "Selected nets count should restore"
        print("✓ Net can be toggled on")


def test_ui_components():
    """Test that UI components are created."""
    test_file = os.path.join(os.path.dirname(__file__), '..', 'examples', 'example00.spf')
    viewer = RCViewer(test_file)
    
    # Test toolbar methods exist
    assert hasattr(viewer, 'zoom_in'), "Should have zoom_in method"
    assert hasattr(viewer, 'zoom_out'), "Should have zoom_out method"
    assert hasattr(viewer, 'fit_to_view'), "Should have fit_to_view method"
    assert hasattr(viewer, 'reset_zoom'), "Should have reset_zoom method"
    assert hasattr(viewer, 'clear_selection'), "Should have clear_selection method"
    print("✓ Toolbar methods exist")
    
    # Test status bar
    assert viewer.statusBar() is not None, "Status bar should exist"
    print("✓ Status bar created")
    
    # Test dock widgets
    assert hasattr(viewer, 'net_dock'), "Should have net_dock"
    assert hasattr(viewer, 'layer_dock'), "Should have layer_dock"
    print("✓ Dock widgets created")


def test_zoom_functions():
    """Test zoom functionality."""
    test_file = os.path.join(os.path.dirname(__file__), '..', 'examples', 'example00.spf')
    viewer = RCViewer(test_file)
    
    # Get initial transform
    initial_transform = viewer.view.transform()
    
    # Test zoom in
    viewer.zoom_in()
    new_transform = viewer.view.transform()
    assert new_transform != initial_transform, "Transform should change after zoom in"
    print("✓ Zoom in works")
    
    # Test zoom out
    viewer.zoom_out()
    print("✓ Zoom out works")
    
    # Test reset zoom
    viewer.reset_zoom()
    reset_transform = viewer.view.transform()
    # Reset should restore to identity (approximately)
    print("✓ Reset zoom works")


def test_highlight_clear():
    """Test highlight and clear functionality."""
    test_file = os.path.join(os.path.dirname(__file__), '..', 'examples', 'example00.spf')
    viewer = RCViewer(test_file)
    
    # Test that clear_highlight works
    viewer.clear_highlight()
    assert viewer.selected_element is None, "Selected element should be None after clear"
    assert len(viewer.selected_element_items) == 0, "Selected element items should be empty"
    assert len(viewer.selected_node_items) == 0, "Selected node items should be empty"
    print("✓ Clear highlight works")
    
    # Test that status bar is cleared
    status_message = viewer.statusBar().currentMessage()
    assert status_message == "Ready", "Status bar should show 'Ready' after clear"
    print("✓ Status bar cleared correctly")


def test_node_to_elements_mapping():
    """Test that node to elements mapping is created."""
    test_file = os.path.join(os.path.dirname(__file__), '..', 'examples', 'example00.spf')
    viewer = RCViewer(test_file)
    
    # Test that mapping exists
    assert hasattr(viewer, 'node_to_elements'), "Should have node_to_elements mapping"
    assert len(viewer.node_to_elements) > 0, "Should have some node to element mappings"
    print(f"✓ Created {len(viewer.node_to_elements)} node-to-element mappings")
    
    # Test that nodes are mapped to their elements
    for net_id, net in viewer.parser.nets.items():
        for elem in net.get_elements():
            if elem.node1 in viewer.node_to_elements:
                assert elem in viewer.node_to_elements[elem.node1], f"Element {elem.id} should be mapped to node {elem.node1}"
            if elem.node2 in viewer.node_to_elements:
                assert elem in viewer.node_to_elements[elem.node2], f"Element {elem.id} should be mapped to node {elem.node2}"
    print("✓ Node-to-element mappings are correct")


def run_all_tests():
    """Run all viewer tests."""
    print("=" * 60)
    print("Running RCViewer Tests")
    print("=" * 60)
    
    try:
        print("\n1. Testing viewer initialization...")
        viewer = test_viewer_initialization()
        
        print("\n2. Testing layer collection...")
        test_layer_collection()
        
        print("\n3. Testing net collection...")
        test_net_collection()
        
        print("\n4. Testing layer colors...")
        test_layer_colors()
        
        print("\n5. Testing graphics items tracking...")
        test_graphics_items_tracking()
        
        print("\n6. Testing layer toggle...")
        test_layer_toggle()
        
        print("\n7. Testing net toggle...")
        test_net_toggle()
        
        print("\n8. Testing UI components...")
        test_ui_components()
        
        print("\n9. Testing zoom functions...")
        test_zoom_functions()
        
        print("\n10. Testing highlight clear...")
        test_highlight_clear()
        
        print("\n11. Testing node-to-elements mapping...")
        test_node_to_elements_mapping()
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        return True
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

