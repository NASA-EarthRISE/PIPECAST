# 🚀 PIPECAST Weather Forecast Module - Getting Started

## What You Have

A complete Python package that transforms your weather forecast analysis workflow into a reusable, configurable library.

## Before & After

### Before (Your Original Code)
```python
# 500+ lines of manual code
# Hardcoded parameters
# Separate scripts for ensemble
# Manual data management
# Copy/paste to reuse
```

### After (PIPECAST Package)
```python
# 5 lines to run complete pipeline
from pipecast import ForecastConfig, ForecastProcessor

config = ForecastConfig(
    forecast_dates=["2025-10-07", "2025-10-08"],
    weather_dataset="hrrr",
    output_dir="./output"
)

processor = ForecastProcessor(config)
results = processor.process_all_forecasts()
```

## Quick Installation

### On Your Machine

```bash
# Navigate to your repo
cd C:\Users\Mayer\Documents\GitHub\PIPECAST

# Install in development mode
pip install -e .

# Or with visualization extras
pip install -e ".[viz]"

# Test installation
python -c "import pipecast; print(pipecast.__version__)"
```

### In Google Colab

```python
!pip install git+https://github.com/NASA-EarthRISE/PIPECAST.git
```

## Directory Structure

```
pipecast_weather/
├── pipecast/                  # Main package
│   ├── __init__.py           # Package API
│   ├── config.py             # Configuration system
│   ├── data_manager.py       # Enhanced layers
│   ├── forecast_processor.py # Core processing
│   ├── ensemble.py           # Ensemble products
│   └── visualization.py      # Visualization
├── examples/
│   └── complete_example.py   # 7 examples
├── setup.py                  # Installation config
├── requirements.txt          # Dependencies
├── README.md                 # Full documentation
├── QUICKSTART_COLAB.md      # Colab guide
├── PROJECT_SUMMARY.md       # This was created
└── .gitignore               # Git config
```

## Usage Patterns

### Pattern 1: Basic Forecast Processing

```python
from pipecast import ForecastConfig, ForecastProcessor

config = ForecastConfig(
    forecast_dates=["2025-10-07", "2025-10-08"],
    fxx_list=[0, 12, 24],
    thresholds=[39, 100, 255],
    weather_dataset="hrrr",
    output_dir="./output"
)

processor = ForecastProcessor(config)
results = processor.process_all_forecasts()
```

### Pattern 2: With Enhanced Layers

```python
config = ForecastConfig(
    forecast_dates=["2025-10-07", "2025-10-08"],
    forecast_methods=["standard", "enhanced"],
    use_census=True,
    use_watershed=True,
    clip_to_land=True,
    output_dir="./output"
)

processor = ForecastProcessor(config)
results = processor.process_all_forecasts()
```

### Pattern 3: Complete Pipeline

```python
from pipecast import ForecastConfig, ForecastProcessor, EnsembleProcessor

# Process
config = ForecastConfig(
    forecast_dates=["2025-10-07", "2025-10-08", "2025-10-09"],
    use_census=True,
    use_watershed=True,
    output_dir="./output"
)

processor = ForecastProcessor(config)
results = processor.process_all_forecasts()

# Ensemble
ensemble = EnsembleProcessor("./output")
prob_paths = ensemble.create_ensemble_probabilities()

# Rank by risk
ranked = ensemble.rank_aois_by_probability(
    census_gdf=processor.census_gdf,
    top_n=50
)
```

### Pattern 4: Alaska HRRR

```python
from pipecast.config import PresetConfigs

config = PresetConfigs.alaska_hrrr(
    forecast_dates=["2025-10-07", "2025-10-08"],
    output_dir="./alaska_output"
)

config.use_census = True
config.use_watershed = True

processor = ForecastProcessor(config)
results = processor.process_all_forecasts()
```

## Your Original Parameters - Now Dynamic

All your original hardcoded parameters are now configurable:

### Weather Dataset (Dynamic)
```python
# Your original code had:
# H = Herbie(date, model="hrrrak", ...)

# Now:
config = ForecastConfig(
    weather_dataset="hrrrak"  # or "hrrr", "ecmwf", etc.
)
```

### Forecast Dates (User-Defined)
```python
# Your original:
# forecast_dates = ["2025-10-07", "2025-10-08", "2025-10-09", "2025-10-10"]

# Now:
config = ForecastConfig(
    forecast_dates=["2025-10-07", "2025-10-08", "2025-10-09", "2025-10-10"]
)
```

### Thresholds (User-Defined)
```python
# Your original:
# thresholds = [5, 39, 50, 100, 254, 255]

# Now:
config = ForecastConfig(
    thresholds=[5, 39, 50, 100, 254, 255]
)
```

