SYSTEM_PROMPT = """
<ROLE>
You are an AI documentation assistant. Your task is to generate comprehensive system documentation based on a given module name and its core code components.
</ROLE>

<OBJECTIVES>
Create documentation that helps developers and maintainers understand:
1. The module's purpose and core functionality
2. Architecture and component relationships
3. How the module fits into the overall system
</OBJECTIVES>

<DOCUMENTATION_STRUCTURE>
Generate documentation following this structure:

1. **Main Documentation File** (`{module_name}.md`):
   - Brief introduction and purpose
   - Architecture overview with diagrams
   - High-level functionality of each sub-module including references to its documentation file
   - Link to other module documentation instead of duplicating information

2. **Sub-module Documentation** (if applicable):
   - Detailed descriptions of each sub-module saved in the working directory under the name of `sub-module_name.md`
   - Core components and their responsibilities

3. **Visual Documentation**:
   - Mermaid architecture diagrams showing module relationships and dependencies
   - IMPORTANT: Use ONLY "graph TD" or "flowchart TD" syntax for diagrams
   - DO NOT use "sequenceDiagram", "classDiagram", or other diagram types
   - Each diagram node should represent a sub-module that links to its documentation file
   - Include edges showing relationships between modules

<ARCHITECTURE_DIAGRAM_EXAMPLE>
CORRECT - Architecture diagram with clickable nodes linking to child module docs:

```mermaid
graph TD
    core[Core Module]
    auth[Authentication]
    db[Database Layer]
    api[API Routes]
    utils[Utilities]
    
    core --> auth
    core --> db
    core --> api
    auth --> utils
    db --> utils
    
    click auth "authentication.md" "View Authentication Module"
    click db "database_layer.md" "View Database Module"
    click api "api_routes.md" "View API Module"
    click utils "utilities.md" "View Utilities Module"
```

Key requirements:
- Use "graph TD" or "flowchart TD" only
- Each node represents a sub-module or documentation file
- Use "click nodeId 'filename.md' 'tooltip'" to make nodes navigable
- Show relationships between modules with arrows
- DO NOT use classDiagram, sequenceDiagram, or other diagram types
</ARCHITECTURE_DIAGRAM_EXAMPLE>
</DOCUMENTATION_STRUCTURE>

<WORKFLOW>
1. Analyze the provided code components and module structure, explore the not given dependencies between the components if needed
2. Create the main `{module_name}.md` file with overview and architecture in working directory
3. Use `generate_sub_module_documentation` to generate detailed sub-modules documentation for COMPLEX modules which at least have more than 1 code file and are able to clearly split into sub-modules
4. Include relevant Mermaid diagrams throughout the documentation
5. After all sub-modules are documented, adjust `{module_name}.md` with ONLY ONE STEP to ensure all generated files including sub-modules documentation are properly cross-refered
</WORKFLOW>

<AVAILABLE_TOOLS>
- `str_replace_editor`: File system operations for creating and editing documentation files
- `read_code_components`: Explore additional code dependencies not included in the provided components
- `generate_sub_module_documentation`: Generate detailed documentation for individual sub-modules via sub-agents
</AVAILABLE_TOOLS>
""".strip()

LEAF_SYSTEM_PROMPT = """
<ROLE>
You are an AI documentation assistant. Your task is to generate comprehensive system documentation based on a given module name and its core code components.
</ROLE>

<OBJECTIVES>
Create a comprehensive documentation that helps developers and maintainers understand:
1. The module's purpose and core functionality
2. Architecture and component relationships
3. How the module fits into the overall system
</OBJECTIVES>

<DOCUMENTATION_REQUIREMENTS>
Generate documentation following the following requirements:
1. Structure: Brief introduction → comprehensive documentation with Mermaid diagrams
2. Diagrams: Use ONLY "graph TD" or "flowchart TD" for architecture diagrams. DO NOT use classDiagram or sequenceDiagram.
3. References: Link to other module documentation instead of duplicating information

<ARCHITECTURE_DIAGRAM_EXAMPLE>
CORRECT - Architecture diagram with clickable nodes:

```mermaid
graph TD
    main[Main Component]
    helper[Helper Utils]
    config[Configuration]
    
    main --> helper
    main --> config
    
    click helper "helper_utils.md" "View Helper Module"
    click config "configuration.md" "View Config Module"
```

Use "click nodeId 'filename.md' 'tooltip'" to make nodes navigable to other documentation files.
</ARCHITECTURE_DIAGRAM_EXAMPLE>
</DOCUMENTATION_REQUIREMENTS>

<WORKFLOW>
1. Analyze provided code components and module structure
2. Explore dependencies between components if needed
3. Generate complete {module_name}.md documentation file
</WORKFLOW>

<AVAILABLE_TOOLS>
- `str_replace_editor`: File system operations for creating and editing documentation files
- `read_code_components`: Explore additional code dependencies not included in the provided components
</AVAILABLE_TOOLS>
""".strip()

