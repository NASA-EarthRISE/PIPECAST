"""
Visualization utilities for PIPECAST.
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple
import warnings

import matplotlib.pyplot as plt
import geopandas as gpd

# Optional dependencies
try:
    import folium
    from folium.raster_layers import ImageOverlay
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False
    warnings.warn("folium not available - interactive maps disabled")


def plot_aois_grid(
    geojson_files: List[Path],
    labels: List[str],
    batch_size: int = 16,
    n_cols: int = 4,
    figsize_per_plot: Tuple[int, int] = (4, 4),
    output_dir: Optional[Path] = None
):
    """
    Plot AOIs in a grid layout.
    
    Parameters
    ----------
    geojson_files : list of Path
        List of GeoJSON files to plot
    labels : list of str
        Labels for each plot
    batch_size : int
        Number of plots per batch
    n_cols : int
        Number of columns in grid
    figsize_per_plot : tuple
        Figure size per subplot
    output_dir : Path, optional
        Directory to save figures
    """
    n_files = len(geojson_files)
    
    for start_idx in range(0, n_files, batch_size):
        end_idx = min(start_idx + batch_size, n_files)
        batch_files = geojson_files[start_idx:end_idx]
        batch_labels = labels[start_idx:end_idx]
        
        n_rows = (len(batch_files) + n_cols - 1) // n_cols
        
        fig, axes = plt.subplots(
            n_rows, n_cols,
            figsize=(figsize_per_plot[0] * n_cols, figsize_per_plot[1] * n_rows)
        )
        axes = axes.flatten() if n_rows * n_cols > 1 else [axes]
        
        for idx, (gjson, label) in enumerate(zip(batch_files, batch_labels)):
            ax = axes[idx]
            
            try:
                gdf = gpd.read_file(gjson)
                
                if not gdf.empty:
                    gdf.boundary.plot(ax=ax, color='blue', linewidth=0.5)
                    ax.set_aspect('equal')
                else:
                    ax.text(0.5, 0.5, 'No AOIs', ha='center', va='center',
                           transform=ax.transAxes, fontsize=10)
                    ax.set_aspect('auto')
                    
            except Exception as e:
                ax.text(0.5, 0.5, f'Error:\n{str(e)[:30]}', ha='center', va='center',
                       transform=ax.transAxes, fontsize=8, color='red')
                ax.set_aspect('auto')
            
            ax.set_title(label, fontsize=8)
            ax.set_xticks([])
            ax.set_yticks([])
        
        # Hide unused axes
        for j in range(len(batch_files), len(axes)):
            axes[j].axis('off')
        
        plt.tight_layout()
        
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"aoi_grid_batch_{start_idx//batch_size + 1}.png"
            plt.savefig(output_file, dpi=150, bbox_inches='tight')
            print(f"✓ Saved: {output_file}")
        
        plt.show()
        
        # Pause between batches
        if end_idx < n_files:
            input(f"Displayed {end_idx}/{n_files} plots. Press Enter to continue...")


def create_interactive_map(
    root_dir: Path,
    target_date: str,
    output_path: Optional[Path] = None,
    center: Optional[Tuple[float, float]] = None,
    zoom_start: int = 6
) -> Optional[any]:
    """
    Create interactive Folium map for a specific date.
    
    Parameters
    ----------
    root_dir : Path
        Root directory with forecast outputs
    target_date : str
        Date to visualize (YYYY-MM-DD)
    output_path : Path, optional
        Path to save HTML map
    center : tuple, optional
        Map center (lat, lon)
    zoom_start : int
        Initial zoom level
        
    Returns
    -------
    folium.Map or None
        Folium map object (if folium available)
    """
    if not FOLIUM_AVAILABLE:
        print("Folium not available - cannot create interactive map")
        return None
    
    # Default center
    if center is None:
        center = [39.0, -98.0]  # Center of US
    
    # Create base map
    m = folium.Map(
        location=center,
        zoom_start=zoom_start,
        tiles="CartoDB positron"
    )
    
    # Add AOIs for target date
    aoi_count = 0
    
    for method_dir in root_dir.iterdir():
        if not method_dir.is_dir() or method_dir.name == "ensemble_probability":
            continue
        
        date_dir = method_dir / target_date
        if not date_dir.exists():
            continue
        
        for file in date_dir.glob("*.geojson"):
            try:
                gdf_aoi = gpd.read_file(file)
                if gdf_aoi.empty:
                    continue
                
                # Ensure WGS84
                gdf_aoi = gdf_aoi.to_crs("EPSG:4326")
                
                popup_label = f"{method_dir.name} | {target_date} | {file.stem}"
                
                folium.GeoJson(
                    gdf_aoi,
                    name=popup_label,
                    tooltip=popup_label,
                    style_function=lambda x: {
                        'fillColor': '#3186cc',
                        'color': '#3186cc',
                        'weight': 1,
                        'fillOpacity': 0.3
                    }
                ).add_to(m)
                
                aoi_count += 1
                
            except Exception as e:
                warnings.warn(f"Failed to add {file}: {e}")
                continue
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Save if path provided
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        m.save(output_path)
        print(f"✓ Interactive map saved: {output_path}")
    
    print(f"✓ Added {aoi_count} AOI layers to map")
    
    return m


def visualize_forecast_outputs(root_dir: str):
    """
    Create standard visualizations for forecast outputs.
    
    Parameters
    ----------
    root_dir : str
        Root directory with forecast outputs
    """
    root_path = Path(root_dir)
    
    print("\n" + "="*70)
    print("CREATING VISUALIZATIONS")
    print("="*70)
    
    # Collect all GeoJSON files
    geojson_files = []
    labels = []
    
    for method_dir in root_path.iterdir():
        if not method_dir.is_dir() or method_dir.name == "ensemble_probability":
            continue
        
        for date_dir in method_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            for file in date_dir.glob("*.geojson"):
                geojson_files.append(file)
                label = f"{method_dir.name} | {date_dir.name} | {file.stem}"
                labels.append(label)
    
    if not geojson_files:
        print("No GeoJSON files found for visualization")
        return
    
    print(f"Found {len(geojson_files)} AOI files")
    
    # Create grid plots
    viz_dir = root_path / "visualizations"
    viz_dir.mkdir(exist_ok=True)
    
    plot_aois_grid(geojson_files, labels, output_dir=viz_dir)
    
    # Create interactive maps for each date (if folium available)
    if FOLIUM_AVAILABLE:
        dates = set()
        for label in labels:
            parts = label.split("|")
            if len(parts) >= 2:
                dates.add(parts[1].strip())
        
        for date in sorted(dates):
            map_path = viz_dir / f"map_{date}.html"
            create_interactive_map(root_path, date, map_path)
    
    print("="*70 + "\n")


class ForecastVisualizer:
    """
    Comprehensive visualization class for PIPECAST outputs.
    """
    
    def __init__(self, root_dir: str):
        """
        Initialize visualizer.
        
        Parameters
        ----------
        root_dir : str
            Root directory with forecast outputs
        """
        self.root_dir = Path(root_dir)
        self.viz_dir = self.root_dir / "visualizations"
        self.viz_dir.mkdir(exist_ok=True)
    
    def plot_threshold_comparison(self, date: str, fxx: int):
        """
        Plot comparison across thresholds for a specific date and forecast hour.
        
        Parameters
        ----------
        date : str
            Date (YYYY-MM-DD)
        fxx : int
            Forecast hour
        """
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        axes = axes.flatten()
        
        thresholds = [5, 39, 50, 100, 254, 255]
        
        for idx, threshold in enumerate(thresholds):
            ax = axes[idx]
            
            # Find matching file
            pattern = f"F{fxx}_T{threshold}_aois.geojson"
            
            for method_dir in self.root_dir.iterdir():
                if not method_dir.is_dir():
                    continue
                
                file_path = method_dir / date / pattern
                if file_path.exists():
                    try:
                        gdf = gpd.read_file(file_path)
                        if not gdf.empty:
                            gdf.boundary.plot(ax=ax, color='blue', linewidth=0.5)
                            ax.set_title(f"Threshold: {threshold}mm\n{len(gdf)} AOIs",
                                       fontsize=10)
                        else:
                            ax.set_title(f"Threshold: {threshold}mm\nNo AOIs",
                                       fontsize=10)
                    except:
                        ax.set_title(f"Threshold: {threshold}mm\nError", fontsize=10)
                    break
            
            ax.set_aspect('equal')
            ax.set_xticks([])
            ax.set_yticks([])
        
        plt.suptitle(f"Threshold Comparison - {date} F{fxx:02d}", fontsize=14, y=1.0)
        plt.tight_layout()
        
        output_file = self.viz_dir / f"threshold_comparison_{date}_F{fxx:02d}.png"
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"✓ Saved: {output_file}")
        plt.close()
    
    def create_all_date_maps(self):
        """Create interactive maps for all dates."""
        if not FOLIUM_AVAILABLE:
            print("Folium not available - skipping interactive maps")
            return
        
        dates = set()
        
        for method_dir in self.root_dir.iterdir():
            if not method_dir.is_dir():
                continue
            
            for date_dir in method_dir.iterdir():
                if date_dir.is_dir():
                    dates.add(date_dir.name)
        
        for date in sorted(dates):
            map_path = self.viz_dir / f"map_{date}.html"
            create_interactive_map(self.root_dir, date, map_path)
