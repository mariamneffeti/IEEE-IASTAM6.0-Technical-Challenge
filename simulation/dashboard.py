"""
Interactive LEO Satellite Orbit Visualization Dashboard
========================================================
Plotly Dash web application that drives the satellite simulation
in real time with play/pause/step controls and full telemetry.

Usage:
    pip install dash dash-bootstrap-components plotly numpy
    python dashboard.py

Then open http://127.0.0.1:8050 in your browser.
"""

import math
from collections import deque
from typing import List, Dict

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, dcc, html, Input, Output, State, callback_context, no_update
import dash_bootstrap_components as dbc

from satellite_sim import Satellite, SimConfig


# ---------------------------------------------------------------------------
# Theme constants
# ---------------------------------------------------------------------------

COLORS = {
    "bg":            "#0b1120",
    "card":          "#111827",
    "card_border":   "#1e293b",
    "text":          "#e2e8f0",
    "text_muted":    "#94a3b8",
    "text_dim":      "#64748b",
    "sunlit":        "#fbbf24",
    "eclipse":       "#334155",
    "gs_pass":       "#34d399",
    "satellite":     "#06b6d4",
    "earth":         "#1e3a5f",
    "earth_edge":    "#3b82f6",
    "sun":           "#f59e0b",
    "good":          "#22c55e",
    "warn":          "#eab308",
    "danger":        "#ef4444",
    "cool":          "#38bdf8",
    "mmu":           "#a78bfa",
    "ram":           "#f472b6",
    "solar":         "#fbbf24",
    "power_draw":    "#f97316",
    "accent":        "#06b6d4",
}

ORBIT_R = 1.5
EARTH_R = 0.6
MAX_HISTORY = 10800     # ~2 orbits of 1-second samples
DEFAULT_SPEED = 5       # simulation steps per UI tick
UI_INTERVAL_MS = 100    # 10 Hz UI refresh


# ---------------------------------------------------------------------------
# Simple heuristic agent (drives interesting activity for the demo)
# ---------------------------------------------------------------------------

def heuristic_agent(sat: Satellite) -> List[Dict]:
    """Compress/infer when power is healthy, downlink during GS pass,
    drop stale payloads when storage is tight."""
    actions: List[Dict] = []
    tel = sat.get_telemetry()

    if tel["in_safe_mode"]:
        return actions

    # --- Downlink during ground-station pass ---
    if tel["in_gs_pass"]:
        ranked = sorted(
            sat.mmu_payloads,
            key=lambda p: (p.processed, p.current_value(sat.env.time_step)),
            reverse=True,
        )
        for p in ranked[:3]:
            actions.append({"type": "downlink", "payload_id": p.id})

    # --- Process when battery & thermal headroom exist ---
    if (tel["battery_soc"] > 0.5
            and not tel["is_throttling"]
            and tel["queue_length"] < 2):
        unprocessed = [p for p in sat.mmu_payloads if not p.processed]
        if unprocessed:
            best = max(unprocessed,
                       key=lambda p: p.current_value(sat.env.time_step))
            mode = "inference" if best.size_mb < 50 else "compressed"
            actions.append({"type": "process",
                            "payload_id": best.id, "mode": mode})

    # --- Drop stale data when MMU > 80 % ---
    mmu_pct = tel["mmu_usage_mb"] / sat.cfg.mmu_capacity_mb
    if mmu_pct > 0.8 and sat.mmu_payloads:
        worst = min(sat.mmu_payloads,
                    key=lambda p: p.current_value(sat.env.time_step))
        if worst.current_value(sat.env.time_step) < 5.0:
            actions.append({"type": "drop", "payload_id": worst.id})

    return actions


# ---------------------------------------------------------------------------
# Simulation state wrapper (module-level singleton for Dash callbacks)
# ---------------------------------------------------------------------------

