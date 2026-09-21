"""
MakeHuman 2 Studio Notes Extension V 1.0 by Elvaerwyn_MH2 2026
A drop-in notepad panel featuring standard tools and named profiles.
Fully Hybrid tool for standalone use and native MH2 docking with plugin panel layouts testing.

black-punkduck:
 * added connection to pluginRepo in MakeHuman2
 * changed file not to use globals anymore (no possible conflicts)
 * use the same order: definition of gui, load extension, unload extension + __main__ for standalone
 * outputs into cli now use logline. added dummies for standalone to use a logLine dummy
 * changed QFileDialog, QColorDialog not to crash in case of OpenGL on Linux
"""

import os
import sys
import json
import base64
from pathlib import Path
from PySide6.QtCore import Qt, QSignalBlocker, QPoint
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
        QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QComboBox,
        QSizePolicy, QPushButton, QSpinBox, QColorDialog, QFileDialog, QMessageBox,
        QInputDialog, QMenu, QGridLayout, QWidgetAction, QApplication, QMainWindow
)

# =======================================================================
# WORKSPACE WIDGET ASSEMBLY & DATA TRACKING LAYER
# =======================================================================

class NotePadPlugin():
    def __init__(self, app_reference, glob_reference, pluginname, outfunc, notes_dir=None):
        self.glob = glob_reference
        self.pluginname = pluginname
        self.outfunc = outfunc

        # get the global reference to mainwindow and global repo
        #
        self.mainwindow = self.glob.MainWindow
        if notes_dir is None:
            self.notes_dir = (Path(self.glob.env.stdUserPath()) / "studio_notebooks").resolve().as_posix()
        else:
            self.notes_dir = notes_dir
        self.outfunc(8, "studio_notebooks path: " + self.notes_dir)

        self.repo = self.glob.pluginRepo
        self.dock = None
                                                        
    class MH2RichNotesArea(QTextEdit):
        """Customized Text Editor layout default."""
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setPlaceholderText("Type your formatted workflow steps, code chunks, or notes here...")
            default_font = QFont("Aileron", 11)
            self.setFont(default_font)

    class Panel(QWidget):
        """Core Controller class managing formatting, data persistence, and text processing operations."""
        def __init__(self, parent=None):
            super().__init__()
            self.initiated = False
            self.parent = parent
            self.glob = parent.glob
            self.notes_dir = parent.notes_dir
            self.current_filename = None
            self.init_ui()
            self.initiated = True

        def showEvent(self, event):
            super().showEvent(event)
            if self.initiated:
                self.scan_notes_directory()

        def init_ui(self):
            master_layout = QVBoxLayout(self)
            master_layout.setContentsMargins(4, 4, 4, 4)
            master_layout.setSpacing(6)

            # --- PROFILE SELECTION AND CREATION BAR ---
            profile_layout = QHBoxLayout()
            profile_layout.setSpacing(4)
        
            self.note_selector = QComboBox()
            self.note_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.note_selector.currentIndexChanged.connect(self.handle_profile_selection_change)
            profile_layout.addWidget(self.note_selector)

            btn_new_note = QPushButton("➕ New")
            btn_new_note.clicked.connect(self.trigger_create_new_profile)
            profile_layout.addWidget(btn_new_note)

            master_layout.addLayout(profile_layout)

            # --- TEXT FORMATTING TOOLBAR ROW ---
            toolbar_layout = QHBoxLayout()
            toolbar_layout.setSpacing(2)

            self.font_selector = QComboBox()
            self.font_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.font_selector.addItem("Aileron (CC0 Sans Helvetica-Twin)", "Aileron")
            self.font_selector.addItem("Vegur (CC0 Sans Soft-Reading)", "Vegur")
            self.font_selector.addItem("Goudy Bookletter (CC0 Serif Classic)", "Goudy Bookletter")
            self.font_selector.addItem("Pixel Operator (CC0 Monospace Coding)", "Pixel Operator")
            self.font_selector.addItem("Tenderness (CC0 Display Headings)", "Tenderness")
            self.font_selector.currentTextChanged.connect(self.change_font_family)
            toolbar_layout.addWidget(self.font_selector)

            # Font Size Selector Clicker for readability scaling
            self.size_selector = QSpinBox()
            self.size_selector.setRange(6, 72)         # Lock safe size boundaries
            self.size_selector.setValue(11)            # Match default baseline style choice
            self.size_selector.setSuffix(" pt")        # Visual decoration identifier text
            self.size_selector.setFixedWidth(65)        # Keeps it compact on tight docks
            self.size_selector.valueChanged.connect(self.change_text_font_size)
            toolbar_layout.addWidget(self.size_selector)

            self.btn_bold = QPushButton("B")
            self.btn_bold.setToolTip("Bold")
            self.btn_bold.setCheckable(True)
            self.btn_bold.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            self.btn_bold.clicked.connect(self.toggle_text_bold)
            toolbar_layout.addWidget(self.btn_bold)

            self.btn_italic = QPushButton("I")
            self.btn_italic.setCheckable(True)
            self.btn_italic.setToolTip("Italic")
            self.btn_italic.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            self.btn_italic.clicked.connect(self.toggle_text_italic)
            toolbar_layout.addWidget(self.btn_italic)

            self.btn_color = QPushButton("🎨")
            self.btn_color.setToolTip("Color")
            self.btn_color.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            self.btn_color.clicked.connect(self.trigger_color_picker)
            toolbar_layout.addWidget(self.btn_color)

            self.btn_img = QPushButton("🖼️")
            self.btn_img.setToolTip("Image")
            self.btn_img.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            self.btn_img.clicked.connect(self.trigger_image_insertion)
            toolbar_layout.addWidget(self.btn_img)

            self.btn_emoji = QPushButton("😀")
            self.btn_emoji.setToolTip("Image")
            self.btn_emoji.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            self.btn_emoji.clicked.connect(self.trigger_emoji_picker)
            toolbar_layout.addWidget(self.btn_emoji)

            master_layout.addLayout(toolbar_layout)

            # --- TEXT EDITOR CONTAINER ---
            self.editor = self.parent.MH2RichNotesArea()
            self.editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.editor.cursorPositionChanged.connect(self.sync_format_buttons_to_cursor)
            master_layout.addWidget(self.editor)

            # --- REPOSITORY FILE CONTROLS ---
            file_layout = QHBoxLayout()
            file_layout.setSpacing(4)

            self.btn_save = QPushButton("💾 Save Note")
            self.btn_save.clicked.connect(self.save_active_note_html)
            file_layout.addWidget(self.btn_save)

            # 📥 ADDED: Load Plain Text Action
            self.btn_load_txt = QPushButton("📥 Load TXT")
            self.btn_load_txt.clicked.connect(self.import_from_plain_text)
            file_layout.addWidget(self.btn_load_txt)

            self.btn_export_txt = QPushButton("📄 Export TXT")
            self.btn_export_txt.clicked.connect(self.export_to_plain_text)
            file_layout.addWidget(self.btn_export_txt)

            self.btn_delete = QPushButton("❌ Delete")
            self.btn_delete.clicked.connect(self.delete_active_note_file)
            file_layout.addWidget(self.btn_delete)

            master_layout.addLayout(file_layout)

        def change_text_font_size(self, numeric_pt_val):
            """Sets the selected character block or incoming stream point text tracking metric weight."""
            self.editor.setFontPointSize(numeric_pt_val)

        def toggle_text_bold(self):
            weight = QFont.Bold if self.btn_bold.isChecked() else QFont.Normal
            self.editor.setFontWeight(weight)

        def toggle_text_italic(self):
            self.editor.setFontItalic(self.btn_italic.isChecked())

        def change_font_family(self, font_display_text):
            target_font_name = self.font_selector.currentData()
            if target_font_name:
                self.editor.setFontFamily(target_font_name)

        def trigger_color_picker(self):
            current_color = self.editor.textColor()
            self.glob.openGLWinUpdate = False
            chosen_color = QColorDialog.getColor(current_color, self, "Select Text Color")
            self.glob.openGLWinUpdate = True
            if chosen_color.isValid():
                self.editor.setTextColor(chosen_color)

        def trigger_image_insertion(self):
            """Converts an image file to a base64 string and embeds it directly into the rich text editor layout."""
            self.glob.openGLWinUpdate = False
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Embed Reference Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
            )
            self.glob.openGLWinUpdate = True
            if not file_path:
                return
        
            try:
                with open(file_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
                ext = os.path.splitext(file_path)[1].lower().replace(".", "")
                if ext == "jpg": 
                    ext = "jpeg"
            
                html_image_tag = f'<br><img src="data:image/{ext};base64,{encoded_string}" width="350"/><br>'
                self.editor.insertHtml(html_image_tag)
                self.parent.outfunc(2, "[Studio Notes UI] Reference image embedded cleanly via base64 strings.")
            except Exception as img_err:
                QMessageBox.critical(self, "Image Error", f"Failed to encode reference image: {img_err}")

        def sync_format_buttons_to_cursor(self):
            """Highlights the toolbar selectors to match the font styles at the user's cursor location."""
            with QSignalBlocker(self.btn_bold):
                self.btn_bold.setChecked(self.editor.fontWeight() == QFont.Bold)
            with QSignalBlocker(self.btn_italic):
                self.btn_italic.setChecked(self.editor.fontItalic())
            with QSignalBlocker(self.size_selector):
                current_size = self.editor.fontPointSize()
                if current_size > 0:
                    self.size_selector.setValue(int(current_size))
                else:
                    # If font size returns 0 or mixed layout bounds, match the font baseline point metric
                    self.size_selector.setValue(int(self.editor.font().pointSize()))
            with QSignalBlocker(self.font_selector):
                current_font_family = self.editor.fontFamily()
                if current_font_family:
                    for idx in range(self.font_selector.count()):
                        if self.font_selector.itemData(idx) == current_font_family:
                            self.font_selector.setCurrentIndex(idx)
                            break

        def scan_notes_directory(self):
            """Loads all individual .json profiles onto the user drop selection tool."""
            base_path = Path(self.notes_dir).resolve()
            if not base_path.exists():
                try: 
                    base_path.mkdir(parents=True, exist_ok=True)
                except Exception: 
                    pass

            with QSignalBlocker(self.note_selector):
                self.note_selector.clear()
                json_files = [f.name for f in base_path.glob("*.json")]
            
                if not json_files:
                    self.note_selector.addItem("Default Workspace Note", "default_workspace_note.json")
                    self.current_filename = "default_workspace_note.json"
                else:
                    for file in json_files:
                        # 🧠 FIXED: Core tuple string conversion extraction array index
                        display_name = os.path.splitext(file)[0].replace("_", " ").title()
                        self.note_selector.addItem(display_name, file)
                
                    if self.current_filename:
                        match_idx = self.note_selector.findData(self.current_filename)
                        if match_idx != -1:
                            self.note_selector.setCurrentIndex(match_idx)
                        else:
                            self.note_selector.setCurrentIndex(0)
                    else:
                        self.note_selector.setCurrentIndex(0)
                    
                self.current_filename = self.note_selector.currentData()
            
            self.load_active_note_html()

        def handle_profile_selection_change(self, index):
            if index == -1:
                return
            self.current_filename = self.note_selector.currentData()
            self.load_active_note_html()

        def trigger_create_new_profile(self):
            name, confirmed = QInputDialog.getText(
                self, "Create New Note Page", "Enter unique name identifier text for the new profile page:"
            )
            if not confirmed or not name.strip():
                return
            
            clean_filename = "".join([c for c in name.strip().lower() if c.isalnum() or c in (" ", "_", "-")]).replace(" ", "_") + ".json"
            full_target_path = (Path(self.notes_dir).resolve() / clean_filename).as_posix()
        
            if os.path.isfile(full_target_path):
                QMessageBox.warning(self, "Profile Exists", "A notebook file matching that descriptive name already exists.")
                return

            self.current_filename = clean_filename
            self.editor.clear()
            self.save_active_note_html()
            self.scan_notes_directory()

        def trigger_emoji_picker(self):
            """Spawns a clean pop-up grid containing standard workflow and expression emoticons."""
            emoji_menu = QMenu(self)
        
            # 🧠 EXPANDED: 6x6 production asset matrix tailored for 3D studio tracking
            emoji_list = [
                ["😀", "😎", "😮", "🔥", "✨", "💯"],  # Status / Feedback / Milestones
                ["📝", "📌", "🏷️", "📂", "💾", "🔗"],  # Project Data / Documentation Controls
                ["⚙️", "🛠️", "🔧", "💻", "🧩", "⚡"],  # Scripting / Engine / Topology Work
                ["🎨", "🖌️", "📐", "📸", "🔮", "💡"],  # Texturing / Materials / Reference Concept
                ["👤", "🦾", "🦴", "👟", "👗", "👑"],  # Topology Nodes / Rigging / Character Clothing
                ["✅", "⬜", "❌", "⚠️", "⏳", "🧠"]   # Pipeline Checkboxes / Errors / Task Delays
            ]
        
            grid_widget = QWidget()
            grid_layout = QGridLayout(grid_widget)
            grid_layout.setContentsMargins(4, 4, 4, 4)
            grid_layout.setSpacing(2)
        
            for row_idx, row in enumerate(emoji_list):
                for col_idx, icon in enumerate(row):
                    btn = QPushButton(icon)
                    btn.setFixedSize(28, 28)
                    btn.setStyleSheet("padding: 0px; font-size: 14px;")
                    btn.clicked.connect(lambda checked=False, em=icon: [
                        self.editor.insertPlainText(em),
                        emoji_menu.close()
                    ])
                    grid_layout.addWidget(btn, row_idx, col_idx)
                
            menu_action = QWidgetAction(emoji_menu)
            menu_action.setDefaultWidget(grid_widget)
            emoji_menu.addAction(menu_action)
            emoji_menu.exec(self.btn_emoji.mapToGlobal(QPoint(0, self.btn_emoji.height())))

        def load_active_note_html(self):
            if not self.current_filename:
                return
            target_path = (Path(self.notes_dir).resolve() / self.current_filename).as_posix()
            if os.path.isfile(target_path):
                try:
                    with open(target_path, 'r', encoding='utf-8') as f:
                        wrapped_data = json.load(f)
                        rich_html_content = wrapped_data.get("rich_text_data", "")
                    
                    if self.editor.toHtml() != rich_html_content:
                        self.editor.setHtml(rich_html_content)
                    self.parent.outfunc(2, f"[Studio Notes IO] Unpacked profile JSON from disk: {self.current_filename}")
                except Exception as read_err:
                    self.parent.outfunc(1, f"[IO ERROR] Failed tracking JSON data reads: {read_err}")
            else:
                self.editor.clear()

        def save_active_note_html(self):
            if not self.current_filename:
                return False
            target_path = (Path(self.notes_dir).resolve() / self.current_filename).as_posix()
            payload = {
                "profile_name": self.note_selector.currentText(),
                "last_modified": "2026-08-09",
                "rich_text_data": self.editor.toHtml()
            }
            try:
                with open(target_path, 'w', encoding='utf-8') as f:
                    json.dump(payload, f, indent=4)
                self.parent.outfunc(1, f"[Studio Notes IO] Successfully synchronized JSON wrapper to disk: {target_path}")
                return True
            except Exception as write_err:
                self.parent.outfunc(1, f"IO ERROR] JSON serialization data streaming crashed: {write_err}")
                return False

        def export_to_plain_text(self):
            """Strips all HTML formatting and dumps pure plain text values out to file tracks."""
            raw_plain_text = self.editor.toPlainText()
            if not raw_plain_text.strip():
                QMessageBox.information(self, "Empty Note", "There is no text content in this note to export.")
                return

            # 🧠 FIXED: Default to a fallback file name securely
            base_name = "exported_notes.txt"
            if self.current_filename:
                # Safely extract the root prefix before appending the target extension
                base_name = os.path.splitext(os.path.basename(self.current_filename))[0] + ".txt"

            # 🧠 FIXED: Anchor the suggested path directly to your active notes folder directory path
            suggested_absolute_target = (Path(self.notes_dir).resolve() / base_name).as_posix()

            # Prompt dialog opens directly in your workspace instead of defaulting to System32
            self.glob.openGLWinUpdate = False
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Export Note as Plain Text", suggested_absolute_target, "Text Files (*.txt)"
            )
            self.glob.openGLWinUpdate = True
            if not save_path:
                return
            
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(raw_plain_text)
                QMessageBox.information(self, "Export Complete", f"Successfully exported text to:\n{save_path}")
            except Exception as export_err:
                QMessageBox.critical(self, "Export Error", f"Failed to write text file to disk:\n{export_err}")

        def import_from_plain_text(self):
            """Prompts user for a standard .txt file and appends or replaces text in the active document layout."""
            # Anchor file browser initialization lookups directly inside active project storage zones
            suggested_dir = Path(self.notes_dir).resolve().as_posix()
        
            # Open file dialog matrix targeted exclusively to standard text extensions
            self.glob.openGLWinUpdate = False
            file_path, _ = QFileDialog.getOpenFileName(
                self.parent.mainwindow, "Import Plain Text File", suggested_dir, "Text Files (*.txt);;All Files (*)"
            )
            self.glob.openGLWinUpdate = True

            if not file_path:
                return  # User clicked cancel

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    incoming_text_string = f.read()

                if not incoming_text_string.strip():
                    QMessageBox.warning(self, "Empty File", "The selected text file contains no text data stream strings.")
                    return

                # Confirm choice options to protect against data overwrites
                confirm = QMessageBox.question(
                    self, "Import Destination Choice",
                    "Would you like to APPEND this text file contents to your current notes layout row?\n\n(Click 'No' to overwrite the page completely.)",
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                )

                if confirm == QMessageBox.Cancel:
                    return
                elif confirm == QMessageBox.Yes:
                    # Insert cleanly right at the active cursor position layout index node
                    self.editor.insertPlainText("\n" + incoming_text_string)
                    self.parent.outfunc(2, f"[Studio Notes IO] Successfully appended content layers from: {file_path}")
                elif confirm == QMessageBox.No:
                    # Wipe old data states and completely replace with incoming plaintext block
                    self.editor.setPlainText(incoming_text_string)
                    self.parent.outfunc(2, f"[Studio Notes IO] Successfully overwritten profile workspace with data stream: {file_path}")

            except Exception as import_err:
                QMessageBox.critical(self, "Import Error", f"Failed parsing document source structure streams:\n{import_err}")

        def delete_active_note_file(self):
            if not self.current_filename:
                return
            confirm = QMessageBox.question(
                self, "Confirm File Deletion",
                f"Are you sure you want to permanently erase the notepad profile file named '{self.note_selector.currentText()}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.No:
                return
            
            target_path = (Path(self.notes_dir).resolve() / self.current_filename).as_posix()
            try:
                if os.path.isfile(target_path):
                    os.remove(target_path)
                self.current_filename = None
                self.editor.clear()
                self.scan_notes_directory()
            except Exception as delete_err:
                self.parent.outfunc(1, f"IO ERROR] Operating system level unlink operation aborted: {delete_err}")

    def shutdown(self):
        self.outfunc(1, "[Studio Notes IO] shutdown ")
        if self.panel:
            self.panel.close()
            self.panel.deleteLater()
        if self.dock:
            self.mainwindow.removeDockWidget(self.dock)
            self.dock.close()
            self.dock.deleteLater()
        self.dock = None
        self.panel = None

    def initialize(self, docked=False):
        """
        the initialize function for this dock panel
        docked: if false, then standalone version is used
        """
        if self.pluginname in self.repo:
            # if loaded second time
            # Clean up old references just in case
            self.shutdown()

        # create the dock widget including UI
        #
        if docked:
            self.dock = QDockWidget("Make Notes", self.mainwindow)
            self.dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
            self.panel = self.Panel(self)
            self.dock.setWidget(self.panel)
            if hasattr(self.mainwindow, "addDockWidget"):
                self.mainwindow.addDockWidget(Qt.RightDockWidgetArea, self.dock)
            else:
                self.dock.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
            self.dock.show()
        else:
            self.panel = self.Panel(self)


        # now add plugin to repository
        #
        self.repo[self.pluginname] = self
        return True

def load_extension(app_reference, glob_reference=None):
    """
    MH2 COMPLIANCE HOOK: Spawns the note-taking panel container safely 
    within the native dashboard interface framework.
    """
    glob_reference.env.logLine(1, "[Studio Notes Core] Initializing hybrid workflow scratchpad logs...")

    pluginname = os.path.abspath(__file__)
    plugin = NotePadPlugin(app_reference, glob_reference, pluginname, glob_reference.env.logLine, None)
    return plugin.initialize(True)


def unload_extension(glob):
    pluginname = os.path.abspath(__file__)
    if pluginname in glob.pluginRepo:
        glob.pluginRepo[pluginname].shutdown()
        glob.pluginRepo.pop(pluginname)     # and delete from repo


# =======================================================================
# STANDALONE HYBRID ENTRY POINT LAYER
# =======================================================================
if __name__ == "__main__":
    """
    DOUBLE-CLICK RUNNER: Fires ONLY when double-clicked directly outside of MH2.
    Forces absolute anchoring into the platform user Documents directory structure.
    """

    class glob():
        """
        dummy class to avoid hasattr in plugin itself etc.
        """
        def __init__(self):
            self.openGLWinUpdate = True
            self.pluginRepo = {}
            self.MainWindow = None

    # cli logLine replacement
    #
    def printoutput(par1, par2):
        # fake logLine
        print ("Level " + str(par1) + ": " + par2)

    glob = glob()
    app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle("📝 Standalone Studio Scratchpad Notes 📝")
    window.resize(450, 650)
    
    desktop_notes_path = (Path.home() / "Documents" / "StudioNotebooks").resolve().as_posix()
    
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    main_layout = QVBoxLayout(central_widget)
    glob.MainWindow = window
    manager = NotePadPlugin(app, glob, None, printoutput, desktop_notes_path)
    manager.initialize()
    main_layout.addWidget(manager.panel)
    
    manager.panel.scan_notes_directory()
    manager.panel.load_active_note_html()
    
    window.show()
    sys.exit(app.exec())
