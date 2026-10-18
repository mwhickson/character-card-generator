import json
import base64
from typing import Dict, Any, Optional, Union
from PIL import Image
from PIL.PngImagePlugin import PngInfo

class TavernCardValidator:
    """
    Validates character card data structures against V1, V2, and V3 specifications,
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
        Validate against V1, V2, or V3 spec.
        Returns: 1 for V1, 2 for V2, 3 for V3, or False if validation fails.
        """
        self._last_validation_error = None

        spec = self.card.get('spec')
        
        if spec == 'chara_card_v3':
            if self.validate_v3():
                return 3
            return False

        if spec == 'chara_card_v2':
            if self.validate_v2():
                return 2
            return False

        if self.validate_v1():
            return 1

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

    def validate_v3(self) -> bool:
        return (
            self._validate_spec_v3()
            and self._validate_spec_version_v3()
            and self._validate_data_v3()
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

    def _validate_spec_v3(self) -> bool:
        if self.card.get('spec') != 'chara_card_v3':
            self._last_validation_error = 'spec'
            return False
        return True

    def _validate_spec_version_v3(self) -> bool:
        try:
            version = float(self.card.get('spec_version', 0))
            if 3.0 <= version < 4.0:
                return True
        except (ValueError, TypeError):
            pass
        self._last_validation_error = 'spec_version'
        return False

    def _validate_data_v3(self) -> bool:
        data = self.card.get('data')
        if not isinstance(data, dict):
            self._last_validation_error = 'No tavern card data found'
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
    validator = TavernCardValidator(raw_data)
    if not validator.validate():
        raise ValueError(f"Invalid character card format: {validator.last_validation_error}")
    return raw_data


def write_card_to_json(card_dict: Dict[str, Any]) -> str:
    """Serializes a character card dictionary to a formatted JSON string."""
    return json.dumps(card_dict, indent=4, ensure_ascii=False)


def read_card_from_png(image_path: str) -> Dict[str, Any]:
    """
    Directly parses PNG binary chunks to extract 'ccv3' or 'chara' text data,
    bypassing Pillow info dictionary filtering. Supports V3 taking precedence over V2.
    """
    text_chunks = {}
    
    with open(image_path, 'rb') as f:
        signature = f.read(8)
        if signature != b'\x89PNG\r\n\x1a\n':
            raise ValueError("Not a valid PNG file.")
        
        while True:
            length_bytes = f.read(4)
            if not length_bytes or len(length_bytes) < 4:
                break
            length = int.from_bytes(length_bytes, byteorder='big')
            chunk_type = f.read(4)
            chunk_data = f.read(length)
            crc = f.read(4)
            
            if chunk_type == b'tEXt':
                # tEXt format: keyword \0 text
                parts = chunk_data.split(b'\x00', 1)
                if len(parts) == 2:
                    keyword = parts[0].decode('latin-1', errors='ignore').strip().lower()
                    text = parts[1].decode('utf-8', errors='ignore')
                    text_chunks[keyword] = text
            elif chunk_type == b'iTXt':
                # iTXt format: keyword \0 compression_flag compression_method language_tag \0 translated_keyword \0 text
                parts = chunk_data.split(b'\x00', 3)
                if len(parts) >= 4:
                    keyword = parts[0].decode('latin-1', errors='ignore').strip().lower()
                    text = parts[3].decode('utf-8', errors='ignore')
                    text_chunks[keyword] = text
            elif chunk_type == b'IEND':
                break

    raw_data = None
    # V3 ('ccv3') takes precedence over V2 ('chara') per SillyTavern spec
    if 'ccv3' in text_chunks:
        raw_data = text_chunks['ccv3']
    elif 'chara' in text_chunks:
        raw_data = text_chunks['chara']

    if not raw_data:
        raise ValueError("No character metadata ('ccv3' or 'chara') found in PNG image.")

    decoded_bytes = base64.b64decode(raw_data)
    json_str = decoded_bytes.decode('utf-8')
    return read_card_from_json(json_str)

def write_card_to_png(image_path: str, output_path: str, card_dict: Dict[str, Any]) -> None:
    """
    Embeds the character card JSON dictionary as a base64-encoded 'chara' 
    tEXt chunk into a target PNG image (preserving V2 export standard).
    """
    validator = TavernCardValidator(card_dict)
    if not validator.validate():
        raise ValueError(f"Cannot write invalid character card: {validator.last_validation_error}")

    json_str = json.dumps(card_dict, ensure_ascii=False)
    base64_data = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')

    with Image.open(image_path) as img:
        metadata = PngInfo()
        
        for key, value in img.info.items():
            if key.lower() not in ('chara', 'ccv3'):
                if isinstance(value, str):
                    metadata.add_text(key, value)

        metadata.add_text('chara', base64_data)
        img.save(output_path, 'PNG', pnginfo=metadata)