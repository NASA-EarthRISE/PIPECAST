# PIPECAST Weather Forecast Analysis

**Pipeline Integrated Prediction & Environmental Climate Analysis using Satellite Tracking**

A Python library for weather forecast analysis, Areas of Interest (AOI) generation, ensemble probability products, and population risk assessment.

## Features

🌦️ **Multi-Dataset Support**
- HRRR (Continental US)
- HRRR Alaska
- ECMWF (planned)
- GFS (planned)
- Extensible to other datasets

📍 **AOI Generation**
- Automatic identification of precipitation areas
- Multiple threshold levels
- Connected region detection
- Land clipping

📊 **Enhanced Analysis**
- Census population data integration
- Watershed analysis
- Custom layer support
- Risk ranking

🎲 **Ensemble Products**
- Probabilistic forecast generation
- Multi-member aggregation
- GeoTIFF probability maps
- Ranked risk assessment

📈 **Visualization**
- Grid plots of AOIs
- Interactive Folium maps
- Threshold comparisons
- Time series analysis

## Installation

### From PyPI (Recommended)
```bash
pip install pipecast-weather
```

### From Source (Development)

```bash
git clone https://github.com/NASA-EarthRISE/PIPECAST.git
cd PIPECAST
pip install -e .
```

### With Visualization Support
```bash
pip install pipecast-weather[viz]
```

### Google Colab

```python
!pip install git+https://github.com/NASA-EarthRISE/PIPECAST.git
```

## Quick Start

### Basic Usage

```python
from pipecast import ForecastConfig, ForecastProcessor

# Configure
config = ForecastConfig(
    forecast_dates=["2025-10-07", "2025-10-08", "2025-10-09"],
    fxx_list=[0, 12, 24],
    thresholds=[39, 100, 255],
    weather_dataset="hrrr",
    output_dir="./output"
)

# Process
processor = ForecastProcessor(config)
results = processor.process_all_forecasts()
```

### Alaska HRRR

```python
from pipecast.config import PresetConfigs

# Use preset configuration
config = PresetConfigs.alaska_hrrr(
    forecast_dates=["2025-10-07", "2025-10-08"],
    output_dir="./alaska_output"
)

processor = ForecastProcessor(config)
results = processor.process_all_forecasts()
```

### With Enhanced Layers (Census + Watershed)

```python
config = ForecastConfig(
    forecast_dates=["2025-10-07"],
    forecast_methods=["standard", "enhanced"],
    use_census=True,
    use_watershed=True,
    output_dir="./enhanced_output"
)

processor = ForecastProcessor(config)
results = processor.process_all_forecasts()
```

## Creating Ensemble Products

```python
from pipecast import EnsembleProcessor

# Create ensemble probability maps
processor = EnsembleProcessor("./output")
prob_paths = processor.create_ensemble_probabilities()

# Rank AOIs by risk
ranked = processor.rank_aois_by_probability(
    census_gdf=census_data,  # optional
    top_n=50
)

print(ranked.head(10))
```

## Visualization

```python
from pipecast.visualization import visualize_forecast_outputs

# Create all standard visualizations
visualize_forecast_outputs("./output")

# Or use the visualizer class for more control
from pipecast.visualization import ForecastVisualizer

viz = ForecastVisualizer("./output")
viz.plot_threshold_comparison("2025-10-07", fxx=12)
viz.create_all_date_maps()
```

## Configuration Options

### Complete Configuration Example

```python
from pipecast import ForecastConfig, WeatherDataset

config = ForecastConfig(
    # Dates and times
    forecast_dates=["2025-10-07", "2025-10-08", "2025-10-09", "2025-10-10"],
    fxx_list=[0, 4, 8, 12, 16, 20, 24],
    
    # Weather dataset
    weather_dataset=WeatherDataset.HRRR,
    product="sfc",
    variable="APCP:surface",
    variable_name="tp",
    
    # Thresholds
    thresholds=[5, 39, 50, 100, 254, 255],
    
    # Processing
    forecast_methods=["standard", "enhanced"],
    target_crs="EPSG:4326",
    min_aoi_area=0.01,
    clip_to_land=True,
    
    # Enhanced layers
    use_census=True,
    use_watershed=True,
    custom_layers={
        "roads": "/path/to/roads.shp",
        "infrastructure": "/path/to/infrastructure.geojson"
    },
    
    # Ensemble
    threshold_bins=[(0, 5), (6, 39), (40, 50), (51, 100), (100, 254), (255, float('inf'))],
    bin_labels=["0-5", "6-39", "40-50", "51-100", "100-254", "255+"],
    ensemble_resolution=0.05,
    
    # Output
    output_dir="./output",
    save_aois=True,
    save_ensemble=True,
    save_visualizations=True
)
```

