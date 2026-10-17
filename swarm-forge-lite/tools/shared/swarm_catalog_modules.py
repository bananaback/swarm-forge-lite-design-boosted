# Auto-generated split from swarm_json.py

from swarm_catalog_support import _tool

MODULES_TOOLS = [
    _tool(
        "modules",
        "resolve",
        "-",
        "The module map, the frozen interfaces, and the module layout of a subsystem.",
        [("subsystem", "string", "-", "The lane. Sets SWARM_LANE; the same string as the record id. (required).")],
        "{subsystem, architecture, interfaces:[{id,path}], modules:[{id,design,skeleton}], split_ready}",
        "swarm.modules({subsystem:'clip'})",
        {
            "subsystem": "clip",
            "architecture": "design/subsystems/clip/02-architect/ARCHITECTURE.md",
            "interfaces": [
                {
                    "id": "engine-read-view",
                    "path": "design/subsystems/clip/interfaces/engine-read-view.md",
                }
            ],
            "modules": [{"id": "engine-read-view", "design": True, "skeleton": False}],
            "split_ready": True,
        },
        "Use it to split the designers: the modules with their skeletons, and the frozen interfaces. Code Mode returns a JSON string; parse with JSON.parse() before reading fields.",
        "orchestrator, critic",
    ),
    _tool(
        "interface",
        "resolve",
        "-",
        "The frozen interface text of one module.",
        [("subsystem", "string", "-", "The lane. Sets SWARM_LANE; the same string as the record id. (required)."), ("module", "string", "-", "The module id (required).")],
        "{subsystem, module, path, text}",
        "swarm.interface({subsystem:'clip',module:'engine-read-view'})",
        {
            "module": "engine-read-view",
            "path": "design/subsystems/clip/interfaces/engine-read-view.md",
            "text": "INTERFACE engine-read-view ...",
        },
        "Read the frozen interface of a module before you design or critique it. Only the architect edits it. Code Mode returns a JSON string; parse with JSON.parse() before reading fields.",
        "orchestrator, designer, critic",
    ),
    _tool(
        "goal",
        "resolve",
        "-",
        "Read, or write, the orchestrator's scratchpad (design/subsystems/<subsystem>/GOAL.md).",
        [("subsystem", "string", "-", "The lane. Sets SWARM_LANE; the same string as the record id. (required)."), ("text", "string", "-", "The new scratchpad text. Omit to read.")],
        "{subsystem, path, exists, text}",
        "swarm.goal({subsystem:'clip'})  ·  swarm.goal({subsystem:'clip',text:'# GOAL ...'})",
        {
            "subsystem": "clip",
            "path": "design/subsystems/clip/GOAL.md",
            "exists": True,
            "text": "# GOAL — clip ...",
        },
        "The orchestrator's scratchpad. Write the pipeline state here, and read it first on a resume. Code Mode returns a JSON string; parse with JSON.parse() before reading fields.",
        "orchestrator",
    ),
]