class SimState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.sat = Satellite(seed=42)
        self.history = {
            "time":        deque(maxlen=MAX_HISTORY),
            "battery_soc": deque(maxlen=MAX_HISTORY),
            "solar_power": deque(maxlen=MAX_HISTORY),
            "power_draw":  deque(maxlen=MAX_HISTORY),
            "temperature":  deque(maxlen=MAX_HISTORY),
            "mmu_usage":   deque(maxlen=MAX_HISTORY),
            "ram_usage":   deque(maxlen=MAX_HISTORY),
        }
        self.events: deque = deque(maxlen=50)

    def step(self, n: int = 1) -> None:
        for _ in range(n):
            actions = heuristic_agent(self.sat)
            feedback = self.sat.step(actions)
            tel = self.sat.get_telemetry()

            self.history["time"].append(tel["time_step"])
            self.history["battery_soc"].append(tel["battery_soc"])
            self.history["solar_power"].append(tel["solar_power_w"])
            self.history["power_draw"].append(
                self.sat.cfg.base_power_w
                + self.sat.active_compute_w
                + self.sat.active_comm_w
            )
            self.history["temperature"].append(tel["temperature_c"])
            self.history["mmu_usage"].append(tel["mmu_usage_mb"])
            self.history["ram_usage"].append(tel["ram_usage_mb"])

            for fb in feedback:
                msg = fb.get("message", fb.get("action", ""))
                self.events.appendleft(
                    f"t={tel['time_step']}: [{fb.get('type', '')}] {msg}"
                )


sim = SimState()


# ---------------------------------------------------------------------------
# Figure builders
# ---------------------------------------------------------------------------

def _arc(cx, cy, r, start_rad, end_rad, n=120):
    """Return (xs, ys) arrays tracing a circular arc."""
    angles = np.linspace(start_rad, end_rad, n)
    return r * np.cos(angles) + cx, r * np.sin(angles) + cy


def build_orbit_figure(sat: Satellite) -> go.Figure:
    cfg = sat.cfg
    env = sat.env
    period = cfg.orbit_period_s
    sunlit = cfg.sunlit_duration_s
    t_orb = env.time_step % period

    fig = go.Figure()

    # Sun glow
    gx, gy = _arc(0, 0, 2.3, -0.35, 0.35, 60)
    fig.add_trace(go.Scatter(
        x=gx, y=gy, mode="lines",
        line=dict(color=COLORS["sun"], width=10), opacity=0.2,
        showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=[2.4], y=[0], mode="text", text=["☀️"],
        textfont=dict(size=24), showlegend=False, hoverinfo="skip"))

    # Earth
    ex, ey = _arc(0, 0, EARTH_R, 0, 2 * math.pi, 120)
    fig.add_trace(go.Scatter(
        x=ex, y=ey, fill="toself",
        fillcolor=COLORS["earth"], line=dict(color=COLORS["earth_edge"], width=2),
        showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=[0], y=[0], mode="text", text=["🌍"],
        textfont=dict(size=20), showlegend=False, hoverinfo="skip"))

    # Sunlit arc
    a_sun = 2 * math.pi * sunlit / period
    sx, sy = _arc(0, 0, ORBIT_R, 0, a_sun, 200)
    fig.add_trace(go.Scatter(
        x=sx, y=sy, mode="lines",
        line=dict(color=COLORS["sunlit"], width=4),
        name="Sunlit", hoverinfo="skip"))

    # Eclipse arc
    ex2, ey2 = _arc(0, 0, ORBIT_R, a_sun, 2 * math.pi, 200)
    fig.add_trace(go.Scatter(
        x=ex2, y=ey2, mode="lines",
        line=dict(color=COLORS["eclipse"], width=4),
        name="Eclipse", hoverinfo="skip"))

    # Ground-station pass arc (slightly outside orbit)
    gs_r = ORBIT_R + 0.13
    gs_a0 = 2 * math.pi * env.gs_start / period
    gs_a1 = 2 * math.pi * env.gs_end / period
    gsx, gsy = _arc(0, 0, gs_r, gs_a0, gs_a1, 60)
    fig.add_trace(go.Scatter(
        x=gsx, y=gsy, mode="lines",
        line=dict(color=COLORS["gs_pass"], width=7),
        opacity=0.85 if env.in_gs_pass else 0.25,
        name="GS Pass", hoverinfo="skip"))

    # Satellite
    sat_a = 2 * math.pi * t_orb / period
    sat_x = ORBIT_R * math.cos(sat_a)
    sat_y = ORBIT_R * math.sin(sat_a)

    # Glow ring
    fig.add_trace(go.Scatter(
        x=[sat_x], y=[sat_y], mode="markers",
        marker=dict(size=28, color=COLORS["satellite"], opacity=0.15),
        showlegend=False, hoverinfo="skip"))
    # Marker
    sat_color = COLORS["danger"] if sat._in_safe_mode else COLORS["satellite"]
    fig.add_trace(go.Scatter(
        x=[sat_x], y=[sat_y], mode="markers",
        marker=dict(size=13, color=sat_color, symbol="diamond",
                    line=dict(color="white", width=1.5)),
        name="Satellite",
        hovertext=f"Orbit time: {t_orb}s",
        hoverinfo="text"))

    # Direction-of-travel arrow (small triangle ahead of satellite)
    arrow_a = sat_a + 0.06
    ax = ORBIT_R * math.cos(arrow_a)
    ay = ORBIT_R * math.sin(arrow_a)
    fig.add_trace(go.Scatter(
        x=[ax], y=[ay], mode="markers",
        marker=dict(size=6, color=sat_color, symbol="triangle-right"),
        showlegend=False, hoverinfo="skip"))

    fig.update_layout(
        plot_bgcolor=COLORS["bg"], paper_bgcolor=COLORS["bg"],
        font=dict(color=COLORS["text"], family="Inter, sans-serif"),
        xaxis=dict(visible=False, range=[-2.9, 2.9],
                   scaleanchor="y", scaleratio=1),
        yaxis=dict(visible=False, range=[-2.2, 2.2]),
        margin=dict(l=5, r=5, t=35, b=5),
        legend=dict(orientation="h", yanchor="bottom", y=1.01,
                    xanchor="center", x=0.5, font=dict(size=10)),
        title=dict(
            text=f"Orbit {env.time_step // period}  ·  {t_orb} / {period} s",
            font=dict(size=13, color=COLORS["text_muted"]), x=0.5),
        height=420,
    )
    return fig


