import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class GameLogger:
    """
    Records game state and agent decisions into a JSONL format
    suitable for offline value network training.
    """
    def __init__(self, output_path: str):
        self.output_path = output_path
        self._is_open = False
        self._file = None

    def open(self):
        try:
            self._file = open(self.output_path, 'a', encoding='utf-8')
            self._is_open = True
        except Exception as e:
            logger.error(f"Failed to open GameLogger at {self.output_path}: {e}")

    def log_turn(self, raw_observation: Dict[str, Any], chosen_action: List[int]):
        """
        Logs a single decision point.
        """
        if not self._is_open:
            return
            
        record = {
            "observation": raw_observation,
            "chosen_action": chosen_action
        }
        
        try:
            self._file.write(json.dumps(record) + "\n")
            self._file.flush()
        except Exception as e:
            logger.error(f"Failed to write to GameLogger: {e}")

    def close(self):
        if self._file and self._is_open:
            self._file.close()
            self._is_open = False
