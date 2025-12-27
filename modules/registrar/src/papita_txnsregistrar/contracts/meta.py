"""
Plugin metadata model for the transaction tracker system.

This module defines the metadata structure for plugins in the transaction tracking system.
It provides a standardized way to specify information about plugins including their name,
version, tags, dependencies, authors, and other attributes, using Pydantic for validation.

The module consists of two main components:
    - Author: A model representing plugin author information with name and email.
    - PluginMetadata: A comprehensive metadata model for plugin registration and discovery.

All models use Pydantic for validation, ensuring data integrity and type safety throughout
the plugin system. The metadata is used by the plugin registry to discover, register, and
manage plugins in the transaction tracking system.
"""

from typing import Annotated, List

from pydantic import BaseModel, Field, field_validator

from papita_txnsmodel.utils.modelutils import validate_python_version_wrapper, validate_tags_wrapper


class Author(BaseModel):
    """Model representing plugin author information.

    This class encapsulates author information for plugins, including the author's name
    and email address. It provides a standardized format for author representation and
    includes a custom string representation that formats the author as "Name <email>".

    Attributes:
        name: The author's name as a string.
        email: The author's email address as a string.

    Note:
        The string representation formats the author as "Name <email>", which is the
        standard format for author attribution in many systems.
    """

    name: str
    email: str

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"


class PluginMetadata(BaseModel):
    """Metadata model for transaction tracker plugins.

    This class defines the structure for plugin metadata, including information about
    the plugin's name, version, features, authors, and status. It uses Pydantic's
    validation to ensure the metadata follows the required format and validates
    version strings and tags according to system standards.

    The metadata is used by the plugin registry system to discover, register, and
    manage plugins. It provides a standardized way to describe plugin capabilities
    and requirements, enabling dynamic plugin discovery and filtering.

    Attributes:
        name: The name of the plugin. Must be a non-empty string.
        version: The version string of the plugin, must be a valid semantic version
            format (validated by validate_python_version_wrapper). Minimum length is 1.
        feature_tags: A list of tags describing the plugin's features. Tags are
            validated and normalized using validate_tags_wrapper. Defaults to an
            empty list.
        description: A description of the plugin's purpose and functionality.
            Defaults to an empty string.
        enabled: Whether the plugin is enabled and should be discovered by the
            registry. Defaults to True.
        authors: A list of plugin authors. Each author can be provided as a string
            (name only), an Author instance, a dictionary with 'name' and 'email'
            keys, or None (which is filtered out). All authors are normalized to
            strings in the format "Name <email>". Defaults to an empty list.
        module: The module path where the plugin is defined. This is typically set
            automatically during plugin discovery. Defaults to an empty string.

    Note:
        The dependencies field is currently commented out and will be re-added when
        a validation mechanism is implemented for dependency checking.
    """

    name: str
    version: Annotated[str, Field(min_length=1), validate_python_version_wrapper]
    feature_tags: Annotated[List[str], Field(default_factory=list), validate_tags_wrapper]
    # TODO: Add dependencies back in when we have a way to validate them, and define a better use for this field
    # dependencies: Annotated[List[str], Field(default_factory=list), validate_tags_wrapper]
    description: str = ""
    enabled: bool = True
    authors: List[str | Author | dict | None] = Field(default_factory=list)
    module: str = ""

    @field_validator("authors", mode="before")
    @classmethod
    def _validate_authors(cls, v: List[str | Author | dict | None]) -> List[str]:
        """Validate and normalize author information.

        Args:
            v: A list of authors in various formats. Each element can be:
                - A string representing the author's name (email will be empty)
                - An Author instance
                - A dictionary with 'name' and optionally 'email' keys
                - None (will be filtered out)

        Returns:
            List[str]: A list of normalized author strings, each in the format
                "Name <email>". If an author has no email, the format is "Name <>".
        """
        authors = []
        for author in v:
            if not author:
                continue

            if isinstance(author, dict):
                author = Author.model_validate(author)
            elif isinstance(author, Author):
                author = str(author)
            else:
                author = Author.model_validate({"name": author, "email": ""})

            authors.append(str(author))

        return authors
