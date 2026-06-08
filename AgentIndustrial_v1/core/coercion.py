"""coercion.py — coercition robuste session_state → valeur métier (PUR).

Contexte (exigence stabilité prod, bug « crash langue / n_die_zones ») :
`st.session_state` peut contenir, à un instant donné, une valeur qui n'est PAS
du type métier attendu — chaîne vide, ``None``, libellé d'UI, ``"2.0"``, type
numpy, valeur héritée d'une version antérieure / d'une session polluée. Les
appels bruts ``int(x)`` / ``float(x)`` lèvent alors ``ValueError`` et cassent la
page (cf. ``state_sync.py`` / ``editing_state.py``).

Ce module fournit trois convertisseurs DÉFENSIFS qui ne lèvent JAMAIS : en cas
de valeur inexploitable, ils retournent le défaut fourni (et le bornent). Ils
constituent la frontière unique « état UI (non fiable) → état métier (fiable) ».

Règles de conception :
  - aucune dépendance Streamlit / disque (testable sur des littéraux) ;
  - jamais d'exception propagée (contrat : retour = valeur sûre) ;
  - bornes optionnelles (clamp) appliquées APRÈS conversion ;
  - une chaîne décimale (``"2.0"``) est acceptée pour ``safe_int`` (tronquée),
    car une valeur métier entière peut transiter en flottant via la session.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence, TypeVar

T = TypeVar("T")


def safe_float(
    value: Any,
    default: float,
    min_value: float | None = None,
    max_value: float | None = None,
) -> float:
    """Convertit ``value`` en ``float`` sans jamais lever.

    Renvoie ``default`` si la conversion échoue ou si le résultat n'est pas fini
    (NaN / inf). Borne ensuite le résultat dans ``[min_value, max_value]`` si
    fournis.
    """
    try:
        out = float(value)
    except (TypeError, ValueError):
        out = float(default)
    # Rejeter NaN / inf (float('nan') != float('nan')).
    if out != out or out in (float("inf"), float("-inf")):
        out = float(default)
    return _clamp(out, min_value, max_value)


def safe_int(
    value: Any,
    default: int,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    """Convertit ``value`` en ``int`` sans jamais lever.

    Tolère les chaînes décimales (``"2.0"`` → ``2``) et les flottants (``2.7`` →
    ``2``, troncature). Renvoie ``default`` si la conversion est impossible.
    Borne ensuite dans ``[min_value, max_value]`` si fournis.
    """
    try:
        out = int(value)
    except (TypeError, ValueError, OverflowError):
        # 2e chance : passer par float (gère "2.0", "3.5", numpy, etc.).
        try:
            f = float(value)
            if f != f or f in (float("inf"), float("-inf")):
                out = int(default)
            else:
                out = int(f)
        except (TypeError, ValueError, OverflowError):
            out = int(default)
    return _clamp(out, min_value, max_value)


def safe_choice(value: Any, allowed: Sequence[T] | Iterable[T], default: T) -> T:
    """Renvoie ``value`` si elle figure dans ``allowed``, sinon ``default``.

    Sert aux champs discrets (langue, archétype, position feeder…) : une valeur
    d'UI traduite ou héritée qui ne fait pas partie des options valides ne doit
    jamais devenir une valeur métier.
    """
    allowed_seq = tuple(allowed)
    return value if value in allowed_seq else default


def _clamp(value: T, lo: Any, hi: Any) -> T:
    """Borne ``value`` dans ``[lo, hi]`` (bornes ignorées si ``None``)."""
    if lo is not None and value < lo:
        return lo
    if hi is not None and value > hi:
        return hi
    return value
