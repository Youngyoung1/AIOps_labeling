"""Integration test: App-level flag change -> autosave -> MongoDB sync

This script runs headless (QT_QPA_PLATFORM=offscreen), creates a QApplication and a
LabelingWidget, sets up a dummy image + description (so JSON will be written), toggles
flags, triggers the internal flag-change handler, runs the event loop briefly to allow
queued saves to run, and then queries MongoDB to validate the document was inserted/updated.

Usage:
  python tools\integration_test_flag_sync.py --mongo mongodb://localhost:27017 --db labeling_db

"""
import os
import sys
import tempfile
import time
import json

# Ensure repo root on path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Use offscreen platform to avoid requiring a display
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt5 import QtWidgets, QtGui, QtCore

# Import LabelingWidget from package
from anylabeling.views.labeling.label_widget import LabelingWidget
from anylabeling.config import get_config, get_default_config
import anylabeling.config as any_config
import yaml

# Import AnnotationManager directly from file to avoid package-level GUI imports (if needed)
import importlib.util
AM_PATH = os.path.join(REPO_ROOT, 'anylabeling', 'services', 'annotation_manager.py')
spec = importlib.util.spec_from_file_location('annotation_manager', AM_PATH)
am_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(am_mod)
AnnotationManager = am_mod.AnnotationManager

import argparse


def create_dummy_image(path):
    # Create a tiny white image and save
    img = QtGui.QImage(32, 32, QtGui.QImage.Format_RGB888)
    img.fill(QtGui.QColor('white'))
    img.save(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mongo', default='mongodb://localhost:27017')
    parser.add_argument('--db', default='labeling_db')
    args = parser.parse_args()

    # Prepare temp image and json base
    tmp_dir = os.getcwd()
    fd_img, img_path = tempfile.mkstemp(prefix='inttest_img_', suffix='.jpg', dir=tmp_dir)
    os.close(fd_img)
    os.remove(img_path)  # we'll write via QImage.save
    create_dummy_image(img_path)

    base_no_ext, _ = os.path.splitext(img_path)
    json_path = base_no_ext + '.json'

    app = QtWidgets.QApplication([])

    # Use default config (avoid get_config None-path which reads external file)
    config = get_default_config()

    # Prevent anylabeling.config.get_config() from attempting to open None
    # by setting current_config_file to a YAML string of the default config.
    any_config.current_config_file = yaml.safe_dump(get_default_config())

    # Create a main window and make the LabelingWidget its central widget so
    # parent.parent().menuBar() calls inside the widget find a valid QMainWindow
    main_window = QtWidgets.QMainWindow()
    # The widget implementation expects parent.parent to be the QMainWindow
    # (it uses self.parent.parent.menuBar()). Create a lightweight wrapper
    # object with a 'parent' attribute pointing to the real main_window.
    class Wrapper:
        pass

    wrapper = Wrapper()
    wrapper.parent = main_window

    # Create an AnnotationManager and attach it to the main_window so the
    # widget can find and use it for MongoDB saves.
    am = AnnotationManager(connection_string=args.mongo, db_name=args.db)
    main_window.annotation_manager = am

    widget = LabelingWidget(parent=wrapper, config=config)
    main_window.setCentralWidget(widget)

    # Prepare widget minimal state so save_labels will write JSON
    widget.image_path = img_path
    widget.image = QtGui.QImage(img_path)
    widget.filename = img_path
    # Ensure other_data has description so JSON will be written by save_labels
    widget.other_data = widget.other_data or {}
    widget.other_data['description'] = 'integration test description'

    # Ensure there is at least one flag item
    if widget.flag_widget.count() == 0:
        # add a 'reviewed' flag item
        item = QtWidgets.QListWidgetItem('reviewed')
        item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
        item.setCheckState(QtCore.Qt.Unchecked)
        widget.flag_widget.addItem(item)

    # Toggle the flag (simulate user checking it)
    item0 = widget.flag_widget.item(0)
    item0.setCheckState(QtCore.Qt.Checked)

    # Call the flags handler which will queue save
    widget._on_flags_changed()

    # Run event loop briefly to let queued save run (save does DB IO)
    # Quit after 2500ms (give more time for file IO and DB insert)
    QtCore.QTimer.singleShot(1500, app.quit)
    app.exec_()

    # Now verify DB
    am = AnnotationManager(connection_string=args.mongo, db_name=args.db)
    # Check if the JSON file was written
    print('Checking JSON file:', json_path)
    if os.path.exists(json_path):
        print('  JSON exists')
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                jd = json.load(f)
            print('  JSON imagePath:', jd.get('imagePath'))
        except Exception as e:
            print('  Failed to read JSON:', e)
    else:
        print('  JSON does not exist')

    # Try to find the inserted document by absolute imagePath first, then basename
    image_abspath = img_path
    image_basename = os.path.basename(img_path)

    doc = am.find_by_image_path(image_abspath)
    if not doc:
        doc = am.find_by_image_path(image_basename)

    if not doc:
        print('FAIL: Document not found in DB for imagePath (tried abs and basename)=', image_abspath, image_basename)
        return 2

    print('OK: Found document in DB:')
    print('  json_file_name:', doc.get('json_file_name'))
    print('  imagePath:', doc.get('imagePath'))
    print('  flags:', doc.get('flags'))
    print('  shape_count:', doc.get('shape_count'))

    # Cleanup temp files
    try:
        if os.path.exists(img_path):
            os.remove(img_path)
        if os.path.exists(json_path):
            os.remove(json_path)
    except Exception:
        pass

    return 0


if __name__ == '__main__':
    sys.exit(main())
