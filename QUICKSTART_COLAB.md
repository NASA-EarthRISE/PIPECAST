# PIPECAST Quick Start for Google Colab

Step-by-step guide for running PIPECAST weather forecast analysis in Google Colab.

## Setup (Run Once)

```python
# 1. Mount Google Drive
from google.colab import drive
drive.mount('/content/drive')

# 2. Install dependencies
!pip install git+https://github.com/NASA-EarthRISE/PIPECAST.git
!pip install herbie-data --quiet
!pip install rasterio --quiet

# 3. Verify installation
import pipecast
print(f"✓ PIPECAST version: {pipecast.__version__}")
```

## Example 1: Basic Forecast Processing

```python
from pipecast import ForecastConfig, ForecastProcessor

# Configure
config = ForecastConfig(
    forecast_dates=["2025-10-07", "2025-10-08"],
    fxx_list=[0, 12, 24],
    thresholds=[39, 100, 255],
    weather_dataset="hrrr",  # or "hrrrak" for Alaska
    forecast_methods=["standard"],
    output_dir="/content/drive/MyDrive/pipecast_output"
)

# Process
processor = ForecastProcessor(config)
results = processor.process_all_forecasts()

print("✅ Processing complete!")
```

## Example 2: With Enhanced Layers (Census + Watershed)

```python
from pipecast import ForecastConfig, ForecastProcessor

config = ForecastConfig(
    forecast_dates=["2025-10-07", "2025-10-08", "2025-10-09"],
    fxx_list=[0, 6, 12, 18, 24],
    thresholds=[5, 39, 50, 100, 254, 255],
    forecast_methods=["standard", "enhanced"],
    
    # Enhanced analysis
    use_census=True,
    use_watershed=True,
    clip_to_land=True,
    
    weather_dataset="hrrr",
    output_dir="/content/drive/MyDrive/pipecast_enhanced"
)

processor = ForecastProcessor(config)
results = processor.process_all_forecasts()

# View summary
import json
print(json.dumps(results["enhanced"]["2025-10-07"], indent=2))
```

## Example 3: Complete Pipeline (Process + Ensemble + Rank)

```python
from pipecast import ForecastConfig, ForecastProcessor, EnsembleProcessor

# Step 1: Configure and process
config = ForecastConfig(
    forecast_dates=["2025-10-07", "2025-10-08", "2025-10-09", "2025-10-10"],
    fxx_list=[0, 4, 8, 12, 16, 20, 24],
    thresholds=[5, 39, 50, 100, 254, 255],
    forecast_methods=["standard", "enhanced"],
    use_census=True,
    use_watershed=True,
    clip_to_land=True,
    weather_dataset="hrrr",
    output_dir="/content/drive/MyDrive/pipecast_complete"
)

print("🚀 Step 1: Processing forecasts...")
processor = ForecastProcessor(config)
results = processor.process_all_forecasts()

# Step 2: Create ensemble probability products
print("\n🎲 Step 2: Creating ensemble products...")
ensemble = EnsembleProcessor(config.output_dir)
prob_paths = ensemble.create_ensemble_probabilities()

# Step 3: Rank AOIs by risk
print("\n📊 Step 3: Ranking AOIs by population risk...")
ranked = ensemble.rank_aois_by_probability(
    census_gdf=processor.census_gdf,
    top_n=50
)

# Display top 10 highest risk areas
print("\n" + "="*70)
print("TOP 10 HIGHEST RISK AOIs")
print("="*70)
print(ranked[['bin', 'ensemble_count', 'mean_precip_mm', 'population_affected']].head(10))

# Save ranked list
ranked.to_csv(f"{config.output_dir}/top_50_risk_aois.csv", index=False)
print(f"\n✅ Saved top 50 risk AOIs to CSV")
```

## Example 4: Alaska HRRR

```python
from pipecast.config import PresetConfigs
from pipecast import ForecastProcessor, EnsembleProcessor

# Use Alaska preset
config = PresetConfigs.alaska_hrrr(
    forecast_dates=["2025-10-07", "2025-10-08", "2025-10-09", "2025-10-10"],
    output_dir="/content/drive/MyDrive/pipecast_alaska"
)

# Enable enhanced mode
config.forecast_methods = ["standard", "enhanced"]
config.use_census = True
config.use_watershed = True

# Process
processor = ForecastProcessor(config)
results = processor.process_all_forecasts()

# Create ensemble
ensemble = EnsembleProcessor(config.output_dir)
prob_paths = ensemble.create_ensemble_probabilities()
ranked = ensemble.rank_aois_by_probability(processor.census_gdf, top_n=50)

print("✅ Alaska analysis complete!")
```

## Example 5: Custom Threshold Bins (Warning Levels)

