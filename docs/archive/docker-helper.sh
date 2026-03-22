#!/bin/bash
# Docker convenience script for MedGuide

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="medguide-ros:humble-latest"
CONTAINER_NAME="medguide-robot"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function print_usage() {
    echo "MedGuide Docker Helper"
    echo ""
    echo "Usage: ./docker-helper.sh <command>"
    echo ""
    echo "Commands:"
    echo "  build                 Build Docker image"
    echo "  run                   Run MedGuide in Docker"
    echo "  shell                 Start interactive shell"
    echo "  launch                Launch unified MedGuide system"
    echo "  test                  Run mission test script"
    echo "  monitor-mission       Monitor mission status"
    echo "  monitor-obstacles     Monitor emergency stop"
    echo "  stop                  Stop running container"
    echo "  clean                 Remove image and containers"
    echo ""
}

function build_image() {
    echo -e "${GREEN}Building Docker image...${NC}"
    docker build -t $IMAGE_NAME .
    echo -e "${GREEN}✓ Image built successfully${NC}"
}

function run_container() {
    echo -e "${GREEN}Starting MedGuide container...${NC}"
    
    # Check if display is available (for GUI)
    if [ -z "$DISPLAY" ]; then
        echo -e "${YELLOW}⚠ DISPLAY not set. Running without GUI support.${NC}"
        docker run -it --rm --name $CONTAINER_NAME \
            --network host \
            $IMAGE_NAME \
            bash
    else
        docker run -it --rm --name $CONTAINER_NAME \
            --network host \
            -e DISPLAY=$DISPLAY \
            -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
            -v ${XAUTHORITY}:/root/.Xauthority:rw \
            -v /dev/dri:/dev/dri \
            -v "$SCRIPT_DIR"/src:/home/ros/medguide_ws/src \
            -v "$SCRIPT_DIR"/config:/home/ros/medguide_ws/config \
            -v "$SCRIPT_DIR"/launch:/home/ros/medguide_ws/launch \
            -v "$SCRIPT_DIR"/worlds:/home/ros/medguide_ws/worlds \
            $IMAGE_NAME \
            bash
    fi
}

function launch_system() {
    echo -e "${GREEN}Launching unified MedGuide system...${NC}"
    
    docker run -it --rm --name $CONTAINER_NAME \
        --network host \
        -e DISPLAY=$DISPLAY \
        -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
        -v ${XAUTHORITY}:/root/.Xauthority:rw \
        -v /dev/dri:/dev/dri \
        -v "$SCRIPT_DIR"/src:/home/ros/medguide_ws/src \
        -v "$SCRIPT_DIR"/config:/home/ros/medguide_ws/config \
        -v "$SCRIPT_DIR"/launch:/home/ros/medguide_ws/launch \
        -v "$SCRIPT_DIR"/worlds:/home/ros/medguide_ws/worlds \
        $IMAGE_NAME \
        bash -c "source /home/ros/medguide_ws/install/setup.bash && \
                 ros2 launch medguide_bringup unified.launch.py"
}

function run_test() {
    echo -e "${GREEN}Running mission test...${NC}"
    
    docker run -it --rm --name $CONTAINER_NAME \
        --network host \
        -v "$SCRIPT_DIR"/scripts:/home/ros/medguide_ws/scripts \
        $IMAGE_NAME \
        bash -c "source /home/ros/medguide_ws/install/setup.bash && \
                 python3 /home/ros/medguide_ws/scripts/test_mission.py"
}

function stop_container() {
    echo -e "${YELLOW}Stopping container...${NC}"
    docker stop $CONTAINER_NAME 2>/dev/null || echo "No running container found"
}

function clean_all() {
    echo -e "${RED}Cleaning up Docker resources...${NC}"
    stop_container
    docker rmi $IMAGE_NAME 2>/dev/null || echo "Image not found"
    echo -e "${GREEN}✓ Cleanup complete${NC}"
}

# Main command dispatch
case "$1" in
    build)
        build_image
        ;;
    run)
        run_container
        ;;
    shell)
        run_container
        ;;
    launch)
        launch_system
        ;;
    test)
        run_test
        ;;
    monitor-mission)
        docker run -it --rm --network host $IMAGE_NAME \
            bash -c "source /home/ros/medguide_ws/install/setup.bash && \
                     python3 /home/ros/medguide_ws/scripts/monitor_mission.py"
        ;;
    monitor-obstacles)
        docker run -it --rm --network host $IMAGE_NAME \
            bash -c "source /home/ros/medguide_ws/install/setup.bash && \
                     python3 /home/ros/medguide_ws/scripts/monitor_emergency_stop.py"
        ;;
    stop)
        stop_container
        ;;
    clean)
        clean_all
        ;;
    *)
        print_usage
        exit 1
        ;;
esac
