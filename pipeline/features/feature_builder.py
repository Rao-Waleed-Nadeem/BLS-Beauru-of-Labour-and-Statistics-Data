"""pipeline.features.feature_builder — M20 Feature Engineering

Consumes processed dataset records and generates ML-ready time-series features.
"""

from typing import Any, Dict, List, Optional
from pipeline.parsers.models import UnifiedObject
from pipeline.storage.storage_manager import StorageManager


class FeatureBuilder:
    """M20 Feature Builder."""

    def __init__(self, storage: Optional[StorageManager] = None) -> None:
        self.storage = storage or StorageManager("storage")

    def build_features(
        self,
        dataset_id: str,
        objects: List[UnifiedObject],
        *,
        write_csv: bool = True,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """
        Build features for a dataset and persist them.

        objects: Should be chronologically sorted list of UnifiedObjects
                 for a single dataset.
        """
        features = self._calculate_features(objects)
        
        storage_result = self.storage.save_features(
            features,
            dataset_id,
            write_csv=write_csv,
            overwrite=overwrite,
        )

        return {
            "dataset_id": dataset_id,
            "record_count": len(features),
            "storage": {
                "success": storage_result.success,
                "skipped": storage_result.skipped,
                "path": str(storage_result.path) if storage_result.path else None,
                "checksum": storage_result.checksum,
                "message": storage_result.message,
            },
        }

    @staticmethod
    def _calculate_features(objects: List[UnifiedObject]) -> List[Dict[str, Any]]:
        features_list = []
        
        # Keep track of previous value for calculations
        previous_value: Optional[float] = None
        
        for obj in objects:
            if not obj.api:
                continue

            current_val_str = obj.api.value
            try:
                current_value = float(current_val_str)
            except (ValueError, TypeError):
                current_value = None

            # Calculate Time Features
            month = None
            quarter = None
            period = obj.api.period
            if period.startswith("M") and period[1:].isdigit():
                month = int(period[1:])
            elif period.startswith("Q") and period[1:].isdigit():
                quarter = int(period[1:])

            # Calculate Market Features
            value_diff = None
            pct_change = None
            
            if current_value is not None and previous_value is not None:
                value_diff = current_value - previous_value
                if previous_value != 0:
                    pct_change = (value_diff / abs(previous_value)) * 100
                    
            # Create feature row
            nlp_text = (
                f"{obj.api.series_title or obj.api.series_id} "
                f"for {obj.api.period_name or obj.api.period} {obj.api.year} "
                f"was {obj.api.value}."
            )
            feat = {
                "series_id": obj.api.series_id,
                "series_title": obj.api.series_title,
                "frequency": obj.api.frequency,
                "year": obj.api.year,
                "period": obj.api.period,
                "period_name": obj.api.period_name,
                "date_index": f"{obj.api.year}-{obj.api.period}",
                "value": current_value,
                "previous_value": previous_value,
                "value_diff": value_diff,
                "pct_change": pct_change,
                "month": month,
                "quarter": quarter,
                "latest": obj.api.latest,
                "footnotes": "; ".join(obj.api.footnotes),
                "nlp_text": nlp_text,
                "publication_datetime": obj.metadata.collection_timestamp if obj.metadata else None,
            }
            features_list.append(feat)
            
            # Update prev value
            if current_value is not None:
                previous_value = current_value
                
        return features_list
