#!/bin/bash

# VokVision M1 Native Setup Script (v2.0)
# This script installs the necessary tools to run 3DGS on your Mac M1.

echo "🚀 Starting VokVision M1 Setup..."

# 1. Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo " Homebrew not found. Please install it from https://brew.sh/"
    exit 1
fi

# 2. Install Build Dependencies
echo "📦 Installing build dependencies via Homebrew..."
brew install cmake libomp ffmpeg wget opencv

# 3. Handle LibTorch (Required for OpenSplat)
echo "📥 Downloading LibTorch (Apple Silicon)..."
mkdir -p pipeline/deps
cd pipeline/deps
if [ ! -d "libtorch" ]; then
    wget https://download.pytorch.org/libtorch/cpu/libtorch-macos-arm64-2.2.2.zip -O libtorch.zip
    unzip libtorch.zip
    rm libtorch.zip
else
    echo " LibTorch already exists."
fi
LIBTORCH_PATH=$(pwd)/libtorch
cd ../..

# 4. Clone & Build OpenSplat
cd pipeline
if [ ! -d "opensplat" ]; then
    echo "📂 Cloning OpenSplat..."
    git clone https://github.com/pierotofy/OpenSplat.git opensplat
fi

echo "🛠 Building OpenSplat..."
cd opensplat
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$LIBTORCH_PATH"
make -j$(sysctl -n hw.logicalcpu)

if [ -f "opensplat" ]; then
    echo "OpenSplat build successful!"
else
    echo "OpenSplat build failed."
    exit 1
fi

# 5. Setup Python Virtual Environment (Safe for Mac)
cd ../../../backend/processor
echo "🐍 Setting up Python Virtual Environment (Venv)..."
python3 -m venv venv
source venv/bin/activate

echo "📦 Installing Python requirements inside Venv..."
./venv/bin/python3 -m pip install --upgrade pip
./venv/bin/python3 -m pip install -r requirements.txt

# 6. Setup Backend
cd ../api
echo "📦 Installing Backend dependencies..."
npm install

echo "----------------------------------------------------"
echo "🎉 Setup Finished!"
echo "----------------------------------------------------"
echo "To start the Processor, use:"
echo "cd backend/processor && ./venv/bin/python3 main.py"
echo "----------------------------------------------------"
