"""Function for setting up regionalization."""

from setuptools import find_packages, setup

setup(
    name="parreg",
    name="parreg",
    version="0.0.1",
    author="Yuqiong.Liu, Matthew.Deshotel",
    author_email="yuqiong.liu@ertcorp.com",
    description="NextGen parameter regionalization",
    long_description=open("../../README.md").read(),
    long_description_content_type="text/markdown",
    url="https://gitlab.sh.nextgenwaterprediction.com/NGWPC/nwm-ngen/ngen-regionalization.git/pkgs/parreg",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        "numpy==1.26.4",
        "scikit-learn==1.3.2",
        "scikit-learn-extra==0.3.0",
        "pandas",
        "hdbscan",
        "joblib",
        "pydantic",
        "pyarrow",
        "geopandas",
        "shapely",
        "pyyaml",
        "pyproj",
        "numba",
        "matplotlib",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
)
