# Codebase Cleanup Guide

This guide outlines the steps to clean up the codebase and standardize on the synced workflow implementation, which provides the most advanced functionality with synchronized variable handling.

## Step 1: Engine Consolidation

The codebase has evolved through several iterations of the workflow engine:

1. `engine.py` - Original engine implementation
2. `fixed_engine.py` - Enhanced engine with parallel path support
3. `synced_engine.py` - Latest engine with variable synchronization

**Action:** Use `synced_engine.py` as the standard implementation and rename or keep as reference:

```bash
# Option 1: Rename synced_engine.py to engine.py (backup original first)
mv engine.py engine.py.backup
cp synced_engine.py engine.py

# Option 2: Keep synced_engine.py as the main implementation and update imports
# This requires updating import statements in app files to reference synced_engine
```

## Step 2: Application Consolidation

Similar to the engine, there are multiple app implementations:

1. `app.py` - Original app
2. `app_fixed.py` - App using the fixed engine
3. `app_synced.py` - Latest app using the synced engine

**Action:** Use `app_synced.py` as the standard implementation:

```bash
# Option 1: Rename app_synced.py to app.py (backup original first)
mv app.py app.py.backup
cp app_synced.py app.py

# Option 2: Keep app_synced.py as the main implementation
```

## Step 3: Setup Script Consolidation

The setup scripts have also evolved:

1. `setup_fixed_implementation.sh`
2. `setup_synced_implementation.sh`

**Action:** Use `setup_synced_implementation.sh` as the standard implementation:

```bash
# Rename setup_synced_implementation.sh to setup.sh
cp setup_synced_implementation.sh setup.sh
chmod +x setup.sh
```

## Step 4: Documentation Cleanup

Multiple README files and documentation:

1. `readme.md` - Original documentation
2. `FIXED_IMPLEMENTATION_README.md`
3. `SYNCED_IMPLEMENTATION_README.md`
4. `VARIABLE_HANDLING_FIX.md`

The consolidated README.md has been created that incorporates all the latest information.

## Step 5: Testing Files Organization

The repository contains multiple testing and debug scripts. Consider organizing them into a dedicated folder:

```bash
# Create a tests folder if it doesn't exist
mkdir -p tests

# Move testing files
mv test_*.py tests/
mv debug_*.py tests/
```

## Step 6: Optional Cleanup of Obsolete Files

Once you've verified everything works with the consolidated implementation, you may choose to archive or remove obsolete files:

Files that can potentially be archived (after thorough testing):
- `engine.py.backup` (original engine)
- `fixed_engine.py` (intermediate engine)
- `app.py.backup` (original app)
- `app_fixed.py` (intermediate app)
- `setup_fixed_implementation.sh` (intermediate setup)
- `FIXED_IMPLEMENTATION_README.md` (documentation superseded by README.md)
- `SYNCED_IMPLEMENTATION_README.md` (documentation superseded by README.md)
- `VARIABLE_HANDLING_FIX.md` (documentation superseded by README.md)

## Step 7: Update Imports in Custom Scripts

If you have any custom scripts that import from the engine or app files, update the imports to reference the new consolidated files.

## Step 8: Update Requirements

The requirements.txt file has been updated to include all necessary dependencies for the synced workflow implementation.

## Step 9: Testing

After completing these cleanup steps, thoroughly test the application to ensure everything works as expected:

```bash
# Run the setup script
./setup.sh

# Test the application endpoints and functionality
``` 