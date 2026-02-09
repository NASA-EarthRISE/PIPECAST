"""
Data management for PIPECAST enhanced layers.
"""

import os
import zipfile
from pathlib import Path
from typing import Optional, Dict, Tuple
import geopandas as gpd
import requests
from tqdm import tqdm


class DataManager:
    """
    Manages enhanced data layers (census, watershed, custom).
    
    Downloads from Zenodo and caches locally.
    """
    
    def __init__(self, cache_dir: str = "./pipecast_data"):
        """
        Initialize DataManager.
        
        Parameters
        ----------
        cache_dir : str
            Directory to cache downloaded data
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.census_gdf: Optional[gpd.GeoDataFrame] = None
        self.watershed_gdf: Optional[gpd.GeoDataFrame] = None
        self.custom_layers: Dict[str, gpd.GeoDataFrame] = {}
    
    def download_file(self, url: str, filename: str) -> Path:
        """
        Download file from URL with progress bar.
        
        Parameters
        ----------
        url : str
            URL to download from
        filename : str
            Name for saved file
            
        Returns
        -------
        Path
            Path to downloaded file
        """
        filepath = self.cache_dir / filename
        
        # Check if already downloaded
        if filepath.exists():
            print(f"✓ File already cached: {filepath}")
            return filepath
        
        print(f"Downloading {filename}...")
        
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(filepath, 'wb') as f, tqdm(
            total=total_size,
            unit='B',
            unit_scale=True,
            desc=filename
        ) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
        
        print(f"✓ Downloaded: {filepath}")
        return filepath
    
    def extract_zip(self, zip_path: Path) -> Path:
        """
        Extract ZIP file.
        
        Parameters
        ----------
        zip_path : Path
            Path to ZIP file
            
        Returns
        -------
        Path
            Directory containing extracted files
        """
        extract_dir = zip_path.parent / zip_path.stem
        
        if extract_dir.exists():
            print(f"✓ Already extracted: {extract_dir}")
            return extract_dir
        
        print(f"Extracting {zip_path.name}...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        print(f"✓ Extracted to: {extract_dir}")
        return extract_dir
    
    def download_census_data(self, url: str) -> gpd.GeoDataFrame:
        """
        Download and load census data.
        
        Parameters
        ----------
        url : str
            Zenodo URL for census data
            
        Returns
        -------
        gpd.GeoDataFrame
            Census data
        """
        if self.census_gdf is not None:
            return self.census_gdf
        
        # Download
        zip_path = self.download_file(url, "census_data.zip")
        
        # Extract
        extract_dir = self.extract_zip(zip_path)
        
        # Find shapefile
        shp_files = list(extract_dir.glob("**/*.shp"))
        if not shp_files:
            raise FileNotFoundError(f"No shapefile found in {extract_dir}")
        
        shp_path = shp_files[0]
        print(f"Loading census data from: {shp_path}")
        
        self.census_gdf = gpd.read_file(shp_path)
        
        # CRITICAL FIX: The shapefile has WRONG CRS metadata
        # The bounds show it's in a projected system (meters), not degrees
        # Check if bounds are unrealistic for lat/lon
        bounds = self.census_gdf.total_bounds
        
        if abs(bounds[0]) > 200 or abs(bounds[2]) > 200:
            # These are projected coordinates, not lat/lon
            print(f"⚠️  WARNING: Census CRS metadata is incorrect!")
            print(f"   Bounds: {bounds}")
            print(f"   CRS says: {self.census_gdf.crs}")
            print(f"   But these are clearly projected coordinates (meters)")
            
            # Try to identify the actual projection
            # Most likely this is Albers Equal Area Conic (EPSG:5070) or similar
            # Let's check the .prj file
            prj_file = shp_path.with_suffix('.prj')
            if prj_file.exists():
                with open(prj_file, 'r') as f:
                    prj_text = f.read()
                    print(f"   PRJ file content: {prj_text[:200]}...")
                    
                    # Check for common projections
                    if 'Albers' in prj_text or 'EPSG",5070' in prj_text:
                        print(f"   Detected: Albers Equal Area Conic (EPSG:5070)")
                        self.census_gdf = self.census_gdf.set_crs("EPSG:5070", allow_override=True)
                    elif 'Web_Mercator' in prj_text or 'EPSG",3857' in prj_text:
                        print(f"   Detected: Web Mercator (EPSG:3857)")
                        self.census_gdf = self.census_gdf.set_crs("EPSG:3857", allow_override=True)
                    else:
                        # Default assumption for US census data
                        print(f"   Assuming: Albers Equal Area Conic (EPSG:5070)")
                        self.census_gdf = self.census_gdf.set_crs("EPSG:5070", allow_override=True)
            else:
                # No PRJ file, assume standard US census projection
                print(f"   Assuming: Albers Equal Area Conic (EPSG:5070)")
                self.census_gdf = self.census_gdf.set_crs("EPSG:5070", allow_override=True)
            
            # Now convert to WGS84
            print(f"   Converting to EPSG:4326...")
            self.census_gdf = self.census_gdf.to_crs("EPSG:4326")
            
            # Verify conversion
            new_bounds = self.census_gdf.total_bounds
            print(f"   New bounds: {new_bounds}")
            print(f"   ✓ Conversion successful!")
        
        else:
            # Bounds look reasonable for lat/lon, ensure it's set correctly
            if self.census_gdf.crs is None:
                print("Setting CRS to EPSG:4326")
                self.census_gdf = self.census_gdf.set_crs("EPSG:4326")
            elif self.census_gdf.crs.to_string() != "EPSG:4326":
                print(f"Converting census from {self.census_gdf.crs} to EPSG:4326")
                self.census_gdf = self.census_gdf.to_crs("EPSG:4326")
        
        print(f"✓ Loaded {len(self.census_gdf):,} census features (EPSG:4326)")
        print(f"  Final bounds: {self.census_gdf.total_bounds}")
        
        return self.census_gdf
    
    def download_watershed_data(self, url: str) -> gpd.GeoDataFrame:
        """
        Download and load watershed data.
        
        Parameters
        ----------
        url : str
            Zenodo URL for watershed data
            
        Returns
        -------
        gpd.GeoDataFrame
            Watershed data
        """
        if self.watershed_gdf is not None:
            return self.watershed_gdf
        
        # Download
        zip_path = self.download_file(url, "watershed_data.zip")
        
        # Extract
        extract_dir = self.extract_zip(zip_path)
        
        # Find shapefile
        shp_files = list(extract_dir.glob("**/*.shp"))
        if not shp_files:
            raise FileNotFoundError(f"No shapefile found in {extract_dir}")
        
        shp_path = shp_files[0]
        print(f"Loading watershed data from: {shp_path}")
        
        self.watershed_gdf = gpd.read_file(shp_path)
        
        # Check and fix CRS similar to census
        bounds = self.watershed_gdf.total_bounds
        
        if abs(bounds[0]) > 200 or abs(bounds[2]) > 200:
            # Projected coordinates
            print(f"⚠️  WARNING: Watershed CRS metadata is incorrect!")
            print(f"   Assuming: Albers Equal Area Conic (EPSG:5070)")
            self.watershed_gdf = self.watershed_gdf.set_crs("EPSG:5070", allow_override=True)
            print(f"   Converting to EPSG:4326...")
            self.watershed_gdf = self.watershed_gdf.to_crs("EPSG:4326")
            print(f"   ✓ Conversion successful!")
        else:
            # Ensure WGS84
            if self.watershed_gdf.crs is None:
                self.watershed_gdf = self.watershed_gdf.set_crs("EPSG:4326")
            elif self.watershed_gdf.crs.to_string() != "EPSG:4326":
                print(f"Converting watershed from {self.watershed_gdf.crs} to EPSG:4326")
                self.watershed_gdf = self.watershed_gdf.to_crs("EPSG:4326")
        
        print(f"✓ Loaded {len(self.watershed_gdf):,} watershed features (EPSG:4326)")
        print(f"  Final bounds: {self.watershed_gdf.total_bounds}")
        
        return self.watershed_gdf
    
    def load_custom_layer(self, name: str, filepath: str) -> gpd.GeoDataFrame:
        """
        Load a custom enhanced layer.
        
        Parameters
        ----------
        name : str
            Name for the layer
        filepath : str
            Path to shapefile or GeoJSON
            
        Returns
        -------
        gpd.GeoDataFrame
            Custom layer data
        """
        if name in self.custom_layers:
            return self.custom_layers[name]
        
        print(f"Loading custom layer '{name}' from: {filepath}")
        gdf = gpd.read_file(filepath)
        self.custom_layers[name] = gdf
        print(f"✓ Loaded {len(gdf):,} features for layer '{name}'")
        
        return gdf
    
    def get_enhanced_layers(
        self,
        use_census: bool = True,
        use_watershed: bool = True,
        census_url: Optional[str] = None,
        watershed_url: Optional[str] = None,
        custom_layers: Optional[Dict[str, str]] = None
    ) -> Tuple[Optional[gpd.GeoDataFrame], Optional[gpd.GeoDataFrame], Dict[str, gpd.GeoDataFrame]]:
        """
        Get all requested enhanced layers.
        
        Parameters
        ----------
        use_census : bool
            Whether to load census data
        use_watershed : bool
            Whether to load watershed data
        census_url : str, optional
            Zenodo URL for census
        watershed_url : str, optional
            Zenodo URL for watershed
        custom_layers : dict, optional
            Custom layers {name: filepath}
            
        Returns
        -------
        tuple
            (census_gdf, watershed_gdf, custom_layers_dict)
        """
        census_gdf = None
        watershed_gdf = None
        custom_dict = {}
        
        if use_census and census_url:
            census_gdf = self.download_census_data(census_url)
        
        if use_watershed and watershed_url:
            watershed_gdf = self.download_watershed_data(watershed_url)
        
        if custom_layers:
            for name, filepath in custom_layers.items():
                custom_dict[name] = self.load_custom_layer(name, filepath)
        
        return census_gdf, watershed_gdf, custom_dict
    
    def clip_to_land(self, gdf: gpd.GeoDataFrame, 
                     land_boundary: Optional[gpd.GeoDataFrame] = None) -> gpd.GeoDataFrame:
        """
        Clip GeoDataFrame to land areas.
        
        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            GeoDataFrame to clip
        land_boundary : gpd.GeoDataFrame, optional
            Boundary to use (defaults to census boundary)
            
        Returns
        -------
        gpd.GeoDataFrame
            Clipped GeoDataFrame
        """
        if land_boundary is None:
            if self.census_gdf is None:
                print("Warning: No land boundary available for clipping")
                return gdf
            land_boundary = self.census_gdf
        
        # Ensure same CRS
        if gdf.crs != land_boundary.crs:
            gdf = gdf.to_crs(land_boundary.crs)
        
        # OPTIMIZATION: Use spatial index instead of full union
        print("Clipping to land using spatial index...")
        
        # Get bounding box of all AOIs
        bounds = gdf.total_bounds
        
        # Pre-filter census data to only relevant area
        land_subset = land_boundary.cx[bounds[0]:bounds[2], bounds[1]:bounds[3]]
        
        if len(land_subset) == 0:
            print("Warning: No land features in AOI area")
            return gpd.GeoDataFrame(columns=gdf.columns, crs=gdf.crs)
        
        print(f"Using {len(land_subset):,} land features (filtered from {len(land_boundary):,})")
        
        # Use spatial join instead of union (much faster)
        clipped = gpd.sjoin(gdf, land_subset, how='inner', predicate='intersects')
        
        # Remove duplicate columns from spatial join
        clipped = clipped[gdf.columns]
        
        # Remove duplicates (one AOI might intersect multiple census blocks)
        clipped = clipped.drop_duplicates(subset=['id'] if 'id' in clipped.columns else None)
        
        print(f"✓ Retained {len(clipped)}/{len(gdf)} features over land")
        
        return clipped


# Convenience functions
def download_enhanced_layers(
    cache_dir: str = "./pipecast_data",
    census_url: Optional[str] = None,
    watershed_url: Optional[str] = None
) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Download enhanced layers from Zenodo.
    
    Parameters
    ----------
    cache_dir : str
        Cache directory
    census_url : str, optional
        Census Zenodo URL
    watershed_url : str, optional
        Watershed Zenodo URL
        
    Returns
    -------
    tuple
        (census_gdf, watershed_gdf)
    """
    manager = DataManager(cache_dir)
    
    # Use default URLs if not provided
    if census_url is None:
        census_url = "https://zenodo.org/records/18497756/files/National_block_groups_with_pop.zip"
    if watershed_url is None:
        watershed_url = "https://zenodo.org/records/18497756/files/National_Huc_12_preprocessed.zip"
    
    census_gdf = manager.download_census_data(census_url)
    watershed_gdf = manager.download_watershed_data(watershed_url)
    
    return census_gdf, watershed_gdf


def load_enhanced_layers(
    census_path: str,
    watershed_path: str
) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Load enhanced layers from local files.
    
    Parameters
    ----------
    census_path : str
        Path to census shapefile
    watershed_path : str
        Path to watershed shapefile
        
    Returns
    -------
    tuple
        (census_gdf, watershed_gdf)
    """
    print(f"Loading census from: {census_path}")
    census_gdf = gpd.read_file(census_path)
    print(f"✓ Loaded {len(census_gdf):,} census features")
    
    print(f"Loading watershed from: {watershed_path}")
    watershed_gdf = gpd.read_file(watershed_path)
    print(f"✓ Loaded {len(watershed_gdf):,} watershed features")
    
    return census_gdf, watershed_gdf