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
find_package(Python3 COMPONENTS Interpreter QUIET)
if(Python3_Interpreter_FOUND)
  add_test(
    NAME 125A_source_baseline_contract
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/source_contracts.py" "${CMAKE_CURRENT_SOURCE_DIR}"
  )
endif()

# VST3 implementation deliberately not registered yet. No functional VST3
# is claimed until the audited engine adapter and real host lifecycle exist.
