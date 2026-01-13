#!/usr/bin/env python3
"""
Benchmark script for CodeWiki documentation generation.
Measures: time per stage, tokens used, cost estimate, module depth.
"""

import subprocess
import json
import time
import os
import sys
from pathlib import Path
from datetime import datetime

# Get script directory and project root
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Fix SSL certificate issue for Python 3.14
# Set SSL_CERT_FILE to certifi's certificate bundle
try:
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
except ImportError:
    pass  # certifi not available, continue without it

# Token pricing (approximate, per 1M tokens)
PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},  # $/1M tokens
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash": {"input": 0.075, "output": 0.30},  # Same pricing as 1.5 Flash
    "default": {"input": 1.00, "output": 4.00}  # Conservative estimate
}

# Repos to benchmark - will clone if not present
# Using a mix of sizes for scaling analysis
GITHUB_REPOS = [
    ("tiangolo/fastapi", "fastapi"),                       # Python web framework
    ("pallets/flask", "flask"),                            # Python web framework
    ("vercel/next.js", "nextjs"),                          # React framework (TypeScript)
    ("facebook/react", "react"),                           # React library (JavaScript/TypeScript)
    ("golang/go", "go"),                                   # Go language (Go)
    ("rust-lang/rust", "rust"),                            # Rust language (Rust)
    ("microsoft/vscode", "vscode"),                        # VS Code editor (TypeScript)
    ("kubernetes/kubernetes", "kubernetes"),               # Kubernetes (Go)
    ("tensorflow/tensorflow", "tensorflow"),              # TensorFlow (Python/C++)
    ("pytorch/pytorch", "pytorch"),                        # PyTorch (Python/C++)
]

TEST_REPOS_DIR = PROJECT_ROOT / "test_repos"


def count_code_files(repo_path: str) -> int:
    """Count code files in a repository."""
    extensions = {'.py', '.ts', '.tsx', '.js', '.jsx', '.cs', '.java', '.go', '.rs', '.rb', '.php'}
    count = 0
    for root, dirs, files in os.walk(repo_path):
        # Skip common non-source directories
        dirs[:] = [d for d in dirs if d not in {'node_modules', '.git', '__pycache__', 'venv', 'dist', 'build'}]
        for f in files:
            if any(f.endswith(ext) for ext in extensions):
                count += 1
    return count


def get_repo_size_mb(repo_path: str) -> float:
    """Get repository size in MB."""
    total_size = 0
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in {'node_modules', '.git', '__pycache__', 'venv', 'dist', 'build'}]
        for f in files:
            fp = os.path.join(root, f)
            try:
                total_size += os.path.getsize(fp)
            except:
                pass
    return total_size / (1024 * 1024)


def get_module_depth(module_tree: dict, current_depth: int = 0) -> int:
    """Calculate maximum depth of module tree."""
    if not module_tree:
        return current_depth
    
    max_depth = current_depth
    for module_name, module_info in module_tree.items():
        if isinstance(module_info, dict) and "children" in module_info:
            child_depth = get_module_depth(module_info["children"], current_depth + 1)
            max_depth = max(max_depth, child_depth)
    
    return max_depth


def estimate_cost(tokens_used: int, model: str = "default") -> float:
    """Estimate cost based on tokens used."""
    pricing = PRICING.get(model, PRICING["default"])
    # Assume 80% input, 20% output ratio
    input_tokens = tokens_used * 0.8
    output_tokens = tokens_used * 0.2
    cost = (input_tokens / 1_000_000) * pricing["input"] + (output_tokens / 1_000_000) * pricing["output"]
    return cost


