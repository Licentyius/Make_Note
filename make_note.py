"""
MakeHuman 2 Studio Notes Extension V 1.0 by Elvaerwyn_MH2 2026
A drop-in notepad panel featuring standard tools and named profiles.
Fully Hybrid tool for standalone use and native MH2 docking with plugin panel layouts testing.
"""

import os
import sys
import json
import base64
from pathlib import Path
from PySide6 import QtWidgets, QtCore, QtGui

TOOL_NAME = "Make Notes"
_active_notes_dock = None

def load_extension(app_reference, glob_reference=None):
    """
    MH2 COMPLIANCE HOOK: Spawns the note-taking panel container safely 
    within the native dashboard interface framework.
    """
    global _active_notes_dock
    print("[Studio Notes Core] Initializing hybrid workflow scratchpad logs...")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    try:
        _active_notes_dock = MH2NotesDockWidget(parent=app_reference)
        
        # HYBRID ANCHOR: Respects internal MH2 user directories natively
        env_object = getattr(app_reference, 'env', None)
        if env_object and hasattr(env_object, 'stdUserPath'):
            notes_dir_path = (Path(env_object.stdUserPath()) / "studio_notebooks").resolve().as_posix()
        else:
            script_directory = os.path.dirname(os.path.abspath(__file__))
            notes_dir_path = (Path(script_directory) / "studio_notebooks").resolve().as_posix()

        tool_layout = QtWidgets.QVBoxLayout(_active_notes_dock)
        tool_layout.setContentsMargins(4, 4, 4, 4)
        tool_layout.setSpacing(6)
        
        _active_notes_dock.manager_widget = MH2NotesManager(notes_dir_path, parent=_active_notes_dock)
        tool_layout.addWidget(_active_notes_dock.manager_widget)

        if hasattr(app_reference, 'add_sidebar_widget'):
            app_reference.add_sidebar_widget(TOOL_NAME, _active_notes_dock)
        elif hasattr(app_reference, 'ui') and hasattr(app_reference.ui, 'right_dock_layout'):
            app_reference.ui.right_dock_layout.addWidget(_active_notes_dock)
        else:
            dock_holder = QtWidgets.QDockWidget(TOOL_NAME, app_reference)
            dock_holder.setWidget(_active_notes_dock)
            app_reference.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock_holder)

        print(f"[Studio Notes Core] Workspace pad panel docked successfully at: {notes_dir_path}")
        return _active_notes_dock

    except Exception as launch_error:
        print(f"[Studio Notes Error] Failed to boot workspace note engine: {launch_error}")
        return None

def unload_extension():
    """Wipes active panel variables on layout dashboard unchecks."""
    global _active_notes_dock
    print("[Studio Notes Core] Deactivating module context nodes safely...")
    if _active_notes_dock is not None:
        try:
            _active_notes_dock.setParent(None)
            _active_notes_dock.deleteLater()
        except Exception:
            pass
    _active_notes_dock = None
# =======================================================================
# WORKSPACE WIDGET ASSEMBLY & DATA TRACKING LAYER
# =======================================================================

class MH2NotesDockWidget(QtWidgets.QWidget):
    """Custom container widget tailored to lock directly inside the MH2 framework sidebar layouts."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager_widget = None

    def showEvent(self, event):
        super().showEvent(event)
        if self.manager_widget:
            self.manager_widget.scan_notes_directory()

class MH2RichNotesArea(QtWidgets.QTextEdit):
    """Customized Text Editor layout default."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Type your formatted workflow steps, code chunks, or notes here...")
        default_font = QtGui.QFont("Aileron", 11)
        self.setFont(default_font)

