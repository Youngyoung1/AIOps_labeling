import os

# Temporary fix for: bus error
# Source: https://stackoverflow.com/questions/73072612/
# why-does-np-linalg-solve-raise-bus-error-when-running-on-its-own-thread-mac-m1
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

# Suppress ICC profile warnings
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.gui.icc=false"

import argparse
import codecs
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import yaml
from PyQt5 import QtCore, QtWidgets

from anylabeling.app_info import __appname__, __version__, __url__
from anylabeling.config import get_config
from anylabeling import config as anylabeling_config
from anylabeling.views.mainwindow import MainWindow
from anylabeling.views.labeling.logger import logger
from anylabeling.views.labeling.utils import new_icon, gradient_text
from anylabeling.views.labeling.utils.update_checker import (
    check_for_updates_async,
)
from anylabeling.services.bidirectional_sync import BidirectionalSyncService

# NOTE: Do not remove this import, it is required for loading translations
from anylabeling.resources import resources


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reset-config", action="store_true", help="reset qt config"
    )
    parser.add_argument(
        "--logger-level",
        default="info",
        choices=["debug", "info", "warning", "fatal", "error"],
        help="logger level",
    )
    parser.add_argument(
        "--no-auto-update-check",
        action="store_true",
        help="disable automatic update check on startup",
    )
    parser.add_argument(
        "filename",
        nargs="?",
        help=(
            "image or label filename; "
            "If a directory path is passed in, the folder will be loaded automatically"
        ),
    )
    parser.add_argument(
        "--output",
        "-O",
        "-o",
        help=(
            "output file or directory (if it ends with .json it is "
            "recognized as file, else as directory)"
        ),
    )
    default_config_file = os.path.join(
        os.path.expanduser("~"), ".xanylabelingrc"
    )
    parser.add_argument(
        "--config",
        dest="config",
        help=(
            "config file or yaml-format string (default:"
            f" {default_config_file})"
        ),
        default=default_config_file,
    )
    # config for the gui
    parser.add_argument(
        "--nodata",
        dest="store_data",
        action="store_false",
        help="stop storing image data to JSON file",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--autosave",
        dest="auto_save",
        action="store_true",
        help="auto save",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--nosortlabels",
        dest="sort_labels",
        action="store_false",
        help="stop sorting labels",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--flags",
        help="comma separated list of flags OR file containing flags",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--labelflags",
        dest="label_flags",
        help=r"yaml string of label specific flags OR file containing json "
        r"string of label specific flags (ex. {person-\d+: [male, tall], "
        r"dog-\d+: [black, brown, white], .*: [occluded]})",  # NOQA
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--labels",
        help="comma separated list of labels OR file containing labels",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--validatelabel",
        dest="validate_label",
        choices=["exact"],
        help="label validation types",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--keep-prev",
        action="store_true",
        help="keep annotation of previous frame",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--epsilon",
        type=float,
        help="epsilon to find nearest vertex on canvas",
        default=argparse.SUPPRESS,
    )
    args = parser.parse_args()

    if hasattr(args, "flags"):
        if os.path.isfile(args.flags):
            with codecs.open(args.flags, "r", encoding="utf-8") as f:
                args.flags = [line.strip() for line in f if line.strip()]
        else:
            args.flags = [line for line in args.flags.split(",") if line]

    if hasattr(args, "labels"):
        if os.path.isfile(args.labels):
            with codecs.open(args.labels, "r", encoding="utf-8") as f:
                args.labels = [line.strip() for line in f if line.strip()]
        else:
            args.labels = [line for line in args.labels.split(",") if line]

    if hasattr(args, "label_flags"):
        if os.path.isfile(args.label_flags):
            with codecs.open(args.label_flags, "r", encoding="utf-8") as f:
                args.label_flags = yaml.safe_load(f)
        else:
            args.label_flags = yaml.safe_load(args.label_flags)

    config_from_args = args.__dict__
    reset_config = config_from_args.pop("reset_config")
    filename = config_from_args.pop("filename")
    output = config_from_args.pop("output")
    config_file_or_yaml = config_from_args.pop("config")
    logger_level = config_from_args.pop("logger_level")
    no_auto_update_check = config_from_args.pop("no_auto_update_check", False)

    logger.setLevel(getattr(logging, logger_level.upper()))
    logger.info(
        f"🚀 {gradient_text(f'X-AnyLabeling v{__version__} launched!')}"
    )
    logger.info(f"⭐ If you like it, give us a star: {__url__}")
    anylabeling_config.current_config_file = config_file_or_yaml
    config = get_config(config_file_or_yaml, config_from_args, show_msg=True)

    if not config["labels"] and config["validate_label"]:
        logger.error(
            "--labels must be specified with --validatelabel or "
            "validate_label: exact in the config file "
            "(ex. ~/.xanylabelingrc)."
        )
        sys.exit(1)

    output_file = None
    output_dir = None
    if output is not None:
        if output.endswith(".json"):
            output_file = output
        else:
            output_dir = output

    language = config.get("language", QtCore.QLocale.system().name())
    translator = QtCore.QTranslator()
    loaded_language = translator.load(
        ":/languages/translations/" + language + ".qm"
    )
    # Enable scaling for high dpi screens
    QtWidgets.QApplication.setAttribute(
        QtCore.Qt.AA_EnableHighDpiScaling, True
    )  # enable highdpi scaling
    QtWidgets.QApplication.setAttribute(
        QtCore.Qt.AA_UseHighDpiPixmaps, True
    )  # use highdpi icons
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)

    # Create QApplication
    app = QtWidgets.QApplication(sys.argv)
    
    # Set application icon
    app.setWindowIcon(new_icon("icon"))
    
    # Install translator after QApplication exists
    if loaded_language:
        app.installTranslator(translator)
        # Keep a reference to avoid translator being GC'd
        app._xanylabeling_translator = translator

    # Create main window
    window = MainWindow(
        app=app,
        config=config,
        filename=filename,
        output=output,
        output_file=output_file,
        output_dir=output_dir,
    )

    # Show window
    window.show()
    window.raise_()
    window.activateWindow()

    # Enable bidirectional sync (JSON ↔ MongoDB)
    try:
        sync_service = BidirectionalSyncService(window)

        # Determine watch directories from inputs
        watch_dirs = set()
        try:
            if filename:
                if os.path.isdir(filename):
                    watch_dirs.add(os.path.abspath(filename))
                elif os.path.isfile(filename):
                    watch_dirs.add(os.path.dirname(os.path.abspath(filename)))
        except Exception:
            pass

        if output_dir:
            try:
                watch_dirs.add(os.path.abspath(output_dir))
            except Exception:
                pass

        # Fallback to current working directory if nothing else
        if not watch_dirs:
            try:
                watch_dirs.add(os.path.abspath(os.getcwd()))
            except Exception:
                pass

        for d in watch_dirs:
            if d and os.path.exists(d):
                sync_service.add_watch_directory(d)

        # Start and inject into window if MongoDB available
        if sync_service.start():
            window.set_bidirectional_sync_service(sync_service)
        else:
            logger.debug("Bidirectional sync not started (missing MongoDB connection or no watch dirs)")
    except Exception as e:
        logger.debug(f"Bidirectional sync initialization skipped: {e}")

    # Check for updates if enabled
    if not no_auto_update_check:
        check_for_updates_async()

    sys.exit(app.exec_())


# this main block is required to generate executable by pyinstaller
if __name__ == "__main__":
    main()