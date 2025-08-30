import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DataHub:
    """
    Manages the state of data in the pipeline.
    - Caches data in memory.
    - Tracks persisted data files.
    - Lazily loads data from disk on demand.
    - Automatically persists data when registered if a path is defined.
    """

    def __init__(self, case_path: Path, data_sources: dict = None):
        """
        Initializes the DataHub.
        Args:
            case_path: The root path of the current case.
            data_sources: A dictionary defining the data items and their file paths.
        """
        self._case_path = case_path
        self._data = {}  # In-memory cache: {name: DataFrame}
        self._registry = {}  # Maps data name to its absolute file path: {name: Path}

        if data_sources:
            for name, source_info in data_sources.items():
                if "path" in source_info:
                    path = Path(source_info["path"])
                    if not path.is_absolute():
                        path = self._case_path.parent.parent / path # project root
                    self._registry[name] = path
        
        logger.info(f"DataHub initialized for case {case_path.name} with {len(self._registry)} registered sources.")

    def register(self, name: str, data: pd.DataFrame):
        """
        Registers a data object with the Hub and persists it if a path is registered.
        Args:
            name: The unique name of the data.
            data: The pandas DataFrame to register.
        """
        if not isinstance(data, pd.DataFrame):
            raise TypeError(f"Data '{name}' is not a DataFrame and cannot be registered.")

        self._data[name] = data
        logger.debug(f"Data '{name}' registered in memory.")

        # Auto-persist if a path is defined in the registry
        if name in self._registry:
            path = self._registry[name]
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                if path.suffix == '.parquet':
                    data.to_parquet(path)
                elif path.suffix == '.csv':
                    data.to_csv(path, index=False)
                else:
                    logger.warning(f"Unsupported file type for auto-persistence: {path.suffix}. Data '{name}' not persisted.")
                    return
                logger.info(f"Data '{name}' automatically persisted to: {path}")
            except Exception as e:
                logger.error(f"Failed to persist data '{name}' to {path}: {e}")


    def get(self, name: str) -> pd.DataFrame:
        """
        Retrieves data from the Hub.
        If data is not in memory, it's lazy-loaded from the registered file path.
        Args:
            name: The name of the data to retrieve.
        Returns:
            The requested pandas DataFrame.
        Raises:
            KeyError: If the data is not found in memory or in the registry.
        """
        if name in self._data:
            logger.debug(f"Getting data '{name}' from memory.")
            return self._data[name]
        
        if name in self._registry:
            path = self._registry[name]
            logger.info(f"Lazy loading data '{name}' from: {path}...")
            
            if not path.exists():
                raise FileNotFoundError(f"File for data source '{name}' not found at: {path}")

            try:
                if path.suffix == '.parquet':
                    df = pd.read_parquet(path)
                elif path.suffix == '.csv':
                    df = pd.read_csv(path)
                else:
                    raise ValueError(f"Unsupported file type for lazy loading: {path.suffix}")
                
                self._data[name] = df  # Cache in memory after loading
                return df
            except Exception as e:
                logger.error(f"Failed to load data '{name}' from {path}: {e}")
                raise
            
        raise KeyError(f"Data '{name}' not found in DataHub.")

    def get_path(self, name: str) -> Path | None:
        """
        Gets the registered file path for a data source.
        Args:
            name: The name of the data source.
        Returns:
            The Path object if it exists, otherwise None.
        """
        return self._registry.get(name)

    def __contains__(self, name: str) -> bool:
        """Allows using the `in` keyword to check if data exists."""
        return name in self._data or name in self._registry

    def summary(self) -> dict:
        """
        Returns a summary of the DataHub's current state.
        """
        return {
            "in_memory_data": list(self._data.keys()),
            "registered_files": {name: str(path) for name, path in self._registry.items()}
        }