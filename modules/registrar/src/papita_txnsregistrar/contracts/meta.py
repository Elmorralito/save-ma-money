"""
Plugin metadata model for the transaction tracker system.

This module defines the metadata structure for plugins in the transaction tracking system.
It provides a standardized way to specify information about plugins including their name,
version, tags, dependencies, and other attributes, using Pydantic for validation.
"""

from typing import Annotated, List

from pydantic import BaseModel, Field

from papita_txnsregistrar.utils.modelutils import validate_python_version, validate_tags_wrapper


class PluginMetadata(BaseModel):
    """
    Metadata model for transaction tracker plugins.

    This class defines the structure for plugin metadata, including information about
    the plugin's name, version, features, dependencies, and status. It uses Pydantic's
    validation to ensure the metadata follows the required format.

    Attributes:
        name: The name of the plugin.
        version: The version string of the plugin, must be a valid Python version format.
        feature_tags: A list of tags describing the plugin's features.
        dependencies: A list of tags representing the plugin's dependencies.
        description: A description of the plugin's purpose and functionality. Defaults to an empty string.
        enabled: Whether the plugin is enabled. Defaults to True.
    """

    name: str
    version: Annotated[str, Field(min_length=1), validate_python_version]
    feature_tags: Annotated[List[str], Field(default_factory=list), validate_tags_wrapper]
    # TODO: Add dependencies back in when we have a way to validate them, and define a better use for this field
    # dependencies: Annotated[List[str], Field(default_factory=list), validate_tags_wrapper]
    description: str = ""
    enabled: bool = True
