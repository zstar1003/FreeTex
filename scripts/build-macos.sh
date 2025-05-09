#!/bin/bash

# Clean up any previous builds.
rm -rf build dist

# Compile the resources.
[ ! -f "resources/app_rc.py" ] && uv run pyrcc5 resources/app.qrc -o resources/app_rc.py -compress 3

# Create the app bundle.
uv run pyinstaller main.spec

# Create a folder (named dmg) to prepare our DMG in (if it doesn't already exist).
mkdir -p dist/dmg

# Empty the dmg folder.
rm -rf dist/dmg/*

# Copy the app bundle to the dmg folder.
cp -a "dist/FreeTeX.app" dist/dmg

# If the DMG already exists, delete it.
test -f "dist/FreeTeX.dmg" && rm "dist/FreeTeX.dmg"
create-dmg \
    --volname "FreeTeX" \
    --volicon "images/icon.icns" \
    --window-pos 200 120 \
    --window-size 600 300 \
    --icon-size 100 \
    --icon "FreeTeX.app" 175 120 \
    --hide-extension "FreeTeX.app" \
    --app-drop-link 425 120 \
    "dist/FreeTeX.dmg" \
    "dist/dmg/"
