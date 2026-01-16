#!/bin/bash
# Script to run CodeWiki generation for 5 repos using gemini-3-flash-preview

set -e

# Source .env if it exists
if [ -f ".env" ]; then
    source .env
fi

REPOS=(
    "https://github.com/truefoundry/KubeElasti"
    "https://github.com/pallets/flask"
    "https://github.com/tiangolo/fastapi"
    "https://github.com/vercel/next.js"
    "https://github.com/golang/go"
)

WORK_DIR="/Users/shreyaspatel/CodeWiki/test_repos"
OUTPUT_BASE="/Users/shreyaspatel/CodeWiki/test_repos"

# Ensure work directory exists
mkdir -p "$WORK_DIR"

# Configure CodeWiki to use gemini-3-flash-preview
echo "Configuring CodeWiki to use gemini-3-flash-preview..."

# Check for API key
if [ -z "$GEMINI_API_KEY" ]; then
    echo "Error: GEMINI_API_KEY not set in environment"
    echo "Please set it with: export GEMINI_API_KEY=your_key"
    exit 1
fi

# Set the model configuration (base-url not needed for Gemini)
codewiki config set --main-model "gemini-3-flash-preview" --cluster-model "gemini-3-flash-preview" || {
    echo "Setting full config with API key..."
    codewiki config set --api-key "$GEMINI_API_KEY" --main-model "gemini-3-flash-preview" --cluster-model "gemini-3-flash-preview"
}

# Process each repo
for repo_url in "${REPOS[@]}"; do
    repo_name=$(basename "$repo_url" .git)
    repo_dir="$WORK_DIR/$repo_name"
    
    echo ""
    echo "=========================================="
    echo "Processing: $repo_name"
    echo "=========================================="
    
    # Clone or update repo
    if [ -d "$repo_dir" ]; then
        echo "Repository exists, updating..."
        cd "$repo_dir"
        git fetch --all
        git reset --hard origin/main || git reset --hard origin/master
    else
        echo "Cloning repository..."
        git clone "$repo_url" "$repo_dir"
        cd "$repo_dir"
    fi
    
    # Remove existing docs to avoid confirmation prompt
    if [ -d "$OUTPUT_BASE/$repo_name/docs" ]; then
        echo "Removing existing documentation..."
        rm -rf "$OUTPUT_BASE/$repo_name/docs"
    fi
    
    # Run CodeWiki generation
    echo "Running CodeWiki generation..."
    codewiki generate --output "$OUTPUT_BASE/$repo_name/docs" --verbose --no-cache || {
        echo "Warning: Generation failed for $repo_name, continuing..."
    }
    
    echo "Completed: $repo_name"
    echo ""
done

echo "=========================================="
echo "All repositories processed!"
echo "=========================================="

