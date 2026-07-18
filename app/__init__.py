from importlib.metadata import PackageNotFoundError, version

try:
    __version__: str = version("neuroflag")
except PackageNotFoundError:
    __version__ = "dev"
