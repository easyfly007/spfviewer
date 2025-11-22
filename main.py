import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import spf_viewer.viewer as viewer
from spf_viewer.viewer import RCViewer
from PySide6.QtWidgets import QApplication, QWidget

# add the parent directory to the path so that we can import the spf_viewer module

if __name__ == "__main__":
    print("sys.argv: ", sys.argv)
    if len(sys.argv) < 2:
        spffile = "examples/example00.spf"
        print("Usage: python main.py <spf_file>")
    else:
        spffile = sys.argv[1]
    app = QApplication(sys.argv)
    viewer = RCViewer(spffile)
    viewer.show()
    sys.exit(app.exec())
