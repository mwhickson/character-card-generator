import unittest
import json
import tempfile
import os
from PIL import Image

from card_model import (
    TavernCardValidator,
    create_empty_v2_card,
    read_card_from_json,
    write_card_to_json,
    read_card_from_png,
    write_card_to_png,
    ensure_character_book
)

class TestTavernCardModel(unittest.TestCase):

    def setUp(self):
        self.valid_v1_card = {
            "name": "Test Character",
            "description": "A test description.",
            "personality": "Friendly",
            "scenario": "A test scenario.",
            "first_mes": "Hello!",
            "mes_example": "<START>\n{{user}}: hi\n{{char}}: hello"
        }

        self.valid_v2_card = create_empty_v2_card()
        self.valid_v2_card["data"]["name"] = "V2 Character"

    def test_validator_v1_success(self):
        validator = TavernCardValidator(self.valid_v1_card)
        self.assertEqual(validator.validate(), 1)
        self.assertIsNone(validator.last_validation_error)

    def test_validator_v1_failure_missing_field(self):
        invalid_card = self.valid_v1_card.copy()
        del invalid_card["personality"]
        validator = TavernCardValidator(invalid_card)
        self.assertFalse(validator.validate())
        self.assertEqual(validator.last_validation_error, "personality")

    def test_validator_v2_success(self):
        validator = TavernCardValidator(self.valid_v2_card)
        self.assertEqual(validator.validate(), 2)
        self.assertIsNone(validator.last_validation_error)

    def test_validator_v3_success(self):
        v3_card = {
            "spec": "chara_card_v3",
            "spec_version": "3.0",
            "data": {
                "name": "V3 Character"
            }
        }
        validator = TavernCardValidator(v3_card)
        self.assertEqual(validator.validate(), 3)
        self.assertIsNone(validator.last_validation_error)

    def test_validator_v2_invalid_spec(self):
        card = self.valid_v2_card.copy()
        card["spec"] = "wrong_spec"
        validator = TavernCardValidator(card)
        self.assertFalse(validator.validate())
        self.assertEqual(validator.last_validation_error, "spec")

    def test_validator_v2_invalid_spec_version(self):
        card = self.valid_v2_card.copy()
        card["spec_version"] = "1.0"
        validator = TavernCardValidator(card)
        self.assertFalse(validator.validate())
        self.assertEqual(validator.last_validation_error, "spec_version")

    def test_validator_v2_missing_data_field(self):
        card = self.valid_v2_card.copy()
        del card["data"]["creator"]
        validator = TavernCardValidator(card)
        self.assertFalse(validator.validate())
        self.assertEqual(validator.last_validation_error, "data.creator")

    def test_validator_v2_invalid_types(self):
        card = self.valid_v2_card.copy()
        card["data"]["tags"] = "not_an_array"
        validator = TavernCardValidator(card)
        self.assertFalse(validator.validate())
        self.assertEqual(validator.last_validation_error, "data.tags")

    def test_validator_v2_with_character_book(self):
        card = self.valid_v2_card.copy()
        card["data"]["character_book"] = {
            "extensions": {},
            "entries": [
                {
                    "keys": ["test"],
                    "content": "Lore content",
                    "extensions": {},
                    "enabled": True,
                    "insertion_order": 100
                }
            ]
        }
        validator = TavernCardValidator(card)
        self.assertEqual(validator.validate(), 2)

    def test_ensure_character_book(self):
        card = {"data": {}}
        book = ensure_character_book(card)
        self.assertIn("character_book", card["data"])
        self.assertIn("entries", book)
        self.assertEqual(book["entries"], [])

    def test_json_roundtrip(self):
        json_str = write_card_to_json(self.valid_v2_card)
        parsed_card = read_card_from_json(json_str)
        self.assertEqual(parsed_card, self.valid_v2_card)

    def test_json_parsing_invalid(self):
        invalid_json = json.dumps({"spec": "chara_card_v2"})
        with self.assertRaises(ValueError):
            read_card_from_json(invalid_json)

    def test_png_metadata_roundtrip(self):
        # Create a temporary base image and output file using tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            input_img_path = os.path.join(tmpdir, "base.png")
            output_img_path = os.path.join(tmpdir, "character.png")

            # Create a small blank image with Pillow
            img = Image.new('RGB', (100, 100), color='white')
            img.save(input_img_path, 'PNG')

            # Write card to PNG metadata
            write_card_to_png(input_img_path, output_img_path, self.valid_v2_card)
            self.assertTrue(os.path.exists(output_img_path))

            # Read card back from PNG metadata
            read_card = read_card_from_png(output_img_path)
            self.assertEqual(read_card, self.valid_v2_card)

    def test_png_missing_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            blank_img_path = os.path.join(tmpdir, "blank.png")
            img = Image.new('RGB', (100, 100), color='white')
            img.save(blank_img_path, 'PNG')

            with self.assertRaises(ValueError):
                read_card_from_png(blank_img_path)

if __name__ == '__main__':
    unittest.main()