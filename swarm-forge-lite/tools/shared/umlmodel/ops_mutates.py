"""Op catalog: mutate ops."""

from __future__ import annotations

from . import mutate
from .ops_dsl import M, Op, p

MUTATES = [
    Op(
        "add-class",
        "mutate",
        "Add a class with its annotations and fields.",
        [
            p(
                "id",
                required=True,
                purpose="The new class id, component.Name.",
                example="--id core.New",
            ),
            p(
                "name",
                purpose="The display name. Default: the last id segment.",
                example="--name New",
            ),
            p(
                "stereotype",
                purpose="class | interface | abstract | enum. Default class.",
                example="--stereotype interface",
            ),
            p(
                "package",
                purpose="The target package. Default: the id's first segment.",
                example="--package core",
            ),
            p("core", "bool", purpose="Set annotations.core.", example="--core true"),
            p(
                "secret",
                purpose="Set annotations.secret.",
                example='--secret "the on-disk format"',
            ),
            p(
                "responsibility",
                purpose="Set annotations.responsibility.",
                example='--responsibility "Hold one clip."',
            ),
            p(
                "field",
                multi=True,
                purpose="A field text; repeat for more than one.",
                example='--field "isbn : String"',
            ),
        ],
        f"umlmodel add-class {M} --id core.New --name New --package core",
        mutate.add_class,
    ),
    Op(
        "set-class",
        "mutate",
        "Set fields of an existing class. Set only what you name.",
        [
            p("id", required=True, purpose="The class id.", example="--id core.New"),
            p("name", purpose="The display name.", example="--name Better"),
            p(
                "stereotype",
                purpose="class | interface | abstract | enum.",
                example="--stereotype abstract",
            ),
            p("ns", purpose="The namespace note.", example="--ns core"),
            p("level", "int", purpose="The explicit level rank.", example="--level 2"),
            p(
                "hide-members",
                "bool",
                purpose="Hide the member list in the view.",
                example="--hide-members true",
            ),
            p("core", "bool", purpose="Set annotations.core.", example="--core false"),
            p("secret", purpose="Set annotations.secret.", example='--secret "..."'),
            p(
                "responsibility",
                purpose="Set annotations.responsibility.",
                example='--responsibility "..."',
            ),
        ],
        f"umlmodel set-class {M} --id core.New --stereotype interface --core true",
        mutate.set_class,
    ),
    Op(
        "remove-class",
        "mutate",
        "Remove a class, and every edge and override that names it.",
        [p("id", required=True, purpose="The class id.", example="--id core.Old")],
        f"umlmodel remove-class {M} --id core.Old",
        mutate.remove_class,
    ),
    Op(
        "rename-class",
        "mutate",
        "Rename a class id, and rewrite every edge that names it.",
        [
            p(
                "id",
                required=True,
                purpose="The current class id.",
                example="--id core.Old",
            ),
            p(
                "new",
                required=True,
                purpose="The new class id.",
                example="--new core.New",
            ),
        ],
        f"umlmodel rename-class {M} --id core.Old --new core.New",
        mutate.rename_class,
    ),
    Op(
        "move-class",
        "mutate",
        "Move a class to another package.",
        [
            p("id", required=True, purpose="The class id.", example="--id core.New"),
            p(
                "package",
                required=True,
                purpose="The target package id.",
                example="--package shell",
            ),
        ],
        f"umlmodel move-class {M} --id core.New --package shell",
        mutate.move_class,
    ),
    Op(
        "add-op",
        "mutate",
        "Add an op to a class, with its args and contract annotations.",
        [
            p("id", required=True, purpose="The class id.", example="--id core.New"),
            p("name", required=True, purpose="The op name.", example="--name run"),
            p(
                "args",
                "json",
                purpose="The arg list, as JSON.",
                example='--args \'[{"name":"x","type":"int"}]\'',
            ),
            p("returns", purpose="The return type.", example="--returns None"),
            p("type", purpose="A member type note.", example="--type str"),
            p("cqs", purpose="command | query.", example="--cqs command"),
            p("pre", purpose="The precondition.", example='--pre "x > 0"'),
            p("post", purpose="The postcondition.", example='--post "the run is done"'),
            p(
                "invariant",
                purpose="The invariant.",
                example='--invariant "x stays positive"',
            ),
            p(
                "visibility",
                purpose="The visibility note.",
                example="--visibility private",
            ),
            p(
                "private",
                "bool",
                purpose="Mark the op private.",
                example="--private true",
            ),
        ],
        f"umlmodel add-op {M} --id core.New --name run --cqs command --post done",
        mutate.add_op,
    ),
    Op(
        "set-op",
        "mutate",
        "Set fields of an existing op. Set only what you name.",
        [
            p("id", required=True, purpose="The class id.", example="--id core.New"),
            p(
                "name",
                required=True,
                purpose="The op name, to identify it.",
                example="--name run",
            ),
            p(
                "args",
                "json",
                purpose="The new arg list, as JSON.",
                example='--args \'[{"name":"x"}]\'',
            ),
            p("returns", purpose="The return type.", example="--returns bool"),
            p("type", purpose="A member type note.", example="--type str"),
            p(
                "private",
                "bool",
                purpose="Mark the op private.",
                example="--private false",
            ),
            p("cqs", purpose="command | query.", example="--cqs query"),
            p("pre", purpose="The precondition.", example='--pre "none"'),
            p("post", purpose="The postcondition.", example='--post "the answer"'),
            p("invariant", purpose="The invariant.", example='--invariant "..."'),
            p(
                "visibility",
                purpose="The visibility note.",
                example="--visibility public",
            ),
        ],
        f"umlmodel set-op {M} --id core.New --name run --returns bool",
        mutate.set_op,
    ),
    Op(
        "remove-op",
        "mutate",
        "Remove an op from a class.",
        [
            p("id", required=True, purpose="The class id.", example="--id core.New"),
            p("name", required=True, purpose="The op name.", example="--name run"),
        ],
        f"umlmodel remove-op {M} --id core.New --name run",
        mutate.remove_op,
    ),
    Op(
        "add-field",
        "mutate",
        "Add a field to a class.",
        [
            p("id", required=True, purpose="The class id.", example="--id core.New"),
            p(
                "text",
                required=True,
                purpose="The field text.",
                example='--text "isbn : String"',
            ),
            p(
                "private",
                "bool",
                purpose="Mark the field private.",
                example="--private true",
            ),
        ],
        f'umlmodel add-field {M} --id core.New --text "isbn : String"',
        mutate.add_field,
    ),
    Op(
        "set-field",
        "mutate",
        "Replace a field's text, matched by its current text.",
        [
            p("id", required=True, purpose="The class id.", example="--id core.New"),
            p(
                "text",
                required=True,
                purpose="The current field text.",
                example='--text "isbn : String"',
            ),
            p(
                "new",
                required=True,
                purpose="The new field text.",
                example='--new "isbn : str"',
            ),
            p(
                "private",
                "bool",
                purpose="Set the private flag.",
                example="--private false",
            ),
        ],
        f'umlmodel set-field {M} --id core.New --text "isbn : String" --new "isbn : str"',
        mutate.set_field,
    ),
    Op(
        "add-edge",
        "mutate",
        "Add one edge between two known classes.",
        [
            p(
                "from",
                required=True,
                purpose="The source class id.",
                example="--from shell.Svc",
            ),
            p(
                "to",
                required=True,
                purpose="The target class id.",
                example="--to core.New",
            ),
            p(
                "kind",
                purpose="The edge kind. Default association.",
                example="--kind dependency",
            ),
            p("label", purpose="An edge label.", example='--label "uses"'),
        ],
        f"umlmodel add-edge {M} --from shell.Svc --to core.New --kind dependency",
        mutate.add_edge,
    ),
    Op(
        "set-edge-kind",
        "mutate",
        "Change the kind of an existing edge.",
        [
            p(
                "from",
                required=True,
                purpose="The source class id.",
                example="--from shell.Svc",
            ),
            p(
                "to",
                required=True,
                purpose="The target class id.",
                example="--to core.New",
            ),
            p(
                "kind",
                required=True,
                purpose="The new edge kind.",
                example="--kind implements",
            ),
        ],
        f"umlmodel set-edge-kind {M} --from shell.Svc --to core.New --kind implements",
        mutate.set_edge_kind,
    ),
    Op(
        "remove-edge",
        "mutate",
        "Remove an edge and its edge-kind override.",
        [
            p(
                "from",
                required=True,
                purpose="The source class id.",
                example="--from shell.Svc",
            ),
            p(
                "to",
                required=True,
                purpose="The target class id.",
                example="--to core.New",
            ),
        ],
        f"umlmodel remove-edge {M} --from shell.Svc --to core.New",
        mutate.remove_edge,
    ),
    Op(
        "set-levels",
        "mutate",
        "Replace the level groups, inner first.",
        [
            p(
                "levels",
                "json",
                required=True,
                purpose="The level groups, as a JSON list of lists.",
                example='--levels \'[["core"],["shell"]]\'',
            )
        ],
        f'umlmodel set-levels {M} --levels \'[["core"],["shell"]]\'',
        mutate.set_levels,
    ),
    Op(
        "set-annotation",
        "mutate",
        "Set one annotation on a class, or on one of its ops.",
        [
            p("id", required=True, purpose="The class id.", example="--id core.New"),
            p(
                "key",
                required=True,
                purpose="The annotation key.",
                example="--key core",
            ),
            p(
                "value",
                required=True,
                purpose="The value. JSON is decoded when it parses.",
                example="--value true",
            ),
            p(
                "op-name",
                purpose="Set on this op of the class instead.",
                example="--op-name run",
            ),
        ],
        f"umlmodel set-annotation {M} --id core.New --key core --value true",
        mutate.set_annotation,
    ),
    Op(
        "add-foreign",
        "mutate",
        "Add a foreign id (an external oval).",
        [
            p(
                "id",
                required=True,
                purpose="The foreign id or prefix.",
                example="--id pyservicemaker",
            )
        ],
        f"umlmodel add-foreign {M} --id pyservicemaker",
        mutate.add_foreign,
    ),
    Op(
        "remove-foreign",
        "mutate",
        "Remove a foreign id.",
        [
            p(
                "id",
                required=True,
                purpose="The foreign id.",
                example="--id pyservicemaker",
            )
        ],
        f"umlmodel remove-foreign {M} --id pyservicemaker",
        mutate.remove_foreign,
    ),
    Op(
        "set-title",
        "mutate",
        "Set the model title.",
        [
            p(
                "title",
                required=True,
                purpose="The new title.",
                example='--title "clip - the seam"',
            )
        ],
        f'umlmodel set-title {M} --title "clip"',
        mutate.set_title,
    ),
    Op(
        "set-direction",
        "mutate",
        "Set the layout direction: tb or lr.",
        [
            p(
                "direction",
                required=True,
                purpose="tb (top-bottom) or lr (left-right).",
                example="--direction lr",
            )
        ],
        f"umlmodel set-direction {M} --direction lr",
        mutate.set_direction,
    ),
]

