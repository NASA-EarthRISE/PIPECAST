"""
Main forecast processing module for PIPECAST.

Handles weather data fetching, AOI generation, and enhanced analysis.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import warnings

import numpy as np
import geopandas as gpd
import rasterio
from rasterio import features
from rasterio.transform import from_bounds
from scipy.ndimage import label
from shapely.geometry import shape
from herbie import Herbie

from .config import ForecastConfig, WeatherDataset
from .data_manager import DataManager


class ForecastProcessor:
    """
    Main class for processing weather forecasts and generating AOIs.
    
    This processor:
    1. Fetches weather forecast data (HRRR, ECMWF, etc.)
    2. Identifies Areas of Interest (AOIs) based on thresholds
    3. Optionally enhances with census/watershed data
    4. Saves results and generates summaries
    """
    
    def __init__(self, config: ForecastConfig):
        """
        Initialize ForecastProcessor.
        
        Parameters
        ----------
        config : ForecastConfig
            Configuration object
        """
        self.config = config
        self.data_manager = DataManager()
        
        # Create output directory
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Results storage
        self.results: Dict = {}
        
        # Enhanced layers
        self.census_gdf: Optional[gpd.GeoDataFrame] = None
        self.watershed_gdf: Optional[gpd.GeoDataFrame] = None
        self.custom_layers: Dict[str, gpd.GeoDataFrame] = {}
        self.land_boundary: Optional[gpd.GeoDataFrame] = None
        
        # Load enhanced layers if needed
        self._load_enhanced_layers()
    
    def _load_enhanced_layers(self):
        """Load enhanced layers based on configuration."""
        if not any([
            self.config.use_census,
            self.config.use_watershed,
            self.config.custom_layers
        ]):
            return
        
        print("\n" + "="*70)
        print("LOADING ENHANCED LAYERS")
        print("="*70)
        
        # Load census
        if self.config.use_census:
            try:
                self.census_gdf = self.data_manager.download_census_data(
                    self.config.census_zenodo_url
                )
                # Use census as land boundary for clipping
                self.land_boundary = self.census_gdf
            except Exception as e:
                warnings.warn(f"Failed to load census data: {e}")
        
        # Load watershed
        if self.config.use_watershed:
            try:
                self.watershed_gdf = self.data_manager.download_watershed_data(
                    self.config.watershed_zenodo_url
                )
            except Exception as e:
                warnings.warn(f"Failed to load watershed data: {e}")
        
        # Load custom layers
        if self.config.custom_layers:
            for name, filepath in self.config.custom_layers.items():
                try:
                    self.custom_layers[name] = self.data_manager.load_custom_layer(
                        name, filepath
                    )
                except Exception as e:
                    warnings.warn(f"Failed to load custom layer '{name}': {e}")
        
        print("="*70 + "\n")
    
    def fetch_forecast_data(self, date: datetime, fxx: int) -> Tuple[np.ndarray, any]:
        """
        Fetch weather forecast data using Herbie.
        
        Parameters
        ----------
        date : datetime
            Forecast initialization date
        fxx : int
            Forecast hour
            
        Returns
        -------
        tuple
            (precipitation_data, xarray_dataset)
        """
        print(f"  Fetching {self.config.weather_dataset.value} data for F{fxx:02d}...")
        
        try:
            H = Herbie(
                date,
                model=self.config.get_model_name(),
                product=self.config.product,
                fxx=fxx,
                verbose=False
            )
            
            ds = H.xarray(self.config.variable)
            precip_data = ds[self.config.variable_name].values
            
            return precip_data, ds
            
        except Exception as e:
            raise RuntimeError(f"Failed to fetch forecast data: {e}")
    
    def generate_aois(
        self,
        precip_data: np.ndarray,
        ds: any,
        threshold: float,
        min_area: Optional[float] = None
    ) -> gpd.GeoDataFrame:
        """
        Generate Areas of Interest from precipitation data.
        
        Parameters
        ----------
        precip_data : np.ndarray
            Precipitation data array
        ds : xarray.Dataset
            Xarray dataset with coordinate info
        threshold : float
            Precipitation threshold in mm
        min_area : float, optional
            Minimum area for AOI polygons
            
        Returns
        -------
        gpd.GeoDataFrame
            AOIs as GeoDataFrame
        """
        if min_area is None:
            min_area = self.config.min_aoi_area
        
        # Create binary mask
        mask = precip_data > threshold
        
        # Label connected regions
        labeled, num_features = label(mask)
        
        if num_features == 0:
            # No AOIs found
            return gpd.GeoDataFrame(
                columns=['id', 'mean_precip_mm', 'max_precip_mm', 'area_deg2'],
                geometry=[],
                crs=self.config.target_crs
            )
        
        # # Build transform for geolocation
        # transform = from_bounds(
        #     float(ds.longitude.min()),
        #     float(ds.latitude.min()),
        #     float(ds.longitude.max()),
        #     float(ds.latitude.max()),
        #     ds.dims["x"],
        #     ds.dims["y"]
        # )

        # Build transform for geolocation
        # CRITICAL: Convert HRRR longitude from 0-360 to -180-180
        lon_min = float(ds.longitude.min())
        lon_max = float(ds.longitude.max())
        lat_min = float(ds.latitude.min())
        lat_max = float(ds.latitude.max())

        # Convert longitude if in 0-360 range
        if lon_min > 180:
            lon_min -= 360
        if lon_max > 180:
            lon_max -= 360

        print(f"  Longitude range: {lon_min:.2f} to {lon_max:.2f}")
        print(f"  Latitude range: {lat_min:.2f} to {lat_max:.2f}")

        transform = from_bounds(
            lon_min, lat_min, lon_max, lat_max,
            ds.dims["x"],
            ds.dims["y"]
        )

        # # Build transform for geolocation
        # # Note: HRRR uses (lon, lat) order, rasterio expects (west, south, east, north)
        # lon_min = float(ds.longitude.min())
        # lon_max = float(ds.longitude.max())
        # lat_min = float(ds.latitude.min())
        # lat_max = float(ds.latitude.max())

        # transform = from_bounds(
        #     lon_min, lat_min, lon_max, lat_max,
        #     ds.dims["x"],
        #     ds.dims["y"]
        # )
                
        # Convert labeled regions to shapes
        shapes = list(features.shapes(
            labeled.astype(np.int16),
            mask=mask,
            transform=transform
        ))
        
        # Extract polygons and compute statistics
        polygons = []
        ids = []
        mean_precips = []
        max_precips = []
        areas = []
        
        for geom, label_id in shapes:
            if label_id == 0:
                continue
            
            poly = shape(geom)
            
            # Filter by area
            if poly.area < min_area:
                continue
            
            # Compute statistics for this AOI
            aoi_mask = labeled == label_id
            mean_precip = float(precip_data[aoi_mask].mean())
            max_precip = float(precip_data[aoi_mask].max())
            
            polygons.append(poly)
            ids.append(int(label_id))
            mean_precips.append(mean_precip)
            max_precips.append(max_precip)
            areas.append(poly.area)
        
        # Create GeoDataFrame
        gdf_aoi = gpd.GeoDataFrame({
            'id': ids,
            'mean_precip_mm': mean_precips,
            'max_precip_mm': max_precips,
            'area_deg2': areas
        }, geometry=polygons, crs=self.config.target_crs)
        
        return gdf_aoi
    
    def enhance_aois(
        self,
        gdf_aoi: gpd.GeoDataFrame
    ) -> Dict[str, any]:
        """
        Enhance AOIs with census, watershed, and custom layer data.
        
        Parameters
        ----------
        gdf_aoi : gpd.GeoDataFrame
            AOIs to enhance
            
        Returns
        -------
        dict
            Enhancement statistics
        """
        stats = {}
        
        # Census intersection
        if self.census_gdf is not None and not gdf_aoi.empty:
            try:
                census_intersect = gpd.overlay(
                    gdf_aoi,
                    self.census_gdf,
                    how='intersection'
                )
                
                # Sum population (adjust column name as needed)
                pop_columns = ['U7H001', 'population', 'POP', 'POPULATION']
                pop_col = None
                for col in pop_columns:
                    if col in census_intersect.columns:
                        pop_col = col
                        break
                
                if pop_col:
                    stats['census_pop_sum'] = int(census_intersect[pop_col].sum())
                else:
                    stats['census_pop_sum'] = 0
                    warnings.warn("No population column found in census data")
                
                stats['census_features'] = len(census_intersect)
                
            except Exception as e:
                warnings.warn(f"Census intersection failed: {e}")
                stats['census_pop_sum'] = 0
                stats['census_features'] = 0
        else:
            stats['census_pop_sum'] = 0
            stats['census_features'] = 0
        
        # Watershed intersection
        if self.watershed_gdf is not None and not gdf_aoi.empty:
            try:
                ws_intersect = gpd.overlay(
                    gdf_aoi,
                    self.watershed_gdf,
                    how='intersection'
                )
                
                # Sum watershed area
                stats['watershed_area_sum'] = float(ws_intersect.geometry.area.sum())
                stats['watershed_features'] = len(ws_intersect)
                
            except Exception as e:
                warnings.warn(f"Watershed intersection failed: {e}")
                stats['watershed_area_sum'] = 0
                stats['watershed_features'] = 0
        else:
            stats['watershed_area_sum'] = 0
            stats['watershed_features'] = 0
        
        # Custom layer intersections
        for layer_name, layer_gdf in self.custom_layers.items():
            if not gdf_aoi.empty:
                try:
                    custom_intersect = gpd.overlay(
                        gdf_aoi,
                        layer_gdf,
                        how='intersection'
                    )
                    
                    stats[f'{layer_name}_features'] = len(custom_intersect)
                    stats[f'{layer_name}_area_sum'] = float(custom_intersect.geometry.area.sum())
                    
                except Exception as e:
                    warnings.warn(f"Custom layer '{layer_name}' intersection failed: {e}")
                    stats[f'{layer_name}_features'] = 0
                    stats[f'{layer_name}_area_sum'] = 0
            else:
                stats[f'{layer_name}_features'] = 0
                stats[f'{layer_name}_area_sum'] = 0
        
        return stats
    
    def process_single_forecast(
        self,
        date: datetime,
        fxx: int,
        threshold: float,
        method: str
    ) -> Tuple[gpd.GeoDataFrame, Dict]:
        """
        Process a single forecast (one date, one fxx, one threshold).
        
        Parameters
        ----------
        date : datetime
            Forecast date
        fxx : int
            Forecast hour
        threshold : float
            Precipitation threshold
        method : str
            Processing method ('standard' or 'enhanced')
            
        Returns
        -------
        tuple
            (gdf_aoi, statistics_dict)
        """
        # Fetch data
        precip_data, ds = self.fetch_forecast_data(date, fxx)
        
        # Generate AOIs
        gdf_aoi = self.generate_aois(precip_data, ds, threshold)
        
        # Clip to land if requested
        if self.config.clip_to_land and self.land_boundary is not None and not gdf_aoi.empty:
            gdf_aoi = self.data_manager.clip_to_land(gdf_aoi, self.land_boundary)
        
        # Statistics
        stats = {
            'forecast_hour': fxx,
            'threshold_mm': threshold,
            'num_aois': len(gdf_aoi),
            'mean_precip_over_aois': float(gdf_aoi['mean_precip_mm'].mean()) if not gdf_aoi.empty else 0,
            'max_precip_over_aois': float(gdf_aoi['max_precip_mm'].max()) if not gdf_aoi.empty else 0,
            'total_area_deg2': float(gdf_aoi['area_deg2'].sum()) if not gdf_aoi.empty else 0
        }
        
        # Enhanced mode: add census/watershed/custom stats
        if method == "enhanced":
            enhancement_stats = self.enhance_aois(gdf_aoi)
            stats.update(enhancement_stats)
        
        return gdf_aoi, stats
    
    def process_all_forecasts(self) -> Dict:
        """
        Process all forecasts according to configuration.
        
        Returns
        -------
        dict
            Complete results dictionary
        """
        print("\n" + "#"*70)
        print("PIPECAST FORECAST PROCESSING")
        print("#"*70)
        print(f"Weather Dataset: {self.config.weather_dataset.value}")
        print(f"Dates: {len(self.config.forecast_dates)}")
        print(f"Forecast Hours: {self.config.fxx_list}")
        print(f"Thresholds: {self.config.thresholds}")
        print(f"Methods: {self.config.forecast_methods}")
        print(f"Output: {self.output_dir}")
        print("#"*70 + "\n")
        
        # Initialize results structure
        for method in self.config.forecast_methods:
            self.results[method] = {}
        
        # Loop over methods
        for method in self.config.forecast_methods:
            method_dir = self.output_dir / method
            method_dir.mkdir(exist_ok=True)
            
            print(f"\n{'='*70}")
            print(f"METHOD: {method.upper()}")
            print(f"{'='*70}")
            
            # Loop over dates
            for date_str in self.config.forecast_dates:
                date = datetime.strptime(date_str, "%Y-%m-%d")
                date_dir = method_dir / date_str
                date_dir.mkdir(exist_ok=True)
                
                self.results[method][date_str] = {}
                
                print(f"\n--- Date: {date_str} ---")
                
                # Loop over forecast hours
                for fxx in self.config.fxx_list:
                    print(f"\n  Forecast Hour: F{fxx:02d}")
                    
                    # Loop over thresholds
                    for threshold in self.config.thresholds:
                        try:
                            # Process this forecast
                            gdf_aoi, stats = self.process_single_forecast(
                                date, fxx, threshold, method
                            )
                            
                            # Store statistics
                            key = f"F{fxx}_T{int(threshold)}"
                            self.results[method][date_str][key] = stats
                            
                            # Save AOI GeoJSON
                            if self.config.save_aois:
                                out_gdf_path = date_dir / f"{key}_aois.geojson"
                                gdf_aoi.to_file(out_gdf_path, driver="GeoJSON")
                            
                            print(f"    T{int(threshold):3d}mm: {len(gdf_aoi):3d} AOIs | "
                                  f"Mean precip: {stats['mean_precip_over_aois']:.1f}mm")
                            
                        except Exception as e:
                            print(f"    T{int(threshold):3d}mm: ERROR - {e}")
                            self.results[method][date_str][f"F{fxx}_T{int(threshold)}"] = {
                                'error': str(e)
                            }
        
        # Save summary
        self.save_summary()
        
        print("\n" + "#"*70)
        print("✓ PROCESSING COMPLETE")
        print("#"*70 + "\n")
        
        return self.results
    
    def save_summary(self):
        """Save results summary to JSON."""
        summary_path = self.output_dir / "experiment_summary.json"
        
        with open(summary_path, "w") as f:
            json.dump(self.results, f, indent=4)
        
        print(f"\n✓ Summary saved: {summary_path}")
    
    def get_aoi_files(self) -> List[Path]:
        """
        Get list of all generated AOI GeoJSON files.
        
        Returns
        -------
        list
            List of Path objects
        """
        aoi_files = []
        
        for method in self.config.forecast_methods:
            method_dir = self.output_dir / method
            if not method_dir.exists():
                continue
            
            for date_str in self.config.forecast_dates:
                date_dir = method_dir / date_str
                if not date_dir.exists():
                    continue
                
                aoi_files.extend(date_dir.glob("*_aois.geojson"))
        
        return sorted(aoi_files)


# Convenience functions
def process_forecast_dates(
    config: ForecastConfig
) -> Dict:
    """
    Process forecasts for all dates in configuration.
    
    Parameters
    ----------
    config : ForecastConfig
        Configuration object
        
    Returns
    -------
    dict
        Results dictionary
    """
    processor = ForecastProcessor(config)
    return processor.process_all_forecasts()


def generate_aois(
    date: datetime,
    fxx: int,
    threshold: float,
    weather_dataset: WeatherDataset = WeatherDataset.HRRR,
    output_dir: str = "./output"
) -> gpd.GeoDataFrame:
    """
    Quick function to generate AOIs for a single forecast.
    
    Parameters
    ----------
    date : datetime
        Forecast date
    fxx : int
        Forecast hour
    threshold : float
        Precipitation threshold
    weather_dataset : WeatherDataset
        Weather dataset to use
    output_dir : str
        Output directory
        
    Returns
    -------
    gpd.GeoDataFrame
        Generated AOIs
    """
    config = ForecastConfig(
        forecast_dates=[date.strftime("%Y-%m-%d")],
        fxx_list=[fxx],
        thresholds=[threshold],
        weather_dataset=weather_dataset,
        forecast_methods=["standard"],
        use_census=False,
        use_watershed=False,
        save_aois=False,
        output_dir=output_dir
    )
    
    processor = ForecastProcessor(config)
    gdf_aoi, _ = processor.process_single_forecast(date, fxx, threshold, "standard")
    
    return gdf_aoi
