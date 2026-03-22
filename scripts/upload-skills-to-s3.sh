#!/bin/bash

# Upload skills to S3/MinIO
# Usage: ./upload-skills-to-s3.sh [bucket-name] [--minio]
#
# Examples:
#   ./upload-skills-to-s3.sh synkora-skills           # AWS S3
#   ./upload-skills-to-s3.sh synkora-skills --minio   # Local MinIO
#
# For MinIO, set these environment variables:
#   export AWS_ACCESS_KEY_ID=minioadmin
#   export AWS_SECRET_ACCESS_KEY=minioadmin
#   export AWS_ENDPOINT_URL=http://localhost:9000

BUCKET_NAME=${1:-"synkora-skills"}
USE_MINIO=false

# Check for --minio flag
if [ "$2" = "--minio" ]; then
    USE_MINIO=true
fi

SKILLS_DIR="web/lib/data/claude-skills"
S3_PREFIX="skills"

if [ ! -d "$SKILLS_DIR" ]; then
    echo "Error: Skills directory not found at $SKILLS_DIR"
    echo "Run this script from the project root directory"
    exit 1
fi

# Set endpoint for MinIO
ENDPOINT_ARGS=""
if [ "$USE_MINIO" = true ]; then
    ENDPOINT_URL=${AWS_ENDPOINT_URL:-"http://localhost:9000"}
    ENDPOINT_ARGS="--endpoint-url $ENDPOINT_URL"
    echo "Using MinIO endpoint: $ENDPOINT_URL"
fi

echo "Uploading skills to s3://$BUCKET_NAME/$S3_PREFIX/"
echo "================================================"

# Create bucket if it doesn't exist (for MinIO)
if [ "$USE_MINIO" = true ]; then
    echo "Creating bucket if not exists..."
    aws s3 mb "s3://$BUCKET_NAME" $ENDPOINT_ARGS 2>/dev/null || true
fi

# Find all SKILL.md files and upload them
find "$SKILLS_DIR" -name "SKILL.md" | while read filepath; do
    # Get relative path from claude-skills directory
    rel_path=${filepath#$SKILLS_DIR/}

    # Get category and skill name from path
    # e.g., engineering-team/aws-solution-architect/SKILL.md
    category=$(dirname $(dirname "$rel_path"))
    skill_name=$(basename $(dirname "$rel_path"))

    # Handle nested structures (e.g., project-management/packaged-skills/skill-name)
    if [ "$category" = "." ]; then
        category=$(dirname "$rel_path" | cut -d'/' -f1)
    fi

    s3_key="$S3_PREFIX/$category/$skill_name/SKILL.md"

    echo "Uploading: $skill_name -> s3://$BUCKET_NAME/$s3_key"

    aws s3 cp "$filepath" "s3://$BUCKET_NAME/$s3_key" \
        --content-type "text/markdown" \
        --cache-control "max-age=3600" \
        $ENDPOINT_ARGS
done

echo ""
echo "Done! Skills uploaded to s3://$BUCKET_NAME/$S3_PREFIX/"
echo ""
if [ "$USE_MINIO" = true ]; then
    echo "Add to your backend .env:"
    echo "SKILLS_S3_BUCKET=$BUCKET_NAME"
else
    echo "Add to your backend .env:"
    echo "SKILLS_S3_BUCKET=$BUCKET_NAME"
fi
