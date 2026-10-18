import json
import base64
from typing import Dict, Any, Optional, Union
from PIL import Image
from PIL.PngImagePlugin import PngInfo

class TavernCardValidator:
    """
    Validates character card data structures against V1 and V2 specifications,
    matching the reference implementation from SillyTavern.
    """
    def __init__(self, card: Dict[str, Any]):
        self.card = card
        self._last_validation_error: Optional[str] = None

    @property
    def last_validation_error(self) -> Optional[str]:
        return self._last_validation_error

    def validate(self) -> Union[int, bool]:
        """
        Validate against V1 or V2 spec.
        Returns: 1 for V1, 2 for V2, or False if validation fails.
        """
        self._last_validation_error = None

        if self.validate_v1():
            return 1

        if self.validate_v2():
            return 2

        return False

    def validate_v1(self) -> bool:
        required_fields = ['name', 'description', 'personality', 'scenario', 'first_mes', 'mes_example']
        for field in required_fields:
            if field not in self.card:
                self._last_validation_error = field
                return False
        return True

    def validate_v2(self) -> bool:
        return (
            self._validate_spec_v2()
            and self._validate_spec_version_v2()
            and self._validate_data_v2()
            and self._validate_character_book_v2()
        )

    def _validate_spec_v2(self) -> bool:
        if self.card.get('spec') != 'chara_card_v2':
            self._last_validation_error = 'spec'
            return False
        return True

    def _validate_spec_version_v2(self) -> bool:
        if self.card.get('spec_version') != '2.0':
            self._last_validation_error = 'spec_version'
            return False
        return True

    def _validate_data_v2(self) -> bool:
        data = self.card.get('data')
        if not isinstance(data, dict):
            self._last_validation_error = 'No tavern card data found'
            return False

        required_fields = [
            'name', 'description', 'personality', 'scenario', 'first_mes', 'mes_example',
            'creator_notes', 'system_prompt', 'post_history_instructions',
            'alternate_greetings', 'tags', 'creator', 'character_version', 'extensions'
        ]

        for field in required_fields:
            if field not in data:
                self._last_validation_error = f'data.{field}'
                return False

        if not isinstance(data.get('alternate_greetings'), list):
            self._last_validation_error = 'data.alternate_greetings'
            return False

        if not isinstance(data.get('tags'), list):
            self._last_validation_error = 'data.tags'
            return False

        if not isinstance(data.get('extensions'), dict):
            self._last_validation_error = 'data.extensions'
            return False

        return True

    def _validate_character_book_v2(self) -> bool:
        data = self.card.get('data', {})
        character_book = data.get('character_book')

        if character_book is None:
            return True

        if not isinstance(character_book, dict):
            self._last_validation_error = 'data.character_book'
            return False

        if 'extensions' not in character_book or 'entries' not in character_book:
            self._last_validation_error = 'data.character_book structure'
            return False

        if not isinstance(character_book.get('entries'), list):
            self._last_validation_error = 'data.character_book.entries'
            return False

        if not isinstance(character_book.get('extensions'), dict):
            self._last_validation_error = 'data.character_book.extensions'
            return False

        return True


def create_empty_v2_card() -> Dict[str, Any]:
    """Returns a fully structured, empty V2 character card dictionary."""
    return {
        "spec": "chara_card_v2",
        "spec_version": "2.0",
        "data": {
            "name": "",
            "description": "",
            "personality": "",
            "scenario": "",
            "first_mes": "",
            "mes_example": "",
            "creator_notes": "",
            "system_prompt": "",
            "post_history_instructions": "",
            "alternate_greetings": [],
            "tags": [],
            "creator": "",
            "character_version": "1.0",
            "extensions": {}
        }
    }


def read_card_from_json(json_str: str) -> Dict[str, Any]:
    """Parses and validates a character card from a JSON string."""
    raw_data = json.loads(json_str)
    
    # If it's a V1 card, wrap it into V2 structure or keep as is depending on workflow
    validator = TavernCardValidator(raw_data)
    if not validator.validate():
        raise ValueError(f"Invalid character card format: {validator.last_validation_error}")
    
    return raw_data


def write_card_to_json(card_dict: Dict[str, Any]) -> str:
    """Serializes a character card dictionary to a formatted JSON string."""
    return json.dumps(card_dict, indent=4, ensure_ascii=False)


def read_card_from_png(image_path: str) -> Dict[str, Any]:
    """
    Extracts the base64-encoded 'chara' chunk from a PNG file, 
    decodes it from UTF-8, and parses the JSON character card data.
    """
    with Image.open(image_path) as img:
        # Check standard info dictionary or raw metadata chunks
        chara_data = img.info.get('chara')
        
        if not chara_data:
            # Fallback check case-insensitively across info keys
            for key, value in img.info.items():
                if key.lower() == 'chara':
                    chara_data = value
                    break

        if not chara_data:
            raise ValueError("No character metadata ('chara' chunk) found in PNG image.")

        # Decode base64 to string, then parse JSON
        decoded_bytes = base64.b64decode(chara_data)
        json_str = decoded_bytes.decode('utf-8')
        return read_card_from_json(json_str)


def write_card_to_png(image_path: str, output_path: str, card_dict: Dict[str, Any]) -> None:
    """
    Embeds the character card JSON dictionary as a base64-encoded 'chara' 
    tEXt chunk into a target PNG image.
    """
    validator = TavernCardValidator(card_dict)
    if not validator.validate():
        raise ValueError(f"Cannot write invalid character card: {validator.last_validation_error}")

    json_str = json.dumps(card_dict, ensure_ascii=False)
    base64_data = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')

    with Image.open(image_path) as img:
        metadata = PngInfo()
        
        # Copy existing PNG metadata chunks except 'chara'
        for key, value in img.info.items():
            if key.lower() != 'chara':
                if isinstance(value, str):
                    metadata.add_text(key, value)

        # Add the character card chunk
        metadata.add_text('chara', base64_data)
        
        # Save output image preserving format
        img.save(output_path, 'PNG', pnginfo=metadata)