# gbx-py

![PyPI version](https://img.shields.io/pypi/v/gbx-py.svg)
[![Documentation Status](https://readthedocs.org/projects/gbx-py/badge/?version=latest)](https://gbx-py.readthedocs.io/en/latest/?version=latest)

Read and write GBX files for Trackmania.

-   PyPI package: https://pypi.org/project/gbx-py/
-   Free software: MIT License
-   Documentation: https://gbx-py.readthedocs.io.

## Features

-   TODO

## Getting start

`py -m pip install gbx-py`

## Dev

Install and build locally

```
del src\gbx\lzo*.pyd
py -m pip install -e .
```

### Deploy

Change version in `src/gbx/_version.py`. Commit and push.

```
git tag v<version>
git push --tags
```
