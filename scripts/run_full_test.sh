#!/bin/bash
# Full end-to-end test script for LLM Review Tool

echo "============================================"
echo "LLM Review Tool - Full End-to-End Test"
echo "============================================"
echo ""

# Check if GEMINI_API_KEY is set
if [ -z "$GEMINI_API_KEY" ]; then
    echo "❌ Error: GEMINI_API_KEY environment variable not set!"
    echo "Please set your API key:"
    echo "  export GEMINI_API_KEY='your-api-key-here'"
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: Virtual environment not activated"
    echo "Activating virtual environment..."
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        echo "Creating virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        echo "Installing dependencies..."
        pip install -e .
    fi
fi

echo "✅ Environment ready"
echo ""

# Run the demo
echo "📝 Step 1: Running demo scenarios..."
echo "This will create test repositories and run the tool on various code issues"
echo ""
python demo.py

# Check if demo succeeded
if [ $? -ne 0 ]; then
    echo "❌ Demo failed to run"
    exit 1
fi

echo ""
echo "📊 Step 2: Analyzing results..."
echo "This will validate that the tool correctly identified expected issues"
echo ""
python analyze_demo_results.py

# Show results location
echo ""
echo "============================================"
echo "Test Complete!"
echo "============================================"
echo ""
echo "📁 Results saved in: demo_results/"
echo ""
echo "To view detailed results:"
echo "  1. cd demo_results/[latest_timestamp]"
echo "  2. cat validation_report.md"
echo "  3. Review individual scenario_*.md files"
echo ""
echo "The validation report shows:"
echo "  - Which issues were correctly identified"
echo "  - Navigation efficiency metrics"
echo "  - Overall success rate"
echo ""