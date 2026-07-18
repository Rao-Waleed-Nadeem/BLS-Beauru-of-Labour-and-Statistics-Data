from abc import ABC, abstractmethod
from typing import Any, Dict

from pipeline.parsers.models import UnifiedObject

class BaseParser(ABC):
    """
    Abstract base class for all BLS pipeline parsers.
    Parsers are responsible for converting raw data from collectors
    into the canonical UnifiedObject format.
    """

    @abstractmethod
    def parse(self, raw_data: Any, metadata: Dict[str, Any]) -> UnifiedObject:
        """
        Parse raw data into a UnifiedObject.
        
        Args:
            raw_data: The raw content to parse (e.g. HTML string, JSON dict, bytes).
            metadata: Dictionary containing collection metadata for this payload.
            
        Returns:
            UnifiedObject: The fully populated unified schema object.
            
        Raises:
            ValueError: If parsing fails or required fields are missing.
        """
        pass