USER_PROMPT = """
Generate comprehensive documentation for the {module_name} module using the provided module tree and core components.

<MODULE_TREE>
{module_tree}
</MODULE_TREE>
* NOTE: You can refer the other modules in the module tree based on the dependencies between their core components to make the documentation more structured and avoid repeating the same information. Know that all documentation files are saved in the same folder not structured as module tree. e.g. [alt text]([ref_module_name].md)

<CORE_COMPONENT_CODES>
{formatted_core_component_codes}
</CORE_COMPONENT_CODES>
""".strip()

REPO_OVERVIEW_PROMPT = """
You are an AI documentation assistant. Your task is to generate a brief overview of the {repo_name} repository.

The overview should be a brief documentation of the repository, including:
- The purpose of the repository
- A mermaid architecture diagram showing the main modules and their relationships
- Each node in the diagram should be clickable and link to its documentation file

IMPORTANT: Use ONLY "graph TD" or "flowchart TD" syntax. DO NOT use classDiagram or sequenceDiagram.

Example architecture diagram with clickable nodes:
```mermaid
graph TD
    core[Core Module]
    auth[Authentication]
    db[Database]
    
    core --> auth
    core --> db
    
    click auth "authentication.md" "View Auth Module"
    click db "database.md" "View Database Module"
```

IMPORTANT: When creating links to module documentation, use the module's markdown file name format: [Module Name](module_name.md). 
For example, if a module is named "chat_module", link to it as [Chat Module](chat_module.md). 
DO NOT link to source code files - only link to the generated markdown documentation files.

Provide `{repo_name}` repo structure and its core modules documentation:
<REPO_STRUCTURE>
{repo_structure}
</REPO_STRUCTURE>

Please generate the overview of the `{repo_name}` repository in markdown format with the following structure:
<OVERVIEW>
overview_content
</OVERVIEW>
""".strip()

MODULE_OVERVIEW_PROMPT = """
You are an AI documentation assistant. Your task is to generate a brief overview of `{module_name}` module.

The overview should be a brief documentation of the module, including:
- The purpose of the module
- The architecture of the module visualized by mermaid diagrams
- The references to the core components documentation

IMPORTANT: Use ONLY "graph TD" or "flowchart TD" syntax. DO NOT use classDiagram or sequenceDiagram.

Example architecture diagram with clickable nodes:
```mermaid
graph TD
    main[Main Component]
    sub1[Sub Component 1]
    sub2[Sub Component 2]
    
    main --> sub1
    main --> sub2
    
    click sub1 "sub_component_1.md" "View Sub Component 1"
    click sub2 "sub_component_2.md" "View Sub Component 2"
```

Provide repo structure and core components documentation of the `{module_name}` module:
<REPO_STRUCTURE>
{repo_structure}
</REPO_STRUCTURE>

Please generate the overview of the `{module_name}` module in markdown format with the following structure:
<OVERVIEW>
overview_content
</OVERVIEW>
""".strip()

CLUSTER_REPO_PROMPT = """
Here is list of all potential core components of the repository (It's normal that some components are not essential to the repository):
<POTENTIAL_CORE_COMPONENTS>
{potential_core_components}
</POTENTIAL_CORE_COMPONENTS>

IMPORTANT: You MUST output the <GROUPED_COMPONENTS> tag FIRST, BEFORE any reasoning or explanation.
Group components by their file paths and logical relationships. Create modules based on directory structure and naming patterns.

Your response MUST start immediately with:
<GROUPED_COMPONENTS>
{{
    "module_name_1": {{
        "path": "path/to/module",
        "components": ["component_1", "component_2"]
    }},
    "module_name_2": {{
        "path": "path/to/other/module", 
        "components": ["component_3", "component_4"]
    }}
}}
</GROUPED_COMPONENTS>

Rules:
- Group by top-level directories (e.g., all components in "torch/nn/" -> "neural_network_module")
- Keep groups manageable (5-50 components each when possible)
- Use snake_case for module names
- Only include essential components, skip test/example files
- DO NOT include any reasoning, explanation, or text before the <GROUPED_COMPONENTS> tag
""".strip()

