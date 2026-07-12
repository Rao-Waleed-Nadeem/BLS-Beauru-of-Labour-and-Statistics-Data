from typing import Dict, Union


class PrioritySystem:
    """Maps named priority levels to numeric queue priorities from configuration."""

    NAMED_PRIORITIES = ("Critical", "High", "Medium", "Low")

    def __init__(self, queue_config: Dict[str, int]) -> None:
        self.high_priority = queue_config.get("high_priority", 0)
        self.default_priority = queue_config.get("default_priority", 1)
        self.low_priority = queue_config.get("low_priority", 2)

    def resolve(self, priority: Union[str, int]) -> int:
        if isinstance(priority, int):
            return priority

        mapping = {
            "Critical": self.high_priority,
            "High": self.default_priority,
            "Medium": self.low_priority,
            "Low": self.low_priority,
        }
        return mapping.get(priority, self.default_priority)

    def is_higher_than(self, left: int, right: int) -> bool:
        return left < right
