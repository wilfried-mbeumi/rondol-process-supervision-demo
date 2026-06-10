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
from physics.multi_feeder import (
    STATUS_CALIBRATION_MISSING,
    STATUS_DISABLED,
    STATUS_OK,
    FeederCalibration,
    MultiFeederResult,
    resolve_multi_feeder,
)
from AgentIndustrial_v1.core.coercion import safe_float

# Clés session (USER_INPUT).
FEEDER_RPM_KEY = "feeder_rpm"
FEEDER_CALIB_KEY = "feeder_calib_g_h_per_rpm"  # 0.0 = non renseigné

# Streamlit multipage purge les clés de WIDGET non montées lors d'une navigation.
# L'étalonnage saisi sur Profile serait donc perdu sur Moteur Procédé. On le
# MIROITE dans des clés PERSISTANTES (non liées à un widget) qui survivent à la
# navigation. Lecture nav-safe = widget si présent, sinon miroir persistant.
_PERSIST_SUFFIX = "__persist"


def _persist_one(session: MutableMapping[str, Any], key: str) -> None:
    try:
        if key in session:
            session[key + _PERSIST_SUFFIX] = session[key]
    except Exception:  # pragma: no cover - proxy hors contexte
        pass


def mirror_calibration_to_persistent(
    session: MutableMapping[str, Any], feeder_ids=range(1, 6),
) -> None:
    """Copie les clés d'étalonnage WIDGET → clés PERSISTANTES (survie navigation)."""
    _persist_one(session, FEEDER_RPM_KEY)
    _persist_one(session, FEEDER_CALIB_KEY)
    for fid in feeder_ids:
        if fid != 1:
            _persist_one(session, f"feedcal_rpm_{fid}")
            _persist_one(session, f"feedcal_coeff_{fid}")


def calib_read(session: Mapping[str, Any], widget_key: str, default: float) -> float:
    """Lecture nav-safe d'une clé d'étalonnage : widget → persistant → défaut."""
    try:
        if widget_key in session:
            return safe_float(session[widget_key], default, 0.0, 100000.0)
        pk = widget_key + _PERSIST_SUFFIX
        if pk in session:
            return safe_float(session[pk], default, 0.0, 100000.0)
    except Exception:  # pragma: no cover
        pass
    return default

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
    """Résout le débit réel depuis les clés session (lecture nav-safe)."""
    rpm = calib_read(session, FEEDER_RPM_KEY, 30.0)
    calib_raw = calib_read(session, FEEDER_CALIB_KEY, 0.0)
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
        # i18n : « Non renseigné » → « Not entered » en anglais (import défensif,
        # le module reste importable hors contexte Streamlit avec repli FR).
        try:
            from rondol_i18n import t as _t_i18n
            _not_entered = _t_i18n("historique.comp_not_entered")
        except Exception:  # pragma: no cover
            _not_entered = "Non renseigné"
        add("Coefficient étalonnage", _not_entered, NOT_AVAILABLE)
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


# ---------------------------------------------------------------------------
# Multi-feeder : clés par feeder + résolution + rendu Settings
# ---------------------------------------------------------------------------
def feedcal_rpm_key(feeder_id: int) -> str:
    """Clé RPM d'un feeder (feeder #1 = clé legacy, migration propre)."""
    return FEEDER_RPM_KEY if feeder_id == 1 else f"feedcal_rpm_{feeder_id}"


def feedcal_coeff_key(feeder_id: int) -> str:
    """Clé coefficient g/h/RPM d'un feeder (feeder #1 = clé legacy)."""
    return FEEDER_CALIB_KEY if feeder_id == 1 else f"feedcal_coeff_{feeder_id}"


def multi_feeder_from_session(session: Mapping[str, Any], feeders) -> MultiFeederResult:
    """Construit le banc multi-feeder résolu depuis la session + le banc feeders.

    `feeders` = itérable de FeederSpec (feeder_id / enabled / label / polymer_name).
    Feeder #1 migre depuis les clés legacy. Aucune matière inventée.
    """
    cals: list[FeederCalibration] = []
    for f in feeders:
        fid = int(f.feeder_id)
        rpm_default = 30.0 if fid == 1 else 0.0
        rpm = calib_read(session, feedcal_rpm_key(fid), rpm_default)
        coeff_raw = calib_read(session, feedcal_coeff_key(fid), 0.0)
        poly = (getattr(f, "polymer_name", "") or "").strip()
        cals.append(FeederCalibration(
            feeder_id=fid, label=(f.label or f"Feeder {fid}"),
            enabled=bool(getattr(f, "enabled", False)), rpm=rpm,
            coeff_g_h_per_rpm=(coeff_raw if coeff_raw > 0.0 else None),
            material_label=poly,
            material_source=(USER_INPUT if poly else NOT_AVAILABLE),
        ))
    return resolve_multi_feeder(cals)


_STATUS_LABEL = {
    STATUS_OK: "OK",
    STATUS_CALIBRATION_MISSING: "Non étalonné",
    STATUS_DISABLED: "Désactivé",
}


