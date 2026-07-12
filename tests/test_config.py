import pytest
from pipeline.config.loader import ConfigLoader

def test_config_loader_loads_all_files():
    loader = ConfigLoader()
    
    # Test individual loads
    settings = loader.load_settings()
    assert 'project' in settings
    
    pipeline = loader.load_pipeline()
    assert 'pipeline' in pipeline
    assert 'stages' in pipeline['pipeline']
    
    storage = loader.load_storage()
    assert 'storage' in storage
    assert 'root_dir' in storage['storage']
    
    scheduler = loader.load_scheduler()
    assert 'scheduler' in scheduler
    
    logging_cfg = loader.load_logging()
    assert 'logging' in logging_cfg
    
    # Test bulk load
    all_configs = loader.load_all()
    assert 'settings' in all_configs
    assert 'pipeline' in all_configs
    assert 'storage' in all_configs
    assert 'scheduler' in all_configs
    assert 'logging' in all_configs

def test_config_loader_missing_file():
    loader = ConfigLoader(config_dir="non_existent_dir")
    with pytest.raises(FileNotFoundError):
        loader.load_settings()