class MH2NotesManager(QtWidgets.QWidget):
    """Core Controller class managing formatting, data persistence, and text processing operations."""
    def __init__(self, notes_dir, parent=None):
        super().__init__(parent)
        self.notes_dir = notes_dir
        self.current_filename = None
        self.init_ui()

    def init_ui(self):
        master_layout = QtWidgets.QVBoxLayout(self)
        master_layout.setContentsMargins(4, 4, 4, 4)
        master_layout.setSpacing(6)

        # --- PROFILE SELECTION AND CREATION BAR ---
        profile_layout = QtWidgets.QHBoxLayout()
        profile_layout.setSpacing(4)
        
        self.note_selector = QtWidgets.QComboBox()
        self.note_selector.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.note_selector.currentIndexChanged.connect(self.handle_profile_selection_change)
        profile_layout.addWidget(self.note_selector)

        btn_new_note = QtWidgets.QPushButton("➕ New")
        btn_new_note.clicked.connect(self.trigger_create_new_profile)
        profile_layout.addWidget(btn_new_note)

        master_layout.addLayout(profile_layout)

        # --- TEXT FORMATTING TOOLBAR ROW ---
        toolbar_layout = QtWidgets.QHBoxLayout()
        toolbar_layout.setSpacing(2)

        self.font_selector = QtWidgets.QComboBox()
        self.font_selector.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.font_selector.addItem("Aileron (CC0 Sans Helvetica-Twin)", "Aileron")
        self.font_selector.addItem("Vegur (CC0 Sans Soft-Reading)", "Vegur")
        self.font_selector.addItem("Goudy Bookletter (CC0 Serif Classic)", "Goudy Bookletter")
        self.font_selector.addItem("Pixel Operator (CC0 Monospace Coding)", "Pixel Operator")
        self.font_selector.addItem("Tenderness (CC0 Display Headings)", "Tenderness")
        self.font_selector.currentTextChanged.connect(self.change_font_family)
        toolbar_layout.addWidget(self.font_selector)

        # Font Size Selector Clicker for readability scaling
        self.size_selector = QtWidgets.QSpinBox()
        self.size_selector.setRange(6, 72)         # Lock safe size boundaries
        self.size_selector.setValue(11)            # Match default baseline style choice
        self.size_selector.setSuffix(" pt")        # Visual decoration identifier text
        self.size_selector.setFixedWidth(65)        # Keeps it compact on tight docks
        self.size_selector.valueChanged.connect(self.change_text_font_size)
        toolbar_layout.addWidget(self.size_selector)

        self.btn_bold = QtWidgets.QPushButton("B")
        self.btn_bold.setCheckable(True)
        self.btn_bold.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.btn_bold.clicked.connect(self.toggle_text_bold)
        toolbar_layout.addWidget(self.btn_bold)

        self.btn_italic = QtWidgets.QPushButton("I")
        self.btn_italic.setCheckable(True)
        self.btn_italic.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.btn_italic.clicked.connect(self.toggle_text_italic)
        toolbar_layout.addWidget(self.btn_italic)

        self.btn_color = QtWidgets.QPushButton("🎨")
        self.btn_color.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.btn_color.clicked.connect(self.trigger_color_picker)
        toolbar_layout.addWidget(self.btn_color)

        self.btn_img = QtWidgets.QPushButton("🖼️")
        self.btn_img.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.btn_img.clicked.connect(self.trigger_image_insertion)
        toolbar_layout.addWidget(self.btn_img)

        self.btn_emoji = QtWidgets.QPushButton("😀")
        self.btn_emoji.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.btn_emoji.clicked.connect(self.trigger_emoji_picker)
        toolbar_layout.addWidget(self.btn_emoji)

        master_layout.addLayout(toolbar_layout)

        # --- TEXT EDITOR CONTAINER ---
        self.editor = MH2RichNotesArea()
        self.editor.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.editor.cursorPositionChanged.connect(self.sync_format_buttons_to_cursor)
        master_layout.addWidget(self.editor)

        # --- REPOSITORY FILE CONTROLS ---
        file_layout = QtWidgets.QHBoxLayout()
        file_layout.setSpacing(4)

        self.btn_save = QtWidgets.QPushButton("💾 Save Note")
        self.btn_save.clicked.connect(self.save_active_note_html)
        file_layout.addWidget(self.btn_save)

        # 📥 ADDED: Load Plain Text Action
        self.btn_load_txt = QtWidgets.QPushButton("📥 Load TXT")
        self.btn_load_txt.clicked.connect(self.import_from_plain_text)
        file_layout.addWidget(self.btn_load_txt)

        self.btn_export_txt = QtWidgets.QPushButton("📄 Export TXT")
        self.btn_export_txt.clicked.connect(self.export_to_plain_text)
        file_layout.addWidget(self.btn_export_txt)

        self.btn_delete = QtWidgets.QPushButton("❌ Delete")
        self.btn_delete.clicked.connect(self.delete_active_note_file)
        file_layout.addWidget(self.btn_delete)

        master_layout.addLayout(file_layout)

    def change_text_font_size(self, numeric_pt_val):
        """Sets the selected character block or incoming stream point text tracking metric weight."""
        self.editor.setFontPointSize(numeric_pt_val)

    def toggle_text_bold(self):
        weight = QtGui.QFont.Bold if self.btn_bold.isChecked() else QtGui.QFont.Normal
        self.editor.setFontWeight(weight)

    def toggle_text_italic(self):
        self.editor.setFontItalic(self.btn_italic.isChecked())

    def change_font_family(self, font_display_text):
        target_font_name = self.font_selector.currentData()
        if target_font_name:
            self.editor.setFontFamily(target_font_name)

    def trigger_color_picker(self):
        current_color = self.editor.textColor()
        chosen_color = QtWidgets.QColorDialog.getColor(current_color, self, "Select Text Color")
        if chosen_color.isValid():
            self.editor.setTextColor(chosen_color)

    def trigger_image_insertion(self):
        """Converts an image file to a base64 string and embeds it directly into the rich text editor layout."""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Embed Reference Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
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
            print("[Studio Notes UI] Reference image embedded cleanly via base64 strings.")
        except Exception as img_err:
            QtWidgets.QMessageBox.critical(self, "Image Error", f"Failed to encode reference image: {img_err}")

    def sync_format_buttons_to_cursor(self):
        """Highlights the toolbar selectors to match the font styles at the user's cursor location."""
        with QtCore.QSignalBlocker(self.btn_bold):
            self.btn_bold.setChecked(self.editor.fontWeight() == QtGui.QFont.Bold)
        with QtCore.QSignalBlocker(self.btn_italic):
            self.btn_italic.setChecked(self.editor.fontItalic())
        with QtCore.QSignalBlocker(self.size_selector):
            current_size = self.editor.fontPointSize()
            if current_size > 0:
                self.size_selector.setValue(int(current_size))
            else:
                # If font size returns 0 or mixed layout bounds, match the font baseline point metric
                self.size_selector.setValue(int(self.editor.font().pointSize()))
        with QtCore.QSignalBlocker(self.font_selector):
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

        with QtCore.QSignalBlocker(self.note_selector):
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
        name, confirmed = QtWidgets.QInputDialog.getText(
            self, "Create New Note Page", "Enter unique name identifier text for the new profile page:"
        )
        if not confirmed or not name.strip():
            return
            
        clean_filename = "".join([c for c in name.strip().lower() if c.isalnum() or c in (" ", "_", "-")]).replace(" ", "_") + ".json"
        full_target_path = (Path(self.notes_dir).resolve() / clean_filename).as_posix()
        
        if os.path.isfile(full_target_path):
            QtWidgets.QMessageBox.warning(self, "Profile Exists", "A notebook file matching that descriptive name already exists.")
            return

        self.current_filename = clean_filename
        self.editor.clear()
        self.save_active_note_html()
        self.scan_notes_directory()

    def trigger_emoji_picker(self):
        """Spawns a clean pop-up grid containing standard workflow and expression emoticons."""
        emoji_menu = QtWidgets.QMenu(self)
        
        # 🧠 EXPANDED: 6x6 production asset matrix tailored for 3D studio tracking
        emoji_list = [
            ["😀", "😎", "😮", "🔥", "✨", "💯"],  # Status / Feedback / Milestones
            ["📝", "📌", "🏷️", "📂", "💾", "🔗"],  # Project Data / Documentation Controls
            ["⚙️", "🛠️", "🔧", "💻", "🧩", "⚡"],  # Scripting / Engine / Topology Work
            ["🎨", "🖌️", "📐", "📸", "🔮", "💡"],  # Texturing / Materials / Reference Concept
            ["👤", "🦾", "🦴", "👟", "👗", "👑"],  # Topology Nodes / Rigging / Character Clothing
            ["✅", "⬜", "❌", "⚠️", "⏳", "🧠"]   # Pipeline Checkboxes / Errors / Task Delays
        ]
        
        grid_widget = QtWidgets.QWidget()
        grid_layout = QtWidgets.QGridLayout(grid_widget)
        grid_layout.setContentsMargins(4, 4, 4, 4)
        grid_layout.setSpacing(2)
        
        for row_idx, row in enumerate(emoji_list):
            for col_idx, icon in enumerate(row):
                btn = QtWidgets.QPushButton(icon)
                btn.setFixedSize(28, 28)
                btn.setStyleSheet("padding: 0px; font-size: 14px;")
                btn.clicked.connect(lambda checked=False, em=icon: [
                    self.editor.insertPlainText(em),
                    emoji_menu.close()
                ])
                grid_layout.addWidget(btn, row_idx, col_idx)
                
        menu_action = QtWidgets.QWidgetAction(emoji_menu)
        menu_action.setDefaultWidget(grid_widget)
        emoji_menu.addAction(menu_action)
        emoji_menu.exec(self.btn_emoji.mapToGlobal(QtCore.QPoint(0, self.btn_emoji.height())))

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
                print(f"[Studio Notes IO] Unpacked profile JSON from disk: {self.current_filename}")
            except Exception as read_err:
                print(f"❌ [IO ERROR] Failed tracking JSON data reads: {read_err}")
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
            print(f"[Studio Notes IO] Successfully synchronized JSON wrapper to disk: {target_path}")
            return True
        except Exception as write_err:
            print(f"❌ [IO ERROR] JSON serialization data streaming crashed: {write_err}")
            return False

    def export_to_plain_text(self):
        """Strips all HTML formatting and dumps pure plain text values out to file tracks."""
        raw_plain_text = self.editor.toPlainText()
        if not raw_plain_text.strip():
            QtWidgets.QMessageBox.information(self, "Empty Note", "There is no text content in this note to export.")
            return

        # 🧠 FIXED: Default to a fallback file name securely
        base_name = "exported_notes.txt"
        if self.current_filename:
            # Safely extract the root prefix before appending the target extension
            base_name = os.path.splitext(os.path.basename(self.current_filename))[0] + ".txt"

        # 🧠 FIXED: Anchor the suggested path directly to your active notes folder directory path
        suggested_absolute_target = (Path(self.notes_dir).resolve() / base_name).as_posix()

        # Prompt dialog opens directly in your workspace instead of defaulting to System32
        save_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Note as Plain Text", suggested_absolute_target, "Text Files (*.txt)"
        )
        if not save_path:
            return
            
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(raw_plain_text)
            QtWidgets.QMessageBox.information(self, "Export Complete", f"Successfully exported text to:\n{save_path}")
        except Exception as export_err:
            QtWidgets.QMessageBox.critical(self, "Export Error", f"Failed to write text file to disk:\n{export_err}")

    def import_from_plain_text(self):
        """Prompts user for a standard .txt file and appends or replaces text in the active document layout."""
        # Anchor file browser initialization lookups directly inside active project storage zones
        suggested_dir = Path(self.notes_dir).resolve().as_posix()
        
        # Open file dialog matrix targeted exclusively to standard text extensions
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import Plain Text File", suggested_dir, "Text Files (*.txt);;All Files (*)"
        )
        if not file_path:
            return  # User clicked cancel

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                incoming_text_string = f.read()

            if not incoming_text_string.strip():
                QtWidgets.QMessageBox.warning(self, "Empty File", "The selected text file contains no text data stream strings.")
                return

            # Confirm choice options to protect against data overwrites
            confirm = QtWidgets.QMessageBox.question(
                self, "Import Destination Choice",
                "Would you like to APPEND this text file contents to your current notes layout row?\n\n(Click 'No' to overwrite the page completely.)",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel
            )

            if confirm == QtWidgets.QMessageBox.Cancel:
                return
            elif confirm == QtWidgets.QMessageBox.Yes:
                # Insert cleanly right at the active cursor position layout index node
                self.editor.insertPlainText("\n" + incoming_text_string)
                print(f"[Studio Notes IO] Successfully appended content layers from: {file_path}")
            elif confirm == QtWidgets.QMessageBox.No:
                # Wipe old data states and completely replace with incoming plaintext block
                self.editor.setPlainText(incoming_text_string)
                print(f"[Studio Notes IO] Successfully overwritten profile workspace with data stream: {file_path}")

        except Exception as import_err:
            QtWidgets.QMessageBox.critical(self, "Import Error", f"Failed parsing document source structure streams:\n{import_err}")

    def delete_active_note_file(self):
        if not self.current_filename:
            return
        confirm = QtWidgets.QMessageBox.question(
            self, "Confirm File Deletion",
            f"Are you sure you want to permanently erase the notepad profile file named '{self.note_selector.currentText()}'?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm == QtWidgets.QMessageBox.No:
            return
            
        target_path = (Path(self.notes_dir).resolve() / self.current_filename).as_posix()
        try:
            if os.path.isfile(target_path):
                os.remove(target_path)
            self.current_filename = None
            self.editor.clear()
            self.scan_notes_directory()
        except Exception as delete_err:
            print(f"❌ [IO ERROR] Operating system level unlink operation aborted: {delete_err}")

# =======================================================================
# STANDALONE HYBRID ENTRY POINT LAYER
# =======================================================================
if __name__ == "__main__":
    """
    DOUBLE-CLICK RUNNER: Fires ONLY when double-clicked directly outside of MH2.
    Forces absolute anchoring into the platform user Documents directory structure.
    """
    import sys
    app = QtWidgets.QApplication(sys.argv)
    
    window = QtWidgets.QMainWindow()
    window.setWindowTitle("📝 Standalone Studio Scratchpad Notes 📝")
    window.resize(450, 650)
    
    desktop_notes_path = (Path.home() / "Documents" / "StudioNotebooks").resolve().as_posix()
    
    central_widget = QtWidgets.QWidget()
    window.setCentralWidget(central_widget)
    main_layout = QtWidgets.QVBoxLayout(central_widget)
    
    manager = MH2NotesManager(desktop_notes_path)
    main_layout.addWidget(manager)
    
    manager.scan_notes_directory()
    manager.load_active_note_html()
    
    window.show()
    sys.exit(app.exec())
