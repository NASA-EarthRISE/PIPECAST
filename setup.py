from setuptools import setup, find_packages

setup(
    name="pipecast-weather",
    version="0.2.0",
    author="NASA-EarthRISE PIPECAST Team",
    author_email="",
    description="Weather forecast analysis with ensemble probability and population risk assessment",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/NASA-EarthRISE/PIPECAST",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Atmospheric Science",
        "Topic :: Scientific/Engineering :: GIS",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.20.0",
        "pandas>=1.3.0",
        "geopandas>=0.10.0",
        "shapely>=1.8.0",
        "rasterio>=1.2.0",
        "scipy>=1.7.0",
        "herbie-data>=0.0.10",
        "xarray>=0.19.0",
        "requests>=2.26.0",
        "tqdm>=4.62.0",
    ],
    extras_require={
        'viz': [
            'matplotlib>=3.3.0',
            'folium>=0.12.0',
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/NASA-EarthRISE/PIPECAST/issues",
        "Source": "https://github.com/NASA-EarthRISE/PIPECAST",
    },
)