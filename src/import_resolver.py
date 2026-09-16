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

    # Handling ordinary import
    if (
        reference.imported_name is None
        and reference.level == 0
        and reference.module is not None
    ):
        return module_index.get(reference.module)

    return None
