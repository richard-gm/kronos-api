#!/bin/bash
# Download Kronos model and tokenizer files from HuggingFace
# Run this once before first start, or to update models

set -e

echo "Downloading Kronos models to ./models/"

mkdir -p models/tokenizer models/kronos-mini models/kronos-small models/kronos-base

echo "Downloading tokenizer..."
cd models/tokenizer
for f in .gitattributes README.md config.json model.safetensors; do
    echo "  $f"
    curl -k -L "https://huggingface.co/NeoQuasar/Kronos-Tokenizer-base/resolve/main/$f" -o "$f" --silent
done

echo "Downloading kronos-mini (4M params, fastest)..."
cd ../kronos-mini
for f in .gitattributes README.md config.json model.safetensors; do
    echo "  $f"
    curl -k -L "https://huggingface.co/NeoQuasar/Kronos-mini/resolve/main/$f" -o "$f" --silent
done

echo "Downloading kronos-small (25M params, recommended)..."
cd ../kronos-small
for f in .gitattributes README.md config.json model.safetensors; do
    echo "  $f"
    curl -k -L "https://huggingface.co/NeoQuasar/Kronos-small/resolve/main/$f" -o "$f" --silent
done

echo "Downloading kronos-base (102M params, best accuracy)..."
cd ../kronos-base
for f in .gitattributes README.md config.json model.safetensors; do
    echo "  $f"
    curl -k -L "https://huggingface.co/NeoQuasar/Kronos-base/resolve/main/$f" -o "$f" --silent
done

cd ../..
echo ""
echo "Done! Models downloaded:"
du -sh models/*/
echo ""
echo "To use a specific model, set KRONOS_MODEL in .env:"
echo "  KRONOS_MODEL=/models/kronos-small"
echo "  KRONOS_MODEL=/models/kronos-base"