"""
PIPECAST Weather Forecast Analysis - Complete Example

This script demonstrates the full workflow from forecast processing
to ensemble generation and risk ranking.
"""

from datetime import datetime
from pipecast import (
    ForecastConfig,
    ForecastProcessor,
    EnsembleProcessor,
    WeatherDataset
)
from pipecast.config import PresetConfigs
from pipecast.visualization import visualize_forecast_outputs


# =============================================================================
# EXAMPLE 1: Basic Forecast Processing (Standard Mode)
# =============================================================================

def example_basic_processing():
    """Basic forecast processing without enhanced layers."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Forecast Processing")
    print("="*70)
    
    config = ForecastConfig(
        forecast_dates=["2025-10-07", "2025-10-08"],
        fxx_list=[0, 12, 24],
        thresholds=[39, 100, 255],
        forecast_methods=["standard"],
        use_census=False,
        use_watershed=False,
        weather_dataset=WeatherDataset.HRRR,
        output_dir="./output/example1_basic"
    )
    
    processor = ForecastProcessor(config)
    results = processor.process_all_forecasts()
    
    print("\n✓ Example 1 complete!")
    return results


# =============================================================================
# EXAMPLE 2: Alaska HRRR with Enhanced Layers
# =============================================================================

def example_alaska_enhanced():
    """Process Alaska HRRR with census and watershed data."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Alaska HRRR with Enhanced Layers")
    print("="*70)
    
    config = PresetConfigs.alaska_hrrr(
        forecast_dates=["2025-10-07", "2025-10-08", "2025-10-09", "2025-10-10"],
        output_dir="./output/example2_alaska"
    )
    
    # Enable enhanced mode
    config.forecast_methods = ["standard", "enhanced"]
    config.use_census = True
    config.use_watershed = True
    config.fxx_list = [0, 4, 8, 12, 16, 20, 24]
    config.thresholds = [5, 39, 50, 100, 254, 255]
    
    processor = ForecastProcessor(config)
    results = processor.process_all_forecasts()
    
    print("\n✓ Example 2 complete!")
    return results


# =============================================================================
# EXAMPLE 3: Custom Threshold Bins for Warning Levels
# =============================================================================

def example_custom_thresholds():
    """Use custom threshold bins for specific warning levels."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Custom Threshold Bins")
    print("="*70)
    
    config = ForecastConfig(
        forecast_dates=["2025-10-07"],
        fxx_list=[0, 12, 24],
        
        # Custom thresholds matching your warning system
        thresholds=[10, 25, 50, 75, 100],
        
        # Custom bins for ensemble
        threshold_bins=[
            (0, 10),      # Advisory
            (10, 25),     # Watch
            (25, 50),     # Warning
            (50, 100),    # High Warning
            (100, float('inf'))  # Extreme Warning
        ],
        bin_labels=["Advisory", "Watch", "Warning", "High", "Extreme"],
        
        forecast_methods=["enhanced"],
        use_census=True,
        weather_dataset=WeatherDataset.HRRR,
        output_dir="./output/example3_custom_bins"
    )
    
    processor = ForecastProcessor(config)
    results = processor.process_all_forecasts()
    
    print("\n✓ Example 3 complete!")
    return results


# =============================================================================
# EXAMPLE 4: Complete Pipeline with Ensemble and Ranking
# =============================================================================

def example_complete_pipeline():
    """Run complete workflow: process, ensemble, rank, visualize."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Complete Pipeline")
    print("="*70)
    
    # Step 1: Configure
    config = ForecastConfig(
        forecast_dates=["2025-10-07", "2025-10-08", "2025-10-09"],
        fxx_list=[0, 6, 12, 18, 24],
        thresholds=[5, 39, 50, 100, 254, 255],
        forecast_methods=["standard", "enhanced"],
        use_census=True,
        use_watershed=True,
        clip_to_land=True,
        weather_dataset=WeatherDataset.HRRR,
        output_dir="./output/example4_complete"
    )
    
    # Step 2: Process forecasts
    print("\n>>> Step 1: Processing forecasts...")
    processor = ForecastProcessor(config)
    results = processor.process_all_forecasts()
    
    # Step 3: Create ensemble products
    print("\n>>> Step 2: Creating ensemble products...")
    ensemble = EnsembleProcessor(
        config.output_dir,
        bins=config.threshold_bins,
        bin_labels=config.bin_labels,
        resolution_deg=0.05
    )
    prob_paths = ensemble.create_ensemble_probabilities()
    
    # Step 4: Rank AOIs by risk
    print("\n>>> Step 3: Ranking AOIs by risk...")
    ranked = ensemble.rank_aois_by_probability(
        census_gdf=processor.census_gdf,
        top_n=100
    )
    
    # Step 5: Visualize
    print("\n>>> Step 4: Creating visualizations...")
    visualize_forecast_outputs(config.output_dir)
    
    print("\n" + "="*70)
    print("✓ COMPLETE PIPELINE FINISHED!")
    print("="*70)
    print(f"\nResults saved to: {config.output_dir}")
    print(f"\nTop 10 Highest Risk AOIs:")
    print("-"*70)
    
    display_cols = ['bin', 'ensemble_count', 'mean_precip_mm', 'area_deg2']
    if 'population_affected' in ranked.columns:
        display_cols.append('population_affected')
    
    print(ranked[display_cols].head(10).to_string(index=False))
    print("="*70)
    
    return results, ranked


