"""
Trend Visualization Module

Generates interactive Plotly charts for historical performance trends.
"""

from datetime import datetime
from typing import Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .trends_models import (
    PerformanceTrajectory,
    SeasonalPattern,
    TrendAnalysis,
    TrendDirection,
    YearOverYearComparison,
)


class TrendsPlotter:
    """Creates interactive visualizations for trend analysis."""

    def __init__(self):
        """Initialize the trends plotter."""
        self.color_scheme = {
            "improving": "#2ECC71",  # Green
            "stable": "#3498DB",  # Blue
            "declining": "#E74C3C",  # Red
            "neutral": "#95A5A6",  # Gray
            "trendline": "#F39C12",  # Orange
        }

    def plot_metric_trend(
        self,
        trend: TrendAnalysis,
        title: str | None = None,
        show_trendline: bool = True,
    ) -> go.Figure:
        """
        Create an interactive plot for a single metric trend.

        Args:
            trend: TrendAnalysis object to visualize
            title: Optional custom title
            show_trendline: Whether to show linear trend line

        Returns:
            Plotly Figure object
        """
        if not trend.data_points:
            # Return empty figure with message
            fig = go.Figure()
            fig.add_annotation(
                text="No data available",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
            )
            return fig

        # Extract data
        dates = [dp.timestamp for dp in trend.data_points]
        values = [dp.value for dp in trend.data_points]

        # Determine color based on trend direction
        if trend.direction == TrendDirection.IMPROVING:
            color = self.color_scheme["improving"]
        elif trend.direction == TrendDirection.DECLINING:
            color = self.color_scheme["declining"]
        else:
            color = self.color_scheme["stable"]

        # Create figure
        fig = go.Figure()

        # Add scatter plot for actual data
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=values,
                mode="markers+lines",
                name=trend.metric_name,
                marker=dict(size=8, color=color),
                line=dict(color=color, width=2),
                hovertemplate="<b>%{x}</b><br>Value: %{y:.2f}<extra></extra>",
            )
        )

        # Add trend line if requested and available
        if show_trendline and trend.trend_line_slope is not None:
            # Calculate trend line values
            x_numeric = [(d - dates[0]).days for d in dates]
            baseline = values[0] if values else 0
            trendline_values = [
                baseline + trend.trend_line_slope * x for x in x_numeric
            ]

            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=trendline_values,
                    mode="lines",
                    name="Trend Line",
                    line=dict(
                        color=self.color_scheme["trendline"], width=3, dash="dash"
                    ),
                    hovertemplate="<b>Trend</b><br>%{y:.2f}<extra></extra>",
                )
            )

        # Add baseline and current value annotations if available
        if trend.baseline_value is not None and trend.current_value is not None:
            fig.add_annotation(
                x=dates[0],
                y=trend.baseline_value,
                text=f"Baseline: {trend.baseline_value:.1f}",
                showarrow=True,
                arrowhead=2,
                ax=40,
                ay=-40,
            )

            fig.add_annotation(
                x=dates[-1],
                y=trend.current_value,
                text=f"Current: {trend.current_value:.1f}",
                showarrow=True,
                arrowhead=2,
                ax=-40,
                ay=-40,
            )

        # Update layout
        plot_title = title or f"{trend.metric_name} Trend Analysis"
        if trend.change_percentage is not None:
            plot_title += f" ({trend.change_percentage:+.1f}%)"

        fig.update_layout(
            title=plot_title,
            xaxis_title="Date",
            yaxis_title=trend.metric_name,
            hovermode="x unified",
            template="plotly_white",
            showlegend=True,
            height=500,
        )

        # Add direction indicator in subtitle
        direction_text = f"Direction: {trend.direction.value.upper()}"
        if trend.r_squared is not None:
            direction_text += f" (R² = {trend.r_squared:.3f})"

        fig.add_annotation(
            text=direction_text,
            xref="paper",
            yref="paper",
            x=0.5,
            y=1.05,
            showarrow=False,
            font=dict(size=12),
        )

        return fig

    def plot_seasonal_patterns(
        self, seasonal_patterns: list[SeasonalPattern], metric_name: str
    ) -> go.Figure:
        """
        Create a bar chart showing seasonal performance patterns.

        Args:
            seasonal_patterns: List of seasonal patterns
            metric_name: Name of the metric being analyzed

        Returns:
            Plotly Figure object
        """
        if not seasonal_patterns:
            fig = go.Figure()
            fig.add_annotation(
                text="No seasonal data available",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
            )
            return fig

        # Sort by month
        patterns_sorted = sorted(seasonal_patterns, key=lambda p: p.month)

        months = [p.month_name for p in patterns_sorted]
        avg_values = [p.average_value for p in patterns_sorted]
        sample_sizes = [p.sample_size for p in patterns_sorted]

        # Color bars based on whether they're above or below overall mean
        overall_mean = sum(avg_values) / len(avg_values)
        colors = [
            self.color_scheme["improving"] if v >= overall_mean else self.color_scheme["declining"]
            for v in avg_values
        ]

        # Create bar chart
        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=months,
                y=avg_values,
                marker=dict(color=colors),
                text=[f"{v:.1f}" for v in avg_values],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>"
                + f"{metric_name}: %{{y:.2f}}<br>"
                + "Sample size: %{customdata}<extra></extra>",
                customdata=sample_sizes,
            )
        )

        # Add horizontal line for overall mean
        fig.add_hline(
            y=overall_mean,
            line_dash="dash",
            line_color=self.color_scheme["neutral"],
            annotation_text=f"Annual Average: {overall_mean:.1f}",
            annotation_position="right",
        )

        fig.update_layout(
            title=f"Seasonal Patterns - {metric_name}",
            xaxis_title="Month",
            yaxis_title=f"Average {metric_name}",
            template="plotly_white",
            showlegend=False,
            height=500,
        )

        return fig

    def plot_year_over_year_comparison(
        self, comparisons: list[YearOverYearComparison], metric_name: str
    ) -> go.Figure:
        """
        Create a grouped bar chart for year-over-year comparisons.

        Args:
            comparisons: List of year-over-year comparisons
            metric_name: Name of the metric being analyzed

        Returns:
            Plotly Figure object
        """
        if not comparisons:
            fig = go.Figure()
            fig.add_annotation(
                text="No year-over-year data available",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
            )
            return fig

        # Sort by year
        comparisons_sorted = sorted(comparisons, key=lambda c: c.year)

        years = [str(c.year) for c in comparisons_sorted]
        values = [c.average_value for c in comparisons_sorted]
        sample_sizes = [c.sample_size for c in comparisons_sorted]

        # Color based on change from previous year
        colors = []
        for i, comp in enumerate(comparisons_sorted):
            if comp.change_from_previous is None or i == 0:
                colors.append(self.color_scheme["neutral"])
            elif comp.change_from_previous > 2:
                colors.append(self.color_scheme["improving"])
            elif comp.change_from_previous < -2:
                colors.append(self.color_scheme["declining"])
            else:
                colors.append(self.color_scheme["stable"])

        # Create bar chart
        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=years,
                y=values,
                marker=dict(color=colors),
                text=[
                    f"{v:.1f}"
                    + (f"<br>({c.change_from_previous:+.1f}%)" if c.change_from_previous else "")
                    for v, c in zip(values, comparisons_sorted)
                ],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>"
                + f"{metric_name}: %{{y:.2f}}<br>"
                + "Sample size: %{customdata}<extra></extra>",
                customdata=sample_sizes,
            )
        )

        fig.update_layout(
            title=f"Year-over-Year Comparison - {metric_name}",
            xaxis_title="Year",
            yaxis_title=f"Average {metric_name}",
            template="plotly_white",
            showlegend=False,
            height=500,
        )

        return fig

    def plot_performance_trajectory(
        self, trajectory: PerformanceTrajectory
    ) -> go.Figure:
        """
        Create a comprehensive multi-panel visualization for performance trajectory.

        Args:
            trajectory: PerformanceTrajectory object with complete analysis

        Returns:
            Plotly Figure with multiple subplots
        """
        # Determine number of metrics to plot
        num_metrics = len(trajectory.metric_trends)
        if num_metrics == 0:
            fig = go.Figure()
            fig.add_annotation(
                text="No metrics available",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
            )
            return fig

        # Create subplots - one row per metric
        fig = make_subplots(
            rows=num_metrics,
            cols=1,
            subplot_titles=[trend.metric_name for trend in trajectory.metric_trends],
            vertical_spacing=0.12,
        )

        # Add each metric trend
        for idx, trend in enumerate(trajectory.metric_trends, start=1):
            if not trend.data_points:
                continue

            dates = [dp.timestamp for dp in trend.data_points]
            values = [dp.value for dp in trend.data_points]

            # Determine color
            if trend.direction == TrendDirection.IMPROVING:
                color = self.color_scheme["improving"]
            elif trend.direction == TrendDirection.DECLINING:
                color = self.color_scheme["declining"]
            else:
                color = self.color_scheme["stable"]

            # Add data points
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=values,
                    mode="markers+lines",
                    name=trend.metric_name,
                    marker=dict(size=6, color=color),
                    line=dict(color=color, width=2),
                    showlegend=False,
                ),
                row=idx,
                col=1,
            )

            # Add trend line
            if trend.trend_line_slope is not None:
                x_numeric = [(d - dates[0]).days for d in dates]
                baseline = values[0] if values else 0
                trendline_values = [
                    baseline + trend.trend_line_slope * x for x in x_numeric
                ]

                fig.add_trace(
                    go.Scatter(
                        x=dates,
                        y=trendline_values,
                        mode="lines",
                        line=dict(
                            color=self.color_scheme["trendline"], width=2, dash="dash"
                        ),
                        showlegend=False,
                    ),
                    row=idx,
                    col=1,
                )

            # Update y-axis title
            fig.update_yaxes(title_text=trend.metric_name, row=idx, col=1)

        # Update layout
        title_text = f"Performance Trajectory - {trajectory.athlete_name}<br>"
        title_text += (
            f"<sub>{trajectory.analysis_period_years}-Year Analysis | "
            f"Overall: {trajectory.overall_direction.value.upper()}</sub>"
        )

        fig.update_layout(
            title=title_text,
            template="plotly_white",
            height=400 * num_metrics,
            hovermode="x unified",
        )

        # Update x-axis for bottom subplot only
        fig.update_xaxes(title_text="Date", row=num_metrics, col=1)

        return fig

    def create_trends_dashboard(
        self, trajectory: PerformanceTrajectory
    ) -> dict[str, go.Figure]:
        """
        Create a complete set of visualizations for a performance trajectory.

        Args:
            trajectory: PerformanceTrajectory object

        Returns:
            Dictionary of figure names to Plotly figures
        """
        figures = {}

        # Main trajectory plot
        figures["trajectory"] = self.plot_performance_trajectory(trajectory)

        # Individual metric trends
        for trend in trajectory.metric_trends:
            figure_name = f"trend_{trend.metric_name.lower().replace(' ', '_')}"
            figures[figure_name] = self.plot_metric_trend(trend)

        # Seasonal patterns for each metric with seasonal data
        for i, pattern_list in enumerate(trajectory.seasonal_patterns):
            if pattern_list:
                metric_name = trajectory.metric_trends[i].metric_name
                figure_name = f"seasonal_{metric_name.lower().replace(' ', '_')}"
                figures[figure_name] = self.plot_seasonal_patterns(
                    [pattern_list], metric_name
                )

        # Year-over-year comparisons
        for i, yoy_list in enumerate(trajectory.year_over_year):
            if yoy_list:
                metric_name = trajectory.metric_trends[i].metric_name
                figure_name = f"yoy_{metric_name.lower().replace(' ', '_')}"
                figures[figure_name] = self.plot_year_over_year_comparison(
                    [yoy_list], metric_name
                )

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

    def save_dashboard(
        self,
        figures: dict[str, go.Figure],
        output_dir: str,
        format: str = "html",
    ) -> list[str]:
        """
        Save all dashboard figures to files.

        Args:
            figures: Dictionary of figure names to figures
            output_dir: Output directory path
            format: Output format

        Returns:
            List of saved file paths
        """
        from pathlib import Path

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        saved_files = []
        for name, fig in figures.items():
            filepath = output_path / f"{name}.{format}"
            self.save_figure(fig, str(filepath), format=format)
            saved_files.append(str(filepath))

        return saved_files
