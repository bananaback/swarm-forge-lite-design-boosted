"""The mutating ops of the uml model tool.

Every handler changes the model dict in place and returns `(data, text)`. The
caller validates the result and writes the file, so a handler never touches the
disk. A handler raises `UmlModelError` when the request is bad.
"""

from __future__ import annotations

import json

from .errors import UmlModelError
from .validate import KINDS, STEREOTYPES

OP_ANNOTATIONS = ("cqs", "pre", "post", "invariant", "visibility")
CLASS_ANNOTATIONS = ("core", "secret", "responsibility")


# --------------------------------------------------------------------------- #
# lookups and small helpers
# --------------------------------------------------------------------------- #


def _packages(model: dict) -> list:
    if not isinstance(model.get("packages"), list):
        model["packages"] = []
    return model["packages"]


def _all_classes(model: dict) -> list:
    return [cls for pkg in _packages(model) for cls in (pkg.get("classes") or [])]


def _require(params: dict, name: str):
    value = params.get(name)
    if value is None or value == "":
        raise UmlModelError(f"pass --{name}")
    return value


def _find_package(model: dict, pid: str):
    for pkg in _packages(model):
        if str(pkg.get("id")) == pid:
            return pkg
    return None


def _ensure_package(model: dict, pid: str) -> dict:
    pkg = _find_package(model, pid)
    if pkg is None:
        pkg = {"id": pid, "label": pid, "classes": []}
        _packages(model).append(pkg)
    if not isinstance(pkg.get("classes"), list):
        pkg["classes"] = []
    return pkg


def _find_class(model: dict, cid: str) -> tuple[dict, dict]:
    for pkg in _packages(model):
        for cls in pkg.get("classes") or []:
            if str(cls.get("id")) == cid:
                return pkg, cls
    raise UmlModelError(f"no such class: {cid}")


def _find_op(cls: dict, name: str) -> dict:
    for op in cls.get("ops") or []:
        if str(op.get("name")) == name:
            return op
    raise UmlModelError(f"no such op on {cls.get('id')}: {name}")


def _field_text(field) -> str:
    return field if isinstance(field, str) else str(field.get("text", ""))


def _find_field(cls: dict, text: str) -> dict:
    for field in cls.get("fields") or []:
        if _field_text(field) == text:
            return field
    raise UmlModelError(f"no such field on {cls.get('id')}: {text}")


def _annotations(owner: dict) -> dict:
    if not isinstance(owner.get("annotations"), dict):
        owner["annotations"] = {}
    return owner["annotations"]


def _check_stereotype(value: str) -> None:
    if value not in STEREOTYPES:
        raise UmlModelError(f"stereotype must be one of {', '.join(STEREOTYPES)}")


def _check_kind(value: str) -> None:
    if value not in KINDS:
        raise UmlModelError(f"kind must be one of {', '.join(KINDS)}")


def _risky_edges(model: dict, cid: str) -> list:
    return [
        edge
        for edge in model.get("edges") or []
        if str(edge.get("from")) == cid or str(edge.get("to")) == cid
    ]


# --------------------------------------------------------------------------- #
# classes
# --------------------------------------------------------------------------- #


def add_class(model: dict, params: dict) -> tuple[dict, str]:
    """Add a class, its annotations, and its fields."""
    cid = _require(params, "id")
    if any(str(cls.get("id")) == cid for cls in _all_classes(model)):
        raise UmlModelError(f"class exists: {cid}")
    stereotype = str(params.get("stereotype") or "class")
    _check_stereotype(stereotype)
    pid = str(params.get("package") or cid.split(".")[0])
    pkg = _ensure_package(model, pid)
    cls = {
        "id": cid,
        "name": params.get("name") or cid.split(".")[-1],
        "stereotype": stereotype,
    }
    _write_class_annotations(cls, params)
    fields = params.get("field") or []
    if fields:
        cls["fields"] = [{"text": str(text)} for text in fields]
    pkg["classes"].append(cls)
    return {"id": cid, "package": pid}, f"added class {cid} to {pid}"


