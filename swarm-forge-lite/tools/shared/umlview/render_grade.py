from __future__ import annotations

import math

CRAP_THRESHOLDS = {"green": 8, "yellow": 12, "red": 20}
GRADE_BEST = 10.0
GRADE_MID = 5.5
GRADE_WORST = 1.0


def crap_band(score):
    """config.clj `crap-band`: the traffic light for a CRAP score. Missing is red."""
    if score is None:
        return "red"
    if score <= CRAP_THRESHOLDS["green"]:
        return "green"
    if score <= CRAP_THRESHOLDS["yellow"]:
        return "yellow"
    return "red"


def _lerp(x, x0, x1, y0, y1):
    """config.clj `lerp`: linear interpolation between two stops."""
    if float(x0) == float(x1):
        return float(y0)
    t = (float(x) - float(x0)) / (float(x1) - float(x0))
    return y0 + t * (y1 - y0)


def _along(x, x0, x1, x2, y0, y1, y2):
    """config.clj `along`: clamp x onto the stops [x0 x1 x2] mapped to [y0 y1 y2]."""
    x = float(x)
    if x <= x0:
        return y0
    if x <= x1:
        return _lerp(x, x0, x1, y0, y1)
    if x <= x2:
        return _lerp(x, x1, x2, y1, y2)
    return y2


def crap_risk(crap):
    """config.clj `crap-risk`: mu + sigma of a pooled CRAP map, or None."""
    if not crap or crap.get("mu") is None:
        return None
    return float(crap["mu"]) + float(crap.get("sigma") or 0)


def crap_grade(score):
    """config.clj `crap-grade`: the CRAP risk on the 1-10 scale, 10 is best.
    Missing counts as red (1)."""
    if score is None:
        return GRADE_WORST
    return _along(
        score,
        CRAP_THRESHOLDS["green"],
        CRAP_THRESHOLDS["yellow"],
        CRAP_THRESHOLDS["red"],
        GRADE_BEST,
        GRADE_MID,
        GRADE_WORST,
    )


def combined_grade(*grades):
    """config.clj `combined-grade`, with the mutation half dropped: the mean of
    the present grades. None when no grade is present."""
    present = [g for g in grades if g is not None]
    if not present:
        return None
    return sum(present) / len(present)


def _round1(x):
    """config.clj `round1`: the nearest tenth."""
    return float(math.floor(float(x) * 10 + 0.5) / 10)


def score_of(crap):
    """config.clj `score-of`: a CRAP number, or the mu of a CRAP map."""
    if isinstance(crap, bool):
        return None
    if isinstance(crap, (int, float)):
        return float(crap)
    if isinstance(crap, dict) and crap.get("mu") is not None:
        return float(crap["mu"])
    return None


def op_scores(module):
    """config.clj `op-scores`: the function CRAP scores of one module.
    The live overlay writes `op.metrics.crap`; a function without it drops."""
    scores = []
    for op in module.get("ops", []):
        score = score_of((op.get("metrics") or {}).get("crap"))
        if score is not None:
            scores.append(score)
    return scores


def function_weight(module):
    """config.clj `function-weight`: the functions listed, or one when none is.
    The fallback of one answers a rolled summary that covers a subtree with no
    listed functions. A module with no functions is not in that path: it has
    nothing to measure, so `_crap_sample` drops it."""
    count = len(module.get("ops", []))
    return count if count > 0 else 1


def _score_group(scores):
    """config.clj `score-group`: mu, max and population sigma of a score sample."""
    xs = [float(s) for s in scores]
    n = len(xs)
    mu = sum(xs) / n
    var = sum((s - mu) ** 2 for s in xs) / n
    return {"n": n, "mu": mu, "sigma": math.sqrt(var), "max": max(xs)}


def _round_group(group):
    return {
        "mu": _round1(group["mu"]),
        "max": _round1(group["max"]),
        "sigma": _round1(group["sigma"]),
        "n": int(group["n"]),
    }