def run_codewiki(repo_path: str, output_dir: str) -> dict:
    """Run codewiki generate and capture metrics."""
    repo_name = os.path.basename(repo_path)
    
    # Clean up previous docs
    docs_path = Path(output_dir)
    if docs_path.exists():
        import shutil
        shutil.rmtree(docs_path)
    
    start_time = time.time()
    
    # Run codewiki generate
    # Note: codewiki generate should be run from repo directory or with proper args
    cmd = [
        "python3.12", "-m", "codewiki", "generate",
        "-o", output_dir,
        "--github-pages",
        "-v"  # Verbose for stage timings
    ]
    
    print(f"\n{'='*60}")
    print(f"Running: {repo_name}")
    print(f"Command: cd {repo_path} && {' '.join(cmd)}")
    print(f"{'='*60}")
    
    # Pass environment with SSL cert fix
    env = os.environ.copy()
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=1800,  # 30 minute timeout for large repos
        cwd=repo_path,  # Run from repo directory
        env=env  # Pass environment with SSL_CERT_FILE
    )
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Parse output for stage timings
    stage_timings = {}
    tokens_used = 0
    
    # Look for stage timing patterns in output
    combined_output = result.stdout + result.stderr
    
    # Extract stage timings from output
    import re
    
    # Pattern: [STAGE X] ... COMPLETE in Xs
    stage_patterns = [
        (r'\[STAGE 1.*?COMPLETE in ([\d.]+)s', 'Dependency Analysis'),
        (r'\[STAGE 2.*?COMPLETE in ([\d.]+)s', 'Module Clustering'),
        (r'\[STAGE 3.*?complete.*?([\d.]+)s', 'Documentation Generation'),
        (r'\[STAGE 4.*?complete.*?([\d.]+)s', 'Agent Processing'),
        (r'\[STAGE 5.*?COMPLETE in ([\d.]+)s', 'HTML Generation'),
    ]
    
    for pattern, stage_name in stage_patterns:
        match = re.search(pattern, combined_output, re.IGNORECASE)
        if match:
            stage_timings[stage_name] = float(match.group(1))
    
    # Extract token counts and actual cost from TokenTracker
    token_matches = re.findall(r'(\d+)\s*tokens?', combined_output)
    if token_matches:
        tokens_used = sum(int(t) for t in token_matches if int(t) < 1000000)  # Filter out unreasonable values
    
    # Extract actual cost from TokenTracker logs (more accurate than estimation)
    cost_match = re.search(r'Running total:\s*\$([\d.]+)', combined_output)
    actual_cost = 0.0
    if cost_match:
        actual_cost = float(cost_match.group(1))
    
    # Load metrics from generated files if available
    metrics_path = docs_path / "metrics.json"
    module_tree_path = docs_path / "module_tree.json"
    
    module_count = 0
    module_depth = 0
    
    if module_tree_path.exists():
        try:
            with open(module_tree_path) as f:
                module_tree = json.load(f)
                module_count = len(module_tree)
                module_depth = get_module_depth(module_tree)
        except:
            pass
    
    # Check for index.html
    html_exists = (docs_path / "index.html").exists()
    html_size = 0
    if html_exists:
        html_size = (docs_path / "index.html").stat().st_size
    
    # Count md files
    md_files = list(docs_path.glob("*.md"))
    
    return {
        "repo_name": repo_name,
        "repo_path": repo_path,
        "success": result.returncode == 0,
        "return_code": result.returncode,
        "duration_seconds": round(duration, 2),
        "stage_timings": stage_timings,
        "tokens_used": tokens_used,
        "cost_usd": round(actual_cost, 4) if actual_cost > 0 else round(estimate_cost(tokens_used), 4),
        "code_files": count_code_files(repo_path),
        "repo_size_mb": round(get_repo_size_mb(repo_path), 2),
        "module_count": module_count,
        "module_depth": module_depth,
        "md_files_generated": len(md_files),
        "html_generated": html_exists,
        "html_size_kb": round(html_size / 1024, 2) if html_exists else 0,
        "stdout_excerpt": result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout,
        "stderr_excerpt": result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr,
    }


def clone_repo(github_repo: str, local_name: str) -> str:
    """Clone a GitHub repo if not already present."""
    local_path = TEST_REPOS_DIR / local_name
    
    if local_path.exists():
        print(f"✓ {local_name} already exists")
        return str(local_path)
    
    print(f"📥 Cloning {github_repo}...")
    TEST_REPOS_DIR.mkdir(parents=True, exist_ok=True)
    
    result = subprocess.run(
        ["git", "clone", "--depth", "1", f"https://github.com/{github_repo}.git", str(local_path)],
        capture_output=True,
        text=True,
        timeout=300
    )
    
    if result.returncode == 0:
        print(f"✓ Cloned {local_name}")
    else:
        print(f"❌ Failed to clone {github_repo}: {result.stderr}")
        return None
    
    return str(local_path)


