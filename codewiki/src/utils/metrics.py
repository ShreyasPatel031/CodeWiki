"""
Metrics collection system for CodeWiki performance analysis.
Tracks timing, tokens, files, and time-to-first-overview.
"""
import time
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class StageMetrics:
    """Metrics for a single stage."""
    stage_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    tokens_used: int = 0
    files_created: int = 0
    files_created_list: List[str] = field(default_factory=list)
    
    def complete(self):
        """Mark stage as complete and calculate duration."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time


@dataclass
class RepoMetrics:
    """Complete metrics for a repository."""
    repo_name: str
    repo_path: str
    repo_size_mb: float = 0.0
    total_files: int = 0
    total_code_files: int = 0
    
    # Stage timings
    stages: Dict[str, StageMetrics] = field(default_factory=dict)
    
    # Critical metrics
    time_to_first_overview: Optional[float] = None
    first_overview_file: Optional[str] = None
    
    # Totals
    total_duration: Optional[float] = None
    total_tokens: int = 0
    total_files_created: int = 0
    
    # Start/end times
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    def start_stage(self, stage_name: str) -> StageMetrics:
        """Start tracking a stage."""
        stage = StageMetrics(stage_name=stage_name, start_time=time.time())
        self.stages[stage_name] = stage
        return stage
    
    def complete_stage(self, stage_name: str):
        """Complete a stage."""
        if stage_name in self.stages:
            self.stages[stage_name].complete()
    
    def record_first_overview(self, file_path: str):
        """Record when first overview is created."""
        if self.time_to_first_overview is None:
            self.time_to_first_overview = time.time() - self.start_time
            self.first_overview_file = file_path
    
    def finalize(self):
        """Finalize metrics and calculate totals."""
        self.end_time = time.time()
        self.total_duration = self.end_time - self.start_time
        
        # Sum up tokens and files from all stages
        self.total_tokens = sum(stage.tokens_used for stage in self.stages.values())
        self.total_files_created = sum(stage.files_created for stage in self.stages.values())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "repo_name": self.repo_name,
            "repo_path": self.repo_path,
            "repo_size_mb": self.repo_size_mb,
            "total_files": self.total_files,
            "total_code_files": self.total_code_files,
            "stages": {
                name: {
                    "stage_name": stage.stage_name,
                    "duration": stage.duration,
                    "tokens_used": stage.tokens_used,
                    "files_created": stage.files_created,
                    "files_created_list": stage.files_created_list
                }
                for name, stage in self.stages.items()
            },
            "time_to_first_overview": self.time_to_first_overview,
            "first_overview_file": self.first_overview_file,
            "total_duration": self.total_duration,
            "total_tokens": self.total_tokens,
            "total_files_created": self.total_files_created,
            "start_time": self.start_time,
            "end_time": self.end_time
        }
    
    def save(self, output_path: Path):
        """Save metrics to JSON file."""
        with open(output_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


class MetricsCollector:
    """Global metrics collector."""
    
    def __init__(self):
        self.current_metrics: Optional[RepoMetrics] = None
        self.all_metrics: List[RepoMetrics] = []
    
    def start_repo(self, repo_name: str, repo_path: str) -> RepoMetrics:
        """Start tracking metrics for a repository."""
        self.current_metrics = RepoMetrics(repo_name=repo_name, repo_path=repo_path)
        return self.current_metrics
    
    def get_current(self) -> Optional[RepoMetrics]:
        """Get current repository metrics."""
        return self.current_metrics
    
    def finalize_repo(self):
        """Finalize current repo metrics."""
        if self.current_metrics:
            self.current_metrics.finalize()
            self.all_metrics.append(self.current_metrics)
            self.current_metrics = None
    
    def save_all(self, output_path: Path):
        """Save all metrics to JSON file."""
        data = {
            "repos": [metrics.to_dict() for metrics in self.all_metrics],
            "summary": self._generate_summary()
        }
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics across all repos."""
        if not self.all_metrics:
            return {}
        
        return {
            "total_repos": len(self.all_metrics),
            "avg_total_duration": sum(m.total_duration or 0 for m in self.all_metrics) / len(self.all_metrics),
            "avg_time_to_first_overview": sum(m.time_to_first_overview or 0 for m in self.all_metrics) / len([m for m in self.all_metrics if m.time_to_first_overview]),
            "avg_total_tokens": sum(m.total_tokens for m in self.all_metrics) / len(self.all_metrics),
            "avg_total_files_created": sum(m.total_files_created for m in self.all_metrics) / len(self.all_metrics),
            "stage_avg_durations": self._calculate_stage_averages()
        }
    
    def _calculate_stage_averages(self) -> Dict[str, float]:
        """Calculate average duration for each stage."""
        stage_totals = {}
        stage_counts = {}
        
        for metrics in self.all_metrics:
            for stage_name, stage in metrics.stages.items():
                if stage.duration is not None:
                    stage_totals[stage_name] = stage_totals.get(stage_name, 0) + stage.duration
                    stage_counts[stage_name] = stage_counts.get(stage_name, 0) + 1
        
        return {
            stage_name: stage_totals[stage_name] / stage_counts[stage_name]
            for stage_name in stage_totals
        }


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector."""
    return _metrics_collector






