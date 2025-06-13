"""Function for setting up regionalization."""

from setuptools import find_packages, setup

setup(
    name="parreg",
    version="0.0.1",
    author="Yuqiong.Liu",
    author_email="yuqiong.liu@ertcorp.com",
    description="NextGen parameter regionalization",
    # long_description=open("README.md").read(),
    long_description="NextGen parameter regionalization",
    long_description_content_type="text/markdown",
    # url="https://github.com/yourusername/your-repo",  # Optional
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        "pydantic>=2.0",
        "pyyaml",
        # Add other dependencies here
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