def _write_class_annotations(cls: dict, params: dict) -> None:
    for key in CLASS_ANNOTATIONS:
        if key in params:
            _annotations(cls)[key] = params[key]


def set_class(model: dict, params: dict) -> tuple[dict, str]:
    """Set one or more fields of an existing class."""
    cid = _require(params, "id")
    _pkg, cls = _find_class(model, cid)
    changed = []
    for key in ("name", "ns", "level", "hide-members"):
        if key in params:
            cls[key] = params[key]
            changed.append(key)
    if "stereotype" in params:
        _check_stereotype(str(params["stereotype"]))
        cls["stereotype"] = params["stereotype"]
        changed.append("stereotype")
    _write_class_annotations(cls, params)
    changed.extend(key for key in CLASS_ANNOTATIONS if key in params)
    if not changed:
        raise UmlModelError("set-class needs at least one field to set")
    return {"id": cid, "set": changed}, f"set {cid}: {', '.join(changed)}"


def remove_class(model: dict, params: dict) -> tuple[dict, str]:
    """Remove a class, its edges, and its edge-kind overrides.

    A package that this removal leaves with no classes goes too, so a package
    that `add-class` created does not survive its last class. A package with a
    remaining class stays.
    """
    cid = _require(params, "id")
    pkg, cls = _find_class(model, cid)
    pkg["classes"].remove(cls)
    dropped = _risky_edges(model, cid)
    if dropped:
        model["edges"] = [
            edge for edge in model.get("edges") or [] if edge not in dropped
        ]
        _drop_edge_kinds(model, cid)
    pruned = _prune_package(model, pkg)
    text = f"removed {cid} and {len(dropped)} edge(s)"
    if pruned:
        text += f" and pruned the empty package {pruned}"
    return {
        "id": cid,
        "edges_removed": len(dropped),
        "package_removed": pruned,
    }, text


def _prune_package(model: dict, pkg: dict):
    """Drop a package this removal emptied. Return its id, or None."""
    if pkg.get("classes"):
        return None
    model["packages"] = [item for item in _packages(model) if item is not pkg]
    return str(pkg.get("id"))


def rename_class(model: dict, params: dict) -> tuple[dict, str]:
    """Rename a class id, and rewrite every edge and override that names it."""
    old = _require(params, "id")
    new = str(_require(params, "new"))
    if any(str(cls.get("id")) == new for cls in _all_classes(model)):
        raise UmlModelError(f"class exists: {new}")
    _pkg, cls = _find_class(model, old)
    cls["id"] = new
    touched = 0
    for edge in model.get("edges") or []:
        if str(edge.get("from")) == old:
            edge["from"] = new
            touched += 1
        if str(edge.get("to")) == old:
            edge["to"] = new
            touched += 1
    _rename_edge_kinds(model, old, new)
    return {
        "id": new,
        "edges": touched,
    }, f"renamed {old} -> {new} ({touched} edge end(s))"


def move_class(model: dict, params: dict) -> tuple[dict, str]:
    """Move a class to another package, creating the package if it is new."""
    cid = _require(params, "id")
    pid = str(_require(params, "package"))
    pkg, cls = _find_class(model, cid)
    if str(pkg.get("id")) == pid:
        raise UmlModelError(f"{cid} is already in {pid}")
    pkg["classes"].remove(cls)
    _ensure_package(model, pid)["classes"].append(cls)
    return {"id": cid, "package": pid}, f"moved {cid} to {pid}"


# --------------------------------------------------------------------------- #
# ops
# --------------------------------------------------------------------------- #


def add_op(model: dict, params: dict) -> tuple[dict, str]:
    """Add an op, with its args and its contract annotations."""
    cid = _require(params, "id")
    name = str(_require(params, "name"))
    _pkg, cls = _find_class(model, cid)
    if any(str(op.get("name")) == name for op in cls.get("ops") or []):
        raise UmlModelError(f"op exists on {cid}: {name}")
    op = {"name": name}
    _write_op(op, params)
    cls.setdefault("ops", []).append(op)
    return {"id": cid, "op": name}, f"added op {cid}.{name}"


