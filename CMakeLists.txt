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

# Windows VST3 P14 development editor uses VSTGUI; host acceptance is separate
# from compilation and native engine tests.

# SDK-independent project state/asset config regression.
add_executable(awe32_asset_state_test tests/asset_state.cpp)
target_include_directories(awe32_asset_state_test PRIVATE src/vst3)
target_compile_features(awe32_asset_state_test PRIVATE cxx_std_23)
add_test(NAME 125A_asset_state COMMAND awe32_asset_state_test)

# P116 SDK-independent master-volume smoothing and mute behavior.
add_executable(awe32_p116_master_volume_test tests/p116_master_volume.cpp)
target_include_directories(awe32_p116_master_volume_test PRIVATE src/vst3)
target_compile_features(awe32_p116_master_volume_test PRIVATE cxx_std_23)
add_test(NAME 125A_p116_master_volume COMMAND awe32_p116_master_volume_test)

# P117: direct bank/preset menus must never invent missing SoundFont programs.
add_executable(awe32_p117_direct_presets_test tests/p117_direct_preset_selection.cpp)
target_include_directories(awe32_p117_direct_presets_test PRIVATE src/vst3
  src/opl3 ../upstream/AWE32Emu/AWE32Emu/src)
target_compile_features(awe32_p117_direct_presets_test PRIVATE cxx_std_23)
add_test(NAME 125A_p117_direct_presets COMMAND awe32_p117_direct_presets_test)

# P117: synthetic SoundFont 1.0 metadata must enumerate the original GM
# bank and drumkit in both direct menus; this fixture contains no ROM data.
add_executable(awe32_p117_synthgm_catalog_test tests/p117_synthgm_catalog.cpp)
target_include_directories(awe32_p117_synthgm_catalog_test PRIVATE src/vst3 src/opl3
  ../upstream/AWE32Emu/AWE32Emu/src)
target_compile_features(awe32_p117_synthgm_catalog_test PRIVATE cxx_std_23)
add_test(NAME 125A_p117_synthgm_catalog COMMAND awe32_p117_synthgm_catalog_test)

# P118: no-SDK MIDI host mapping contract, 16-channel IDs and defaults.
add_executable(awe32_p118_midi_mapping_test tests/p118_midi_mapping.cpp)
target_include_directories(awe32_p118_midi_mapping_test PRIVATE src/vst3)
target_compile_features(awe32_p118_midi_mapping_test PRIVATE cxx_std_23)
add_test(NAME 125A_p118_midi_mapping COMMAND awe32_p118_midi_mapping_test)

# P119: ensure live per-channel MIDI state survives asset/ROM swaps.
add_executable(awe32_p119_midi_live_state_test tests/p119_midi_live_state.cpp)
target_include_directories(awe32_p119_midi_live_state_test PRIVATE src/vst3)
target_compile_features(awe32_p119_midi_live_state_test PRIVATE cxx_std_23)
add_test(NAME 125A_p119_midi_live_state COMMAND awe32_p119_midi_live_state_test)

# P119 atomic exchange guarantees RT renderer never waits on a control
# mutex and retired engines are freed on the control thread only.
add_executable(awe32_p119_engine_exchange_test tests/p119_realtime_engine_exchange.cpp)
target_include_directories(awe32_p119_engine_exchange_test PRIVATE src/vst3)
target_compile_features(awe32_p119_engine_exchange_test PRIVATE cxx_std_23)
add_test(NAME 125A_p119_engine_exchange COMMAND awe32_p119_engine_exchange_test)

# P119: hidden Win32 UI message queue works without an open VSTGUI editor.
if(WIN32)
  add_executable(awe32_p119_ui_dispatch_test tests/p119_win_ui_dispatch.cpp)
  target_include_directories(awe32_p119_ui_dispatch_test PRIVATE src/vst3)
  target_compile_features(awe32_p119_ui_dispatch_test PRIVATE cxx_std_23)
  add_test(NAME 125A_p119_ui_dispatch COMMAND awe32_p119_ui_dispatch_test)
endif()

# P120: independent reproductions of Codex P119 audit failures.
# A thousand retirements MUST clear automatically, with a bounded queue and
# no destruction on the audio thread.
add_executable(awe32_p120_engine_retirement_test tests/p120_engine_retirement.cpp)
target_include_directories(awe32_p120_engine_retirement_test PRIVATE src/vst3)
target_compile_features(awe32_p120_engine_retirement_test PRIVATE cxx_std_23)
add_test(NAME 125A_p120_engine_retirement COMMAND awe32_p120_engine_retirement_test)

add_executable(awe32_p120_midi_automation_test tests/p120_midi_automation.cpp)
target_include_directories(awe32_p120_midi_automation_test PRIVATE src/vst3)
target_compile_features(awe32_p120_midi_automation_test PRIVATE cxx_std_23)
add_test(NAME 125A_p120_midi_automation COMMAND awe32_p120_midi_automation_test)

if(WIN32)
  add_executable(awe32_p120_ui_reentrancy_test tests/p120_win_ui_reentrancy.cpp)
  target_include_directories(awe32_p120_ui_reentrancy_test PRIVATE src/vst3)
  target_compile_features(awe32_p120_ui_reentrancy_test PRIVATE cxx_std_23)
  add_test(NAME 125A_p120_ui_reentrancy COMMAND awe32_p120_ui_reentrancy_test)
endif()

