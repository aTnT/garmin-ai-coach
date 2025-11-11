"""
Power Curve Visualization Module

Generates interactive Plotly charts for power curves and critical power analysis.
"""

from datetime import datetime

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .power_models import (
    CriticalPower,
    CriticalPowerHistory,
    FitnessSignature,
    PowerCurve,
    PowerCurveComparison,
    PowerMetric,
    TrainingZones,
)


class PowerCurvePlotter:
    """Creates interactive visualizations for power curve analysis."""

    def __init__(self):
        """Initialize the power curve plotter."""
        self.color_scheme = {
            "power_curve": "#3498DB",  # Blue
            "cp_model": "#E74C3C",  # Red
            "best_efforts": "#2ECC71",  # Green
            "comparison": "#F39C12",  # Orange
            "zones": {
                1: "#95A5A6",  # Recovery: Gray
                2: "#3498DB",  # Endurance: Blue
                3: "#2ECC71",  # Tempo: Green
                4: "#F39C12",  # Threshold: Orange
                5: "#E74C3C",  # VO2max: Red
                6: "#9B59B6",  # Anaerobic: Purple
            },
        }

    def plot_power_curve(
        self,
        power_curve: PowerCurve,
        show_model: bool = True,
        cp_model: CriticalPower | None = None,
    ) -> go.Figure:
        """
        Create an interactive power curve plot.

        Args:
            power_curve: PowerCurve object to visualize
            show_model: Whether to overlay CP model prediction
            cp_model: Optional CriticalPower model to display

        Returns:
            Plotly Figure object
        """
        if not power_curve.best_efforts:
            fig = go.Figure()
            fig.add_annotation(
                text="No power data available",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
            )
            return fig

        # Extract data
        durations = [e.duration_seconds for e in power_curve.best_efforts]
        powers = [e.value for e in power_curve.best_efforts]

        # Determine y-axis label
        if power_curve.metric_type == PowerMetric.POWER_WATTS:
            y_label = "Power (watts)"
        elif power_curve.metric_type in [PowerMetric.PACE_MIN_PER_KM, PowerMetric.PACE_MIN_PER_MILE]:
            y_label = f"Pace ({power_curve.metric_type.value})"
        else:
            y_label = f"Speed ({power_curve.metric_type.value})"

        # Create figure
        fig = go.Figure()

        # Add best efforts as scatter plot
        hover_text = [
            f"<b>{e.duration_label}</b><br>"
            f"Power: {e.value:.1f}<br>"
            f"Date: {e.activity_date.strftime('%Y-%m-%d') if e.activity_date else 'Unknown'}<br>"
            f"Activity: {e.activity_name or 'Unknown'}"
            for e in power_curve.best_efforts
        ]

        fig.add_trace(
            go.Scatter(
                x=durations,
                y=powers,
                mode="markers+lines",
                name="Best Efforts",
                marker=dict(size=10, color=self.color_scheme["best_efforts"]),
                line=dict(color=self.color_scheme["power_curve"], width=2),
                hovertemplate="%{customdata}<extra></extra>",
                customdata=hover_text,
            )
        )

        # Add CP model curve if requested
        if show_model and cp_model:
            # Generate smooth curve for CP model
            duration_range = np.linspace(min(durations), max(durations), 100)
            model_powers = [cp_model.predict_power(d) for d in duration_range]

            fig.add_trace(
                go.Scatter(
                    x=duration_range,
                    y=model_powers,
                    mode="lines",
                    name=f"CP Model (CP={cp_model.cp:.1f}, W'={cp_model.w_prime:.0f}J)",
                    line=dict(color=self.color_scheme["cp_model"], width=3, dash="dash"),
                    hovertemplate="<b>CP Model</b><br>Duration: %{x}s<br>Power: %{y:.1f}<extra></extra>",
                )
            )

            # Add CP line
            fig.add_hline(
                y=cp_model.cp,
                line_dash="dot",
                line_color=self.color_scheme["cp_model"],
                annotation_text=f"Critical Power: {cp_model.cp:.1f}",
                annotation_position="right",
            )

        # Update layout with log scale on x-axis for better visualization
        fig.update_layout(
            title=f"Power Curve - {power_curve.athlete_name}<br>"
                  f"<sub>{power_curve.data_period_start.strftime('%Y-%m-%d')} to "
                  f"{power_curve.data_period_end.strftime('%Y-%m-%d')} "
                  f"({power_curve.total_activities} activities)</sub>",
            xaxis_title="Duration (seconds)",
            yaxis_title=y_label,
            xaxis_type="log",
            hovermode="closest",
            template="plotly_white",
            showlegend=True,
            height=600,
        )

        # Add custom x-axis tick labels
        tick_vals = [5, 30, 60, 300, 1200, 3600, 7200]
        tick_text = ["5s", "30s", "1min", "5min", "20min", "1hr", "2hr"]
        fig.update_xaxes(tickvals=tick_vals, ticktext=tick_text)

        return fig

    def plot_training_zones(self, zones: TrainingZones) -> go.Figure:
        """
        Create a visualization of training zones.

        Args:
            zones: TrainingZones object

        Returns:
            Plotly Figure object
        """
        # Create horizontal bar chart for zones
        zone_boundaries = [
            0,
            zones.recovery_max,
            zones.endurance_max,
            zones.tempo_max,
            zones.threshold_max,
            zones.vo2max_max,
            zones.anaerobic_min * 1.3,  # Upper bound for visual
        ]

        zone_names = zones.zone_names
        zone_colors = [self.color_scheme["zones"][i+1] for i in range(6)]

        fig = go.Figure()

        # Add each zone as a bar
        for i in range(len(zone_names)):
            lower = zone_boundaries[i]
            upper = zone_boundaries[i + 1]
            mid_point = (lower + upper) / 2

            fig.add_trace(
                go.Bar(
                    x=[upper - lower],
                    y=[zone_names[i]],
                    orientation="h",
                    name=f"Zone {i+1}: {zone_names[i]}",
                    marker=dict(color=zone_colors[i]),
                    text=f"{lower:.0f}-{upper:.0f}",
                    textposition="inside",
                    hovertemplate=f"<b>Zone {i+1}: {zone_names[i]}</b><br>"
                                  f"Range: {lower:.0f}-{upper:.0f}<br>"
                                  f"<extra></extra>",
                    base=lower,
                )
            )

        # Add CP marker
        fig.add_vline(
            x=zones.cp,
            line_dash="dash",
            line_color="black",
            line_width=2,
            annotation_text=f"CP: {zones.cp:.0f}",
            annotation_position="top",
        )

        fig.update_layout(
            title="Training Zones (Based on Critical Power)",
            xaxis_title="Power (watts)" if zones.metric_type == PowerMetric.POWER_WATTS else "Pace",
            yaxis_title="Zone",
            barmode="overlay",
            template="plotly_white",
            showlegend=False,
            height=400,
        )

        return fig

    def plot_power_curve_comparison(
        self, comparison: PowerCurveComparison
    ) -> go.Figure:
        """
        Create a comparison plot between two power curves.

        Args:
            comparison: PowerCurveComparison object

        Returns:
            Plotly Figure object
        """
        fig = go.Figure()

        # Current curve
        current_durations = [e.duration_seconds for e in comparison.current_curve.best_efforts]
        current_powers = [e.value for e in comparison.current_curve.best_efforts]

        fig.add_trace(
            go.Scatter(
                x=current_durations,
                y=current_powers,
                mode="markers+lines",
                name="Current",
                marker=dict(size=10, color=self.color_scheme["best_efforts"]),
                line=dict(color=self.color_scheme["power_curve"], width=2),
            )
        )

        # Comparison curve
        comp_durations = [e.duration_seconds for e in comparison.comparison_curve.best_efforts]
        comp_powers = [e.value for e in comparison.comparison_curve.best_efforts]

        fig.add_trace(
            go.Scatter(
                x=comp_durations,
                y=comp_powers,
                mode="markers+lines",
                name=comparison.comparison_label,
                marker=dict(size=10, color=self.color_scheme["comparison"]),
                line=dict(color=self.color_scheme["comparison"], width=2, dash="dash"),
            )
        )

        # Determine y-axis label
        if comparison.metric_type == PowerMetric.POWER_WATTS:
            y_label = "Power (watts)"
        else:
            y_label = f"Pace/Speed ({comparison.metric_type.value})"

        fig.update_layout(
            title=f"Power Curve Comparison - {comparison.comparison_label}<br>"
                  f"<sub>Overall Change: {comparison.overall_change_percent:+.1f}%</sub>",
            xaxis_title="Duration (seconds)",
            yaxis_title=y_label,
            xaxis_type="log",
            template="plotly_white",
            showlegend=True,
            height=600,
        )

        # Custom x-axis ticks
        tick_vals = [5, 30, 60, 300, 1200, 3600, 7200]
        tick_text = ["5s", "30s", "1min", "5min", "20min", "1hr", "2hr"]
        fig.update_xaxes(tickvals=tick_vals, ticktext=tick_text)

        return fig

    def plot_critical_power_history(
        self, cp_history: CriticalPowerHistory
    ) -> go.Figure:
        """
        Create a plot showing CP and W' evolution over time.

        Args:
            cp_history: CriticalPowerHistory object

        Returns:
            Plotly Figure with two subplots (CP and W')
        """
        fig = make_subplots(
            rows=2,
            cols=1,
            subplot_titles=("Critical Power (CP)", "Anaerobic Capacity (W')"),
            vertical_spacing=0.15,
        )

        # CP over time
        cp_dates = [m[0] for m in cp_history.cp_measurements]
        cp_values = [m[1] for m in cp_history.cp_measurements]

        fig.add_trace(
            go.Scatter(
                x=cp_dates,
                y=cp_values,
                mode="markers+lines",
                name="CP",
                marker=dict(size=10, color=self.color_scheme["power_curve"]),
                line=dict(color=self.color_scheme["power_curve"], width=2),
            ),
            row=1,
            col=1,
        )

        # W' over time
        w_dates = [m[0] for m in cp_history.w_prime_measurements]
        w_values = [m[1] for m in cp_history.w_prime_measurements]

        fig.add_trace(
            go.Scatter(
                x=w_dates,
                y=w_values,
                mode="markers+lines",
                name="W'",
                marker=dict(size=10, color=self.color_scheme["cp_model"]),
                line=dict(color=self.color_scheme["cp_model"], width=2),
                showlegend=False,
            ),
            row=2,
            col=1,
        )

        # Update axes
        fig.update_yaxes(title_text="CP (watts)", row=1, col=1)
        fig.update_yaxes(title_text="W' (joules)", row=2, col=1)
        fig.update_xaxes(title_text="Date", row=2, col=1)

        # Add trend annotations
        cp_trend_text = ""
        if cp_history.cp_trend_direction and cp_history.cp_change_percent:
            cp_trend_text = f" ({cp_history.cp_trend_direction.upper()}: {cp_history.cp_change_percent:+.1f}%)"

        w_trend_text = ""
        if cp_history.w_prime_trend_direction and cp_history.w_prime_change_percent:
            w_trend_text = f" ({cp_history.w_prime_trend_direction.upper()}: {cp_history.w_prime_change_percent:+.1f}%)"

        fig.update_layout(
            title=f"Fitness Signature Evolution - {cp_history.athlete_name}<br>"
                  f"<sub>CP{cp_trend_text} | W'{w_trend_text}</sub>",
            template="plotly_white",
            height=700,
            hovermode="x unified",
        )

        return fig

    def plot_fitness_signature(self, signature: FitnessSignature) -> go.Figure:
        """
        Create a radar chart of fitness signature.

        Args:
            signature: FitnessSignature object

        Returns:
            Plotly Figure object
        """
        # Prepare data for radar chart
        categories = []
        values = []

        if signature.peak_5_sec:
            categories.append("5s Sprint")
            # Normalize to 0-100 scale (arbitrary max: 1500W for cycling)
            values.append(min(100, (signature.peak_5_sec / 15) * 100))

        if signature.peak_1_min:
            categories.append("1min Power")
            values.append(min(100, (signature.peak_1_min / 8) * 100))

        if signature.peak_5_min:
            categories.append("5min Power")
            values.append(min(100, (signature.peak_5_min / 5) * 100))

        if signature.peak_20_min:
            categories.append("20min Power")
            values.append(min(100, (signature.peak_20_min / 4) * 100))

        if signature.peak_60_min:
            categories.append("60min Power")
            values.append(min(100, (signature.peak_60_min / 3.5) * 100))

        if signature.fatigue_resistance:
            categories.append("Fatigue Resistance")
            values.append(signature.fatigue_resistance * 100)

        if not categories:
            fig = go.Figure()
            fig.add_annotation(
                text="Insufficient data for fitness signature",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
            )
            return fig

        fig = go.Figure()

        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=categories,
                fill="toself",
                name="Fitness Profile",
                marker=dict(color=self.color_scheme["power_curve"]),
            )
        )

        profile_text = signature.fitness_profile.value.replace("_", " ").title() if signature.fitness_profile else "Unknown"

        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100])
            ),
            title=f"Fitness Signature - {signature.signature_date.strftime('%Y-%m-%d')}<br>"
                  f"<sub>Profile: {profile_text} | CP: {signature.cp:.1f} | W': {signature.w_prime:.0f}J</sub>",
            template="plotly_white",
            height=600,
        )

        return fig

    def plot_limiter_analysis(
        self, limiters: dict, athlete_name: str
    ) -> go.Figure:
        """
        Create a bar chart showing relative strengths and weaknesses.

        Args:
            limiters: Dictionary from identify_limiters()
            athlete_name: Athlete's name

        Returns:
            Plotly Figure object
        """
        categories = ["Sprint", "Anaerobic", "VO2max", "Threshold", "Endurance"]
        scores = []
        colors = []

        # Convert limiter assessment to scores (100 = strong, 50 = moderate, 0 = weak)
        for key in ["sprint_power", "anaerobic_capacity", "vo2max", "threshold", "endurance"]:
            if limiters.get(key) == "weak":
                scores.append(30)
                colors.append(self.color_scheme["cp_model"])  # Red
            elif limiters.get(key) == "moderate":
                scores.append(60)
                colors.append(self.color_scheme["comparison"])  # Orange
            else:  # strong or None
                scores.append(90)
                colors.append(self.color_scheme["best_efforts"])  # Green

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=categories,
                y=scores,
                marker=dict(color=colors),
                text=[f"{s}%" for s in scores],
                textposition="outside",
            )
        )

        fig.update_layout(
            title=f"Performance Profile - {athlete_name}<br>"
                  f"<sub>Strengths and Limiters</sub>",
            xaxis_title="Performance Category",
            yaxis_title="Relative Strength (%)",
            yaxis_range=[0, 110],
            template="plotly_white",
            showlegend=False,
            height=500,
        )

        return fig

    def plot_race_prediction(
        self, prediction: dict, race_name: str = "Target Race"
    ) -> go.Figure:
        """
        Create a visualization of race performance prediction.

        Args:
            prediction: Dictionary from predict_race_performance()
            race_name: Name of the race

        Returns:
            Plotly Figure object
        """
        # Create pie chart for energy contribution
        labels = ["Aerobic (CP)", "Anaerobic (W')"]
        values = [
            prediction["power_from_aerobic_kj"],
            prediction["power_from_anaerobic_kj"],
        ]
        colors = [self.color_scheme["power_curve"], self.color_scheme["cp_model"]]

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    marker=dict(colors=colors),
                    hole=0.4,
                    textinfo="label+percent",
                    hovertemplate="<b>%{label}</b><br>Energy: %{value:.1f} kJ<extra></extra>",
                )
            ]
        )

        fig.update_layout(
            title=f"Race Performance Prediction - {race_name}<br>"
                  f"<sub>Duration: {prediction['race_duration_minutes']:.1f} min | "
                  f"Avg Power: {prediction['predicted_average_power']:.1f}W | "
                  f"Total Work: {prediction['total_work_kj']:.1f} kJ</sub>",
            template="plotly_white",
            height=500,
        )

        return fig

    def create_power_dashboard(
        self,
        power_curve: PowerCurve,
        cp_model: CriticalPower,
        zones: TrainingZones,
        signature: FitnessSignature,
        limiters: dict | None = None,
    ) -> dict[str, go.Figure]:
        """
        Create a complete dashboard of power analysis visualizations.

        Args:
            power_curve: PowerCurve object
            cp_model: CriticalPower model
            zones: TrainingZones object
            signature: FitnessSignature object
            limiters: Optional limiter analysis

        Returns:
            Dictionary of figure names to Plotly figures
        """
        figures = {}

        # Main power curve
        figures["power_curve"] = self.plot_power_curve(power_curve, show_model=True, cp_model=cp_model)

        # Training zones
        figures["training_zones"] = self.plot_training_zones(zones)

        # Fitness signature
        figures["fitness_signature"] = self.plot_fitness_signature(signature)

        # Limiter analysis
        if limiters:
            figures["limiters"] = self.plot_limiter_analysis(limiters, power_curve.athlete_name)

        return figures

    def save_figure(
        self,
        fig: go.Figure,
        filepath: str,
        format: str = "html",
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """
        Save a figure to file.

        Args:
            fig: Plotly figure to save
            filepath: Output file path
            format: Output format ('html', 'png', 'svg', 'pdf')
            width: Optional width in pixels (for image formats)
            height: Optional height in pixels (for image formats)
        """
        if format == "html":
            fig.write_html(filepath)
        elif format in ["png", "svg", "pdf"]:
            fig.write_image(filepath, width=width, height=height)
        else:
            raise ValueError(f"Unsupported format: {format}")
