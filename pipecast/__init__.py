"""
PIPECAST: Pipeline Integrated Prediction & Environmental Climate Analysis using Satellite Tracking

A Python library for weather forecast analysis, AOI generation, and risk assessment.
"""

__version__ = "0.2.0"
__author__ = "PIPECAST Development Team"

from .forecast_processor import (
    ForecastProcessor,
    process_forecast_dates,
    generate_aois
)

from .ensemble import (
    EnsembleProcessor,
    create_ensemble_probability,
    rank_aois_by_risk
)

from .data_manager import (
    DataManager,
    download_enhanced_layers,
    load_enhanced_layers
)

from .config import (
    ForecastConfig,
    WeatherDataset
)

__all__ = [
    # Main processing
    "ForecastProcessor",
    "process_forecast_dates",
    "generate_aois",
    
    # Ensemble
    "EnsembleProcessor",
    "create_ensemble_probability",
    "rank_aois_by_risk",
    
    # Data management
    "DataManager",
    "download_enhanced_layers",
    "load_enhanced_layers",
    
    # Configuration
    "ForecastConfig",
    "WeatherDataset"
]