# Independent executable proves the exact 125A master SVG is usable as vector
# paths without linking a Windows GUI or loading any copyrighted ROM.
add_executable(awe32_p19_master_logo_test tests/p19_logo_geometry.cpp)
target_include_directories(awe32_p19_master_logo_test PRIVATE src/vst3)
target_compile_features(awe32_p19_master_logo_test PRIVATE cxx_std_23)
add_test(NAME 125A_p19_master_logo
  COMMAND awe32_p19_master_logo_test
    "${PROJECT_SOURCE_DIR}/src/vst3/resource/125A_Logo_Master_FINAL.svg")

option(125A_BUILD_VST3 "Build experimental Windows VST3" OFF)
if(125A_BUILD_VST3)
  if(NOT WIN32)
    message(FATAL_ERROR "125A VST3 is Windows-only")
  endif()
  set(SMTG_ENABLE_VST3_PLUGIN_EXAMPLES OFF CACHE BOOL "" FORCE)
  # Opt-in only for Windows CI: compile Steinberg's real GUI EditorHost.
  # Core release builds retain the minimal SDK without extra host targets.
  option(125A_BUILD_EDITORHOST_TEST "Build Steinberg EditorHost for actual Win32 GUI smoke" OFF)
  if(125A_BUILD_EDITORHOST_TEST)
    set(SMTG_ENABLE_VST3_HOSTING_EXAMPLES ON CACHE BOOL "" FORCE)
  else()
    set(SMTG_ENABLE_VST3_HOSTING_EXAMPLES OFF CACHE BOOL "" FORCE)
  endif()
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

# P122: repeated GUI bank selections must survive host parameter coalescing,
# without an allocation or lock in the real-time consumer.
add_executable(awe32_p122_browser_bank_command_test tests/p122_browser_bank_command.cpp)
target_include_directories(awe32_p122_browser_bank_command_test PRIVATE src/vst3)
target_compile_features(awe32_p122_browser_bank_command_test PRIVATE cxx_std_23)
add_test(NAME 125A_p122_browser_bank_command
  COMMAND awe32_p122_browser_bank_command_test)

# P122: bounded host restart failures and shutdown with a pending retry timer.
if(WIN32)
  add_executable(awe32_p122_host_shutdown_test tests/p122_host_shutdown.cpp)
  target_include_directories(awe32_p122_host_shutdown_test PRIVATE src/vst3)
  target_compile_features(awe32_p122_host_shutdown_test PRIVATE cxx_std_23)
  add_test(NAME 125A_p122_host_shutdown COMMAND awe32_p122_host_shutdown_test)
endif()

# P122 Codex audit: protect project state from torn multi-channel program
# snapshots during automation and concurrent control-thread recall.
add_executable(awe32_p122_state_snapshot_test tests/p122_rt_state_snapshot.cpp)
target_include_directories(awe32_p122_state_snapshot_test PRIVATE src/vst3)
target_compile_features(awe32_p122_state_snapshot_test PRIVATE cxx_std_23)
add_test(NAME 125A_p122_state_snapshot COMMAND awe32_p122_state_snapshot_test)

include(tests/p128_processor.cmake)

# P134 A/B: execute previous, clean P133-V11 VST3 and current P134-V11 VST3
# side by side using actual SDK Processor with synthetic ROM/SF2, identical
# active FX switching, MIDI automation and per-block state snapshots.
# Kept opt-in because the independently pinned P133 binary is not a package
# dependency; the GitHub audit workflow fetches it by exact Actions run.
option(125A_P134_AB "Enable actual P133-vs-P134 VST3 bitexact A/B" OFF)
set(P134_BASELINE_VST3 "" CACHE FILEPATH "P133 V11 VST3 binary from verified run 42196456180")
if(125A_P134_AB)
  if(NOT WIN32 OR NOT 125A_BUILD_VST3 OR NOT EXISTS "${P134_BASELINE_VST3}")
    message(FATAL_ERROR "P134 bitexact A/B requires real Windows VST3 and verified P133 baseline binary")
  endif()
  add_executable(awe32_p134_vst3_pcm_compare
    "${PROJECT_SOURCE_DIR}/tests/p134/vst3_pcm_compare.cpp"
    "${PROJECT_SOURCE_DIR}/external/vst3sdk/public.sdk/source/common/memorystream.cpp"
    "${PROJECT_SOURCE_DIR}/external/vst3sdk/public.sdk/source/vst/hosting/parameterchanges.cpp"
    "${PROJECT_SOURCE_DIR}/external/vst3sdk/public.sdk/source/vst/hosting/eventlist.cpp")
  target_include_directories(awe32_p134_vst3_pcm_compare PRIVATE
    "${PROJECT_SOURCE_DIR}/external/vst3sdk"
    "${PROJECT_SOURCE_DIR}/src/vst3" "${PROJECT_SOURCE_DIR}/tests/p134")
  target_link_libraries(awe32_p134_vst3_pcm_compare PRIVATE sdk winmm)
  target_compile_features(awe32_p134_vst3_pcm_compare PRIVATE cxx_std_23)
  add_dependencies(awe32_p134_vst3_pcm_compare 125A_AWE_Synthesizer p128_assets)
  add_test(NAME 125A_p134_p133_full_pcm_ab
    COMMAND awe32_p134_vst3_pcm_compare compare-baseline
      "${P134_BASELINE_VST3}" "$<TARGET_FILE:125A_AWE_Synthesizer>"
      "${p128_assets}" "${PROJECT_BINARY_DIR}/p134-ab")
  set_tests_properties(125A_p134_p133_full_pcm_ab PROPERTIES TIMEOUT 180)
endif()

# P139 full P135-replicated ETW real-VST3 stress on isolated P137 shadow-DSP optimization.
include(tests/p139/audit.cmake)