```python
from pipecast import ForecastConfig, ForecastProcessor

# Define your organization's warning level thresholds
config = ForecastConfig(
    forecast_dates=["2025-10-07", "2025-10-08"],
    fxx_list=[0, 12, 24],
    
    # Thresholds matching your warning system
    thresholds=[10, 25, 50, 75, 100, 150],
    
    # Bins for ensemble probability
    threshold_bins=[
        (0, 10),      # Green - Advisory
        (10, 25),     # Yellow - Watch
        (25, 50),     # Orange - Warning
        (50, 100),    # Red - Severe Warning
        (100, float('inf'))  # Purple - Extreme
    ],
    bin_labels=["Advisory", "Watch", "Warning", "Severe", "Extreme"],
    
    forecast_methods=["enhanced"],
    use_census=True,
    weather_dataset="hrrr",
    output_dir="/content/drive/MyDrive/pipecast_warnings"
)

processor = ForecastProcessor(config)
results = processor.process_all_forecasts()

print("✅ Custom warning levels processed!")
```

## Visualization

```python
from pipecast.visualization import visualize_forecast_outputs

# Create all standard visualizations
visualize_forecast_outputs("/content/drive/MyDrive/pipecast_output")

# Or create interactive map for specific date
from pipecast.visualization import create_interactive_map
from pathlib import Path

m = create_interactive_map(
    root_dir=Path("/content/drive/MyDrive/pipecast_output"),
    target_date="2025-10-07",
    output_path=Path("/content/drive/MyDrive/pipecast_output/map_20251007.html"),
    center=[39.0, -98.0],  # US center
    zoom_start=5
)

# Display in Colab
m
```

## Download Ensemble Probability Maps

```python
from google.colab import files
import os

# Download the probability GeoTIFFs
output_dir = "/content/drive/MyDrive/pipecast_output/ensemble_probability"

for file in os.listdir(output_dir):
    if file.endswith('.tif'):
        filepath = os.path.join(output_dir, file)
        files.download(filepath)
        print(f"Downloaded: {file}")
```

## View Results Summary

```python
import json
import pandas as pd

# Load experiment summary
with open("/content/drive/MyDrive/pipecast_output/experiment_summary.json", "r") as f:
    summary = json.load(f)

# Convert to DataFrame for easy viewing
all_stats = []
for method in summary:
    for date in summary[method]:
        for key, stats in summary[method][date].items():
            if 'error' not in stats:
                stats['method'] = method
                stats['date'] = date
                stats['key'] = key
                all_stats.append(stats)

df = pd.DataFrame(all_stats)
print(df.head(20))

# Summary by date and method
summary_df = df.groupby(['date', 'method']).agg({
    'num_aois': 'sum',
    'mean_precip_over_aois': 'mean',
    'census_pop_sum': 'sum'
}).round(2)

print("\n" + "="*70)
print("SUMMARY BY DATE AND METHOD")
print("="*70)
print(summary_df)
```

## Tips for Colab

1. **Save to Drive**: Always use `/content/drive/MyDrive/` for outputs
2. **Long Runs**: Colab may disconnect - save frequently
3. **Memory**: If you get memory errors, process fewer dates
4. **GPU**: Not needed for this workflow
5. **Runtime**: Expect 5-15 minutes per day of forecasts

## Troubleshooting

**"Herbie cannot find data"**
- Check date is valid (within HRRR availability)
- Try different fxx values
- Verify internet connection

**"Out of memory"**
- Process fewer dates at once
- Reduce number of thresholds
- Skip ensemble generation

**"Census/watershed download fails"**
- Check Zenodo is accessible
- Wait and retry
- Use local files if you have them

## What You Get

After running, your Drive will contain:

```
MyDrive/pipecast_output/
├── standard/
│   └── [date]/
│       └── F*_T*_aois.geojson
├── enhanced/
│   └── [date]/
│       └── F*_T*_aois.geojson
├── ensemble_probability/
│   ├── probability_*.tif
│   ├── ranked_aois.csv
│   └── ensemble_manifest.json
├── visualizations/
│   ├── aoi_grid_*.png
│   └── map_*.html
└── experiment_summary.json
```

## Next Steps

1. Download GeoTIFFs to your GIS software
2. View interactive HTML maps
3. Analyze ranked_aois.csv
4. Integrate with your workflows

## Full Template

```python
# Complete template for copy-paste

from google.colab import drive
drive.mount('/content/drive')

!pip install git+https://github.com/NASA-EarthRISE/PIPECAST.git
!pip install herbie-data rasterio --quiet

from pipecast import ForecastConfig, ForecastProcessor, EnsembleProcessor

config = ForecastConfig(
    forecast_dates=["2025-10-07", "2025-10-08", "2025-10-09"],
    fxx_list=[0, 12, 24],
    thresholds=[39, 100, 255],
    forecast_methods=["standard", "enhanced"],
    use_census=True,
    use_watershed=True,
    weather_dataset="hrrr",
    output_dir="/content/drive/MyDrive/pipecast_output"
)

processor = ForecastProcessor(config)
results = processor.process_all_forecasts()

ensemble = EnsembleProcessor(config.output_dir)
prob_paths = ensemble.create_ensemble_probabilities()
ranked = ensemble.rank_aois_by_probability(processor.census_gdf, top_n=50)

print("✅ Complete!")
print(f"Results in: {config.output_dir}")
```
