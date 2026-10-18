import sys
import os
import json
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from card_model import (
    create_empty_v2_card,
    read_card_from_json,
    write_card_to_json,
    read_card_from_png,
    write_card_to_png,
    TavernCardValidator
)

class CharacterCardEditorWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="SillyTavern Character Card Creator (V2/V3)")
        self.set_default_size(950, 750)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.current_file_path = None
        self.current_avatar_path = None
        self.card_data = create_empty_v2_card()

        # Main Layout Box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(main_box)

        # Header / Toolbar
        toolbar = self.create_toolbar()
        main_box.pack_start(toolbar, False, False, 0)

        # Notebook for Tabs
        self.notebook = Gtk.Notebook()
        self.notebook.connect("switch-page", self.on_notebook_switch_page)
        main_box.pack_start(self.notebook, True, True, 0)

        # Build Tabs
        self.notebook.append_page(self.create_core_tab(), Gtk.Label(label="Core Identity"))
        self.notebook.append_page(self.create_prompts_tab(), Gtk.Label(label="Prompts & Settings"))
        self.notebook.append_page(self.create_greetings_tab(), Gtk.Label(label="Alternate Greetings"))
        self.notebook.append_page(self.create_metadata_tab(), Gtk.Label(label="Metadata & Tags"))
        self.notebook.append_page(self.create_summary_tab(), Gtk.Label(label="Summary & Tokens"))

        # Status Bar / Token Info
        self.status_bar = Gtk.Statusbar()
        main_box.pack_start(self.status_bar, False, False, 0)
        self.update_status("Ready. Create or load a character card.")

        # Load initial empty data into UI
        self.populate_ui_from_card()

    def create_toolbar(self):
        toolbar = Gtk.Toolbar()
        
        new_item = Gtk.ToolButton()
        new_item.set_icon_name("document-new")
        new_item.set_tooltip_text("New Card")
        new_item.connect("clicked", self.on_new_clicked)
        toolbar.insert(new_item, -1)

        open_item = Gtk.ToolButton()
        open_item.set_icon_name("document-open")
        open_item.set_tooltip_text("Open Card (JSON or PNG)")
        open_item.connect("clicked", self.on_open_clicked)
        toolbar.insert(open_item, -1)

        save_item = Gtk.ToolButton()
        save_item.set_icon_name("document-save")
        save_item.set_tooltip_text("Save Card (JSON)")
        save_item.connect("clicked", self.on_save_json_clicked)
        toolbar.insert(save_item, -1)

        save_png_item = Gtk.ToolButton()
        save_png_item.set_icon_name("document-save-as")
        save_png_item.set_tooltip_text("Export to PNG (Embed Card)")
        save_png_item.connect("clicked", self.on_save_png_clicked)
        toolbar.insert(save_png_item, -1)

        return toolbar

    def create_scrolled_text_view(self):
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.IN)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        textView = Gtk.TextView()
        textView.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        
        scrolled.add(textView)
        frame.add(scrolled)
        return frame, textView

    def create_core_tab(self):
        grid = Gtk.Grid()
        grid.set_border_width(12)
        grid.set_column_spacing(12)
        grid.set_row_spacing(10)

        # Name
        lbl_name = Gtk.Label(label="Character Name:", xalign=0)
        lbl_name.set_valign(Gtk.Align.START)
        grid.attach(lbl_name, 0, 0, 1, 1)
        
        self.entry_name = Gtk.Entry()
        self.entry_name.set_hexpand(True)
        self.entry_name.set_valign(Gtk.Align.START)
        grid.attach(self.entry_name, 1, 0, 1, 1)

        # Description
        lbl_desc = Gtk.Label(label="Description:", xalign=0)
        lbl_desc.set_valign(Gtk.Align.START)
        grid.attach(lbl_desc, 0, 1, 1, 1)
        
        frame_desc, self.textview_desc = self.create_scrolled_text_view()
        frame_desc.set_hexpand(True)
        frame_desc.set_vexpand(True)
        grid.attach(frame_desc, 1, 1, 1, 1)

        # Personality
        lbl_pers = Gtk.Label(label="Personality Summary:", xalign=0)
        lbl_pers.set_valign(Gtk.Align.START)
        grid.attach(lbl_pers, 0, 2, 1, 1)
        
        frame_pers, self.textview_pers = self.create_scrolled_text_view()
        frame_pers.set_hexpand(True)
        frame_pers.set_vexpand(True)
        grid.attach(frame_pers, 1, 2, 1, 1)

        # Scenario
        lbl_scen = Gtk.Label(label="Scenario:", xalign=0)
        lbl_scen.set_valign(Gtk.Align.START)
        grid.attach(lbl_scen, 0, 3, 1, 1)
        
        frame_scen, self.textview_scen = self.create_scrolled_text_view()
        frame_scen.set_hexpand(True)
        frame_scen.set_vexpand(True)
        grid.attach(frame_scen, 1, 3, 1, 1)

        # First Message
        lbl_first = Gtk.Label(label="First Message:", xalign=0)
        lbl_first.set_valign(Gtk.Align.START)
        grid.attach(lbl_first, 0, 4, 1, 1)
        
        frame_first, self.textview_first = self.create_scrolled_text_view()
        frame_first.set_hexpand(True)
        frame_first.set_vexpand(True)
        grid.attach(frame_first, 1, 4, 1, 1)

        # Example Dialogue
        lbl_ex = Gtk.Label(label="Example Dialogue:", xalign=0)
        lbl_ex.set_valign(Gtk.Align.START)
        grid.attach(lbl_ex, 0, 5, 1, 1)
        
        frame_ex, self.textview_ex = self.create_scrolled_text_view()
        frame_ex.set_hexpand(True)
        frame_ex.set_vexpand(True)
        grid.attach(frame_ex, 1, 5, 1, 1)

        return grid

    def create_prompts_tab(self):
        grid = Gtk.Grid()
        grid.set_border_width(12)
        grid.set_column_spacing(12)
        grid.set_row_spacing(10)

        # System Prompt
        lbl_sys = Gtk.Label(label="System Prompt (Overrides Global):", xalign=0)
        lbl_sys.set_valign(Gtk.Align.START)
        grid.attach(lbl_sys, 0, 0, 1, 1)
        
        frame_sys, self.textview_sys = self.create_scrolled_text_view()
        frame_sys.set_hexpand(True)
        frame_sys.set_vexpand(True)
        grid.attach(frame_sys, 1, 0, 1, 1)

        # Post History Instructions
        lbl_post = Gtk.Label(label="Post-History Instructions (Jailbreak):", xalign=0)
        lbl_post.set_valign(Gtk.Align.START)
        grid.attach(lbl_post, 0, 1, 1, 1)
        
        frame_post, self.textview_post = self.create_scrolled_text_view()
        frame_post.set_hexpand(True)
        frame_post.set_vexpand(True)
        grid.attach(frame_post, 1, 1, 1, 1)

        # Creator Notes
        lbl_notes = Gtk.Label(label="Creator Notes:", xalign=0)
        lbl_notes.set_valign(Gtk.Align.START)
        grid.attach(lbl_notes, 0, 2, 1, 1)
        
        frame_notes, self.textview_notes = self.create_scrolled_text_view()
        frame_notes.set_hexpand(True)
        frame_notes.set_vexpand(True)
        grid.attach(frame_notes, 1, 2, 1, 1)

        return grid

    def create_greetings_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(12)

        lbl = Gtk.Label(label="Alternate Greetings (Separate entries with '---' on a new line):", xalign=0)
        lbl.set_valign(Gtk.Align.START)
        box.pack_start(lbl, False, False, 0)
        
        frame_greetings, self.textview_greetings = self.create_scrolled_text_view()
        box.pack_start(frame_greetings, True, True, 0)

        return box

    def create_metadata_tab(self):
        grid = Gtk.Grid()
        grid.set_border_width(12)
        grid.set_column_spacing(12)
        grid.set_row_spacing(10)

        # Creator
        lbl_creator = Gtk.Label(label="Creator:", xalign=0)
        lbl_creator.set_valign(Gtk.Align.START)
        grid.attach(lbl_creator, 0, 0, 1, 1)
        
        self.entry_creator = Gtk.Entry()
        self.entry_creator.set_hexpand(True)
        self.entry_creator.set_valign(Gtk.Align.START)
        grid.attach(self.entry_creator, 1, 0, 1, 1)

        # Character Version
        lbl_version = Gtk.Label(label="Character Version:", xalign=0)
        lbl_version.set_valign(Gtk.Align.START)
        grid.attach(lbl_version, 0, 1, 1, 1)
        
        self.entry_version = Gtk.Entry()
        self.entry_version.set_hexpand(True)
        self.entry_version.set_valign(Gtk.Align.START)
        grid.attach(self.entry_version, 1, 1, 1, 1)

        # Tags
        lbl_tags = Gtk.Label(label="Tags (Comma separated):", xalign=0)
        lbl_tags.set_valign(Gtk.Align.START)
        grid.attach(lbl_tags, 0, 2, 1, 1)
        
        self.entry_tags = Gtk.Entry()
        self.entry_tags.set_hexpand(True)
        self.entry_tags.set_valign(Gtk.Align.START)
        grid.attach(self.entry_tags, 1, 2, 1, 1)

        return grid

    def create_summary_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_border_width(16)

        title = Gtk.Label()
        title.set_markup("<b>Character Card Token &amp; Character Count Summary</b>")
        title.set_xalign(0.0)
        title.set_yalign(0.0)
        box.pack_start(title, False, False, 0)

        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.IN)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        self.summary_textview = Gtk.TextView()
        self.summary_textview.set_editable(False)
        self.summary_textview.set_cursor_visible(False)
        self.summary_textview.set_monospace(True)
        
        scrolled.add(self.summary_textview)
        frame.add(scrolled)
        box.pack_start(frame, True, True, 0)

        btn_refresh = Gtk.Button(label="Refresh Summary")
        btn_refresh.connect("clicked", lambda w: self.refresh_summary_view())
        box.pack_start(btn_refresh, False, False, 0)

        return box

    def refresh_summary_view(self):
        self.update_card_from_ui()
        data = self.card_data.get("data", self.card_data)

        fields_to_check = [
            ("Character Name", data.get("name", "")),
            ("Description", data.get("description", "")),
            ("Personality Summary", data.get("personality", "")),
            ("Scenario", data.get("scenario", "")),
            ("First Message", data.get("first_mes", "")),
            ("Example Dialogue", data.get("mes_example", "")),
            ("System Prompt", data.get("system_prompt", "")),
            ("Post-History Instructions", data.get("post_history_instructions", "")),
            ("Creator Notes", data.get("creator_notes", "")),
            ("Creator", data.get("creator", "")),
            ("Character Version", str(data.get("character_version", ""))),
            ("Tags", ", ".join(data.get("tags", []))),
            ("Alternate Greetings", "\n".join(data.get("alternate_greetings", [])))
        ]

        lines = []
        lines.append(f"{'Field Name':<30} | {'Characters':<12} | {'Est. Tokens':<12}")
        lines.append("-" * 60)

        total_chars = 0
        total_tokens = 0

        for name, text in fields_to_check:
            chars = len(text)
            # Standard heuristic: ~4 characters per token for English text
            tokens = max(1, chars // 4) if chars > 0 else 0
            total_chars += chars
            total_tokens += tokens
            lines.append(f"{name:<30} | {chars:<12} | {tokens:<12}")

        lines.append("-" * 60)
        lines.append(f"{'GRAND TOTAL':<30} | {total_chars:<12} | {total_tokens:<12}")

        buffer = self.summary_textview.get_buffer()
        buffer.set_text("\n".join(lines))

    def on_notebook_switch_page(self, notebook, page, page_num):
        # If switching to the Summary tab (last tab index 4), auto-refresh stats
        if page_num == 4:
            self.refresh_summary_view()

    def get_text_from_textview(self, textview):
        buffer = textview.get_buffer()
        return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)

    def set_text_to_textview(self, textview, text):
        buffer = textview.get_buffer()
        buffer.set_text(text if text else "")

    def populate_ui_from_card(self):
        data = self.card_data.get("data", self.card_data)
        
        self.entry_name.set_text(data.get("name", ""))
        self.set_text_to_textview(self.textview_desc, data.get("description", ""))
        self.set_text_to_textview(self.textview_pers, data.get("personality", ""))
        self.set_text_to_textview(self.textview_scen, data.get("scenario", ""))
        self.set_text_to_textview(self.textview_first, data.get("first_mes", ""))
        self.set_text_to_textview(self.textview_ex, data.get("mes_example", ""))

        self.set_text_to_textview(self.textview_sys, data.get("system_prompt", ""))
        self.set_text_to_textview(self.textview_post, data.get("post_history_instructions", ""))
        self.set_text_to_textview(self.textview_notes, data.get("creator_notes", ""))

        greetings = data.get("alternate_greetings", [])
        self.set_text_to_textview(self.textview_greetings, "\n---\n".join(greetings))

        self.entry_creator.set_text(data.get("creator", ""))
        self.entry_version.set_text(str(data.get("character_version", "1.0")))
        
        tags = data.get("tags", [])
        self.entry_tags.set_text(", ".join(tags))

    def update_card_from_ui(self):
        data = self.card_data.setdefault("data", {})

        data["name"] = self.entry_name.get_text()
        data["description"] = self.get_text_from_textview(self.textview_desc)
        data["personality"] = self.get_text_from_textview(self.textview_pers)
        data["scenario"] = self.get_text_from_textview(self.textview_scen)
        data["first_mes"] = self.get_text_from_textview(self.textview_first)
        data["mes_example"] = self.get_text_from_textview(self.textview_ex)

        data["system_prompt"] = self.get_text_from_textview(self.textview_sys)
        data["post_history_instructions"] = self.get_text_from_textview(self.textview_post)
        data["creator_notes"] = self.get_text_from_textview(self.textview_notes)

        greetings_text = self.get_text_from_textview(self.textview_greetings)
        if greetings_text.strip():
            greetings = [g.strip() for g in greetings_text.split("---") if g.strip()]
            data["alternate_greetings"] = greetings
        else:
            data["alternate_greetings"] = []

        data["creator"] = self.entry_creator.get_text()
        data["character_version"] = self.entry_version.get_text()
        
        tags_text = self.entry_tags.get_text()
        if tags_text.strip():
            data["tags"] = [t.strip() for t in tags_text.split(",") if t.strip()]
        else:
            data["tags"] = []

    def update_status(self, message):
        self.status_bar.push(0, message)

    def on_new_clicked(self, widget):
        self.card_data = create_empty_v2_card()
        self.current_file_path = None
        self.current_avatar_path = None
        self.populate_ui_from_card()
        self.update_status("Created new character card.")

    def on_open_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Open Character Card",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            "_Cancel", Gtk.ResponseType.CANCEL,
            "_Open", Gtk.ResponseType.ACCEPT
        )

        filter_any = Gtk.FileFilter()
        filter_any.set_name("Character Cards (JSON, PNG)")
        filter_any.add_pattern("*.json")
        filter_any.add_pattern("*.png")
        dialog.add_filter(filter_any)

        if dialog.run() == Gtk.ResponseType.ACCEPT:
            filepath = dialog.get_filename()
            dialog.destroy()
            try:
                if filepath.endswith(".json"):
                    with open(filepath, "r", encoding="utf-8") as f:
                        self.card_data = read_card_from_json(f.read())
                elif filepath.endswith(".png"):
                    self.card_data = read_card_from_png(filepath)
                    self.current_avatar_path = filepath
                
                self.current_file_path = filepath
                self.populate_ui_from_card()
                self.update_status(f"Successfully loaded: {os.path.basename(filepath)}")
            except Exception as e:
                self.show_error_dialog(f"Failed to load card:\n{str(e)}")
        else:
            dialog.destroy()

    def on_save_json_clicked(self, widget):
        self.update_card_from_ui()
        dialog = Gtk.FileChooserDialog(
            title="Save Character Card JSON",
            parent=self,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            "_Cancel", Gtk.ResponseType.CANCEL,
            "_Save", Gtk.ResponseType.ACCEPT
        )
        default_name = self.card_data.get("data", self.card_data).get("name", "character")
        dialog.set_current_name(f"{default_name}.json")

        if dialog.run() == Gtk.ResponseType.ACCEPT:
            filepath = dialog.get_filename()
            dialog.destroy()
            try:
                json_str = write_card_to_json(self.card_data)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(json_str)
                self.current_file_path = filepath
                self.update_status(f"Saved JSON to {os.path.basename(filepath)}")
            except Exception as e:
                self.show_error_dialog(f"Failed to save JSON:\n{str(e)}")
        else:
            dialog.destroy()

    def on_save_png_clicked(self, widget):
        self.update_card_from_ui()
        
        base_img_path = self.current_avatar_path
        if not base_img_path or not os.path.exists(base_img_path):
            dialog = Gtk.FileChooserDialog(
                title="Select Base PNG Avatar Image",
                parent=self,
                action=Gtk.FileChooserAction.OPEN
            )
            dialog.add_buttons("_Cancel", Gtk.ResponseType.CANCEL, "_Open", Gtk.ResponseType.ACCEPT)
            f_filter = Gtk.FileFilter()
            f_filter.set_name("PNG Images")
            f_filter.add_pattern("*.png")
            dialog.add_filter(f_filter)
            
            if dialog.run() == Gtk.ResponseType.ACCEPT:
                base_img_path = dialog.get_filename()
            dialog.destroy()

        if not base_img_path:
            return

        save_dialog = Gtk.FileChooserDialog(
            title="Export Character Card PNG",
            parent=self,
            action=Gtk.FileChooserAction.SAVE
        )
        save_dialog.add_buttons("_Cancel", Gtk.ResponseType.CANCEL, "_Save", Gtk.ResponseType.ACCEPT)
        default_name = self.card_data.get("data", self.card_data).get("name", "character")
        save_dialog.set_current_name(f"{default_name}.png")

        if save_dialog.run() == Gtk.ResponseType.ACCEPT:
            output_path = save_dialog.get_filename()
            save_dialog.destroy()
            try:
                write_card_to_png(base_img_path, output_path, self.card_data)
                self.update_status(f"Successfully exported PNG card to {os.path.basename(output_path)}")
            except Exception as e:
                self.show_error_dialog(f"Failed to export PNG:\n{str(e)}")
        else:
            save_dialog.destroy()

    def show_error_dialog(self, message):
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Error"
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

if __name__ == "__main__":
    win = CharacterCardEditorWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()