### Ensemble Bins (User-Defined)
```python
# Your original:
# bins = [(0, 5), (6, 39), (40, 50), (51, 100), (100, 254), (255, float('inf'))]

# Now:
config = ForecastConfig(
    threshold_bins=[(0, 5), (6, 39), (40, 50), (51, 100), (100, 254), (255, float('inf'))],
    bin_labels=["0-5", "6-39", "40-50", "51-100", "100-254", "255+"]
)
```

### Enhanced Layers (Toggle On/Off)
```python
# Your original:
# census_gdf = ...
# ws_gdf = ...

# Now:
config = ForecastConfig(
    use_census=True,  # Auto-download from Zenodo
    use_watershed=True,  # Auto-download from Zenodo
    custom_layers={
        "pipelines": "/path/to/pipelines.shp",
        "your_layer": "/path/to/your_data.geojson"
    }
)
```

### Land Clipping (Auto)
```python
# Your original: Manual implementation

# Now:
config = ForecastConfig(
    clip_to_land=True  # Uses census boundary automatically
)
```

## Running Examples

The package includes 7 examples in `examples/complete_example.py`:

```bash
# Run from your PIPECAST directory
python examples/complete_example.py
```

Or run individual examples:

```python
from examples.complete_example import example_complete_pipeline

results, ranked = example_complete_pipeline()
```

## Common Tasks

### Task 1: Replace Your Alaska Script

**Your original script:**
```python
# 150+ lines of manual code for Alaska
```

**New code:**
```python
from pipecast.config import PresetConfigs
from pipecast import ForecastProcessor

config = PresetConfigs.alaska_hrrr(
    ["2025-10-07", "2025-10-08", "2025-10-09"],
    "./alaska_output"
)

processor = ForecastProcessor(config)
results = processor.process_all_forecasts()
```

### Task 2: Custom Warning Levels

```python
config = ForecastConfig(
    thresholds=[10, 25, 50, 75, 100],
    threshold_bins=[
        (0, 10),    # Advisory
        (10, 25),   # Watch
        (25, 50),   # Warning
        (50, 100),  # Severe
        (100, float('inf'))  # Extreme
    ],
    bin_labels=["Advisory", "Watch", "Warning", "Severe", "Extreme"]
)
```

### Task 3: Risk Ranking

```python
from pipecast import EnsembleProcessor

ensemble = EnsembleProcessor("./output")
ranked = ensemble.rank_aois_by_probability(
    census_gdf=census_data,
    top_n=50
)

print(ranked.head(10))
```

## What Gets Produced

```
output/
├── standard/
│   └── [date]/
│       └── F*_T*_aois.geojson       # AOI polygons
├── enhanced/
│   └── [date]/
│       └── F*_T*_aois.geojson       # AOIs with census/watershed
├── ensemble_probability/
│   ├── probability_*.tif             # Probability maps
│   ├── ranked_aois.csv              # Ranked by risk
│   └── ensemble_manifest.json       # Metadata
└── experiment_summary.json           # Complete results
```

## Next Steps

1. **Install**: `pip install -e .`
2. **Test**: Run `examples/complete_example.py`
3. **Read**: Check `README.md` for full documentation
4. **Colab**: See `QUICKSTART_COLAB.md`
5. **Customize**: Modify `ForecastConfig` for your needs

## Files to Read

1. **PROJECT_SUMMARY.md** - Complete overview (this file)
2. **README.md** - Full package documentation
3. **QUICKSTART_COLAB.md** - Colab-specific guide
4. **examples/complete_example.py** - Working examples

## Support

- **Full Documentation**: README.md
- **Quick Start**: This file
- **Colab Guide**: QUICKSTART_COLAB.md
- **Examples**: examples/complete_example.py
- **Code Docs**: Comprehensive docstrings in all modules

## Comparison

| Aspect | Original | Package |
|--------|----------|---------|
| Lines to run | ~500 | ~5 |
| Configuration | Hardcoded | Dynamic |
| Datasets | Manual switch | Enum-based |
| Enhanced layers | Hardcoded paths | Auto-download |
| Ensemble | Separate script | Integrated |
| Visualization | Manual | Built-in |
| Reusability | Copy/paste | pip install |

## Tips

1. **Start Simple**: Try Pattern 1 first
2. **Add Features**: Gradually enable enhanced mode
3. **Custom Bins**: Define your warning levels
4. **Visualize**: Use built-in visualization
5. **Colab**: Full support for cloud processing

## Troubleshooting

**Import Error**: Make sure you ran `pip install -e .`
**Herbie Error**: Check date is within HRRR availability
**Memory Error**: Process fewer dates at once
**Download Error**: Check internet connection for Zenodo

## Ready to Start!

```python
from pipecast import ForecastConfig, ForecastProcessor

config = ForecastConfig(
    forecast_dates=["2025-10-07"],
    weather_dataset="hrrr",
    output_dir="./test_output"
)

processor = ForecastProcessor(config)
results = processor.process_all_forecasts()

print("✅ Done! Check ./test_output")
```

---

**Your 500+ lines of code → 5 lines with PIPECAST! 🎉**