def render_multi_feeder_calibration(st_module, feeders, container=None) -> MultiFeederResult:
    """Bloc Settings « Étalonnage feeders » : RPM + coefficient par feeder.

    Rend, pour chaque feeder du banc, RPM + coefficient g/h/RPM (clés live ;
    feeder #1 = clés legacy). Affiche débit individuel + statut + total + un
    avertissement si un feeder actif n'est pas étalonné. Retourne le banc résolu.

    Tous les libellés passent par le catalogue i18n (`rondol_i18n`) pour
    survivre au changement FR/EN (exigence Phase 6 manager 2026-06-09).
    """
    # Import local pour éviter les cycles (feeder_ui chargé tôt par Profile).
    from rondol_i18n import t  # noqa: PLC0415

    c = container if container is not None else st_module
    ss = st_module.session_state
    feeders = list(feeders)

    # Semis des clés (feeder #1 via defaults legacy ; autres à 0 = non renseigné).
    ensure_feeder_defaults(ss)
    for f in feeders:
        fid = int(f.feeder_id)
        if fid != 1:
            if feedcal_rpm_key(fid) not in ss:
                ss[feedcal_rpm_key(fid)] = 0.0
            if feedcal_coeff_key(fid) not in ss:
                ss[feedcal_coeff_key(fid)] = 0.0

    c.caption(t("feedcal.caption"))
    for f in feeders:
        fid = int(f.feeder_id)
        enabled = bool(getattr(f, "enabled", False))
        label = f.label or f"Feeder {fid}"
        cc1, cc2, cc3 = c.columns([1.4, 1.0, 1.0])
        _status = t("feedcal.active") if enabled else t("feedcal.disabled")
        cc1.markdown(f"**#{fid} · {label}** · {_status}")
        cc2.number_input(
            t("feedcal.rpm_label", fid=fid),
            min_value=0.0, max_value=100000.0, step=1.0,
            key=feedcal_rpm_key(fid), disabled=not enabled,
        )
        cc3.number_input(
            t("feedcal.coeff_label", fid=fid),
            min_value=0.0, max_value=100000.0, step=0.5,
            key=feedcal_coeff_key(fid), disabled=not enabled,
        )

    # Persiste l'étalonnage saisi (survie navigation multipage).
    mirror_calibration_to_persistent(ss, [int(f.feeder_id) for f in feeders])

    multi = multi_feeder_from_session(ss, feeders)
    for line in multi.lines:
        if line.status == STATUS_OK:
            c.caption(t(
                "feedcal.line_ok",
                fid=line.feeder_id, lbl=line.label,
                gh=f"{line.flow_g_h:.0f}", gmin=f"{line.flow_g_min:.2f}",
            ))
        elif line.status == STATUS_CALIBRATION_MISSING:
            c.caption(t("feedcal.line_missing", fid=line.feeder_id, lbl=line.label))
        # désactivé : silencieux (0)

    if multi.total_calculable:
        total_msg = t(
            "feedcal.total_ok",
            gh=f"{multi.total_g_h:.0f}", gmin=f"{multi.total_g_min:.2f}",
        )
        if multi.has_uncalibrated_active:
            c.warning(total_msg + " — " + t("feedcal.total_incomplete"), icon="⚠️")
        else:
            c.success(total_msg)
    else:
        c.warning(t("feedcal.total_none"), icon="⚠️")
    return multi


def render_feeder_calibration(st_module, container=None) -> FeederFlow:
    """Rend le bloc d'étalonnage feeder et retourne le `FeederFlow` résolu.

    Effet de bord : si l'étalonnage est exploitable, écrit le débit EFFECTIF
    (g/min) dans `feeder_g_per_min` — la clé consommée par toute la chaîne de
    calcul existante (fill factor, résidence, moteur procédé, recos). Sinon, ne
    touche pas `feeder_g_per_min` (le débit réel reste « non calculable »).

    i18n FR/EN via `rondol_i18n` (Phase 6 manager 2026-06-09).
    """
    from rondol_i18n import t  # noqa: PLC0415

    c = container if container is not None else st_module
    ensure_feeder_defaults(st_module.session_state)

    c.caption(t("feedcal.profile_caption"))
    c.number_input(
        t("feedcal.rpm_simple"),
        min_value=0.0, max_value=100000.0, step=1.0,
        key=FEEDER_RPM_KEY,
    )
    c.number_input(
        t("feedcal.coeff_simple"),
        min_value=0.0, max_value=100000.0, step=0.5,
        key=FEEDER_CALIB_KEY,
        help=t(
            "feedcal.coeff_help",
            coeff=f"{EXAMPLE_CALIBRATION_G_H_PER_RPM:.0f}",
            max_gh=f"{MAX_FEEDER_FLOW_G_H:.0f}",
        ),
    )

    # Persiste l'étalonnage feeder #1 (survie navigation multipage Profile→Moteur).
    mirror_calibration_to_persistent(st_module.session_state, [1])

    ff = current_feeder_flow(st_module.session_state)

    if not ff.calibrated:
        c.warning(t("feedcal.not_calibrated"), icon="⚠️")
        return ff

    # Étalonné → propage le débit EFFECTIF à la chaîne de calcul existante.
    st_module.session_state["feeder_g_per_min"] = float(ff.effective_g_min or 0.0)

    if ff.clamped:
        c.warning(
            t(
                "feedcal.clamped",
                req=f"{ff.requested_g_h:.0f}",
                max_gh=f"{ff.max_machine_g_h:.0f}",
                eff=f"{ff.effective_g_h:.0f}",
                eff_min=f"{ff.effective_g_min:.2f}",
            ),
            icon="⚠️",
        )
    else:
        c.caption(t(
            "feedcal.ok",
            rpm=f"{ff.feeder_rpm:.0f}",
            coeff=f"{ff.calibration_g_h_per_rpm:.0f}",
            req=f"{ff.requested_g_h:.0f}",
            eff_min=f"{ff.effective_g_min:.2f}",
            eff_s=f"{ff.effective_g_s:.4f}",
        ))
    return ff
