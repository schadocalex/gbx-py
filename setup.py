import os
import sys
from glob import glob
from setuptools import setup, Extension, find_packages

__version__ = "0.3.0"

lzo_dir = "src/gbx/lzo/lzo-2.10"  # Relative path.

src_list = ["src/gbx/lzo/lzomodule.c"]
if sys.platform == "win32":
    src_list += glob(os.path.join(lzo_dir, "src/*.c"))

gbx_lzo = Extension(
    "gbx.lzo",
    sources=src_list,
    include_dirs=[os.path.join(lzo_dir, "include")],
    library_dirs=[os.path.join(lzo_dir, "lib")],
)

setup(
    name="gbx-py",
    version=__version__,
    description="Read and write gbx files for Trackmania.",
    long_description=open("README.md", "r").read(),
    long_description_content_type="text/markdown",
    author="schadocalex",
    author_email="schad.alexis@gmail.com",
    maintainer="schadocalex",
    url="https://github.com/schadocalex/gbx-py",
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    python_requires=">=3.10",
    py_modules=["gbx"],
    package_dir={"": "src"},
    packages=find_packages(),
    ext_modules=[gbx_lzo],
)
