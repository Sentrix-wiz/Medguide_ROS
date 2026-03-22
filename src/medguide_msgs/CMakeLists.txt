cmake_minimum_required(VERSION 3.8)
project(medguide_msgs)

find_package(ament_cmake REQUIRED)
find_package(std_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/MissionStatus.msg"
  "msg/GoalResult.msg"
  "msg/SystemState.msg"
  "srv/SetMode.srv"
  "srv/RunExperiment.srv"
  DEPENDENCIES std_msgs
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
