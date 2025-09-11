"""
This module defines the core types for plugin dependency declaration.

It introduces `DataSource` and `DataSink` classes to be used with `typing.Annotated`
for declaratively specifying a plugin's input and output dependencies.
"""
from typing import Any

class DataSource:
    """
    A marker for annotating a Pydantic field as a data input source.

    When a plugin's config field is annotated with `DataSource`, the framework
    will recognize it as a dependency that needs to be loaded from an external
    source (e.g., a file) by the `DataHub`.

    Attributes:
        name: The logical name of the data source, used to look up the actual
              path and handler in the case configuration's `io_mapping` section.
        handler_args: A dictionary of optional arguments to be passed to the
                      corresponding data handler.
    """
    def __init__(self, name: str, handler_args: dict[str, Any] | None = None):
        self.name = name
        self.handler_args = handler_args or {}

class DataSink:
    """
    A marker for annotating a Pydantic field as a data output target.

    When a plugin's config field is annotated with `DataSink`, the framework
    understands that the plugin's return value should be written to the
    destination specified by this sink.

    Attributes:
        name: The logical name of the data sink, used to look up the actual
              path and handler in the case configuration's `io_mapping` section.
        handler_args: A dictionary of optional arguments to be passed to the
                      corresponding data handler for writing.
    """
    def __init__(self, name: str, handler_args: dict[str, Any] | None = None):
        self.name = name
        self.handler_args = handler_args or {}