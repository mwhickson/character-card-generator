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
        super().__init__(title="SillyTavern Character Card Creator (V2)")
        self.set_default_size(850, 700)
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
        main_box.pack_start(self.notebook, True, True, 0)

        # Build Tabs
        self.notebook.append_page(self.create_core_tab(), Gtk.Label(label="Core Identity"))
        self.notebook.append_page(self.create_prompts_tab(), Gtk.Label(label="Prompts & Settings"))
        self.notebook.append_page(self.create_greetings_tab(), Gtk.Label(label="Alternate Greetings"))
        self.notebook.append_page(self.create_metadata_tab(), Gtk.Label(label="Metadata & Tags"))

        # Status Bar / Token Info
        self.status_bar = Gtk.Statusbar()
        main_box.pack_start(self.status_bar, False, False, 0)
        self.update_status("Ready. Create or load a character card.")

        # Load initial empty data into UI
        self.populate_ui_from_card()

    def create_toolbar(self):
        toolbar = Gtk.Toolbar()
        
        new_item = Gtk.ToolButton.new_from_stock(Gtk.STOCK_NEW)
        new_item.set_tooltip_text("New Card")
        new_item.connect("clicked", self.on_new_clicked)
        toolbar.insert(new_item, -1)

        open_item = Gtk.ToolButton.new_from_stock(Gtk.STOCK_OPEN)
        open_item.set_tooltip_text("Open Card (JSON or PNG)")
        open_item.connect("clicked", self.on_open_clicked)
        toolbar.insert(open_item, -1)

        save_item = Gtk.ToolButton.new_from_stock(Gtk.STOCK_SAVE)
        save_item.set_tooltip_text("Save Card (JSON)")
        save_item.connect("clicked", self.on_save_json_clicked)
        toolbar.insert(save_item, -1)

        save_png_item = Gtk.ToolButton.new_from_stock(Gtk.STOCK_SAVE_AS)
        save_png_item.set_tooltip_text("Export to PNG (Embed Card)")
        save_png_item.connect("clicked", self.on_save_png_clicked)
        toolbar.insert(save_png_item, -1)

        return toolbar

    def create_scrolled_text_view(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        textView = Gtk.TextView()
        textView.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scrolled.add(textView)
        return scrolled, textView

    def create_core_tab(self):
        grid = Gtk.Grid()
        grid.set_border_width(10)
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)

        # Name
        grid.attach(Gtk.Label(label="Character Name:", xalign=0), 0, 0, 1, 1)
        self.entry_name = Gtk.Entry()
        grid.attach(self.entry_name, 1, 0, 1, 1)

        # Description
        grid.attach(Gtk.Label(label="Description:", xalign=0), 0, 1, 1, 1)
        scrolled_desc, self.textview_desc = self.create_scrolled_text_view()
        grid.attach(scrolled_desc, 1, 1, 1, 1)

        # Personality
        grid.attach(Gtk.Label(label="Personality Summary:", xalign=0), 0, 2, 1, 1)
        scrolled_pers, self.textview_pers = self.create_scrolled_text_view()
        grid.attach(scrolled_pers, 1, 2, 1, 1)

        # Scenario
        grid.attach(Gtk.Label(label="Scenario:", xalign=0), 0, 3, 1, 1)
        scrolled_scen, self.textview_scen = self.create_scrolled_text_view()
        grid.attach(scrolled_scen, 1, 3, 1, 1)

        # First Message (Greeting)
        grid.attach(Gtk.Label(label="First Message:", xalign=0), 0, 4, 1, 1)
        scrolled_first, self.textview_first = self.create_scrolled_text_view()
        grid.attach(scrolled_first, 1, 4, 1, 1)

        # Example Dialogue
        grid.attach(Gtk.Label(label="Example Dialogue:", xalign=0), 0, 5, 1, 1)
        scrolled_ex, self.textview_ex = self.create_scrolled_text_view()
        grid.attach(scrolled_ex, 1, 5, 1, 1)

        grid.set_column_homogeneous(False)
        return grid

    def create_prompts_tab(self):
        grid = Gtk.Grid()
        grid.set_border_width(10)
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)

        # System Prompt
        grid.attach(Gtk.Label(label="System Prompt (Overrides Global):", xalign=0), 0, 0, 1, 1)
        scrolled_sys, self.textview_sys = self.create_scrolled_text_view()
        grid.attach(scrolled_sys, 1, 0, 1, 1)

        # Post History Instructions
        grid.attach(Gtk.Label(label="Post-History Instructions (Jailbreak):", xalign=0), 0, 1, 1, 1)
        scrolled_post, self.textview_post = self.create_scrolled_text_view()
        grid.attach(scrolled_post, 1, 1, 1, 1)

        # Creator Notes
        grid.attach(Gtk.Label(label="Creator Notes:", xalign=0), 0, 2, 1, 1)
        scrolled_notes, self.textview_notes = self.create_scrolled_text_view()
        grid.attach(scrolled_notes, 1, 2, 1, 1)

        return grid

    def create_greetings_tab(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_border_width(10)

        box.pack_start(Gtk.Label(label="Alternate Greetings (One greeting per line):", xalign=0), False, False, 0)
        
        scrolled, self.textview_greetings = self.create_scrolled_text_view()
        box.pack_start(scrolled, True, True, 0)

        return box

    def create_metadata_tab(self):
        grid = Gtk.Grid()
        grid.set_border_width(10)
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)

        # Creator
        grid.attach(Gtk.Label(label="Creator:", xalign=0), 0, 0, 1, 1)
        self.entry_creator = Gtk.Entry()
        grid.attach(self.entry_creator, 1, 0, 1, 1)

        # Character Version
        grid.attach(Gtk.Label(label="Character Version:", xalign=0), 0, 1, 1, 1)
        self.entry_version = Gtk.Entry()
        grid.attach(self.entry_version, 1, 1, 1, 1)

        # Tags
        grid.attach(Gtk.Label(label="Tags (Comma separated):", xalign=0), 0, 2, 1, 1)
        self.entry_tags = Gtk.Entry()
        grid.attach(self.entry_tags, 1, 2, 1, 1)

        return grid

    def get_text_from_textview(self, textview):
        buffer = textview.get_buffer()
        return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)

    def set_text_to_textview(self, textview, text):
        buffer = textview.get_buffer()
        buffer.set_text(text if text else "")

    def populate_ui_from_card(self):
        data = self.card_data.get("data", {})
        
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
        self.entry_version.set_text(data.get("character_version", "1.0"))
        
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
            # Support splitting by newline or '---' delimiter
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
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT
        )

        filter_any = Gtk.FileFilter()
        filter_any.set_name("Character Cards (JSON, PNG)")
        filter_any.add_pattern("*.json")
        filter_any.add_pattern("*.png")
        dialog.add_filter(filter_any)

        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            filepath = dialog.get_filename()
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
        
        dialog.destroy()

    def on_save_json_clicked(self, widget):
        self.update_card_from_ui()
        dialog = Gtk.FileChooserDialog(
            title="Save Character Card JSON",
            parent=self,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT
        )
        dialog.set_current_name(f"{self.card_data['data'].get('name', 'character')}.json")

        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            filepath = dialog.get_filename()
            try:
                json_str = write_card_to_json(self.card_data)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(json_str)
                self.current_file_path = filepath
                self.update_status(f"Saved JSON to {os.path.basename(filepath)}")
            except Exception as e:
                self.show_error_dialog(f"Failed to save JSON:\n{str(e)}")
        
        dialog.destroy()

    def on_save_png_clicked(self, widget):
        self.update_card_from_ui()
        
        # Prompt for source base image if we don't have one loaded
        base_img_path = self.current_avatar_path
        if not base_img_path or not os.path.exists(base_img_path):
            dialog = Gtk.FileChooserDialog(
                title="Select Base PNG Avatar Image",
                parent=self,
                action=Gtk.FileChooserAction.OPEN
            )
            dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT)
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
        save_dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT)
        save_dialog.set_current_name(f"{self.card_data['data'].get('name', 'character')}.png")

        if save_dialog.run() == Gtk.ResponseType.ACCEPT:
            output_path = save_dialog.get_filename()
            try:
                write_card_to_png(base_img_path, output_path, self.card_data)
                self.update_status(f"Successfully exported PNG card to {os.path.basename(output_path)}")
            except Exception as e:
                self.show_error_dialog(f"Failed to export PNG:\n{str(e)}")
        
        save_dialog.destroy()

    def show_error_dialog(self, message):
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Error"
        .format()
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

if __name__ == "__main__":
    win = CharacterCardEditorWindow()
    win.connect("destroy", Gtk.Main.quit)
    win.show_all()
    Gtk.main()