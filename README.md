# Codebase City

Codebase City is an interactive codebase visualizer that turns a software repository into an explorable 3D city. Instead of learning an unfamiliar project only through folders, files, and text, a developer can see its structure, move through it, follow relationships, and jump directly from the visualization to the source code.

## Mapping

| Code concept         | City representation                              |
| -------------------- | ------------------------------------------------ |
| Repository           | Entire city                                      |
| Folder or package    | District                                         |
| File                 | Building                                         |
| Class                | Rectangular section within a building            |
| Function or method   | Floor                                            |
| Import or dependency | Directed road                                    |
| Test                 | Nearby test structure with a distinct connection |
| External library     | Distant neighbouring city connected by a highway |

## Core Interaction

### Movement

- **Overview mode:** A zoomed-out, free-flying view similar to Google Earth. The user can inspect the entire city, move between districts, and select a location to descend into.
- **First-person mode:** A ground-level view for walking through districts, buildings, and their relationships.

The user should be able to select a point in overview mode and enter first-person mode at that location.

### Structure

The city should communicate code structure through position, grouping, and scale. Folders form distinct districts. Files appear as buildings inside their parent district. Classes form joined sections of those buildings, and functions form their floors.

Folder structure determines district membership. Dependencies influence placement within each district without overriding that structure. A building should move toward the edge of its district nearest the other districts it connects to. Tightly coupled modules remain separate buildings but should be placed beside one another.

### Roads

Roads represent imports or other code dependencies. They should be directional:

- A road starts at the code being imported.
- It ends at the file, class, or function that imports it.
- If both sides depend on one another, roads exist in both directions.

Circular dependencies should be represented as roundabouts so that the relationship is recognizable and can also act as a warning structure.

Vehicles moving along these roads could represent runtime calls, events, or network packets when real execution data is available. Static analysis must not pretend to show live runtime traffic.

Selecting a road should reveal the imports, dependencies, or calls grouped into it. Any moving vehicle or other traffic should also be selectable, allowing the camera to follow it closely through the city.

### Inspect a building

Selecting a building should move the camera into a focused view of the whole building and open an information panel for its file. The building then becomes semi-transparent or expands into a blown-up view so its class sections and floors can be selected. Maybe a drill down effect.

Selecting a class or floor updates the camera and information panel for that element. The user can move directly between floors without returning to the city view.
