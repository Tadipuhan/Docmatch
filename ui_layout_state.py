"""Small, Qt-independent helpers for DocMatch review-panel layouts."""


def group_check_state(selected):
    """Return Qt-compatible check state (0 unchecked, 1 partial, 2 checked)."""
    states = list(selected)
    if not states or not any(states):
        return 0
    if all(states):
        return 2
    return 1


def responsive_split_widths(total, desired_panel=360, panel_min=300,
                            panel_max=480, documents_min=460):
    """Keep the inspector visible without forcing a wider-than-screen layout.

    Narrow screens preserve the inspector minimum when feasible; the dual PDF
    viewers can then scroll instead of inflating the top-level window width.
    """
    total = max(1, int(total))
    if total < panel_min + documents_min:
        panel = min(panel_min, max(180, int(total * 0.4)))
    else:
        panel = max(panel_min, min(panel_max, int(desired_panel)))
        panel = min(panel, total - documents_min)
    return [max(1, total-panel), max(1, panel)]
