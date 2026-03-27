"""
Celery pipeline for orchestrating the full conversion workflow.
"""
from celery import chain, chord
from worker.tasks import (
    process_image_task,
    generate_json_task,
    clean_json_task,
    create_onshape_model_task,
)


def run_conversion_pipeline(image_bytes: bytes, file_stem: str) -> chain:
    """
    Create and execute the full conversion pipeline.
    
    Pipeline flow:
    1. Process image and detect part type
    2. Generate JSON using Gemini AI
    3. Clean and validate JSON
    4. Create 3D model in OnShape
    
    Args:
        image_bytes: Raw bytes of the uploaded image
        file_stem: Filename stem for output files
        
    Returns:
        Celery chain object that can be executed with .apply_async() or .delay()
        
    Usage:
        >>> pipeline = run_conversion_pipeline(image_bytes, "bracket")
        >>> result = pipeline.apply_async()
        >>> task_id = result.id
    """
    # Create the pipeline chain with proper result passing
    # Each task returns a dict, and the next task unpacks it using **kwargs
    pipeline = (
        process_image_task.s(image_bytes, file_stem) |
        generate_json_task.s() |
        clean_json_task.s() |
        create_onshape_model_task.s()
    )
    
    return pipeline


def run_conversion_pipeline_with_callback(
    image_bytes: bytes,
    file_stem: str,
    callback=None
) -> chain:
    """
    Run conversion pipeline with optional callback task.
    
    Args:
        image_bytes: Raw bytes of the uploaded image
        file_stem: Filename stem for output files
        callback: Optional Celery task to execute after pipeline completes
        
    Returns:
        Celery chain with callback appended
    """
    pipeline = run_conversion_pipeline(image_bytes, file_stem)
    
    if callback:
        pipeline = pipeline | callback
    
    return pipeline


# Convenience function for direct execution
def convert_image_to_3d(image_bytes: bytes, file_stem: str):
    """
    Directly execute the conversion pipeline.
    
    Args:
        image_bytes: Raw bytes of the uploaded image
        file_stem: Filename stem for output files
        
    Returns:
        AsyncResult: Celery task result that can be used to track progress
        
    Example:
        >>> result = convert_image_to_3d(image_bytes, "bracket")
        >>> # Check if complete
        >>> result.ready()
        >>> # Get result (blocks until complete)
        >>> final_result = result.get()
    """
    pipeline = run_conversion_pipeline(image_bytes, file_stem)
    return pipeline.apply_async()
