#!/bin/bash
# 📊 Run Navigation Experiment — 3 Trials
source /opt/ros/humble/setup.bash
source "$(dirname "$0")/install/setup.bash"

TRIALS=${1:-3}
OUTPUT="logs/experiment_$(date +%Y%m%d_%H%M%S).csv"
mkdir -p logs

echo ""
echo "📊  Navigation Experiment"
echo "═════════════════════════"
echo "  Trials: ${TRIALS}"
echo "  Output: ${OUTPUT}"
echo ""
echo "  Starting in 5 seconds..."
sleep 5

python3 src/medguide_robot/scripts/run_experiment.py \
    --trials "${TRIALS}" \
    --output "${OUTPUT}"

echo ""
echo "✅ Experiment complete! Results: ${OUTPUT}"
echo ""
echo "To analyze results:"
echo "  python3 src/medguide_robot/scripts/analyze_results.py \\"
echo "    --labels Experiment logs/${OUTPUT}"
echo ""
