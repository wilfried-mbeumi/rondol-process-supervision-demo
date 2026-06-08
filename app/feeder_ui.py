"""feeder_ui.py — bloc UI d'étalonnage feeder + audit calcul (couche app).

Centralise :
  - les clés session de l'étalonnage feeder (RPM + coefficient g/h/RPM) ;
  - la résolution du débit réel (délègue au socle PUR `physics.feeder_flow`) ;
  - la construction des LIGNES d'audit (provenance explicite) — partie PURE,
    testable, partagée par Profile et Moteur Procédé ;
  - le rendu Streamlit du bloc d'étalonnage.

Règle manager : sans coefficient d'étalonnage, le débit réel est « non
calculable » — on ne devine jamais. Le coefficient n'est PAS hardcodé.
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping

from physics.feeder_flow import (
    EXAMPLE_CALIBRATION_G_H_PER_RPM,
    MAX_FEEDER_FLOW_G_H,
    FeederFlow,
    resolve_feeder_flow,
)
from AgentIndustrial_v1.core.coercion import safe_float

# Clés session (USER_INPUT).
FEEDER_RPM_KEY = "feeder_rpm"
FEEDER_CALIB_KEY = "feeder_calib_g_h_per_rpm"  # 0.0 = non renseigné

# Provenance canonique (exigence « source de vérité »).
USER_INPUT = "USER_INPUT"
DEFAULT_CONFIG = "DEFAULT_CONFIG"
CALCULATED = "CALCULATED"
NOT_AVAILABLE = "NOT_AVAILABLE"


def ensure_feeder_defaults(session: MutableMapping[str, Any]) -> None:
    """Sème les clés d'étalonnage si absentes (RPM défaut, coeff = non renseigné)."""
    if FEEDER_RPM_KEY not in session:
        session[FEEDER_RPM_KEY] = 30.0
    if FEEDER_CALIB_KEY not in session:
        session[FEEDER_CALIB_KEY] = 0.0  # 0 ⇒ non renseigné (pas l'exemple 10)


def current_feeder_flow(session: Mapping[str, Any]) -> FeederFlow:
    """Résout le débit réel depuis les clés session (coercition robuste)."""
    rpm = safe_float(session.get(FEEDER_RPM_KEY, 30.0) if hasattr(session, "get")
                     else 30.0, 30.0, 0.0, 100000.0)
    calib_raw = safe_float(session.get(FEEDER_CALIB_KEY, 0.0) if hasattr(session, "get")
                           else 0.0, 0.0, 0.0, 100000.0)
    calib = calib_raw if calib_raw > 0.0 else None
    return resolve_feeder_flow(rpm, calib)


def feeder_audit_rows(
    ff: FeederFlow, density_g_cm3: float, density_provenance: str = USER_INPUT,
) -> list[dict[str, str]]:
    """Construit les lignes d'audit feeder (PUR — testable).

    Chaque ligne : {grandeur, valeur, provenance}. Si non calibré, les débits
    réels sont « Non calculable » (provenance NOT_AVAILABLE), jamais devinés.
    """
    rows: list[dict[str, str]] = []

    def add(grandeur: str, valeur: str, provenance: str) -> None:
        rows.append({"grandeur": grandeur, "valeur": valeur, "provenance": provenance})

    add("RPM feeder", f"{ff.feeder_rpm:.0f} RPM", USER_INPUT)
    if not ff.calibrated:
        add("Coefficient étalonnage", "Non renseigné", NOT_AVAILABLE)
        add("Débit réel", "Non calculable — étalonnage externe requis", NOT_AVAILABLE)
        add("Densité apparente", f"{density_g_cm3:.3f} g/cm³", density_provenance)
        add("Débit volumique", "Non calculable", NOT_AVAILABLE)
        return rows

    add("Coefficient étalonnage", f"{ff.calibration_g_h_per_rpm:.3f} g/h/RPM", USER_INPUT)
    add("Débit demandé", f"{ff.requested_g_h:.1f} g/h", CALCULATED)
    add("Débit max machine", f"{ff.max_machine_g_h:.0f} g/h", DEFAULT_CONFIG)
    eff = ff.effective_g_h or 0.0
    eff_note = " (plafonné)" if ff.clamped else ""
    add("Débit utilisé (calcul)", f"{eff:.1f} g/h{eff_note}", CALCULATED)
    add("  → en g/min", f"{(ff.effective_g_min or 0.0):.3f} g/min", CALCULATED)
    add("  → en g/s", f"{(ff.effective_g_s or 0.0):.5f} g/s", CALCULATED)
    add("Densité apparente", f"{density_g_cm3:.3f} g/cm³", density_provenance)
    if density_g_cm3 > 0:
        qvol = (ff.effective_g_s or 0.0) / density_g_cm3
        add("Débit volumique (ṁ/ρ)", f"{qvol:.4f} cm³/s", CALCULATED)
    return rows


def render_feeder_calibration(st_module, container=None) -> FeederFlow:
    """Rend le bloc d'étalonnage feeder et retourne le `FeederFlow` résolu.

    Effet de bord : si l'étalonnage est exploitable, écrit le débit EFFECTIF
    (g/min) dans `feeder_g_per_min` — la clé consommée par toute la chaîne de
    calcul existante (fill factor, résidence, moteur procédé, recos). Sinon, ne
    touche pas `feeder_g_per_min` (le débit réel reste « non calculable »).
    """
    c = container if container is not None else st_module
    ensure_feeder_defaults(st_module.session_state)

    c.caption("⚙️ Étalonnage feeder — **étalonnage externe requis**")
    c.number_input(
        "RPM feeder", min_value=0.0, max_value=100000.0, step=1.0,
        key=FEEDER_RPM_KEY,
    )
    c.number_input(
        "Coefficient (g/h par RPM)", min_value=0.0, max_value=100000.0, step=0.5,
        key=FEEDER_CALIB_KEY,
        help=(
            f"À mesurer par étalonnage externe du feeder. Exemple Maël : "
            f"{EXAMPLE_CALIBRATION_G_H_PER_RPM:.0f} g/h/RPM (30 RPM → 300 g/h). "
            f"0 = non renseigné → débit réel non calculable."
        ),
    )

    ff = current_feeder_flow(st_module.session_state)

    if not ff.calibrated:
        c.warning("Débit réel non calculable — coefficient feeder à renseigner.", icon="⚠️")
        return ff

    # Étalonné → propage le débit EFFECTIF à la chaîne de calcul existante.
    st_module.session_state["feeder_g_per_min"] = float(ff.effective_g_min or 0.0)

    eq = (
        f"{ff.feeder_rpm:.0f} RPM × {ff.calibration_g_h_per_rpm:.0f} g/h/RPM = "
        f"{ff.requested_g_h:.0f} g/h"
    )
    if ff.clamped:
        c.warning(
            f"Débit demandé {ff.requested_g_h:.0f} g/h > max machine "
            f"{ff.max_machine_g_h:.0f} g/h : **plafonné à {ff.effective_g_h:.0f} g/h** "
            f"({ff.effective_g_min:.2f} g/min) pour le calcul.",
            icon="⚠️",
        )
    else:
        c.caption(
            f"✓ {eq} = {ff.effective_g_min:.2f} g/min "
            f"({ff.effective_g_s:.4f} g/s)"
        )
    return ff
