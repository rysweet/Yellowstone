"""
Benchmark report generation.

This module provides tools for generating comprehensive benchmark reports in
multiple formats (HTML, JSON). Reports include performance summaries, visualizations,
and regression detection.
"""

import json
from enum import Enum
from typing import Optional
from datetime import datetime

from .metrics_collector import BenchmarkResults, PerformanceSummary, MetricsCollector


class ReportFormat(Enum):
    """Report output format."""

    HTML = "html"
    JSON = "json"


class ReportGenerator:
    """Generates benchmark reports in various formats.

    Provides methods for creating HTML and JSON reports with performance
    summaries, charts, and regression detection.
    """

    def __init__(self) -> None:
        """Initialize the report generator."""
        self.collector = MetricsCollector()

    def generate_html_report(self, results: BenchmarkResults, output_path: str) -> None:
        """Generate an HTML benchmark report.

        Creates a comprehensive HTML report with:
        - Performance summary
        - Latency percentile charts
        - Query-by-query breakdown
        - Regression detection
        - Environment information

        Args:
            results: BenchmarkResults to report on
            output_path: Path to write HTML file

        Example:
            >>> generator = ReportGenerator()
            >>> generator.generate_html_report(results, "report.html")
        """
        summary = self.collector.compute_summary(results.query_metrics)

        # Generate HTML content
        html = self._generate_html_content(results, summary)

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

    def generate_json_report(self, results: BenchmarkResults, output_path: str) -> None:
        """Generate a JSON benchmark report.

        Creates a machine-readable JSON report with all metrics and summaries.

        Args:
            results: BenchmarkResults to report on
            output_path: Path to write JSON file

        Example:
            >>> generator = ReportGenerator()
            >>> generator.generate_json_report(results, "report.json")
        """
        summary = self.collector.compute_summary(results.query_metrics)

        report_data = {
            "run_id": results.run_id,
            "run_name": results.run_name,
            "start_time": results.start_time.isoformat(),
            "end_time": results.end_time.isoformat(),
            "duration_seconds": results.duration_seconds,
            "summary": self._summary_to_dict(summary),
            "configuration": results.configuration,
            "environment": results.environment,
            "query_metrics": self.collector.export_metrics(),
            "meets_targets": summary.meets_targets(),
            "translation_overhead_ok": summary.translation_overhead_within_target(),
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

    def _generate_html_content(
        self, results: BenchmarkResults, summary: PerformanceSummary
    ) -> str:
        """Generate HTML content for report.

        Args:
            results: BenchmarkResults to report
            summary: PerformanceSummary statistics

        Returns:
            Complete HTML string
        """
        # Determine status colors
        p50_status = "success" if summary.total_time_p50 < 1000 else "warning"
        p95_status = "success" if summary.total_time_p95 < 3000 else "warning"
        p99_status = "success" if summary.total_time_p99 < 5000 else "danger"
        overhead_status = "success" if summary.translation_overhead_within_target() else "warning"

        # Build query breakdown table
        query_rows = []
        for metric in results.query_metrics:
            status_class = "success" if metric.success else "danger"
            query_rows.append(
                f"""
                <tr class="{status_class}">
                    <td>{metric.query_id}</td>
                    <td>{metric.query_name}</td>
                    <td>{metric.metadata.get('complexity', 'N/A')}</td>
                    <td>{metric.total_time_ms:.2f}</td>
                    <td>{metric.translation_time_ms:.2f}</td>
                    <td>{metric.execution_time_ms:.2f}</td>
                    <td>{metric.result_count}</td>
                    <td>{metric.cache_hit}</td>
                    <td>{'✓' if metric.success else metric.error}</td>
                </tr>
                """
            )

        query_table = "\n".join(query_rows)

        # Group metrics by complexity
        complexity_summaries = []
        for complexity in ["simple", "medium", "complex", "stress"]:
            complexity_metrics = self.collector.get_metrics_by_complexity(complexity)
            if complexity_metrics:
                complexity_summary = self.collector.compute_summary(complexity_metrics)
                complexity_summaries.append(
                    f"""
                    <tr>
                        <td>{complexity.capitalize()}</td>
                        <td>{len(complexity_metrics)}</td>
                        <td>{complexity_summary.total_time_p50:.2f}</td>
                        <td>{complexity_summary.total_time_p95:.2f}</td>
                        <td>{complexity_summary.total_time_avg:.2f}</td>
                        <td>{complexity_summary.translation_overhead_avg * 100:.1f}%</td>
                    </tr>
                    """
                )

        complexity_table = "\n".join(complexity_summaries)

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Yellowstone Benchmark Report - {results.run_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}

        h2 {{
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 2px solid #ecf0f1;
        }}

        .header-info {{
            background: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 30px;
        }}

        .header-info p {{
            margin: 5px 0;
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}

        .metric-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            border-left: 4px solid #3498db;
        }}

        .metric-card.success {{
            border-left-color: #27ae60;
        }}

        .metric-card.warning {{
            border-left-color: #f39c12;
        }}

        .metric-card.danger {{
            border-left-color: #e74c3c;
        }}

        .metric-label {{
            font-size: 0.9em;
            color: #7f8c8d;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
            margin: 10px 0;
        }}

        .metric-target {{
            font-size: 0.85em;
            color: #95a5a6;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 0.9em;
        }}

        th {{
            background: #34495e;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}

        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #ecf0f1;
        }}

        tr:hover {{
            background: #f8f9fa;
        }}

        tr.success td {{
            background: #d4edda;
        }}

        tr.danger td {{
            background: #f8d7da;
        }}

        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }}

        .status-badge.success {{
            background: #27ae60;
            color: white;
        }}

        .status-badge.warning {{
            background: #f39c12;
            color: white;
        }}

        .status-badge.danger {{
            background: #e74c3c;
            color: white;
        }}

        .summary-box {{
            background: #e8f4f8;
            border: 2px solid #3498db;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}

        .summary-box h3 {{
            color: #2980b9;
            margin-bottom: 10px;
        }}

        .summary-box p {{
            margin: 5px 0;
        }}

        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #ecf0f1;
            text-align: center;
            color: #95a5a6;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Yellowstone Benchmark Report</h1>

        <div class="header-info">
            <p><strong>Run Name:</strong> {results.run_name}</p>
            <p><strong>Run ID:</strong> {results.run_id}</p>
            <p><strong>Start Time:</strong> {results.start_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Duration:</strong> {results.duration_seconds:.2f} seconds</p>
            <p><strong>Platform:</strong> {results.environment.get('platform', 'N/A')}</p>
        </div>

        <div class="summary-box">
            <h3>Overall Performance Status</h3>
            <p>
                <strong>Target Metrics:</strong>
                {'<span class="status-badge success">✓ ALL TARGETS MET</span>' if summary.meets_targets() else '<span class="status-badge danger">✗ TARGETS NOT MET</span>'}
            </p>
            <p>
                <strong>Translation Overhead:</strong>
                {'<span class="status-badge success">✓ WITHIN ACCEPTABLE RANGE</span>' if summary.translation_overhead_within_target() else '<span class="status-badge warning">⚠ OUTSIDE TARGET RANGE</span>'}
            </p>
        </div>

        <h2>Performance Summary</h2>

        <div class="metrics-grid">
            <div class="metric-card {p50_status}">
                <div class="metric-label">P50 Latency</div>
                <div class="metric-value">{summary.total_time_p50:.0f}ms</div>
                <div class="metric-target">Target: &lt; 1000ms</div>
            </div>

            <div class="metric-card {p95_status}">
                <div class="metric-label">P95 Latency</div>
                <div class="metric-value">{summary.total_time_p95:.0f}ms</div>
                <div class="metric-target">Target: &lt; 3000ms</div>
            </div>

            <div class="metric-card {p99_status}">
                <div class="metric-label">P99 Latency</div>
                <div class="metric-value">{summary.total_time_p99:.0f}ms</div>
                <div class="metric-target">Target: &lt; 5000ms</div>
            </div>

            <div class="metric-card">
                <div class="metric-label">Average Latency</div>
                <div class="metric-value">{summary.total_time_avg:.0f}ms</div>
                <div class="metric-target">Min: {summary.total_time_min:.0f}ms | Max: {summary.total_time_max:.0f}ms</div>
            </div>

            <div class="metric-card {overhead_status}">
                <div class="metric-label">Translation Overhead</div>
                <div class="metric-value">{summary.translation_overhead_avg * 100:.1f}%</div>
                <div class="metric-target">Target: 20-67%</div>
            </div>

            <div class="metric-card">
                <div class="metric-label">Throughput</div>
                <div class="metric-value">{summary.throughput_qps:.1f}</div>
                <div class="metric-target">queries per second</div>
            </div>

            <div class="metric-card success">
                <div class="metric-label">Success Rate</div>
                <div class="metric-value">{results.success_rate:.1f}%</div>
                <div class="metric-target">{results.successful_queries}/{results.total_queries} queries</div>
            </div>

            <div class="metric-card">
                <div class="metric-label">Cache Hit Rate</div>
                <div class="metric-value">{summary.cache_hit_rate:.1f}%</div>
                <div class="metric-target">cached results</div>
            </div>
        </div>

        <h2>Performance by Complexity</h2>
        <table>
            <thead>
                <tr>
                    <th>Complexity</th>
                    <th>Query Count</th>
                    <th>P50 (ms)</th>
                    <th>P95 (ms)</th>
                    <th>Avg (ms)</th>
                    <th>Translation Overhead</th>
                </tr>
            </thead>
            <tbody>
                {complexity_table}
            </tbody>
        </table>

        <h2>Query Details</h2>
        <table>
            <thead>
                <tr>
                    <th>Query ID</th>
                    <th>Name</th>
                    <th>Complexity</th>
                    <th>Total Time (ms)</th>
                    <th>Translation (ms)</th>
                    <th>Execution (ms)</th>
                    <th>Results</th>
                    <th>Cached</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {query_table}
            </tbody>
        </table>

        <h2>System Resources</h2>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Average Memory Usage</div>
                <div class="metric-value">{summary.avg_memory_usage_mb:.1f}MB</div>
            </div>

            <div class="metric-card">
                <div class="metric-label">Average CPU Usage</div>
                <div class="metric-value">{summary.avg_cpu_usage_percent:.1f}%</div>
            </div>
        </div>

        <div class="footer">
            <p>Generated by Yellowstone Benchmark Suite v0.1.0</p>
            <p>Report generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
        """

        return html

    def _summary_to_dict(self, summary: PerformanceSummary) -> dict:
        """Convert PerformanceSummary to dictionary.

        Args:
            summary: PerformanceSummary to convert

        Returns:
            Dictionary representation
        """
        return {
            "total_queries": summary.total_queries,
            "successful_queries": summary.successful_queries,
            "failed_queries": summary.failed_queries,
            "latency": {
                "total_time_ms": {
                    "p50": summary.total_time_p50,
                    "p95": summary.total_time_p95,
                    "p99": summary.total_time_p99,
                    "avg": summary.total_time_avg,
                    "min": summary.total_time_min,
                    "max": summary.total_time_max,
                },
                "translation_time_ms": {
                    "p50": summary.translation_time_p50,
                    "p95": summary.translation_time_p95,
                    "avg": summary.translation_time_avg,
                },
                "execution_time_ms": {
                    "p50": summary.execution_time_p50,
                    "p95": summary.execution_time_p95,
                    "avg": summary.execution_time_avg,
                },
            },
            "translation_overhead_avg": summary.translation_overhead_avg,
            "cache_hit_rate": summary.cache_hit_rate,
            "resource_usage": {
                "avg_memory_mb": summary.avg_memory_usage_mb,
                "avg_cpu_percent": summary.avg_cpu_usage_percent,
            },
            "throughput_qps": summary.throughput_qps,
            "targets": {
                "meets_latency_targets": summary.meets_targets(),
                "translation_overhead_ok": summary.translation_overhead_within_target(),
            },
        }

    def generate_comparison_report(
        self,
        baseline_results: BenchmarkResults,
        current_results: BenchmarkResults,
        output_path: str,
    ) -> None:
        """Generate comparison report between two benchmark runs.

        Args:
            baseline_results: Baseline benchmark results
            current_results: Current benchmark results to compare
            output_path: Path to write HTML report

        Example:
            >>> generator.generate_comparison_report(baseline, current, "comparison.html")
        """
        baseline_summary = self.collector.compute_summary(baseline_results.query_metrics)
        current_summary = self.collector.compute_summary(current_results.query_metrics)

        comparison = self.collector.compare_performance(
            baseline_results.query_metrics, current_results.query_metrics
        )

        html = self._generate_comparison_html(
            baseline_results,
            current_results,
            baseline_summary,
            current_summary,
            comparison,
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

    def _generate_comparison_html(
        self,
        baseline_results: BenchmarkResults,
        current_results: BenchmarkResults,
        baseline_summary: PerformanceSummary,
        current_summary: PerformanceSummary,
        comparison: dict,
    ) -> str:
        """Generate HTML for comparison report.

        Args:
            baseline_results: Baseline results
            current_results: Current results
            baseline_summary: Baseline summary
            current_summary: Current summary
            comparison: Comparison dictionary

        Returns:
            HTML string
        """
        # Determine improvement status
        p50_improved = comparison["p50_improvement_percent"] > 0
        p95_improved = comparison["p95_improvement_percent"] > 0
        throughput_improved = comparison["throughput_improvement_percent"] > 0

        p50_class = "success" if p50_improved else "danger"
        p95_class = "success" if p95_improved else "danger"
        throughput_class = "success" if throughput_improved else "danger"

        regression_alert = ""
        if comparison["regression_detected"]:
            regression_alert = """
            <div style="background: #f8d7da; border: 2px solid #e74c3c; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3 style="color: #e74c3c; margin: 0 0 10px 0;">⚠ Performance Regression Detected</h3>
                <p>Current performance is significantly worse than baseline. Review the changes that caused this regression.</p>
            </div>
            """

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Benchmark Comparison Report</title>
    <style>
        /* Same CSS as main report */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; margin-bottom: 30px; }}
        .comparison-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }}
        .comparison-card {{ background: #f8f9fa; padding: 20px; border-radius: 5px; }}
        .comparison-card.success {{ border-left: 4px solid #27ae60; }}
        .comparison-card.danger {{ border-left: 4px solid #e74c3c; }}
        .metric-label {{ font-size: 0.9em; color: #7f8c8d; text-transform: uppercase; }}
        .metric-value {{ font-size: 1.8em; font-weight: bold; color: #2c3e50; margin: 10px 0; }}
        .improvement {{ font-size: 1.2em; font-weight: bold; }}
        .improvement.positive {{ color: #27ae60; }}
        .improvement.negative {{ color: #e74c3c; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Benchmark Comparison Report</h1>

        {regression_alert}

        <h2>Performance Comparison</h2>

        <div class="comparison-grid">
            <div class="comparison-card {p50_class}">
                <div class="metric-label">P50 Latency</div>
                <div>
                    <span style="color: #7f8c8d;">Baseline:</span> {comparison['baseline']['p50_ms']:.0f}ms<br>
                    <span style="color: #7f8c8d;">Current:</span> {comparison['current']['p50_ms']:.0f}ms
                </div>
                <div class="improvement {'positive' if p50_improved else 'negative'}">
                    {comparison['p50_improvement_percent']:+.1f}%
                </div>
            </div>

            <div class="comparison-card {p95_class}">
                <div class="metric-label">P95 Latency</div>
                <div>
                    <span style="color: #7f8c8d;">Baseline:</span> {comparison['baseline']['p95_ms']:.0f}ms<br>
                    <span style="color: #7f8c8d;">Current:</span> {comparison['current']['p95_ms']:.0f}ms
                </div>
                <div class="improvement {'positive' if p95_improved else 'negative'}">
                    {comparison['p95_improvement_percent']:+.1f}%
                </div>
            </div>

            <div class="comparison-card {throughput_class}">
                <div class="metric-label">Throughput</div>
                <div>
                    <span style="color: #7f8c8d;">Baseline:</span> {comparison['baseline']['throughput_qps']:.1f} QPS<br>
                    <span style="color: #7f8c8d;">Current:</span> {comparison['current']['throughput_qps']:.1f} QPS
                </div>
                <div class="improvement {'positive' if throughput_improved else 'negative'}">
                    {comparison['throughput_improvement_percent']:+.1f}%
                </div>
            </div>
        </div>

        <div style="margin-top: 40px; text-align: center; color: #95a5a6;">
            Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>
        """

        return html