def build_telemetry_figure(history: dict) -> go.Figure:
    times = list(history["time"])
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.07,
        subplot_titles=("Battery SOC", "Power (W)", "Temperature (°C)",
                        "Storage (MB)"),
        row_heights=[0.25, 0.25, 0.25, 0.25],
    )

    if times:
        # Battery
        fig.add_trace(go.Scattergl(
            x=times, y=list(history["battery_soc"]),
            mode="lines", line=dict(color=COLORS["good"], width=1.5),
            showlegend=False), row=1, col=1)
        fig.add_hline(y=0.3, line_dash="dash", line_color=COLORS["danger"],
                      opacity=0.4, row=1, col=1,
                      annotation_text="Min DOD",
                      annotation_font=dict(color=COLORS["danger"], size=9))

        # Power
        fig.add_trace(go.Scattergl(
            x=times, y=list(history["solar_power"]),
            mode="lines", line=dict(color=COLORS["solar"], width=1.5),
            name="Solar", showlegend=False), row=2, col=1)
        fig.add_trace(go.Scattergl(
            x=times, y=list(history["power_draw"]),
            mode="lines", line=dict(color=COLORS["power_draw"], width=1.5),
            name="Draw", showlegend=False), row=2, col=1)

        # Temperature
        fig.add_trace(go.Scattergl(
            x=times, y=list(history["temperature"]),
            mode="lines", line=dict(color=COLORS["cool"], width=1.5),
            showlegend=False), row=3, col=1)
        fig.add_hline(y=50.0, line_dash="dash", line_color=COLORS["danger"],
                      opacity=0.4, row=3, col=1,
                      annotation_text="Throttle",
                      annotation_font=dict(color=COLORS["danger"], size=9))

        # Storage
        fig.add_trace(go.Scattergl(
            x=times, y=list(history["mmu_usage"]),
            mode="lines", line=dict(color=COLORS["mmu"], width=1.5),
            name="MMU", showlegend=False), row=4, col=1)
        fig.add_trace(go.Scattergl(
            x=times, y=list(history["ram_usage"]),
            mode="lines", line=dict(color=COLORS["ram"], width=1.5),
            name="RAM", showlegend=False), row=4, col=1)

    for r in range(1, 5):
        fig.update_xaxes(gridcolor="#1e293b", zeroline=False, row=r, col=1)
        fig.update_yaxes(gridcolor="#1e293b", zeroline=False, row=r, col=1)

    fig.update_yaxes(range=[0, 1.05], row=1, col=1)
    fig.update_xaxes(title_text="Simulation Time (s)", row=4, col=1)

    fig.update_layout(
        plot_bgcolor=COLORS["bg"], paper_bgcolor=COLORS["bg"],
        font=dict(color=COLORS["text"], family="Inter, sans-serif", size=11),
        margin=dict(l=50, r=15, t=30, b=35),
        height=420,
    )
    for ann in fig.layout.annotations:
        ann.font.size = 11
        ann.font.color = COLORS["text_muted"]
    return fig


