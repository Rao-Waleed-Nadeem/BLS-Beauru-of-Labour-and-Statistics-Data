import os
from pathlib import Path
from BLS.pipeline.utils.base_utils import get_project_root, setup_logger

def test_pipeline_directory_structure():
    """Verify that all required pipeline directories exist and contain __init__.py"""
    root = get_project_root()
    pipeline_dir = root / 'pipeline'
    
    assert pipeline_dir.exists(), "pipeline directory is missing"
    assert (pipeline_dir / '__init__.py').exists(), "pipeline/__init__.py is missing"
    
    required_pkgs = [
        'config', 'registry', 'scheduler', 'collectors', 'parsers',
        'normalizers', 'validators', 'storage', 'datasets',
        'features', 'utils'
    ]
    
    for pkg in required_pkgs:
        pkg_dir = pipeline_dir / pkg
        assert pkg_dir.exists(), f"pipeline/{pkg} directory is missing"
        assert (pkg_dir / '__init__.py').exists(), f"pipeline/{pkg}/__init__.py is missing"

def test_storage_directory_structure():
    """Verify that all required storage directories exist"""
    root = get_project_root()
    storage_dir = root / 'storage'
    
    assert storage_dir.exists(), "storage directory is missing"
    
    required_dirs = [
        'raw/bls/api', 'raw/bls/html', 'raw/bls/pdf', 'raw/bls/rss',
        'raw/bls/archive', 'raw/bls/calendar',
        'normalized', 'validated',
        'processed/bls/cpi', 'processed/bls/ppi', 'processed/bls/employment',
        'processed/bls/jolts', 'processed/bls/eci', 'processed/bls/productivity',
        'processed/bls/real_earnings', 'processed/bls/import_export_prices',
        'features', 'metadata',
        'logs/collector', 'logs/validator', 'logs/normalizer',
        'logs/scheduler', 'logs/pipeline',
        'backups'
    ]
    
    for d in required_dirs:
        dir_path = storage_dir / d
        assert dir_path.exists(), f"storage/{d} directory is missing"

def test_base_utils_logger():
    """Verify that the logger sets up correctly"""
    logger = setup_logger('test_logger')
    assert logger.name == 'test_logger'
    assert logger.level == 20 # logging.INFO is 20
