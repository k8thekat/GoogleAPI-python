#!/bin/bash
# - Verify you are in `VENV`
which python3
read -p "Are we in our VENV? (y/n): " confirm
echo "Checking __init__.py"
cat ./gap/__init__.py | grep -e __version__ -e version_info
if [ "$confirm" = "y" ]; then
    # Generate a build based upon our pypyoject.toml
    # rm -r ./dist
    python -m build
    read -p "Set Version (vX.X.X): " version
    echo "Results:" $version
    read -p "Set Tag Notes: " notes
    echo "Results:" $notes
    git tag -a $version -m "$notes"
    git push --follow-tags
else
    echo "Aborting..."
fi