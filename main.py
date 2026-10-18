import sys
import os
import json
import shutil
import tempfile
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, GdkPixbuf, GLib

from card_model import (
    create_empty_v2_card,
    read_card_from_json,
    write_card_to_json,
    read_card_from_png,
    write_card_to_png,
    TavernCardValidator,
    ensure_character_book,
    process_avatar_image
)

class CharacterCardEditorWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="SillyTavern Character Card Creator (V2/V3)")
        self.set_default_size(1100, 850)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.current_file_path = None
        self.original_avatar_path = None
        self.current_avatar_path = None
        self.temp_avatar_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        self.temp_avatar_path = self.temp_avatar_file.name
        self.temp_avatar_file.close()

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
        self.notebook.append_page(self.create_book_tab(), Gtk.Label(label="Character Book"))
        self.notebook.append_page(self.create_avatar_tab(), Gtk.Label(label="Avatar & Image"))
        self.notebook.append_page(self.create_metadata_tab(), Gtk.Label(label="Metadata & Tags"))
        self.notebook.append_page(self.create_summary_tab(), Gtk.Label(label="Summary & Tokens"))

        # Status Bar
        self.status_bar = Gtk.Statusbar()
        main_box.pack_start(self.status_bar, False, False, 0)
        self.update_status("Ready. Create or load a character card.")

        # Load initial empty data into UI
        self.populate_ui_from_card()

    def __del__(self):
        if os.path.exists(self.temp_avatar_path):
            try:
                os.remove(self.temp_avatar_path)
            except Exception:
                pass

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

        lbl_name = Gtk.Label(label="Character Name:", xalign=0)
        lbl_name.set_valign(Gtk.Align.START)
        grid.attach(lbl_name, 0, 0, 1, 1)
        
        self.entry_name = Gtk.Entry()
        self.entry_name.set_hexpand(True)
        self.entry_name.set_valign(Gtk.Align.START)
        grid.attach(self.entry_name, 1, 0, 1, 1)

        lbl_desc = Gtk.Label(label="Description:", xalign=0)
        lbl_desc.set_valign(Gtk.Align.START)
        grid.attach(lbl_desc, 0, 1, 1, 1)
        
        frame_desc, self.textview_desc = self.create_scrolled_text_view()
        frame_desc.set_hexpand(True)
        frame_desc.set_vexpand(True)
        grid.attach(frame_desc, 1, 1, 1, 1)

        lbl_pers = Gtk.Label(label="Personality Summary:", xalign=0)
        lbl_pers.set_valign(Gtk.Align.START)
        grid.attach(lbl_pers, 0, 2, 1, 1)
        
        frame_pers, self.textview_pers = self.create_scrolled_text_view()
        frame_pers.set_hexpand(True)
        frame_pers.set_vexpand(True)
        grid.attach(frame_pers, 1, 2, 1, 1)

        lbl_scen = Gtk.Label(label="Scenario:", xalign=0)
        lbl_scen.set_valign(Gtk.Align.START)
        grid.attach(lbl_scen, 0, 3, 1, 1)
        
        frame_scen, self.textview_scen = self.create_scrolled_text_view()
        frame_scen.set_hexpand(True)
        frame_scen.set_vexpand(True)
        grid.attach(frame_scen, 1, 3, 1, 1)

        lbl_first = Gtk.Label(label="First Message:", xalign=0)
        lbl_first.set_valign(Gtk.Align.START)
        grid.attach(lbl_first, 0, 4, 1, 1)
        
        frame_first, self.textview_first = self.create_scrolled_text_view()
        frame_first.set_hexpand(True)
        frame_first.set_vexpand(True)
        grid.attach(frame_first, 1, 4, 1, 1)

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

        lbl_sys = Gtk.Label(label="System Prompt (Overrides Global):", xalign=0)
        lbl_sys.set_valign(Gtk.Align.START)
        grid.attach(lbl_sys, 0, 0, 1, 1)
        
        frame_sys, self.textview_sys = self.create_scrolled_text_view()
        frame_sys.set_hexpand(True)
        frame_sys.set_vexpand(True)
        grid.attach(frame_sys, 1, 0, 1, 1)

        lbl_post = Gtk.Label(label="Post-History Instructions (Jailbreak):", xalign=0)
        lbl_post.set_valign(Gtk.Align.START)
        grid.attach(lbl_post, 0, 1, 1, 1)
        
        frame_post, self.textview_post = self.create_scrolled_text_view()
        frame_post.set_hexpand(True)
        frame_post.set_vexpand(True)
        grid.attach(frame_post, 1, 1, 1, 1)

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

    def create_book_tab(self):
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_border_width(12)
        paned.set_position(300)

        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        left_box.set_hexpand(False)
        left_box.pack_start(Gtk.Label(label="<b>Book Entries</b>", use_markup=True, xalign=0), False, False, 0)

        self.book_liststore = Gtk.ListStore(int, str)
        self.book_treeview = Gtk.TreeView(model=self.book_liststore)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Key / Summary", renderer, text=1)
        self.book_treeview.append_column(column)
        
        selection = self.book_treeview.get_selection()
        selection.connect("changed", self.on_book_selection_changed)

        scrolled_tree = Gtk.ScrolledWindow()
        scrolled_tree.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_tree.add(self.book_treeview)
        scrolled_tree.set_vexpand(True)
        left_box.pack_start(scrolled_tree, True, True, 0)

        btn_box = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        btn_box.set_layout(Gtk.ButtonBoxStyle.SPREAD)
        
        btn_add = Gtk.Button(label="Add Entry")
        btn_add.connect("clicked", self.on_add_book_entry)
        btn_box.pack_start(btn_add, True, True, 0)

        btn_del = Gtk.Button(label="Delete Entry")
        btn_del.connect("clicked", self.on_delete_book_entry)
        btn_box.pack_start(btn_del, True, True, 0)

        left_box.pack_start(btn_box, False, False, 0)
        paned.pack1(left_box, False, False)

        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        right_box.set_border_width(6)
        right_box.set_hexpand(True)

        right_box.pack_start(Gtk.Label(label="<b>Entry Properties</b>", use_markup=True, xalign=0), False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(8)

        grid.attach(Gtk.Label(label="Trigger Keys (Comma separated):", xalign=0), 0, 0, 1, 1)
        self.entry_book_keys = Gtk.Entry()
        self.entry_book_keys.set_hexpand(True)
        self.entry_book_keys.connect("changed", self.on_book_field_changed)
        grid.attach(self.entry_book_keys, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label="Comment / Name:", xalign=0), 0, 1, 1, 1)
        self.entry_book_comment = Gtk.Entry()
        self.entry_book_comment.set_hexpand(True)
        self.entry_book_comment.connect("changed", self.on_book_field_changed)
        grid.attach(self.entry_book_comment, 1, 1, 1, 1)

        self.chk_book_enabled = Gtk.CheckButton(label="Enabled")
        self.chk_book_enabled.connect("toggled", self.on_book_field_changed)
        grid.attach(self.chk_book_enabled, 1, 2, 1, 1)

        self.chk_book_constant = Gtk.CheckButton(label="Constant (Always include)")
        self.chk_book_constant.connect("toggled", self.on_book_field_changed)
        grid.attach(self.chk_book_constant, 1, 3, 1, 1)

        grid.attach(Gtk.Label(label="Insertion Order:", xalign=0), 0, 4, 1, 1)
        self.spin_book_order = Gtk.SpinButton.new_with_range(0, 9999, 1)
        self.spin_book_order.set_value(100)
        self.spin_book_order.connect("value-changed", self.on_book_field_changed)
        grid.attach(self.spin_book_order, 1, 4, 1, 1)

        grid.attach(Gtk.Label(label="Content:", xalign=0), 0, 5, 1, 1)
        
        frame_content, self.textview_book_content = self.create_scrolled_text_view()
        frame_content.set_hexpand(True)
        frame_content.set_vexpand(True)
        grid.attach(frame_content, 1, 5, 1, 1)

        right_box.pack_start(grid, True, True, 0)
        paned.pack2(right_box, True, False)

        self.current_selected_entry_idx = None
        return paned

    def create_avatar_tab(self):
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_border_width(12)
        paned.set_position(450)

        # Left Side: Image Preview
        preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        preview_box.pack_start(Gtk.Label(label="<b>Avatar Preview</b>", use_markup=True, xalign=0), False, False, 0)

        self.avatar_image = Gtk.Image()
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.avatar_image)
        preview_box.pack_start(scrolled, True, True, 0)

        self.lbl_image_info = Gtk.Label(label="No image loaded", xalign=0)
        preview_box.pack_start(self.lbl_image_info, False, False, 0)

        paned.pack1(preview_box, True, False)

        # Right Side: Image Manipulation Controls
        ctrl_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        ctrl_box.set_border_width(8)

        ctrl_box.pack_start(Gtk.Label(label="<b>Image Tools</b>", use_markup=True, xalign=0), False, False, 0)

        btn_select_img = Gtk.Button(label="Select New Image...")
        btn_select_img.connect("clicked", self.on_select_new_avatar)
        ctrl_box.pack_start(btn_select_img, False, False, 0)

        btn_revert = Gtk.Button(label="Revert to Original Image")
        btn_revert.connect("clicked", self.on_revert_avatar)
        ctrl_box.pack_start(btn_revert, False, False, 0)

        btn_save_as = Gtk.Button(label="Save Processed Avatar As...")
        btn_save_as.connect("clicked", self.on_save_avatar_as)
        ctrl_box.pack_start(btn_save_as, False, False, 0)

        # Quick Aspect Ratio Crop Options
        crop_frame = Gtk.Frame(label=" Aspect Ratio Crop ")
        crop_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        crop_box.set_border_width(8)

        btn_crop_square = Gtk.Button(label="Center Crop to 1:1 Square")
        btn_crop_square.connect("clicked", lambda w: self.apply_image_transform(crop_aspect="1:1"))
        crop_box.pack_start(btn_crop_square, False, False, 0)

        btn_crop_portrait = Gtk.Button(label="Center Crop to 2:3 Portrait")
        btn_crop_portrait.connect("clicked", lambda w: self.apply_image_transform(crop_aspect="2:3"))
        crop_box.pack_start(btn_crop_portrait, False, False, 0)

        crop_frame.add(crop_box)
        ctrl_box.pack_start(crop_frame, False, False, 0)

        # Quick Preset Resizing Options
        resize_frame = Gtk.Frame(label=" Preset Resizing ")
        resize_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        resize_box.set_border_width(8)

        btn_res_400 = Gtk.Button(label="Resize to 400x600 (Standard Portrait)")
        btn_res_400.connect("clicked", lambda w: self.apply_image_transform(target_size=(400, 600)))
        resize_box.pack_start(btn_res_400, False, False, 0)

        btn_res_512 = Gtk.Button(label="Resize to 512x512 (Square)")
        btn_res_512.connect("clicked", lambda w: self.apply_image_transform(target_size=(512, 512)))
        resize_box.pack_start(btn_res_512, False, False, 0)

        btn_res_max = Gtk.Button(label="Cap Max Dimension to 800px")
        btn_res_max.connect("clicked", lambda w: self.apply_image_transform(max_dimension=800))
        resize_box.pack_start(btn_res_max, False, False, 0)

        resize_frame.add(resize_box)
        ctrl_box.pack_start(resize_frame, False, False, 0)

        paned.pack2(ctrl_box, False, False)
        return paned

    def update_avatar_preview(self):
        if self.current_avatar_path and os.path.exists(self.current_avatar_path):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.current_avatar_path)
                w = pixbuf.get_width()
                h = pixbuf.get_height()
                file_size_kb = os.path.getsize(self.current_avatar_path) / 1024.0
                
                max_preview_dim = 450
                if w > max_preview_dim or h > max_preview_dim:
                    if w > h:
                        pw = max_preview_dim
                        ph = int(h * (max_preview_dim / w))
                    else:
                        ph = max_preview_dim
                        pw = int(w * (max_preview_dim / h))
                    preview_pixbuf = pixbuf.scale_simple(pw, ph, GdkPixbuf.InterpType.BILINEAR)
                else:
                    preview_pixbuf = pixbuf

                self.avatar_image.set_from_pixbuf(preview_pixbuf)
                self.lbl_image_info.set_markup(
                    f"<b>Dimensions:</b> {w}x{h} px  |  <b>File Size:</b> {file_size_kb:.1f} KB"
                )
            except Exception as e:
                self.avatar_image.clear()
                self.lbl_image_info.set_text(f"Error loading image preview: {str(e)}")
        else:
            self.avatar_image.clear()
            self.lbl_image_info.set_text("No avatar image associated with current card.")

    def on_select_new_avatar(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Select Avatar Image",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons("_Cancel", Gtk.ResponseType.CANCEL, "_Open", Gtk.ResponseType.ACCEPT)
        
        f_filter = Gtk.FileFilter()
        f_filter.set_name("Standard Images (PNG, JPG, BMP)")
        f_filter.add_pattern("*.png")
        f_filter.add_pattern("*.jpg")
        f_filter.add_pattern("*.jpeg")
        f_filter.add_pattern("*.bmp")
        dialog.add_filter(f_filter)

        if dialog.run() == Gtk.ResponseType.ACCEPT:
            filepath = dialog.get_filename()
            self.original_avatar_path = filepath
            # Copy to safe temp working file so we don't mutate original
            shutil.copyfile(filepath, self.temp_avatar_path)
            self.current_avatar_path = self.temp_avatar_path
            self.update_avatar_preview()
            self.update_status(f"Loaded avatar: {os.path.basename(filepath)}")
        dialog.destroy()

    def on_revert_avatar(self, widget):
        if self.original_avatar_path and os.path.exists(self.original_avatar_path):
            shutil.copyfile(self.original_avatar_path, self.temp_avatar_path)
            self.current_avatar_path = self.temp_avatar_path
            self.update_avatar_preview()
            self.update_status("Reverted avatar edits to original source.")
        else:
            self.show_error_dialog("No original source image to revert to.")

    def on_save_avatar_as(self, widget):
        if not self.current_avatar_path or not os.path.exists(self.current_avatar_path):
            self.show_error_dialog("No processed avatar image to save.")
            return

        dialog = Gtk.FileChooserDialog(
            title="Save Processed Avatar Image",
            parent=self,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons("_Cancel", Gtk.ResponseType.CANCEL, "_Save", Gtk.ResponseType.ACCEPT)
        
        default_name = self.card_data.get("data", self.card_data).get("name", "avatar")
        dialog.set_current_name(f"{default_name}_edited.png")

        if dialog.run() == Gtk.ResponseType.ACCEPT:
            output_path = dialog.get_filename()
            dialog.destroy()
            try:
                shutil.copyfile(self.current_avatar_path, output_path)
                self.update_status(f"Saved processed avatar to {os.path.basename(output_path)}")
            except Exception as e:
                self.show_error_dialog(f"Failed to save avatar image:\n{str(e)}")
        else:
            dialog.destroy()

    def apply_image_transform(self, crop_aspect=None, target_size=None, max_dimension=None):
        if not self.current_avatar_path or not os.path.exists(self.current_avatar_path):
            self.show_error_dialog("Please select or load an image first.")
            return

        try:
            process_avatar_image(
                input_path=self.current_avatar_path,
                output_path=self.current_avatar_path,
                crop_aspect=crop_aspect,
                target_size=target_size,
                max_dimension=max_dimension
            )
            self.update_avatar_preview()
            self.update_status("Image transformed successfully!")
        except Exception as e:
            self.show_error_dialog(f"Failed to transform image:\n{str(e)}")

    def create_metadata_tab(self):
        grid = Gtk.Grid()
        grid.set_border_width(12)
        grid.set_column_spacing(12)
        grid.set_row_spacing(10)

        lbl_creator = Gtk.Label(label="Creator:", xalign=0)
        lbl_creator.set_valign(Gtk.Align.START)
        grid.attach(lbl_creator, 0, 0, 1, 1)
        
        self.entry_creator = Gtk.Entry()
        self.entry_creator.set_hexpand(True)
        self.entry_creator.set_valign(Gtk.Align.START)
        grid.attach(self.entry_creator, 1, 0, 1, 1)

        lbl_version = Gtk.Label(label="Character Version:", xalign=0)
        lbl_version.set_valign(Gtk.Align.START)
        grid.attach(lbl_version, 0, 1, 1, 1)
        
        self.entry_version = Gtk.Entry()
        self.entry_version.set_hexpand(True)
        self.entry_version.set_valign(Gtk.Align.START)
        grid.attach(self.entry_version, 1, 1, 1, 1)

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

        book = data.get("character_book")
        if book and isinstance(book, dict):
            entries = book.get("entries", [])
            for idx, entry in enumerate(entries):
                keys_str = ", ".join(entry.get("keys", []))
                fields_to_check.append((f"Book Entry #{idx+1} [{keys_str}]", entry.get("content", "")))

        lines = []
        lines.append(f"{'Field Name':<35} | {'Characters':<10} | {'Est. Tokens':<10}")
        lines.append("-" * 61)

        total_chars = 0
        total_tokens = 0

        for name, text in fields_to_check:
            chars = len(text)
            tokens = max(1, chars // 4) if chars > 0 else 0
            total_chars += chars
            total_tokens += tokens
            lines.append(f"{name:<35} | {chars:<10} | {tokens:<10}")

        lines.append("-" * 61)
        lines.append(f"{'GRAND TOTAL':<35} | {total_chars:<10} | {total_tokens:<10}")

        buffer = self.summary_textview.get_buffer()
        buffer.set_text("\n".join(lines))

    def on_notebook_switch_page(self, notebook, page, page_num):
        if page_num == 4:
            self.update_avatar_preview()
        elif page_num == 6:
            self.refresh_summary_view()

    def populate_book_list(self):
        self.book_liststore.clear()
        data = self.card_data.get("data", self.card_data)
        book = data.get("character_book")
        if not book or not isinstance(book, dict):
            return
        
        entries = book.get("entries", [])
        for idx, entry in enumerate(entries):
            keys = ", ".join(entry.get("keys", []))
            comment = entry.get("comment", "")
            summary = f"[{keys}]" + (f" - {comment}" if comment else "")
            self.book_liststore.append([idx, summary])

    def on_book_selection_changed(self, selection):
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            idx = model[treeiter][0]
            self.current_selected_entry_idx = idx
            self.load_book_entry_into_ui(idx)
        else:
            self.current_selected_entry_idx = None
            self.clear_book_entry_ui()

    def load_book_entry_into_ui(self, idx):
        data = self.card_data.get("data", self.card_data)
        book = data.get("character_book")
        if not book or idx >= len(book.get("entries", [])):
            return
        
        entry = book["entries"][idx]
        self.entry_book_keys.set_text(", ".join(entry.get("keys", [])))
        self.entry_book_comment.set_text(entry.get("comment", ""))
        self.chk_book_enabled.set_active(entry.get("enabled", True))
        self.chk_book_constant.set_active(entry.get("constant", False))
        self.spin_book_order.set_value(entry.get("insertion_order", 100))
        self.set_text_to_textview(self.textview_book_content, entry.get("content", ""))

    def clear_book_entry_ui(self):
        self.entry_book_keys.set_text("")
        self.entry_book_comment.set_text("")
        self.chk_book_enabled.set_active(True)
        self.chk_book_constant.set_active(False)
        self.spin_book_order.set_value(100)
        self.set_text_to_textview(self.textview_book_content, "")

    def on_book_field_changed(self, widget):
        if self.current_selected_entry_idx is None:
            return
        
        data = self.card_data.get("data", self.card_data)
        book = ensure_character_book(data)
        entries = book.get("entries", [])
        
        if self.current_selected_entry_idx >= len(entries):
            return

        entry = entries[self.current_selected_entry_idx]
        keys_text = self.entry_book_keys.get_text()
        entry["keys"] = [k.strip() for k in keys_text.split(",") if k.strip()]
        entry["comment"] = self.entry_book_comment.get_text()
        entry["enabled"] = self.chk_book_enabled.get_active()
        entry["constant"] = self.chk_book_constant.get_active()
        entry["insertion_order"] = int(self.spin_book_order.get_value())
        entry["content"] = self.get_text_from_textview(self.textview_book_content)

        selection = self.book_treeview.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            keys = ", ".join(entry.get("keys", []))
            comment = entry.get("comment", "")
            summary = f"[{keys}]" + (f" - {comment}" if comment else "")
            model.set_value(treeiter, 1, summary)

    def on_add_book_entry(self, widget):
        data = self.card_data.get("data", self.card_data)
        book = ensure_character_book(data)
        
        new_entry = {
            "keys": ["keyword"],
            "content": "Lore entry content here...",
            "extensions": {},
            "enabled": True,
            "insertion_order": 100,
            "constant": False,
            "selective": False,
            "secondary_keys": []
        }
        book["entries"].append(new_entry)
        self.populate_book_list()
        
        path = Gtk.TreePath.new_from_indices([len(book["entries"]) - 1])
        self.book_treeview.get_selection().select_path(path)

    def on_delete_book_entry(self, widget):
        if self.current_selected_entry_idx is None:
            return
        
        data = self.card_data.get("data", self.card_data)
        book = data.get("character_book")
        if book and "entries" in book:
            idx = self.current_selected_entry_idx
            if 0 <= idx < len(book["entries"]):
                book["entries"].pop(idx)
                self.current_selected_entry_idx = None
                self.populate_book_list()
                self.clear_book_entry_ui()

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

        self.populate_book_list()
        self.update_avatar_preview()

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

        self.on_book_field_changed(None)

    def update_status(self, message):
        self.status_bar.push(0, message)

    def on_new_clicked(self, widget):
        self.card_data = create_empty_v2_card()
        self.current_file_path = None
        self.original_avatar_path = None
        self.current_avatar_path = None
        self.populate_ui_from_card()
        # Reset notebook view back to the first tab (Core Identity)
        self.notebook.set_current_page(0)
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
                    self.original_avatar_path = None
                    self.current_avatar_path = None
                elif filepath.endswith(".png"):
                    self.card_data = read_card_from_png(filepath)
                    self.original_avatar_path = filepath
                    shutil.copyfile(filepath, self.temp_avatar_path)
                    self.current_avatar_path = self.temp_avatar_path
                
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
            f_filter.set_name("Standard Images")
            f_filter.add_pattern("*.png")
            f_filter.add_pattern("*.jpg")
            f_filter.add_pattern("*.jpeg")
            f_filter.add_pattern("*.bmp")
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