CLUSTER_MODULE_PROMPT = """
Here is the module tree of a repository:

<MODULE_TREE>
{module_tree}
</MODULE_TREE>

Here is list of all potential core components of the module {module_name} (It's normal that some components are not essential to the module):
<POTENTIAL_CORE_COMPONENTS>
{potential_core_components}
</POTENTIAL_CORE_COMPONENTS>

IMPORTANT: You MUST output the <GROUPED_COMPONENTS> tag FIRST, BEFORE any reasoning or explanation.
Group these components into smaller sub-modules based on file paths and logical relationships.

Your response MUST start immediately with:
<GROUPED_COMPONENTS>
{{
    "submodule_name_1": {{
        "path": "path/to/submodule",
        "components": ["component_1", "component_2"]
    }},
    "submodule_name_2": {{
        "path": "path/to/other/submodule",
        "components": ["component_3", "component_4"]
    }}
}}
</GROUPED_COMPONENTS>

Rules:
- Group by subdirectories and logical relationships
- Keep groups manageable (5-50 components each when possible)
- Use snake_case for submodule names
- Only include essential components
- DO NOT include any reasoning, explanation, or text before the <GROUPED_COMPONENTS> tag
""".strip()

FILTER_FOLDERS_PROMPT = """
Here is the list of relative paths of files, folders in 2-depth of project {project_name}:
```
{files}
```

In order to analyze the core functionality of the project, we need to analyze the files, folders representing the core functionality of the project.

Please shortlist the files, folders representing the core functionality and ignore the files, folders that are not essential to the core functionality of the project (e.g. test files, documentation files, etc.) from the list above.

Reasoning at first, then return the list of relative paths in JSON format.
"""

from typing import Dict, Any
from codewiki.src.file_manager import file_manager

EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".md": "markdown",
    ".sh": "bash",
    ".json": "json",
    ".yaml": "yaml",
    ".java": "java",
    ".js": "javascript",
    ".ts": "typescript",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".tsx": "typescript",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".cxx": "cpp",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".cs": "csharp"
}


def _count_total_components(module_tree: dict[str, any]) -> int:
    """Count total number of components across entire module tree."""
    total = 0
    for value in module_tree.values():
        total += len(value.get('components', []))
        if isinstance(value.get("children"), dict):
            total += _count_total_components(value["children"])
    return total


def _format_module_tree_full(module_tree: dict[str, any], current_module_name: str) -> str:
    """Format module tree with full component lists (for small repos)."""
    lines = []
    
    def _recurse(tree: dict[str, any], indent: int = 0):
        for key, value in tree.items():
            if key == current_module_name:
                lines.append(f"{'  ' * indent}{key} (current module)")
            else:
                lines.append(f"{'  ' * indent}{key}")
            
            lines.append(f"{'  ' * (indent + 1)} Core components: {', '.join(value['components'])}")
            if isinstance(value.get("children"), dict) and len(value["children"]) > 0:
                lines.append(f"{'  ' * (indent + 1)} Children:")
                _recurse(value["children"], indent + 2)
    
    _recurse(module_tree)
    return "\n".join(lines)


def _format_module_tree_tiered(module_tree: dict[str, any], current_module_name: str) -> str:
    """
    Format module tree with summaries for large repos.
    Shows structure + component counts, with full details only for current module and siblings.
    """
    lines = []
    lines.append("# Repository Module Structure")
    lines.append("# Note: For large repos, only current module shows full component list.")
    lines.append("# Use list_module_components(module_name) tool to get details for other modules.")
    lines.append("")
    
    def _recurse(tree: dict[str, any], indent: int = 0, parent_is_current: bool = False):
        for key, value in tree.items():
            comp_count = len(value.get('components', []))
            is_current = (key == current_module_name)
            
            # Module name
            if is_current:
                lines.append(f"{'  ' * indent}{key} (current module)")
            else:
                lines.append(f"{'  ' * indent}{key}")
            
            # Show full component list for current module and its siblings
            # For other modules, just show count
            if is_current or parent_is_current:
                lines.append(f"{'  ' * (indent + 1)} Core components: {', '.join(value['components'])}")
            else:
                lines.append(f"{'  ' * (indent + 1)} Components: {comp_count} items (use list_module_components to view)")
            
            # Recurse into children
            if isinstance(value.get("children"), dict) and len(value["children"]) > 0:
                lines.append(f"{'  ' * (indent + 1)} Children:")
                _recurse(value["children"], indent + 2, parent_is_current=is_current)
    
    _recurse(module_tree)
    return "\n".join(lines)


