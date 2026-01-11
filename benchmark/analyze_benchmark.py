#!/usr/bin/env python3
"""
Analyze benchmark results and generate comprehensive report.
"""
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
import statistics

# Get script directory and project root
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

OUTPUT_DIR = PROJECT_ROOT / "benchmark_results"


def load_latest_results() -> Dict[str, Any]:
    """Load the most recent benchmark results."""
    if not OUTPUT_DIR.exists():
        print(f"Error: Results directory not found: {OUTPUT_DIR}")
        sys.exit(1)
    
    result_files = sorted(OUTPUT_DIR.glob("benchmark_results_*.json"), reverse=True)
    if not result_files:
        print("Error: No benchmark results found")
        sys.exit(1)
    
    latest_file = result_files[0]
    print(f"Loading results from: {latest_file}")
    
    with open(latest_file, 'r') as f:
        return json.load(f)


def analyze_results(data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze benchmark results and generate insights."""
    repos = data.get("repos", [])
    
    if not repos:
        return {"error": "No repository data found"}
    
    successful = [r for r in repos if r.get("success")]
    failed = [r for r in repos if not r.get("success")]
    
    # Basic statistics
    analysis = {
        "total_repos": len(repos),
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": len(successful) / len(repos) * 100 if repos else 0,
    }
    
    if not successful:
        return analysis
    
    # Timing analysis
    durations = [r.get("duration", 0) for r in successful]
    analysis["timing"] = {
        "min": min(durations),
        "max": max(durations),
        "mean": statistics.mean(durations),
        "median": statistics.median(durations),
        "stdev": statistics.stdev(durations) if len(durations) > 1 else 0,
    }
    
    # Stage-by-stage timing analysis
    stage_1_times = []
    stage_2_times = []
    for r in successful:
        stage_timings = r.get("stage_timings", {})
        if "Dependency Analysis" in stage_timings:
            stage_1_times.append(stage_timings["Dependency Analysis"])
        if "Module Clustering" in stage_timings:
            stage_2_times.append(stage_timings["Module Clustering"])
    
    if stage_1_times:
        analysis["stage_1_timing"] = {
            "min": min(stage_1_times),
            "max": max(stage_1_times),
            "mean": statistics.mean(stage_1_times),
            "median": statistics.median(stage_1_times),
        }
    
    if stage_2_times:
        analysis["stage_2_timing"] = {
            "min": min(stage_2_times),
            "max": max(stage_2_times),
            "mean": statistics.mean(stage_2_times),
            "median": statistics.median(stage_2_times),
        }
    
    # File creation analysis
    files_created = [r.get("files_created", 0) for r in successful]
    analysis["files"] = {
        "min": min(files_created),
        "max": max(files_created),
        "mean": statistics.mean(files_created),
        "median": statistics.median(files_created),
    }
    
    # Component and module counts
    component_counts = [r.get("component_count", 0) for r in successful if r.get("component_count")]
    module_counts = [r.get("module_count", 0) for r in successful if r.get("module_count")]
    
    if component_counts:
        analysis["components"] = {
            "min": min(component_counts),
            "max": max(component_counts),
            "mean": statistics.mean(component_counts),
            "median": statistics.median(component_counts),
        }
    
    if module_counts:
        analysis["modules"] = {
            "min": min(module_counts),
            "max": max(module_counts),
            "mean": statistics.mean(module_counts),
            "median": statistics.median(module_counts),
        }
    
    # Correlation: repo size vs duration
    size_duration_pairs = [
        (r.get("size_mb", 0), r.get("duration", 0))
        for r in successful
        if r.get("size_mb") and r.get("duration")
    ]
    
    # Correlation: code files vs duration
    code_files_duration_pairs = [
        (r.get("total_code_files", 0), r.get("duration", 0))
        for r in successful
        if r.get("total_code_files") and r.get("duration")
    ]
    
    # Correlation: components vs duration
    components_duration_pairs = [
        (r.get("component_count", 0), r.get("duration", 0))
        for r in successful
        if r.get("component_count") and r.get("duration")
    ]
    
    # Correlation: components vs modules
    components_modules_pairs = [
        (r.get("component_count", 0), r.get("module_count", 0))
        for r in successful
        if r.get("component_count") and r.get("module_count")
    ]
    
    def calculate_correlation(x_values, y_values):
        """Calculate Pearson correlation coefficient."""
        if len(x_values) <= 1:
            return 0
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(y_values)
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        x_var = sum((x - x_mean) ** 2 for x in x_values)
        y_var = sum((y - y_mean) ** 2 for y in y_values)
        return numerator / ((x_var * y_var) ** 0.5) if (x_var * y_var) > 0 else 0
    
    analysis["correlations"] = {}
    
    if size_duration_pairs and len(size_duration_pairs) > 1:
        sizes, durations = zip(*size_duration_pairs)
        analysis["correlations"]["size_vs_duration"] = calculate_correlation(sizes, durations)
    
    if code_files_duration_pairs and len(code_files_duration_pairs) > 1:
        code_files, durations = zip(*code_files_duration_pairs)
        analysis["correlations"]["code_files_vs_duration"] = calculate_correlation(code_files, durations)
    
    if components_duration_pairs and len(components_duration_pairs) > 1:
        components, durations = zip(*components_duration_pairs)
        analysis["correlations"]["components_vs_duration"] = calculate_correlation(components, durations)
    
    if components_modules_pairs and len(components_modules_pairs) > 1:
        components, modules = zip(*components_modules_pairs)
        analysis["correlations"]["components_vs_modules"] = calculate_correlation(components, modules)
    
    # Time to first overview (if available)
    overview_times = [r.get("first_overview_time") for r in successful if r.get("first_overview_time")]
    if overview_times:
        analysis["time_to_first_overview"] = {
            "min": min(overview_times),
            "max": max(overview_times),
            "mean": statistics.mean(overview_times),
        }
    
    # Per-repo details
    analysis["repo_details"] = []
    for repo in successful:
        detail = {
            "name": repo.get("repo_name"),
            "duration": repo.get("duration", 0),
            "files_created": repo.get("files_created", 0),
            "size_mb": repo.get("size_mb", 0),
            "code_files": repo.get("total_code_files", 0),
            "components": repo.get("component_count", 0),
            "modules": repo.get("module_count", 0),
            "stage_1_time": repo.get("stage_timings", {}).get("Dependency Analysis", 0),
            "stage_2_time": repo.get("stage_timings", {}).get("Module Clustering", 0),
        }
        analysis["repo_details"].append(detail)
    
    return analysis


def print_report(analysis: Dict[str, Any]):
    """Print a formatted analysis report."""
    print("=" * 80)
    print("CODEWIKI BENCHMARK ANALYSIS REPORT")
    print("=" * 80)
    print()
    
    print(f"Total Repositories: {analysis['total_repos']}")
    print(f"Successful: {analysis['successful']}")
    print(f"Failed: {analysis['failed']}")
    print(f"Success Rate: {analysis['success_rate']:.1f}%")
    print()
    
    if "timing" in analysis:
        print("TIMING STATISTICS")
        print("-" * 80)
        timing = analysis["timing"]
        print(f"  Min Duration:    {timing['min']:.1f}s")
        print(f"  Max Duration:    {timing['max']:.1f}s")
        print(f"  Mean Duration:   {timing['mean']:.1f}s")
        print(f"  Median Duration: {timing['median']:.1f}s")
        print(f"  Std Deviation:   {timing['stdev']:.1f}s")
        print()
    
    if "stage_1_timing" in analysis:
        print("STAGE 1 (Dependency Analysis) TIMING")
        print("-" * 80)
        s1 = analysis["stage_1_timing"]
        print(f"  Min:    {s1['min']:.2f}s")
        print(f"  Max:    {s1['max']:.2f}s")
        print(f"  Mean:   {s1['mean']:.2f}s")
        print(f"  Median: {s1['median']:.2f}s")
        print()
    
    if "stage_2_timing" in analysis:
        print("STAGE 2 (Module Clustering) TIMING")
        print("-" * 80)
        s2 = analysis["stage_2_timing"]
        print(f"  Min:    {s2['min']:.2f}s")
        print(f"  Max:    {s2['max']:.2f}s")
        print(f"  Mean:   {s2['mean']:.2f}s")
        print(f"  Median: {s2['median']:.2f}s")
        print()
    
    if "components" in analysis:
        print("COMPONENT STATISTICS")
        print("-" * 80)
        comp = analysis["components"]
        print(f"  Min:    {comp['min']}")
        print(f"  Max:    {comp['max']}")
        print(f"  Mean:   {comp['mean']:.1f}")
        print(f"  Median: {comp['median']:.1f}")
        print()
    
    if "modules" in analysis:
        print("MODULE STATISTICS")
        print("-" * 80)
        mod = analysis["modules"]
        print(f"  Min:    {mod['min']}")
        print(f"  Max:    {mod['max']}")
        print(f"  Mean:   {mod['mean']:.1f}")
        print(f"  Median: {mod['median']:.1f}")
        print()
    
    if "files" in analysis:
        print("FILE CREATION STATISTICS")
        print("-" * 80)
        files = analysis["files"]
        print(f"  Min Files:    {files['min']}")
        print(f"  Max Files:    {files['max']}")
        print(f"  Mean Files:   {files['mean']:.1f}")
        print(f"  Median Files: {files['median']:.1f}")
        print()
    
    if "correlations" in analysis:
        print("CORRELATIONS")
        print("-" * 80)
        corr = analysis["correlations"]
        if "size_vs_duration" in corr:
            print(f"  Repo Size vs Duration:        {corr['size_vs_duration']:.3f}")
        if "code_files_vs_duration" in corr:
            print(f"  Code Files vs Duration:        {corr['code_files_vs_duration']:.3f}")
        if "components_vs_duration" in corr:
            print(f"  Components vs Duration:        {corr['components_vs_duration']:.3f}")
        if "components_vs_modules" in corr:
            print(f"  Components vs Modules:         {corr['components_vs_modules']:.3f}")
        print()
    
    if "time_to_first_overview" in analysis:
        print("TIME TO FIRST OVERVIEW")
        print("-" * 80)
        overview = analysis["time_to_first_overview"]
        print(f"  Min:  {overview['min']:.1f}s")
        print(f"  Max:  {overview['max']:.1f}s")
        print(f"  Mean: {overview['mean']:.1f}s")
        print()
    
    if "repo_details" in analysis:
        print("PER-REPOSITORY DETAILS")
        print("-" * 80)
        for detail in analysis["repo_details"]:
            print(f"  {detail['name']}:")
            print(f"    Duration:     {detail['duration']:.1f}s")
            print(f"    Stage 1:      {detail.get('stage_1_time', 0):.2f}s")
            print(f"    Stage 2:      {detail.get('stage_2_time', 0):.2f}s")
            print(f"    Components:   {detail.get('components', 0)}")
            print(f"    Modules:      {detail.get('modules', 0)}")
            print(f"    Code Files:   {detail['code_files']}")
            print(f"    Size:         {detail['size_mb']:.2f} MB")
            print()
    
    print("=" * 80)


def main():
    """Main analysis function."""
    data = load_latest_results()
    analysis = analyze_results(data)
    print_report(analysis)
    
    # Save analysis
    analysis_file = OUTPUT_DIR / "analysis.json"
    with open(analysis_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    print(f"Analysis saved to: {analysis_file}")


if __name__ == "__main__":
    main()