## Custom Threshold Bins

```python
# Define custom bins for your warning levels
config = ForecastConfig(
    forecast_dates=["2025-10-07"],
    threshold_bins=[
        (0, 10),      # Light
        (10, 25),     # Moderate
        (25, 50),     # Heavy
        (50, 100),    # Very Heavy
        (100, float('inf'))  # Extreme
    ],
    bin_labels=["Light", "Moderate", "Heavy", "Very Heavy", "Extreme"],
    output_dir="./custom_bins"
)
```

## Working with Custom Layers

```python
# Add your own enhanced layers
config = ForecastConfig(
    forecast_dates=["2025-10-07"],
    forecast_methods=["enhanced"],
    use_census=True,
    use_watershed=True,
    custom_layers={
        "pipelines": "/path/to/pipeline_network.shp",
        "critical_infrastructure": "/path/to/infrastructure.geojson",
        "evacuation_zones": "/path/to/zones.shp"
    },
    output_dir="./custom_layers"
)

processor = ForecastProcessor(config)
results = processor.process_all_forecasts()

# Results will include stats for each custom layer
for date in results['enhanced']:
    for key, stats in results['enhanced'][date].items():
        print(f"{key}: {stats.get('pipelines_features', 0)} pipeline features affected")
```

## AOI Filtering by Region

```python
# Use a shapefile to constrain analysis to a specific region
config = ForecastConfig(
    forecast_dates=["2025-10-07"],
    aoi_shapefile="/path/to/alabama.shp",  # Only analyze Alabama
    output_dir="./alabama_only"
)
```

## Output Structure

```
output/
├── standard/
│   ├── 2025-10-07/
│   │   ├── F0_T39_aois.geojson
│   │   ├── F0_T100_aois.geojson
│   │   ├── F12_T39_aois.geojson
│   │   └── ...
│   ├── 2025-10-08/
│   │   └── ...
│   └── ...
├── enhanced/
│   ├── 2025-10-07/
│   │   └── ...
│   └── ...
├── ensemble_probability/
│   ├── probability_0-5.tif
│   ├── probability_6-39.tif
│   ├── probability_40-50.tif
│   ├── probability_51-100.tif
│   ├── probability_100-254.tif
│   ├── probability_255plus.tif
│   ├── ranked_aois.csv
│   └── ensemble_manifest.json
├── visualizations/
│   ├── aoi_grid_batch_1.png
│   ├── map_2025-10-07.html
│   └── ...
└── experiment_summary.json
```

## Google Colab Example

```python
# Mount Drive
from google.colab import drive
drive.mount('/content/drive')

# Install
!pip install git+https://github.com/NASA-EarthRISE/PIPECAST.git
!pip install herbie-data --quiet
!pip install rasterio

# Run
from pipecast import ForecastConfig, ForecastProcessor

config = ForecastConfig(
    forecast_dates=["2025-10-07", "2025-10-08"],
    fxx_list=[0, 12, 24],
    thresholds=[39, 100, 255],
    weather_dataset="hrrr",
    use_census=True,
    use_watershed=True,
    output_dir="/content/drive/MyDrive/pipecast_output"
)

processor = ForecastProcessor(config)
results = processor.process_all_forecasts()

# Create ensemble products
from pipecast import EnsembleProcessor

ensemble = EnsembleProcessor("/content/drive/MyDrive/pipecast_output")
ensemble.create_ensemble_probabilities()

# Rank by risk
ranked = ensemble.rank_aois_by_probability(
    census_gdf=processor.census_gdf,
    top_n=50
)
```

## API Reference

### ForecastConfig

Configuration class for forecast processing.

**Key Parameters:**
- `forecast_dates`: List of dates (YYYY-MM-DD)
- `fxx_list`: Forecast hours to evaluate
- `thresholds`: Precipitation thresholds in mm
- `weather_dataset`: Dataset to use (HRRR, HRRRAK, etc.)
- `forecast_methods`: ["standard", "enhanced"]
- `use_census`: Include census population data
- `use_watershed`: Include watershed data
- `custom_layers`: Dict of custom layers
- `clip_to_land`: Remove ocean areas
- `output_dir`: Output directory

