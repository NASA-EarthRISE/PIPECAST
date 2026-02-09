"""
Ensemble probability processing for PIPECAST.

Creates probabilistic forecast products from multiple AOI members.
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import warnings

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.transform import from_origin
from rasterio.features import rasterize
from rasterio.crs import CRS

from .config import ForecastConfig


class EnsembleProcessor:
    """
    Processes multiple AOI forecasts into ensemble probability products.
    
    This processor:
    1. Collects all AOI files from forecast processing
    2. Rasterizes each AOI into probability bins
    3. Creates ensemble probability GeoTIFFs
    4. Ranks AOIs by risk (population, area, etc.)
    """
    
    def __init__(
        self,
        root_dir: str,
        bins: Optional[List[Tuple[float, float]]] = None,
        bin_labels: Optional[List[str]] = None,
        resolution_deg: float = 0.05,
        crs: str = "EPSG:4326"
    ):
        """
        Initialize EnsembleProcessor.
        
        Parameters
        ----------
        root_dir : str
            Root directory containing forecast outputs
        bins : list of tuple, optional
            Threshold bins [(min, max), ...]
        bin_labels : list of str, optional
            Labels for bins
        resolution_deg : float
            Grid resolution in degrees
        crs : str
            Coordinate reference system
        """
        self.root_dir = Path(root_dir)
        self.resolution_deg = resolution_deg
        self.crs = CRS.from_string(crs)
        
        # Threshold bins
        if bins is None:
            self.bins = [(0, 5), (6, 39), (40, 50), (51, 100), (100, 254), (255, float('inf'))]
        else:
            self.bins = bins
        
        if bin_labels is None:
            self.bin_labels = ["0-5", "6-39", "40-50", "51-100", "100-254", "255+"]
        else:
            self.bin_labels = bin_labels
        
        # Output directory
        self.out_dir = self.root_dir / "ensemble_probability"
        self.out_dir.mkdir(exist_ok=True)
        
        # Storage
        self.members: List[Dict] = []
        self.prob_paths: Dict[str, Path] = {}
    
    def threshold_to_bin_label(self, threshold: float) -> str:
        """
        Map threshold value to bin label.
        
        Parameters
        ----------
        threshold : float
            Threshold value
            
        Returns
        -------
        str
            Bin label
        """
        for (lo, hi), label in zip(self.bins, self.bin_labels):
            if lo <= threshold <= hi:
                return label
        return "UNBINNED"
    
    def collect_members(self) -> List[Dict]:
        """
        Collect all AOI files with metadata.
        
        Returns
        -------
        list
            List of member dictionaries
        """
        print("\n" + "="*70)
        print("COLLECTING ENSEMBLE MEMBERS")
        print("="*70)
        
        pattern = re.compile(r"F(?P<fxx>\d+)_T(?P<thr>\d+)_aois\.geojson$")
        members = []
        all_bounds = []
        
        # Search directory structure
        for method_dir in self.root_dir.iterdir():
            if not method_dir.is_dir() or method_dir.name == "ensemble_probability":
                continue
            
            for date_dir in method_dir.iterdir():
                if not date_dir.is_dir():
                    continue
                
                for file in date_dir.iterdir():
                    if not file.suffix == ".geojson":
                        continue
                    
                    m = pattern.search(file.name)
                    if not m:
                        continue
                    
                    fxx = int(m.group("fxx"))
                    thr = int(m.group("thr"))
                    
                    # Peek bounds
                    try:
                        gdf = gpd.read_file(file)
                        if not gdf.empty:
                            gdf = gdf.to_crs(epsg=4326)
                            all_bounds.append(gdf.total_bounds.tolist())
                    except Exception as e:
                        warnings.warn(f"Failed to read {file}: {e}")
                        continue
                    
                    members.append({
                        "method": method_dir.name,
                        "date": date_dir.name,
                        "fxx": fxx,
                        "thr": thr,
                        "path": file,
                    })
        
        self.members = members
        
        # Compute extent
        if not all_bounds:
            # Default extent
            self.west, self.south, self.east, self.north = (-125.0, 24.0, -66.0, 50.0)
        else:
            all_bounds = np.array(all_bounds)
            self.west = float(np.min(all_bounds[:, 0]))
            self.south = float(np.min(all_bounds[:, 1]))
            self.east = float(np.max(all_bounds[:, 2]))
            self.north = float(np.max(all_bounds[:, 3]))
            
            # Convert longitude from 0-360 to -180-180 if needed
            if self.west > 180:
                self.west -= 360
            if self.east > 180:
                self.east -= 360
        
        # Add padding
        pad = 0.25
        self.west -= pad
        self.south -= pad
        self.east += pad
        self.north += pad
        
        # Build grid
        self.width = int(np.ceil((self.east - self.west) / self.resolution_deg))
        self.height = int(np.ceil((self.north - self.south) / self.resolution_deg))
        self.transform = from_origin(self.west, self.north, self.resolution_deg, self.resolution_deg)
        
        print(f"Found {len(members)} ensemble members")
        print(f"Grid: {self.width} x {self.height} @ {self.resolution_deg}°")
        print(f"Extent: W{self.west:.2f}° S{self.south:.2f}° E{self.east:.2f}° N{self.north:.2f}°")
        print("="*70 + "\n")
        
        return members
    
    def create_ensemble_probabilities(self) -> Dict[str, Path]:
        """
        Create ensemble probability GeoTIFFs for each bin.
        
        Returns
        -------
        dict
            Mapping of bin label to GeoTIFF path
        """
        if not self.members:
            self.collect_members()
        
        print("\n" + "="*70)
        print("CREATING ENSEMBLE PROBABILITIES")
        print("="*70)
        
        # Initialize accumulators
        counts_by_bin = {
            lbl: np.zeros((self.height, self.width), dtype=np.uint16)
            for lbl in self.bin_labels
        }
        denom_by_bin = {lbl: 0 for lbl in self.bin_labels}
        
        # Rasterize each member
        for mem in self.members:
            lbl = self.threshold_to_bin_label(mem["thr"])
            denom_by_bin[lbl] += 1
            
            try:
                gdf = gpd.read_file(mem["path"])
                if gdf.empty:
                    continue
                
                # Ensure WGS84
                gdf = gdf.to_crs(epsg=4326)
                
                # Rasterize
                shapes = [(geom, 1) for geom in gdf.geometry if geom and not geom.is_empty]
                if not shapes:
                    continue
                
                tmp = rasterize(
                    shapes=shapes,
                    out_shape=(self.height, self.width),
                    transform=self.transform,
                    fill=0,
                    default_value=1,
                    dtype=np.uint8
                )
                
                counts_by_bin[lbl] += tmp.astype(np.uint16)
                
            except Exception as e:
                warnings.warn(f"Failed to process member {mem['path']}: {e}")
                continue
        
        # Compute probabilities and save
        for lbl in self.bin_labels:
            denom = denom_by_bin[lbl]
            
            if denom == 0:
                print(f"[WARN] No members for bin {lbl}")
                continue
            
            # Calculate probability
            prob = counts_by_bin[lbl].astype(np.float32) / float(denom)
            prob = np.clip(prob, 0.0, 1.0)
            
            # Save GeoTIFF
            tif_path = self.out_dir / f"probability_{lbl.replace('+', 'plus')}.tif"
            
            # Delete existing file if it exists
            if tif_path.exists():
                try:
                    tif_path.unlink()
                except PermissionError:
                    import time
                    timestamp = int(time.time())
                    tif_path = self.out_dir / f"probability_{lbl.replace('+', 'plus')}_{timestamp}.tif"
                    print(f"  File locked, using: {tif_path.name}")
            
            profile = {
                "driver": "GTiff",
                "height": prob.shape[0],
                "width": prob.shape[1],
                "count": 1,
                "dtype": "float32",
                "crs": self.crs,
                "transform": self.transform,
                "compress": "lzw"
            }
            
            try:
                with rasterio.open(tif_path, "w", **profile) as dst:
                    dst.write(prob, 1)
                
                self.prob_paths[lbl] = tif_path
                print(f"✓ {lbl:10s}: {tif_path}")
            except PermissionError:
                print(f"✗ {lbl:10s}: Permission denied (file may be open)")
                continue
        
        # Save manifest
        self.save_manifest(denom_by_bin)
        
        print("="*70 + "\n")
        
        return self.prob_paths
    
    def save_manifest(self, denom_by_bin: Dict[str, int]):
        """Save ensemble manifest JSON."""
        manifest = {
            "root_dir": str(self.root_dir),
            "out_dir": str(self.out_dir),
            "grid": {
                "bounds": {
                    "west": self.west,
                    "south": self.south,
                    "east": self.east,
                    "north": self.north
                },
                "resolution_deg": self.resolution_deg,
                "width": self.width,
                "height": self.height,
                "crs": str(self.crs)
            },
            "bins": [
                {"label": l, "range": r}
                for l, r in zip(self.bin_labels, self.bins)
            ],
            "denominators": denom_by_bin,
            "probability_tifs": {k: str(v) for k, v in self.prob_paths.items()}
        }
        
        manifest_path = self.out_dir / "ensemble_manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        
        print(f"✓ Manifest: {manifest_path}")
    
    def rank_aois_by_probability(
        self,
        census_gdf: Optional[gpd.GeoDataFrame] = None,
        top_n: int = 50
    ) -> pd.DataFrame:
        """
        Rank AOIs by ensemble probability.
        
        Parameters
        ----------
        census_gdf : gpd.GeoDataFrame, optional
            Census data for population statistics
        top_n : int
            Number of top AOIs to return
            
        Returns
        -------
        pd.DataFrame
            Ranked AOIs with statistics
        """
        if not self.members:
            self.collect_members()
        
        print("\n" + "="*70)
        print("RANKING AOIs BY ENSEMBLE PROBABILITY")
        print("="*70)
        
        # Collect all AOIs with their ensemble counts
        aoi_data = []
        
        for mem in self.members:
            try:
                gdf = gpd.read_file(mem["path"])
                if gdf.empty:
                    continue
                
                gdf = gdf.to_crs(epsg=4326)
                
                # Extract file identifier
                file_name = mem['path'].stem  # e.g., "F12_T100_aois"
                
                for idx, row in gdf.iterrows():
                    aoi_data.append({
                        'method': mem['method'],
                        'date': mem['date'],
                        'fxx': mem['fxx'],
                        'threshold': mem['thr'],
                        'bin': self.threshold_to_bin_label(mem['thr']),
                        'file_name': file_name,
                        'aoi_id': row.get('id', idx),
                        'geometry': row['geometry'],
                        'mean_precip_mm': row.get('mean_precip_mm', 0),
                        'max_precip_mm': row.get('max_precip_mm', 0),
                        'area_deg2': row.get('area_deg2', row['geometry'].area)
                    })
                    
            except Exception as e:
                warnings.warn(f"Failed to process {mem['path']}: {e}")
                continue
        
        if not aoi_data:
            print("No AOI data found")
            return pd.DataFrame()
        
        # Create DataFrame
        df = pd.DataFrame(aoi_data)
        gdf_all = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:4326')
        
        # Aggregate by spatial overlap (simplified: group by centroid proximity)
        print("Aggregating spatially overlapping AOIs...")
        gdf_all['centroid_lon'] = gdf_all.geometry.centroid.x.round(1)
        gdf_all['centroid_lat'] = gdf_all.geometry.centroid.y.round(1)
        
        grouped = gdf_all.groupby(['centroid_lon', 'centroid_lat', 'bin']).agg({
            'mean_precip_mm': 'mean',
            'max_precip_mm': 'max',
            'area_deg2': 'sum',
            'method': lambda x: list(x),
            'date': lambda x: list(set(x)),
            'fxx': lambda x: list(set(x)),
            'file_name': lambda x: list(set(x)),
            'aoi_id': 'first'
        }).reset_index()
        
        grouped['ensemble_count'] = grouped['method'].apply(len)
        grouped['date_list'] = grouped['date'].apply(lambda x: ','.join(sorted(x)))
        grouped['fxx_list'] = grouped['fxx'].apply(lambda x: ','.join(map(str, sorted(x))))
        
        # Add population if census data provided
        if census_gdf is not None:
            print("Computing population statistics...")
            
            # CRITICAL: Ensure census data is in EPSG:4326
            if census_gdf.crs is None:
                print("WARNING: Census data has no CRS, assuming EPSG:4326")
                census_gdf = census_gdf.set_crs("EPSG:4326")
            elif census_gdf.crs.to_string() != "EPSG:4326":
                print(f"Converting census from {census_gdf.crs.to_string()} to EPSG:4326")
                census_gdf = census_gdf.to_crs("EPSG:4326")
            
            # Ensure AOI data is in EPSG:4326
            if gdf_all.crs is None:
                gdf_all = gdf_all.set_crs("EPSG:4326")
            elif gdf_all.crs.to_string() != "EPSG:4326":
                print(f"Converting AOIs from {gdf_all.crs.to_string()} to EPSG:4326")
                gdf_all = gdf_all.to_crs("EPSG:4326")
            
            from shapely.ops import unary_union
            pop_list = []
            
            for idx, row in grouped.iterrows():
                # Get ALL geometries for this grouped centroid location
                matching_rows = gdf_all[
                    (gdf_all['centroid_lon'] == row['centroid_lon']) &
                    (gdf_all['centroid_lat'] == row['centroid_lat'])
                ]
                
                if len(matching_rows) == 0:
                    pop_list.append(0)
                    continue
                
                # Create union of ALL matching AOI geometries
                geom_list = matching_rows.geometry.tolist()
                if len(geom_list) == 1:
                    combined_geom = geom_list[0]
                else:
                    combined_geom = unary_union(geom_list)
                
                try:
                    # Spatial intersection with census - use actual intersection geometry
                    intersecting_census = census_gdf[census_gdf.intersects(combined_geom)].copy()
                    
                    if len(intersecting_census) == 0:
                        pop_list.append(0)
                        if idx < 3:
                            print(f"[DEBUG] Row {idx}: No intersecting census features")
                        continue
                    
                    # Calculate actual intersection area for weighting
                    intersecting_census['intersection_geom'] = intersecting_census.geometry.intersection(combined_geom)
                    intersecting_census['intersection_area'] = intersecting_census['intersection_geom'].area
                    intersecting_census['original_area'] = intersecting_census.geometry.area
                    intersecting_census['area_fraction'] = intersecting_census['intersection_area'] / intersecting_census['original_area']
                    
                    # Find population column (case-insensitive)
                    pop_col = None
                    possible_cols = ['Population', 'POPULATION', 'population', 'U7H001', 'POP']
                    
                    if idx == 0:
                        print(f"[DEBUG] Census columns: {list(intersecting_census.columns)}")
                    
                    for col in possible_cols:
                        if col in intersecting_census.columns:
                            pop_col = col
                            if idx == 0:
                                print(f"[DEBUG] Using population column: {pop_col}")
                            break
                    
                    if pop_col:
                        # Weight population by intersection area fraction
                        intersecting_census['weighted_pop'] = intersecting_census[pop_col] * intersecting_census['area_fraction']
                        pop_value = intersecting_census['weighted_pop'].sum()
                        pop = int(pop_value)
                        
                        if idx < 3:
                            print(f"[DEBUG] Row {idx}: {len(intersecting_census)} census features, Population = {pop:,}")
                    else:
                        pop = 0
                        if idx == 0:
                            print(f"[WARNING] No population column found")
                    
                    pop_list.append(pop)
                    
                except Exception as e:
                    pop_list.append(0)
                    if idx < 3:
                        print(f"[WARNING] Row {idx}: Error calculating population: {e}")
            
            grouped['population_affected'] = pop_list
        
        # Sort by ensemble count (highest probability)
        grouped = grouped.sort_values('ensemble_count', ascending=False)
        
        # Select top N
        top_aois = grouped.head(top_n)
        
        # Save
        output_path = self.out_dir / "ranked_aois.csv"
        top_aois.to_csv(output_path, index=False)
        print(f"\n✓ Ranked AOIs saved: {output_path}")
        
        # Print summary
        print(f"\nTop {min(10, len(top_aois))} AOIs by Ensemble Probability:")
        print("-" * 100)
        
        cols_to_display = ['file_name', 'aoi_id', 'bin', 'ensemble_count', 
                          'mean_precip_mm', 'area_deg2']
        if 'population_affected' in top_aois.columns:
            cols_to_display.append('population_affected')
        
        print(top_aois[cols_to_display].head(10).to_string(index=False))
        print("="*70 + "\n")
        
        return top_aois


# Convenience functions
def create_ensemble_probability(
    root_dir: str,
    bins: Optional[List[Tuple[float, float]]] = None,
    bin_labels: Optional[List[str]] = None,
    resolution_deg: float = 0.05
) -> Dict[str, Path]:
    """
    Create ensemble probability products from forecast outputs.
    
    Parameters
    ----------
    root_dir : str
        Root directory with forecast outputs
    bins : list of tuple, optional
        Threshold bins
    bin_labels : list of str, optional
        Bin labels
    resolution_deg : float
        Grid resolution
        
    Returns
    -------
    dict
        Mapping of bin label to GeoTIFF path
    """
    processor = EnsembleProcessor(root_dir, bins, bin_labels, resolution_deg)
    return processor.create_ensemble_probabilities()


def rank_aois_by_risk(
    root_dir: str,
    census_gdf: Optional[gpd.GeoDataFrame] = None,
    top_n: int = 50
) -> pd.DataFrame:
    """
    Rank AOIs by risk (ensemble probability + population).
    
    Parameters
    ----------
    root_dir : str
        Root directory with forecast outputs
    census_gdf : gpd.GeoDataFrame, optional
        Census data
    top_n : int
        Number of top AOIs
        
    Returns
        -------
    pd.DataFrame
        Ranked AOIs
    """
    processor = EnsembleProcessor(root_dir)
    return processor.rank_aois_by_probability(census_gdf, top_n)