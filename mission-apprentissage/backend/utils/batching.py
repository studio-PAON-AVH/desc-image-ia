import logging
from typing import List

logger = logging.getLogger(__name__)

def aggregate_image(index: int, size: int, model: str, model_result: List[dict], images_results: dict, images: dict):
        offset = index * size

        if index < len(model_result):
            batch = model_result[index]
            if batch and batch.get('results'):
                for j, item in enumerate(batch['results']):
                    global_idx = offset + j
                    if global_idx < images:
                        images_results[f"image_{global_idx}"][model] = item
                    else:
                        logger.debug("%s: ignored result for global index =%s", model, global_idx)
            else:
                logger.debug("%s: no results for batch %s", model, index)