def _write_op(op: dict, params: dict) -> None:
    if "args" in params:
        op["args"] = params["args"]
    for key in ("returns", "type"):
        if key in params:
            op[key] = params[key]
    if "private" in params:
        op["private"] = bool(params["private"])
    for key in OP_ANNOTATIONS:
        if key in params:
            _annotations(op)[key] = params[key]


def set_op(model: dict, params: dict) -> tuple[dict, str]:
    """Set one or more fields of an existing op."""
    cid = _require(params, "id")
    name = str(_require(params, "name"))
    _pkg, cls = _find_class(model, cid)
    op = _find_op(cls, name)
    before = dict(op)
    _write_op(op, params)
    if op == before:
        raise UmlModelError("set-op needs at least one field to set")
    return {"id": cid, "op": name}, f"set op {cid}.{name}"


def remove_op(model: dict, params: dict) -> tuple[dict, str]:
    """Remove an op from a class."""
    cid = _require(params, "id")
    name = str(_require(params, "name"))
    _pkg, cls = _find_class(model, cid)
    op = _find_op(cls, name)
    cls["ops"].remove(op)
    return {"id": cid, "op": name}, f"removed op {cid}.{name}"


# --------------------------------------------------------------------------- #
# fields
# --------------------------------------------------------------------------- #


def add_field(model: dict, params: dict) -> tuple[dict, str]:
    """Add a field to a class."""
    cid = _require(params, "id")
    text = str(_require(params, "text"))
    _pkg, cls = _find_class(model, cid)
    field = {"text": text}
    if params.get("private"):
        field["private"] = True
    cls.setdefault("fields", []).append(field)
    return {"id": cid, "text": text}, f"added field to {cid}: {text}"


def set_field(model: dict, params: dict) -> tuple[dict, str]:
    """Replace the text of a field, matched by its current text."""
    cid = _require(params, "id")
    text = str(_require(params, "text"))
    new = str(_require(params, "new"))
    _pkg, cls = _find_class(model, cid)
    found = _find_field(cls, text)
    if isinstance(found, str):
        cls["fields"][cls["fields"].index(found)] = new
    else:
        found["text"] = new
        if "private" in params:
            found["private"] = bool(params["private"])
    return {"id": cid, "text": new}, f"set field on {cid}: {new}"


# --------------------------------------------------------------------------- #
# edges
# --------------------------------------------------------------------------- #


def add_edge(model: dict, params: dict) -> tuple[dict, str]:
    """Add one edge between two known classes."""
    left = str(_require(params, "from"))
    right = str(_require(params, "to"))
    if left == right:
        raise UmlModelError("an edge may not point at itself")
    kind = str(params.get("kind") or "association")
    _check_kind(kind)
    for edge in model.get("edges") or []:
        if str(edge.get("from")) == left and str(edge.get("to")) == right:
            raise UmlModelError(f"edge exists: {left} -> {right}; use set-edge-kind")
    edge = {"from": left, "to": right, "kind": kind}
    if params.get("label"):
        edge["label"] = params["label"]
    model.setdefault("edges", []).append(edge)
    return {
        "from": left,
        "to": right,
        "kind": kind,
    }, f"added edge {left} -> {right} ({kind})"


def set_edge_kind(model: dict, params: dict) -> tuple[dict, str]:
    """Change the kind of an existing edge."""
    left = str(_require(params, "from"))
    right = str(_require(params, "to"))
    kind = str(_require(params, "kind"))
    _check_kind(kind)
    for edge in model.get("edges") or []:
        if str(edge.get("from")) == left and str(edge.get("to")) == right:
            edge["kind"] = kind
            return {
                "from": left,
                "to": right,
                "kind": kind,
            }, f"set {left} -> {right} to {kind}"
    raise UmlModelError(f"no such edge: {left} -> {right}")


