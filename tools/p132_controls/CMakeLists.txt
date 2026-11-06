cmake_minimum_required(VERSION 3.24)
project(P132RecallControls LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 23)
set(SMTG_ENABLE_VSTGUI_SUPPORT OFF CACHE BOOL "" FORCE)
set(SMTG_ENABLE_VST3_PLUGIN_EXAMPLES OFF CACHE BOOL "" FORCE)
set(SMTG_ENABLE_VST3_HOSTING_EXAMPLES OFF CACHE BOOL "" FORCE)
get_filename_component(awe_root "../.." ABSOLUTE BASE_DIR "${CMAKE_CURRENT_LIST_DIR}")
set(sdk_root "${awe_root}/external/vst3sdk")
add_subdirectory("${sdk_root}" sdk)
add_executable(p132_controls controls.cpp
  "${sdk_root}/public.sdk/source/common/memorystream.cpp"
  "${sdk_root}/public.sdk/source/vst/hosting/parameterchanges.cpp"
  "${sdk_root}/public.sdk/source/vst/hosting/eventlist.cpp")
target_include_directories(p132_controls PRIVATE "${sdk_root}" "${awe_root}/src/vst3" "${awe_root}/tests/p132")
target_link_libraries(p132_controls PRIVATE sdk winmm)
