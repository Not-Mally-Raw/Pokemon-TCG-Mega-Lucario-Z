#!/bin/bash
# Builds the Kaggle submission tar.gz with required root members (main.py, deck.csv, cg/)

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$DIR")"

cd "$PROJECT_ROOT"

# Ensure required submission targets exist
for req in "main.py" "deck.csv" "cg"; do
    if [ ! -e "$req" ]; then
        echo "Error: Required submission target '$req' not found!"
        exit 1
    fi
done

echo "Creating submission.tar.gz..."
tar -czvf submission.tar.gz \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.DS_Store' \
    main.py deck.csv cg/

SIZE_BYTES=$(wc -c < submission.tar.gz | tr -d ' ')
SIZE_MB=$(awk "BEGIN {printf \"%.2f\", $SIZE_BYTES / 1048576}")

echo "Packaging complete! Size: $SIZE_MB MiB ($SIZE_BYTES bytes)"
if [ $SIZE_BYTES -gt 207303475 ]; then
    echo "ERROR: submission.tar.gz exceeds 197.7 MiB limit!"
    exit 1
fi

echo "Done! submission.tar.gz is ready for upload to Kaggle."