# =============================================================================
# EXAMPLE 5: Multiple Regions Comparison
# =============================================================================

def example_multi_region():
    """Process multiple regions and compare."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Multi-Region Comparison")
    print("="*70)
    
    regions = {
        "alaska": PresetConfigs.alaska_hrrr(
            ["2025-10-07", "2025-10-08"],
            "./output/example5_alaska"
        ),
        "conus": PresetConfigs.conus_hrrr(
            ["2025-10-07", "2025-10-08"],
            "./output/example5_conus"
        )
    }
    
    all_results = {}
    
    for region_name, config in regions.items():
        print(f"\n>>> Processing {region_name.upper()}...")
        config.fxx_list = [0, 12, 24]
        config.thresholds = [39, 100, 255]
        config.use_census = True
        
        processor = ForecastProcessor(config)
        all_results[region_name] = processor.process_all_forecasts()
    
    print("\n✓ Example 5 complete!")
    return all_results


# =============================================================================
# EXAMPLE 6: Single Forecast Quick Analysis
# =============================================================================

def example_quick_analysis():
    """Quick analysis of a single forecast."""
    print("\n" + "="*70)
    print("EXAMPLE 6: Quick Single Forecast Analysis")
    print("="*70)
    
    from pipecast import generate_aois
    
    # Generate AOIs for a single forecast
    date = datetime(2025, 10, 7)
    gdf = generate_aois(
        date=date,
        fxx=12,
        threshold=50.0,
        weather_dataset=WeatherDataset.HRRR,
        output_dir="./output/example6_quick"
    )
    
    print(f"\nGenerated {len(gdf)} AOIs")
    if not gdf.empty:
        print(f"Mean precipitation: {gdf['mean_precip_mm'].mean():.1f} mm")
        print(f"Max precipitation: {gdf['max_precip_mm'].max():.1f} mm")
        print(f"Total area: {gdf['area_deg2'].sum():.2f} deg²")
    
    print("\n✓ Example 6 complete!")
    return gdf


# =============================================================================
# EXAMPLE 7: Custom Enhanced Layers
# =============================================================================

def example_custom_layers():
    """Use custom enhanced layers for specialized analysis."""
    print("\n" + "="*70)
    print("EXAMPLE 7: Custom Enhanced Layers")
    print("="*70)
    
    config = ForecastConfig(
        forecast_dates=["2025-10-07"],
        fxx_list=[0, 12, 24],
        thresholds=[39, 100, 255],
        forecast_methods=["enhanced"],
        
        # Standard layers
        use_census=True,
        use_watershed=True,
        
        # Add your custom layers
        custom_layers={
            # Example paths - replace with your actual data
            # "pipelines": "/path/to/pipeline_network.shp",
            # "infrastructure": "/path/to/critical_infrastructure.geojson",
            # "evacuation_routes": "/path/to/evacuation_routes.shp"
        },
        
        weather_dataset=WeatherDataset.HRRR,
        output_dir="./output/example7_custom_layers"
    )
    
    # Note: This will only work if you have the custom layer files
    if config.custom_layers:
        processor = ForecastProcessor(config)
        results = processor.process_all_forecasts()
        
        # Check custom layer statistics
        for date in results['enhanced']:
            for key, stats in results['enhanced'][date].items():
                print(f"\n{key}:")
                for layer_key, value in stats.items():
                    if 'custom' in layer_key:
                        print(f"  {layer_key}: {value}")
    else:
        print("No custom layers configured - skipping example")
        print("Add paths to your custom shapefiles/geojson files to use this feature")
    
    print("\n✓ Example 7 complete!")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    print("\n" + "#"*70)
    print("PIPECAST WEATHER FORECAST ANALYSIS - EXAMPLES")
    print("#"*70)
    print("\nThis script demonstrates various use cases for PIPECAST.")
    print("Comment/uncomment examples below to run specific workflows.")
    print("#"*70)
    
    # Run examples (uncomment the ones you want to try)
    
    # Example 1: Basic processing
    # results1 = example_basic_processing()
    
    # Example 2: Alaska with enhanced layers
    # results2 = example_alaska_enhanced()
    
    # Example 3: Custom threshold bins
    # results3 = example_custom_thresholds()
    
    # Example 4: Complete pipeline (RECOMMENDED FOR FIRST RUN)
    results4 = example_complete_pipeline()
    
    # Example 5: Multi-region comparison
    # results5 = example_multi_region()
    
    # Example 6: Quick single forecast
    # gdf6 = example_quick_analysis()
    
    # Example 7: Custom layers
    # example_custom_layers()
    
    print("\n" + "#"*70)
    print("✅ ALL EXAMPLES COMPLETE!")
    print("#"*70)
    print("\nCheck the ./output/ directory for results.")
    print("Each example creates its own subdirectory with outputs.")