### ForecastProcessor

Main processing engine.

**Methods:**
- `process_all_forecasts()`: Process all configured forecasts
- `process_single_forecast(date, fxx, threshold, method)`: Process one forecast
- `generate_aois(precip_data, ds, threshold)`: Generate AOIs from data
- `enhance_aois(gdf_aoi)`: Add census/watershed statistics

### EnsembleProcessor

Ensemble probability generator.

**Methods:**
- `create_ensemble_probabilities()`: Create probability GeoTIFFs
- `rank_aois_by_probability(census_gdf, top_n)`: Rank AOIs by risk
- `collect_members()`: Gather all AOI files

### DataManager

Enhanced layer management.

**Methods:**
- `download_census_data(url)`: Download/load census
- `download_watershed_data(url)`: Download/load watershed
- `load_custom_layer(name, filepath)`: Load custom layer
- `clip_to_land(gdf, boundary)`: Clip to land areas

## Preset Configurations

```python
from pipecast.config import PresetConfigs

# Alaska
config = PresetConfigs.alaska_hrrr(dates, output_dir)

# Continental US
config = PresetConfigs.conus_hrrr(dates, output_dir)

# Quick test
config = PresetConfigs.quick_test(date, output_dir)
```

## Workflow Example: Complete Pipeline

```python
from pipecast import ForecastConfig, ForecastProcessor, EnsembleProcessor
from pipecast.visualization import visualize_forecast_outputs

# Step 1: Configure
config = ForecastConfig(
    forecast_dates=["2025-10-07", "2025-10-08", "2025-10-09", "2025-10-10"],
    fxx_list=[0, 4, 8, 12, 16, 20, 24],
    thresholds=[5, 39, 50, 100, 254, 255],
    forecast_methods=["standard", "enhanced"],
    use_census=True,
    use_watershed=True,
    clip_to_land=True,
    output_dir="./complete_run"
)

# Step 2: Process forecasts
print("Processing forecasts...")
processor = ForecastProcessor(config)
results = processor.process_all_forecasts()

# Step 3: Create ensemble products
print("\nCreating ensemble products...")
ensemble = EnsembleProcessor("./complete_run")
prob_paths = ensemble.create_ensemble_probabilities()

# Step 4: Rank by risk
print("\nRanking AOIs by risk...")
ranked = ensemble.rank_aois_by_probability(
    census_gdf=processor.census_gdf,
    top_n=100
)

# Step 5: Visualize
print("\nCreating visualizations...")
visualize_forecast_outputs("./complete_run")

print("\n✅ Complete pipeline finished!")
print(f"Results in: ./complete_run")
print(f"Top 10 highest risk AOIs:")
print(ranked[['bin', 'ensemble_count', 'mean_precip_mm', 'population_affected']].head(10))
```

## Troubleshooting

**Issue: Herbie can't find data**
- Check your date is within HRRR availability
- Verify internet connection
- Try different fxx values

**Issue: Out of memory**
- Process fewer dates at once
- Reduce number of thresholds
- Increase ensemble grid resolution

**Issue: Census/watershed download fails**
- Check Zenodo URLs
- Verify network connection
- Use local files instead

**Issue: No AOIs generated**
- Check thresholds are appropriate for data
- Verify weather data was fetched correctly
- Try lower threshold values

## Performance Tips

1. **Parallel Processing**: Process dates in parallel (future feature)
2. **Caching**: Enhanced layers are cached locally
3. **Grid Resolution**: Increase resolution_deg for faster ensemble
4. **Selective Processing**: Use specific date/threshold lists

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests
4. Submit a pull request

## Citation

If you use PIPECAST in your research:

```
[Citation information to be added]
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**TL;DR:** Use it, modify it, share it - just keep the copyright notice! 🎉

## Contact

- GitHub Issues: [Report issues](https://github.com/NASA-EarthRISE/PIPECAST/issues)
- Documentation: [Full docs](https://pipecast.readthedocs.io) (coming soon)

## Acknowledgments

- NASA-EarthRISE initiative
- NOAA HRRR dataset
- Herbie weather data library