def build_gauge_figure(tel: dict, cfg: SimConfig) -> go.Figure:
    fig = make_subplots(
        rows=1, cols=3,
        specs=[[{"type": "indicator"}] * 3],
    )
    soc = tel["battery_soc"]
    temp = tel["temperature_c"]
    mmu_pct = tel["mmu_usage_mb"] / cfg.mmu_capacity_mb * 100

    def _bar_color(val, thresholds):
        for limit, color in thresholds:
            if val <= limit:
                return color
        return thresholds[-1][1]

    fig.add_trace(go.Indicator(
        mode="gauge+number", value=soc * 100,
        number=dict(suffix="%", font=dict(size=18)),
        title=dict(text="Battery", font=dict(size=12, color=COLORS["text_muted"])),
        gauge=dict(
            axis=dict(range=[0, 100], tickcolor=COLORS["text_dim"]),
            bar=dict(color=_bar_color(soc, [(0.3, COLORS["danger"]),
                                             (0.5, COLORS["warn"]),
                                             (1.0, COLORS["good"])])),
            bgcolor=COLORS["card"], borderwidth=1,
            bordercolor=COLORS["card_border"],
            threshold=dict(line=dict(color=COLORS["danger"], width=2),
                           thickness=0.75, value=30)),
    ), row=1, col=1)

    fig.add_trace(go.Indicator(
        mode="gauge+number", value=temp,
        number=dict(suffix="°C", font=dict(size=18)),
        title=dict(text="Chip Temp", font=dict(size=12, color=COLORS["text_muted"])),
        gauge=dict(
            axis=dict(range=[-20, 70], tickcolor=COLORS["text_dim"]),
            bar=dict(color=_bar_color(temp, [(35, COLORS["cool"]),
                                              (49, COLORS["warn"]),
                                              (999, COLORS["danger"])])),
            bgcolor=COLORS["card"], borderwidth=1,
            bordercolor=COLORS["card_border"],
            threshold=dict(line=dict(color=COLORS["danger"], width=2),
                           thickness=0.75, value=50)),
    ), row=1, col=2)

    fig.add_trace(go.Indicator(
        mode="gauge+number", value=mmu_pct,
        number=dict(suffix="%", font=dict(size=18)),
        title=dict(text="MMU Storage", font=dict(size=12, color=COLORS["text_muted"])),
        gauge=dict(
            axis=dict(range=[0, 100], tickcolor=COLORS["text_dim"]),
            bar=dict(color=COLORS["mmu"]),
            bgcolor=COLORS["card"], borderwidth=1,
            bordercolor=COLORS["card_border"],
            threshold=dict(line=dict(color=COLORS["danger"], width=2),
                           thickness=0.75, value=80)),
    ), row=1, col=3)

    fig.update_layout(
        plot_bgcolor=COLORS["bg"], paper_bgcolor=COLORS["bg"],
        font=dict(color=COLORS["text"], family="Inter, sans-serif"),
        margin=dict(l=25, r=25, t=40, b=10),
        height=185,
    )
    return fig


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------

