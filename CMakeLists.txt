cmake_minimum_required(VERSION 3.26)
project(125A_AWE_Synthesizer VERSION 0.1.0 LANGUAGES C CXX)

# New 125A code targets C++23. The upstream source is kept at its original
# language level to enable faithful baseline comparisons.
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(125A_BUILD_UPSTREAM_CLI "Build pinned upstream console reference (not the VST3)" OFF)

if(125A_BUILD_UPSTREAM_CLI)
  # Auditing the native chip/driver code should not silently download RtAudio.
  set(AWE32EMU_WITH_RTAUDIO OFF CACHE BOOL "Disable upstream RtAudio in baseline" FORCE)
  set(AWE32EMU_NLS OFF CACHE BOOL "Disable optional gettext in baseline" FORCE)
  add_subdirectory(upstream/AWE32Emu)
endif()

enable_testing()

option(125A_BUILD_ENGINE_PROBES "Build the patched EMU8000 safety harness" ON)
if(125A_BUILD_ENGINE_PROBES)
  add_subdirectory(src/engine)
endif()
find_package(Python3 COMPONENTS Interpreter QUIET)
if(Python3_Interpreter_FOUND)
  add_test(
    NAME 125A_source_baseline_contract
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/source_contracts.py" "${CMAKE_CURRENT_SOURCE_DIR}"
  )
  add_test(
    NAME 125A_p14_vstgui_contract
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/p14_vstgui_contract.py" "${CMAKE_CURRENT_SOURCE_DIR}"
  )
endif()

# VST3 implementation deliberately not registered yet. No functional VST3
# is claimed until the audited engine adapter and real host lifecycle exist.

# SDK-independent project state/asset config regression.
add_executable(awe32_asset_state_test tests/asset_state.cpp)
target_include_directories(awe32_asset_state_test PRIVATE src/vst3)
target_compile_features(awe32_asset_state_test PRIVATE cxx_std_23)
add_test(NAME 125A_asset_state COMMAND awe32_asset_state_test)

option(125A_BUILD_VST3 "Build experimental Windows VST3" OFF)
if(125A_BUILD_VST3)
  if(NOT WIN32)
    message(FATAL_ERROR "125A VST3 is Windows-only")
  endif()
  set(SMTG_ENABLE_VST3_PLUGIN_EXAMPLES OFF CACHE BOOL "" FORCE)
  set(SMTG_ENABLE_VST3_HOSTING_EXAMPLES OFF CACHE BOOL "" FORCE)
  set(SMTG_ENABLE_VSTGUI_SUPPORT ON CACHE BOOL "VSTGUI P14 editor" FORCE)
  set(SMTG_CREATE_PLUGIN_LINK OFF CACHE BOOL "" FORCE)
  add_subdirectory(external/vst3sdk)
  add_subdirectory(src/vst3)
endif()

# Independent YMF262/OPL3 chip accuracy module. Register test only;
# no user-visible FM VST3 mode or MIDI patch translator is claimed yet.
option(125A_BUILD_OPL3_PROBES "Build isolated register-level OPL3 core tests" ON)
if(125A_BUILD_OPL3_PROBES)
  add_subdirectory(src/opl3)
endif()
