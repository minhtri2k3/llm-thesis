## ADDED Requirements

### Requirement: Vietnamese module documentation
Every Python module under `fashion_agent/agent` SHALL include a Vietnamese module docstring that explains the file's role in the agent pipeline.

#### Scenario: Opening any agent module
- **WHEN** a developer opens a Python file in `fashion_agent/agent`
- **THEN** the top of the file contains a Vietnamese module docstring describing the module purpose and pipeline role

### Requirement: Vietnamese method documentation
Every public class, public function, dataclass, and important private helper under `fashion_agent/agent` SHALL have a Vietnamese docstring that summarizes what it does and how it is used.

#### Scenario: Inspecting a helper method
- **WHEN** a developer reads a method such as `_resolve_search_query()` or `save_selected_items()`
- **THEN** the method docstring explains its purpose, inputs/outputs, and the surrounding flow when relevant

### Requirement: Documentation-only behavior
Applying Vietnamese docstrings in `fashion_agent/agent` SHALL not change runtime behavior, prompt semantics, database schema, or search results.

#### Scenario: Running the agent after documentation updates
- **WHEN** the application imports and executes the updated modules
- **THEN** the existing runtime behavior remains unchanged aside from the new source-level documentation
