from setuptools import setup, find_packages

setup(
    name="pyget",
    version="0.1.0",
    description="Simple module fetcher via GitHub raw URLs",
    author="Your Name",
    author_email="youremail@example.com",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[],
    entry_points={
        "console_scripts": [
            "pyimporter=pyimporter.cli:main", 
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