def format_user_prompt(module_name: str, core_component_ids: list[str], components: Dict[str, Any], module_tree: dict[str, any]) -> str:
    """
    Format the user prompt with module name and organized core component codes.
    
    For large repos (500+ components), uses tiered module tree format with summaries.
    For small repos, uses full component list format.
    
    Args:
        module_name: Name of the module to document
        core_component_ids: List of component IDs to include
        components: Dictionary mapping component IDs to CodeComponent objects
    
    Returns:
        Formatted user prompt string
    """
    from codewiki.src.config import LARGE_REPO_COMPONENT_THRESHOLD
    import logging
    logger = logging.getLogger(__name__)

    # Count total components to decide formatting approach
    total_components = _count_total_components(module_tree)
    
    # Choose module tree format based on repo size
    if total_components > LARGE_REPO_COMPONENT_THRESHOLD:
        logger.info(f"[PROMPT] Large repo detected ({total_components} components > {LARGE_REPO_COMPONENT_THRESHOLD})")
        logger.info(f"[PROMPT] Using tiered module tree format with summaries")
        formatted_module_tree = _format_module_tree_tiered(module_tree, module_name)
    else:
        formatted_module_tree = _format_module_tree_full(module_tree, module_name)

    # print(f"Formatted module tree:\n{formatted_module_tree}")

    # Group core component IDs by their file path
    grouped_components: dict[str, list[str]] = {}
    for component_id in core_component_ids:
        if component_id not in components:
            continue
        component = components[component_id]
        path = component.relative_path
        if path not in grouped_components:
            grouped_components[path] = []
        grouped_components[path].append(component_id)

    core_component_codes = ""
    for path, component_ids_in_file in grouped_components.items():
        core_component_codes += f"# File: {path}\n\n"
        
        # Get file extension for syntax highlighting
        ext = '.' + path.split('.')[-1] if '.' in path else '.txt'
        lang = EXTENSION_TO_LANGUAGE.get(ext, 'text')
        
        # Include each component's source code (NOT the entire file)
        for component_id in component_ids_in_file:
            component = components[component_id]
            core_component_codes += f"## Component: {component_id}\n"
            if hasattr(component, 'start_line') and hasattr(component, 'end_line'):
                core_component_codes += f"Lines {component.start_line}-{component.end_line}\n"
            core_component_codes += f"```{lang}\n"
            
            # Use component.source_code instead of reading entire file
            if hasattr(component, 'source_code') and component.source_code:
                core_component_codes += component.source_code
            else:
                core_component_codes += f"# Source code not available for {component_id}\n"
            
            core_component_codes += "\n```\n\n"
        
    return USER_PROMPT.format(module_name=module_name, formatted_core_component_codes=core_component_codes, module_tree=formatted_module_tree)



def format_cluster_prompt(potential_core_components: str, module_tree: dict[str, any] = {}, module_name: str = None) -> str:
    """
    Format the cluster prompt with potential core components and module tree.
    """

    # format module tree
    lines = []

    # print(f"Module tree:\n{json.dumps(module_tree, indent=2)}")
    
    def _format_module_tree(module_tree: dict[str, any], indent: int = 0):
        for key, value in module_tree.items():
            if key == module_name:
                lines.append(f"{'  ' * indent}{key} (current module)")
            else:
                lines.append(f"{'  ' * indent}{key}")
            
            lines.append(f"{'  ' * (indent + 1)} Core components: {', '.join(value['components'])}")
            if ("children" in value) and isinstance(value["children"], dict) and len(value["children"]) > 0:
                lines.append(f"{'  ' * (indent + 1)} Children:")
                _format_module_tree(value["children"], indent + 2)
    
    _format_module_tree(module_tree, 0)
    formatted_module_tree = "\n".join(lines)


    if module_tree == {}:
        return CLUSTER_REPO_PROMPT.format(potential_core_components=potential_core_components)
    else:
        return CLUSTER_MODULE_PROMPT.format(potential_core_components=potential_core_components, module_tree=formatted_module_tree, module_name=module_name)