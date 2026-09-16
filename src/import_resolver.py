from pathlib import PurePosixPath

from src.code_entities import CodeEntity, EntityType
from src.import_references import ImportReference


def build_module_index(entities: list[CodeEntity]) -> dict[str, int]:
    """Map repo python module names to file entity IDs."""
    module_lookup = {}
    for entity in entities:
        # Only files
        if entity.entity_type is EntityType.FILE:
            path = PurePosixPath(entity.location.path)

            # Init uses dir name
            if path.name == "__init__.py":
                module_path = path.parent
            else:
                # Ordinary modules use file path without .py
                module_path = path.with_suffix("")

            # Rebuild name
            module_name = ".".join(module_path.parts)

            if not module_name:
                continue
            # Reject collisions
            if module_name in module_lookup:
                raise ValueError(f"Duplicate module name: {module_name}")

            module_lookup[module_name] = entity.id

    return module_lookup


def resolve_import_target(
    reference: ImportReference, module_index: dict[str, int]
) -> int | None:
    # Convert relative module names to absolute names
    module_name = _absolute_import_module(reference)
    if module_name is None:
        return None

    # Ordinary imports target the exact module name.
    if reference.imported_name is None and reference.level == 0:
        return module_index.get(module_name)

    # Handle both absolute and relative from-imports.
    elif reference.imported_name is not None:
        # Wildcard imports target the module itself.
        if reference.imported_name == "*":
            return module_index.get(module_name)

        module_id = module_index.get(module_name)
        submodule_name = module_name + "." + reference.imported_name
        submodule_id = module_index.get(submodule_name)

        # Both candidates exist; more evidence is needed to choose.
        if module_id is not None and submodule_id is not None:
            return None

        # Return the submodule when it is the only matching candidate.
        if submodule_id is not None:
            return submodule_id

        # Return the module candidate, or None if neither exists.
        return module_id

    return None


def _absolute_import_module(reference: ImportReference) -> str | None:
    # Absolute imports already module name
    if reference.level == 0:
        return reference.module

    # Source files parent dirs form package path
    package_parts = PurePosixPath(reference.location.path).parent.parts

    # relative imports leave at least one package component
    if reference.level > len(package_parts):
        return None

    # Calculating how much of package to keep
    keep_count = len(package_parts) - (reference.level - 1)
    base_parts = package_parts[:keep_count]

    base_module = ".".join(base_parts)

    # Add named module to containing package
    if reference.module is not None:
        return f"{base_module}.{reference.module}"

    return base_module