def _badge(text, variant="muted"):
    cls_map = {
        "active":  "badge-active",
        "warning": "badge-warning",
        "danger":  "badge-danger",
        "info":    "badge-info",
        "muted":   "badge-muted",
    }
    return html.Span(text, className=f"status-badge {cls_map.get(variant, 'badge-muted')}")


def _metric(value, label, color=None):
    style = {"color": color} if color else {}
    return html.Div([
        html.Div(str(value), className="metric-value", style=style),
        html.Div(label, className="metric-label"),
    ], className="metric-card")


# ---------------------------------------------------------------------------
# Dash application
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
body { font-family: 'Inter', sans-serif; background: #0b1120; }

.card-custom {
    background: #111827; border: 1px solid #1e293b;
    border-radius: 12px; padding: 12px;
}
.status-badge {
    display: inline-block; padding: 4px 12px; border-radius: 20px;
    font-size: 11px; font-weight: 600; letter-spacing: 0.5px; margin: 0 3px;
}
.badge-active  { background: rgba(34,197,94,.12); color: #22c55e; border: 1px solid rgba(34,197,94,.25); }
.badge-warning { background: rgba(234,179,8,.12); color: #eab308; border: 1px solid rgba(234,179,8,.25); }
.badge-danger  { background: rgba(239,68,68,.12); color: #ef4444; border: 1px solid rgba(239,68,68,.25); }
.badge-info    { background: rgba(6,182,212,.12); color: #06b6d4; border: 1px solid rgba(6,182,212,.25); }
.badge-muted   { background: rgba(148,163,184,.08); color: #94a3b8; border: 1px solid rgba(148,163,184,.15); }

.event-log {
    max-height: 190px; overflow-y: auto;
    font-family: 'Courier New', monospace; font-size: 11px;
    color: #94a3b8; line-height: 1.7;
}
.metric-card { text-align: center; padding: 6px 0; }
.metric-value { font-size: 22px; font-weight: 700; color: #e2e8f0; }
.metric-label { font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; }
"""

app = Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
        "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap",
    ],
    title="LEO Satellite Dashboard",
)

app.index_string = (
    "<!DOCTYPE html><html><head>{%metas%}<title>LEO Satellite Dashboard</title>"
    "{%favicon%}{%css%}<style>" + CUSTOM_CSS + "</style></head>"
    "<body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body></html>"
)

app.layout = dbc.Container([
    # Timers & stores
    dcc.Interval(id="sim-interval", interval=UI_INTERVAL_MS, disabled=True,
                 n_intervals=0),
    dcc.Store(id="speed-store", data=DEFAULT_SPEED),

    # ── Header row ────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col([
            html.H4("🛰️ LEO Satellite Simulation",
                     className="mb-0",
                     style={"fontWeight": "600", "color": COLORS["text"]}),
            html.Small("Real-time orbit & telemetry dashboard",
                       style={"color": COLORS["text_muted"]}),
        ], width=4),
        dbc.Col([
            dbc.ButtonGroup([
                dbc.Button("▶ Play",  id="btn-play",  color="success",
                           size="sm", outline=True, className="px-3"),
                dbc.Button("⏸ Pause", id="btn-pause", color="warning",
                           size="sm", outline=True, className="px-3"),
                dbc.Button("⏭ Step",  id="btn-step",  color="info",
                           size="sm", outline=True, className="px-3"),
                dbc.Button("↻ Reset", id="btn-reset", color="danger",
                           size="sm", outline=True, className="px-3"),
            ], className="me-3"),
            dbc.Select(
                id="speed-select",
                options=[
                    {"label": "1×  real-time", "value": "1"},
                    {"label": "5×",            "value": "5"},
                    {"label": "10×",           "value": "10"},
                    {"label": "50×",           "value": "50"},
                    {"label": "100×",          "value": "100"},
                ],
                value=str(DEFAULT_SPEED),
                style={"display": "inline-block", "width": "130px",
                       "verticalAlign": "middle",
                       "backgroundColor": COLORS["card"],
                       "color": COLORS["text"],
                       "border": f"1px solid {COLORS['card_border']}",
                       "fontSize": "13px"},
            ),
        ], width=5, className="d-flex align-items-center justify-content-center"),
        dbc.Col(html.Div(id="status-badges", className="text-end"), width=3),
    ], className="py-3 mb-2",
       style={"borderBottom": f"1px solid {COLORS['card_border']}"}),

    # ── Metrics bar ───────────────────────────────────────────────────
    dbc.Row([dbc.Col(html.Div(id="metrics-row"), width=12)], className="mb-2"),

    # ── Main: orbit + telemetry ───────────────────────────────────────
    dbc.Row([
        dbc.Col(html.Div(
            dcc.Graph(id="orbit-diagram", config={"displayModeBar": False}),
            className="card-custom"), width=5),
        dbc.Col(html.Div(
            dcc.Graph(id="telemetry-chart", config={"displayModeBar": False}),
            className="card-custom"), width=7),
    ], className="mb-2"),

    # ── Bottom: gauges + table/log ────────────────────────────────────
    dbc.Row([
        dbc.Col(html.Div(
            dcc.Graph(id="gauge-chart", config={"displayModeBar": False}),
            className="card-custom"), width=5),
        dbc.Col(dbc.Row([
            dbc.Col(html.Div([
                html.H6("📦 MMU Payloads",
                         style={"color": COLORS["text_muted"],
                                "fontSize": "12px", "marginBottom": "8px"}),
                html.Div(id="payload-table"),
            ], className="card-custom",
               style={"maxHeight": "210px", "overflowY": "auto"}), width=7),
            dbc.Col(html.Div([
                html.H6("📋 Events",
                         style={"color": COLORS["text_muted"],
                                "fontSize": "12px", "marginBottom": "8px"}),
                html.Div(id="event-log", className="event-log"),
            ], className="card-custom"), width=5),
        ]), width=7),
    ]),
], fluid=True, style={"backgroundColor": COLORS["bg"], "minHeight": "100vh"})


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@app.callback(
    Output("sim-interval", "disabled"),
    Input("btn-play",  "n_clicks"),
    Input("btn-pause", "n_clicks"),
    prevent_initial_call=True,
)
def toggle_play_pause(_play, _pause):
    trigger = callback_context.triggered[0]["prop_id"].split(".")[0]
    return trigger != "btn-play"


@app.callback(
    Output("speed-store", "data"),
    Input("speed-select", "value"),
    prevent_initial_call=True,
)
def update_speed(value):
    return int(value)


@app.callback(
    Output("orbit-diagram",  "figure"),
    Output("telemetry-chart", "figure"),
    Output("gauge-chart",     "figure"),
    Output("status-badges",   "children"),
    Output("metrics-row",     "children"),
    Output("payload-table",   "children"),
    Output("event-log",       "children"),
    Input("sim-interval", "n_intervals"),
    Input("btn-step",     "n_clicks"),
    Input("btn-reset",    "n_clicks"),
    State("speed-store",   "data"),
    State("sim-interval",  "disabled"),
)
def update_dashboard(n_intervals, _step, _reset, speed, is_paused):
    trigger = ""
    if callback_context.triggered:
        trigger = callback_context.triggered[0]["prop_id"].split(".")[0]

    # ── Advance simulation ────────────────────────────────────────────
    if trigger == "btn-reset":
        sim.reset()
    elif trigger == "btn-step":
        sim.step(1)
    elif trigger == "sim-interval":
        sim.step(speed)

    tel = sim.sat.get_telemetry()
    cfg = sim.sat.cfg

    # ── Figures ───────────────────────────────────────────────────────
    orbit_fig     = build_orbit_figure(sim.sat)
    telemetry_fig = build_telemetry_figure(sim.history)
    gauge_fig     = build_gauge_figure(tel, cfg)

    # ── Status badges ─────────────────────────────────────────────────
    badges = []
    if tel["sunlit"]:
        badges.append(_badge("☀ SUNLIT", "active"))
    else:
        badges.append(_badge("🌑 ECLIPSE", "muted"))
    if tel["in_gs_pass"]:
        badges.append(_badge("📡 GS PASS", "active"))
    if tel["in_safe_mode"]:
        badges.append(_badge("⚠ SAFE MODE", "danger"))
    if tel["is_throttling"]:
        badges.append(_badge("🔥 THROTTLE", "warning"))
    acc = tel["accelerator_state"]
    if acc == "active":
        badges.append(_badge("⚡ ACCEL", "info"))
    elif acc == "waking":
        badges.append(_badge("⏳ WAKING", "warning"))

    # ── Metrics ───────────────────────────────────────────────────────
    orbit_num = tel["time_step"] // cfg.orbit_period_s
    prog = tel.get("processing_progress")
    req  = tel.get("processing_required")
    prog_str = f"{prog}/{req}" if prog is not None else "—"

    metrics = dbc.Row([
        dbc.Col(_metric(f"{tel['time_step']:,}", "SIM TIME (s)"), width=2),
        dbc.Col(_metric(orbit_num, "ORBIT"), width=1),
        dbc.Col(_metric(tel["mmu_files"], "MMU FILES", COLORS["mmu"]), width=1),
        dbc.Col(_metric(tel["queue_length"], "QUEUE", COLORS["accent"]), width=1),
        dbc.Col(_metric(f"{tel['downlinked_utility']:.1f}",
                        "UTILITY ↓", COLORS["good"]), width=2),
        dbc.Col(_metric(tel["involuntary_drops"],
                        "INV. DROPS", COLORS["danger"]), width=1),
        dbc.Col(_metric(tel["voluntary_drops"],
                        "VOL. DROPS", COLORS["warn"]), width=1),
        dbc.Col(_metric(prog_str, "JOB PROGRESS", COLORS["accent"]), width=2),
    ], className="g-0")

    # ── Payload table ─────────────────────────────────────────────────
    if sim.sat.mmu_payloads:
        sorted_payloads = sorted(
            sim.sat.mmu_payloads,
            key=lambda p: p.current_value(tel["time_step"]),
            reverse=True,
        )[:15]

        rows = []
        for p in sorted_payloads:
            val = p.current_value(tel["time_step"])
            rows.append(html.Tr([
                html.Td(p.id,
                        style={"color": COLORS["accent"],
                               "fontFamily": "monospace"}),
                html.Td(p.modality,
                        style={"color": COLORS["sunlit"]
                               if p.modality == "Optical"
                               else COLORS["mmu"]}),
                html.Td(f"{p.size_mb:.1f}", style={"textAlign": "right"}),
                html.Td(f"{val:.1f}",
                        style={"textAlign": "right",
                               "color": COLORS["good"] if val > 50
                               else COLORS["warn"] if val > 20
                               else COLORS["text_muted"]}),
                html.Td(p.processing_mode,
                        style={"color": COLORS["gs_pass"] if p.processed
                               else COLORS["text_muted"]}),
            ], style={"fontSize": "11px"}))

        payload_content = html.Table([
            html.Thead(html.Tr([
                html.Th("ID"), html.Th("Type"), html.Th("MB"),
                html.Th("Value"), html.Th("Mode"),
            ], style={"fontSize": "10px", "color": COLORS["text_muted"],
                      "textTransform": "uppercase",
                      "letterSpacing": "0.5px"})),
            html.Tbody(rows),
        ], style={"width": "100%", "borderCollapse": "collapse"})
    else:
        payload_content = html.Div(
            "No payloads in MMU",
            style={"color": COLORS["text_muted"],
                   "fontStyle": "italic", "fontSize": "12px"})

    # ── Event log ─────────────────────────────────────────────────────
    event_items = [html.Div(e) for e in list(sim.events)[:20]]

    return (orbit_fig, telemetry_fig, gauge_fig,
            badges, metrics, payload_content, event_items)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 50)
    print("  LEO Satellite Dashboard")
    print("  Open  http://127.0.0.1:8050  in your browser")
    print("=" * 50)
    app.run(debug=False, port=8050)
