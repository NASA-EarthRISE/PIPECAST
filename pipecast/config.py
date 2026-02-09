"""
Configuration classes for PIPECAST weather forecast processing.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class WeatherDataset(Enum):
    """Supported weather forecast datasets."""
    HRRR = "hrrr"  # High-Resolution Rapid Refresh (Continental US)
    HRRRAK = "hrrrak"  # HRRR Alaska
    ECMWF = "ecmwf"  # European Centre for Medium-Range Weather Forecasts
    GFS = "gfs"  # Global Forecast System
    # Add more as needed


@dataclass
class ForecastConfig:
    """
    Configuration for weather forecast processing.
    
    This class holds all parameters needed to run the PIPECAST forecast
    analysis workflow.
    """
    
    # Date and time parameters
    forecast_dates: List[str] = field(default_factory=list)
    """List of forecast dates in YYYY-MM-DD format."""
    
    fxx_list: List[int] = field(default_factory=lambda: [0, 4, 8, 12, 16, 20, 24])
    """Forecast hours to evaluate (e.g., [0, 4, 8, 12, 16, 20, 24])."""
    
    # Weather dataset parameters
    weather_dataset: WeatherDataset = WeatherDataset.HRRR
    """Weather forecast dataset to use."""
    
    product: str = "sfc"
    """Weather product type (e.g., 'sfc' for surface)."""
    
    variable: str = "APCP:surface"
    """Variable to extract (e.g., 'APCP:surface' for accumulated precipitation)."""
    
    variable_name: str = "tp"
    """Variable name in xarray dataset."""
    
    # Threshold parameters
    thresholds: List[float] = field(default_factory=lambda: [5, 39, 50, 100, 254, 255])
    """Precipitation thresholds in mm."""
    
    threshold_bins: List[Tuple[float, float]] = field(
        default_factory=lambda: [(0, 5), (6, 39), (40, 50), (51, 100), (100, 254), (255, float('inf'))]
    )
    """Threshold bins for ensemble probability calculation."""
    
    bin_labels: List[str] = field(
        default_factory=lambda: ["0-5", "6-39", "40-50", "51-100", "100-254", "255+"]
    )
    """Labels for threshold bins."""
    
    # Processing methods
    forecast_methods: List[str] = field(default_factory=lambda: ["standard", "enhanced"])
    """Processing methods: 'standard' (AOIs only) or 'enhanced' (with census/watershed)."""
    
    # Spatial parameters
    target_crs: str = "EPSG:4326"
    """Target coordinate reference system."""
    
    min_aoi_area: float = 0.01
    """Minimum area for AOI polygons (in degrees squared)."""
    
    ensemble_resolution: float = 0.05
    """Grid resolution for ensemble probability (in degrees)."""
    
    clip_to_land: bool = True
    """Whether to clip AOIs to land areas only."""
    
    # Enhanced layer parameters
    use_census: bool = True
    """Whether to use census population data."""
    
    use_watershed: bool = True
    """Whether to use watershed data."""
    
    custom_layers: Dict[str, str] = field(default_factory=dict)
    """Custom enhanced layers: {layer_name: file_path}."""
    
    # Output parameters
    output_dir: str = "./output"
    """Base output directory."""
    
    save_aois: bool = True
    """Whether to save individual AOI GeoJSON files."""
    
    save_ensemble: bool = True
    """Whether to generate ensemble probability products."""
    
    save_visualizations: bool = True
    """Whether to save visualization outputs."""
    
    # AOI filtering
    aoi_shapefile: Optional[str] = None
    """Optional shapefile to constrain the analysis area."""
    
    # Zenodo data URLs
    census_zenodo_url: str = "https://zenodo.org/records/18497756/files/National_block_groups_with_pop.zip"
    """Zenodo URL for census data."""
    
    watershed_zenodo_url: str = "https://zenodo.org/records/18497756/files/National_Huc_12_preprocessed.zip"
    """Zenodo URL for watershed data."""
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.forecast_dates:
            raise ValueError("forecast_dates cannot be empty")
        
        # Validate dates
        for date_str in self.forecast_dates:
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")
        
        # Validate bins and labels match
        if len(self.threshold_bins) != len(self.bin_labels):
            raise ValueError("threshold_bins and bin_labels must have same length")
        
        # Convert string to enum if needed
        if isinstance(self.weather_dataset, str):
            self.weather_dataset = WeatherDataset(self.weather_dataset.lower())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Enum):
                result[key] = value.value
            elif isinstance(value, (list, tuple)) and value and isinstance(value[0], Enum):
                result[key] = [v.value for v in value]
            else:
                result[key] = value
        return result
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ForecastConfig':
        """Create config from dictionary."""
        # Convert weather_dataset string to enum
        if 'weather_dataset' in config_dict and isinstance(config_dict['weather_dataset'], str):
            config_dict['weather_dataset'] = WeatherDataset(config_dict['weather_dataset'])
        
        return cls(**config_dict)
    
    def get_model_name(self) -> str:
        """Get the model name for Herbie."""
        return self.weather_dataset.value


# Preset configurations for common use cases
class PresetConfigs:
    """Preset configurations for common scenarios."""
    
    @staticmethod
    def alaska_hrrr(forecast_dates: List[str], output_dir: str = "./output") -> ForecastConfig:
        """Configuration for Alaska HRRR analysis."""
        return ForecastConfig(
            forecast_dates=forecast_dates,
            weather_dataset=WeatherDataset.HRRRAK,
            output_dir=output_dir
        )
    
    @staticmethod
    def conus_hrrr(forecast_dates: List[str], output_dir: str = "./output") -> ForecastConfig:
        """Configuration for Continental US HRRR analysis."""
        return ForecastConfig(
            forecast_dates=forecast_dates,
            weather_dataset=WeatherDataset.HRRR,
            output_dir=output_dir
        )
    
    @staticmethod
    def quick_test(forecast_date: str, output_dir: str = "./test_output") -> ForecastConfig:
        """Quick test configuration with minimal parameters."""
        return ForecastConfig(
            forecast_dates=[forecast_date],
            fxx_list=[0, 12, 24],
            thresholds=[39, 100],
            forecast_methods=["standard"],
            use_census=False,
            use_watershed=False,
            save_ensemble=False,
            output_dir=output_dir
        )