def main():
    print("=" * 60)
    print("CodeWiki Benchmark Suite")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Prepare repos
    repo_paths = []
    for github_repo, local_name in GITHUB_REPOS:
        path = clone_repo(github_repo, local_name)
        if path:
            repo_paths.append(path)
    
    results = []
    
    for repo_path in repo_paths:
        if not os.path.exists(repo_path):
            print(f"⚠️ Skipping {repo_path} - not found")
            continue
        
        output_dir = os.path.join(repo_path, "docs")
        
        try:
            result = run_codewiki(repo_path, output_dir)
            results.append(result)
            
            # Print summary
            print(f"\n📊 {result['repo_name']}:")
            print(f"   ✓ Duration: {result['duration_seconds']}s")
            print(f"   ✓ Tokens: {result['tokens_used']}")
            print(f"   ✓ Cost: ${result['cost_usd']}")
            print(f"   ✓ Modules: {result['module_count']} (depth: {result['module_depth']})")
            print(f"   ✓ MD Files: {result['md_files_generated']}")
            print(f"   ✓ HTML: {'✅' if result['html_generated'] else '❌'} ({result['html_size_kb']}KB)")
            print(f"   ✓ Status: {'✅ Success' if result['success'] else '❌ Failed'}")
            
        except subprocess.TimeoutExpired:
            print(f"❌ {os.path.basename(repo_path)}: Timeout after 1800s")
            results.append({
                "repo_name": os.path.basename(repo_path),
                "repo_path": repo_path,
                "success": False,
                "error": "Timeout after 1800s"
            })
        except Exception as e:
            print(f"❌ {os.path.basename(repo_path)}: Error - {e}")
            results.append({
                "repo_name": os.path.basename(repo_path),
                "repo_path": repo_path,
                "success": False,
                "error": str(e)
            })
    
    # Generate summary
    successful = [r for r in results if r.get('success', False)]
    failed = [r for r in results if not r.get('success', False)]
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_repos": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "total_duration_seconds": sum(r.get('duration_seconds', 0) for r in results),
        "total_tokens": sum(r.get('tokens_used', 0) for r in results),
        "total_cost_usd": sum(r.get('cost_usd', 0) for r in results),
        "avg_duration_per_repo": round(sum(r.get('duration_seconds', 0) for r in successful) / len(successful), 2) if successful else 0,
        "avg_cost_per_repo": round(sum(r.get('cost_usd', 0) for r in successful) / len(successful), 4) if successful else 0,
        "results": results
    }
    
    # Save results
    output_path = PROJECT_ROOT / "benchmark_results" / f"benchmark_{int(time.time())}.json"
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"Total repos: {summary['total_repos']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"Total duration: {summary['total_duration_seconds']}s")
    print(f"Total tokens: {summary['total_tokens']}")
    print(f"Total cost: ${summary['total_cost_usd']:.4f}")
    print(f"Avg duration/repo: {summary['avg_duration_per_repo']}s")
    print(f"Avg cost/repo: ${summary['avg_cost_per_repo']:.4f}")
    print(f"\nResults saved to: {output_path}")
    
    # Print prediction model
    if successful:
        print("\n" + "=" * 60)
        print("COST/TIME PREDICTION MODEL")
        print("=" * 60)
        
        # Calculate averages per code file and per module
        total_code_files = sum(r.get('code_files', 0) for r in successful)
        total_duration = sum(r.get('duration_seconds', 0) for r in successful)
        total_cost = sum(r.get('cost_usd', 0) for r in successful)
        
        if total_code_files > 0:
            print(f"Time per code file: {total_duration / total_code_files:.3f}s")
            print(f"Cost per code file: ${total_cost / total_code_files:.6f}")
            print("\nTo estimate for a new repo:")
            print(f"  Time ≈ (code_files) × {total_duration / total_code_files:.3f}s")
            print(f"  Cost ≈ (code_files) × ${total_cost / total_code_files:.6f}")


if __name__ == "__main__":
    main()

