import os
import sys
from glob import glob
from setuptools import setup, Extension, find_packages


def get_version() -> str:
    version_file = "src/gbx/_version.py"
    with open(version_file, encoding="utf-8") as f:
        return f.read().split('"')[1]


GBX_VERSION = get_version()


lzo_dir = "src/gbx/lzo/lzo-2.10"

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
    version=GBX_VERSION,
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
    package_dir={"": "src"},
    packages=find_packages(),
    ext_modules=[gbx_lzo],
)