def _red_group(n):
    """config.clj `red-group`: a module with no CRAP data, at the red threshold."""
    red = float(CRAP_THRESHOLDS["red"])
    return {"n": n, "mu": red, "sigma": 0.0, "max": red}


def _summary_weight(module, summary, scores):
    n = summary.get("n")
    if n and n > 0:
        return int(n)
    if scores:
        return len(scores)
    return function_weight(module)


def _known_group(n, summary):
    return {
        "n": n,
        "mu": float(summary["mu"]),
        "sigma": float(summary.get("sigma") or 0),
        "max": float(summary.get("max", summary["mu"])),
    }


def _crap_sample(module, rolled):
    """config.clj `crap-sample`: one module as an unrounded CRAP group.
    The function scores are the sample. With `rolled`, a summary that already
    covers the subtree wins over the module's own ops. A module that has
    functions but no CRAP data is the red threshold, once per function. A module
    with no functions has nothing to measure, so it contributes no group:
    upstream weights it as one function, and that grades an enum red."""
    if (module.get("live") or {}).get("status") == "missing":
        return None
    scores = op_scores(module)
    summary = module.get("crap")
    has_summary = isinstance(summary, dict) and summary.get("mu") is not None
    if rolled and has_summary:
        return _known_group(_summary_weight(module, summary, scores), summary)
    if scores:
        return _score_group(scores)
    if has_summary:
        return _known_group(_summary_weight(module, summary, scores), summary)
    if not module.get("ops"):
        return None
    return _red_group(function_weight(module))


def is_module(module):
    """config.clj `module?`: a real module, not a foreign oval."""
    return not (module.get("foreign") or module.get("shape") == "oval")


def _combine_groups(groups):
    """config.clj `combine-groups`: the function-weighted mu, sigma and max."""
    groups = [g for g in groups if g and g.get("n", 0) > 0]
    if not groups:
        return None
    n = sum(g["n"] for g in groups)
    sum_w = sum(g["n"] * g["mu"] for g in groups)
    sum_m2 = sum(g["n"] * (g["sigma"] ** 2 + g["mu"] ** 2) for g in groups)
    mx = max(g["max"] for g in groups)
    mu = sum_w / n
    var = max(0.0, sum_m2 / n - mu * mu)
    return _round_group({"n": n, "mu": mu, "sigma": math.sqrt(var), "max": mx})


def pool_crap(modules, rolled=False):
    """config.clj `pool-crap`: function-weighted mu, max and population sigma across
    modules. Each function weighs one. A module that has functions but no CRAP counts
    as the red threshold once per function; a module with no functions contributes
    nothing, because it has nothing to measure. `rolled` is true when each module's
    `crap` summary already pools its subtree."""
    return _combine_groups([_crap_sample(m, rolled) for m in modules if is_module(m)])


def grade_of(summary):
    """The 1-10 CRAP grade of a pooled summary, or None when nothing is pooled."""
    if summary is None:
        return None
    return crap_grade(crap_risk(summary))


def stamp_grades(components):
    """Write the pooled CRAP summary and its grade onto every component and class.
    The pool is rolled: a component trusts the summary of each class. Every op
    carries the band of its own CRAP, so the template never computes a threshold.
    A module with no pool - a class with nothing to measure - carries no risk,
    grade or band, and the template draws no grade for it."""
    for component in components:
        for cls in component["classes"]:
            cls["crap"] = pool_crap([cls])
            for op in cls.get("ops", []):
                crap = score_of((op.get("metrics") or {}).get("crap"))
                if crap is not None:
                    op["band"] = crap_band(crap)
        component["crap"] = pool_crap(component["classes"], rolled=True)
        for module in [component, *component["classes"]]:
            summary = module["crap"]
            if summary is None:
                module["risk"] = None
                continue
            risk = crap_risk(summary)
            module["risk"] = risk
            module["grade"] = combined_grade(crap_grade(risk))
            module["band"] = crap_band(risk)