def remove_edge(model: dict, params: dict) -> tuple[dict, str]:
    """Remove an edge and its edge-kind override."""
    left = str(_require(params, "from"))
    right = str(_require(params, "to"))
    kept = [
        edge
        for edge in model.get("edges") or []
        if not (str(edge.get("from")) == left and str(edge.get("to")) == right)
    ]
    if len(kept) == len(model.get("edges") or []):
        raise UmlModelError(f"no such edge: {left} -> {right}")
    model["edges"] = kept
    (model.get("edge-kinds") or {}).pop(f"{left}->{right}", None)
    return {"from": left, "to": right}, f"removed edge {left} -> {right}"


def _drop_edge_kinds(model: dict, cid: str) -> None:
    kinds = model.get("edge-kinds")
    if not isinstance(kinds, dict):
        return
    for key in list(kinds):
        left, _arrow, right = key.partition("->")
        if left == cid or right == cid:
            del kinds[key]


def _rename_edge_kinds(model: dict, old: str, new: str) -> None:
    kinds = model.get("edge-kinds")
    if not isinstance(kinds, dict) or not kinds:
        return
    renamed = {}
    for key, value in kinds.items():
        left, arrow, right = key.partition("->")
        renamed[
            f"{new if left == old else left}{arrow}{new if right == old else right}"
        ] = value
    model["edge-kinds"] = renamed


# --------------------------------------------------------------------------- #
# model-level keys
# --------------------------------------------------------------------------- #


def set_levels(model: dict, params: dict) -> tuple[dict, str]:
    """Replace the level groups, inner first."""
    levels = params.get("levels")
    if not isinstance(levels, list) or not all(isinstance(g, list) for g in levels):
        raise UmlModelError("levels must be a JSON list of lists")
    model["levels"] = levels
    return {"levels": len(levels)}, f"set {len(levels)} level group(s)"


def set_annotation(model: dict, params: dict) -> tuple[dict, str]:
    """Set one annotation on a class, or on one of its ops."""
    cid = _require(params, "id")
    key = str(_require(params, "key"))
    value = _coerce(_require(params, "value"))
    _pkg, cls = _find_class(model, cid)
    op_name = params.get("op-name")
    owner = _find_op(cls, str(op_name)) if op_name else cls
    _annotations(owner)[key] = value
    target = f"{cid}.{op_name}" if op_name else cid
    return {"id": target, "key": key, "value": value}, f"set {target}.annotations.{key}"


def _coerce(value):
    """Turn a text value into a bool, a number, or a nested value when it can."""
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def add_foreign(model: dict, params: dict) -> tuple[dict, str]:
    """Add a foreign id (an external oval)."""
    pid = str(_require(params, "id"))
    foreign = model.setdefault("foreign", [])
    if pid in foreign:
        raise UmlModelError(f"foreign id exists: {pid}")
    foreign.append(pid)
    return {"foreign": pid}, f"added foreign {pid}"


def remove_foreign(model: dict, params: dict) -> tuple[dict, str]:
    """Remove a foreign id."""
    pid = str(_require(params, "id"))
    foreign = model.get("foreign") or []
    if pid not in foreign:
        raise UmlModelError(f"no such foreign id: {pid}")
    foreign.remove(pid)
    return {"foreign": pid}, f"removed foreign {pid}"


def set_title(model: dict, params: dict) -> tuple[dict, str]:
    """Set the model title."""
    title = str(_require(params, "title"))
    model["title"] = title
    return {"title": title}, "set title"


def set_direction(model: dict, params: dict) -> tuple[dict, str]:
    """Set the layout direction: tb or lr."""
    direction = str(_require(params, "direction"))
    if direction not in ("tb", "lr"):
        raise UmlModelError("direction must be tb or lr")
    model["direction"] = direction
    return {"direction": direction}, f"set direction {direction}"
