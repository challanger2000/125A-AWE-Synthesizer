# 125A AWE Synthesizer: active, isolated chip safety adapter.
# Original upstream files remain untouched under upstream/AWE32Emu.
set(UPSTREAM_SRC "${PROJECT_SOURCE_DIR}/upstream/AWE32Emu/AWE32Emu/src")
add_library(awe32_chip_safety STATIC
  "${CMAKE_CURRENT_SOURCE_DIR}/snd_emu8k.c"
  "${CMAKE_CURRENT_SOURCE_DIR}/Emu8000Box.cpp"
  "${CMAKE_CURRENT_SOURCE_DIR}/SoundFont.cpp"
  "${CMAKE_CURRENT_SOURCE_DIR}/Emu8000.cpp"
  "${CMAKE_CURRENT_SOURCE_DIR}/Synth.cpp"
  "${UPSTREAM_SRC}/I18n.cpp"
)
target_include_directories(awe32_chip_safety PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}"
  "${CMAKE_CURRENT_SOURCE_DIR}/include"
  "${UPSTREAM_SRC}/86box/include"
  "${UPSTREAM_SRC}"
)
target_compile_definitions(awe32_chip_safety PRIVATE AWE32EMU_WITH_86BOX)
if(WIN32)
  target_compile_definitions(awe32_chip_safety PRIVATE _CRT_SECURE_NO_WARNINGS)
else()
  target_link_libraries(awe32_chip_safety PUBLIC m)
endif()
set_target_properties(awe32_chip_safety PROPERTIES C_STANDARD 11 CXX_STANDARD 23)

# Both active Synth and the active DSP renderer are now compiled and linked
# into awe32_chip_safety. This is still a native test engine, NOT a VST3.

add_executable(awe32_engine_safety_test "${PROJECT_SOURCE_DIR}/tests/engine_safety.cpp")
target_include_directories(awe32_engine_safety_test PRIVATE "${UPSTREAM_SRC}" "${CMAKE_CURRENT_SOURCE_DIR}/include" "${UPSTREAM_SRC}/86box/include")
find_package(Threads REQUIRED)
target_link_libraries(awe32_chip_safety PUBLIC Threads::Threads)
target_link_libraries(awe32_engine_safety_test PRIVATE awe32_chip_safety)
set_target_properties(awe32_engine_safety_test PROPERTIES CXX_STANDARD 23)
add_test(NAME 125A_engine_safety COMMAND awe32_engine_safety_test)

add_executable(awe32_sf2_selection_test "${PROJECT_SOURCE_DIR}/tests/sf2_selection.cpp")
target_include_directories(awe32_sf2_selection_test PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}" "${UPSTREAM_SRC}")
target_link_libraries(awe32_sf2_selection_test PRIVATE awe32_chip_safety)
set_target_properties(awe32_sf2_selection_test PROPERTIES CXX_STANDARD 23)
add_test(NAME 125A_sf2_selection COMMAND awe32_sf2_selection_test)

add_executable(awe32_render_rates_test "${PROJECT_SOURCE_DIR}/tests/render_rates.cpp")
target_include_directories(awe32_render_rates_test PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}" "${UPSTREAM_SRC}")
target_link_libraries(awe32_render_rates_test PRIVATE awe32_chip_safety)
set_target_properties(awe32_render_rates_test PROPERTIES CXX_STANDARD 23)
add_test(NAME 125A_render_rates COMMAND awe32_render_rates_test)

add_executable(awe32_box_rates_test "${PROJECT_SOURCE_DIR}/tests/box_rates.cpp")
target_include_directories(awe32_box_rates_test PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}" "${UPSTREAM_SRC}")
target_link_libraries(awe32_box_rates_test PRIVATE awe32_chip_safety)
set_target_properties(awe32_box_rates_test PROPERTIES CXX_STANDARD 23)
add_test(NAME 125A_box_rate_fifo COMMAND awe32_box_rates_test)

add_executable(awe32_sf2_audio_integration_test "${PROJECT_SOURCE_DIR}/tests/sf2_audio_integration.cpp")
target_include_directories(awe32_sf2_audio_integration_test PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}" "${PROJECT_SOURCE_DIR}/src/vst3" "${UPSTREAM_SRC}")
target_link_libraries(awe32_sf2_audio_integration_test PRIVATE awe32_chip_safety)
set_target_properties(awe32_sf2_audio_integration_test PROPERTIES CXX_STANDARD 23)
add_test(NAME 125A_sf2_audio_integration COMMAND awe32_sf2_audio_integration_test)

# P25: Reproduce real, user-supplied SF2 timbre through 86Box with an external
# ROM and bank. The executable has no proprietary assets or external deps.
# It resolves the same assets.cfg as the VST3 and writes two isolated WAVs.
add_executable(awe32_sf2_timbre_probe "${PROJECT_SOURCE_DIR}/tools/sf2_timbre_probe.cpp")
target_include_directories(awe32_sf2_timbre_probe PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}" "${PROJECT_SOURCE_DIR}/src/vst3" "${UPSTREAM_SRC}")
target_link_libraries(awe32_sf2_timbre_probe PRIVATE awe32_chip_safety)
set_target_properties(awe32_sf2_timbre_probe PROPERTIES CXX_STANDARD 23)

# P86: generic non-DAW 86Box audition of any private user SF2.
# Native probe never bundles/redistributes sample banks or ROMs.
add_executable(awe32_p86_generic_sf2_probe "${PROJECT_SOURCE_DIR}/tools/p86_generic_sf2_probe.cpp")
target_include_directories(awe32_p86_generic_sf2_probe PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}" "${PROJECT_SOURCE_DIR}/src/vst3" "${UPSTREAM_SRC}")
target_link_libraries(awe32_p86_generic_sf2_probe PRIVATE awe32_chip_safety)
set_target_properties(awe32_p86_generic_sf2_probe PROPERTIES CXX_STANDARD 23)

# P109 all-preset 86Box ROM-backed private SoundFont diagnostic.
add_executable(awe32_p109_sf2_preset_audit "../../tools/p109_sf2_preset_audit.cpp")
target_include_directories(awe32_p109_sf2_preset_audit PRIVATE "." "../../src/vst3" "../../upstream/AWE32Emu/AWE32Emu/src")
target_link_libraries(awe32_p109_sf2_preset_audit PRIVATE awe32_chip_safety)
set_target_properties(awe32_p109_sf2_preset_audit PROPERTIES CXX_STANDARD 23)

# P90: exact observable Creative SF2 driver mappings (synthetic region tests).
add_executable(awe32_p90_sf2_driver_registers_test "${PROJECT_SOURCE_DIR}/tests/p90_sf2_driver_registers.cpp")
target_include_directories(awe32_p90_sf2_driver_registers_test PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}" "${UPSTREAM_SRC}")
target_link_libraries(awe32_p90_sf2_driver_registers_test PRIVATE awe32_chip_safety)
set_target_properties(awe32_p90_sf2_driver_registers_test PROPERTIES CXX_STANDARD 23)
add_test(NAME 125A_p90_sf2_driver_registers COMMAND awe32_p90_sf2_driver_registers_test)

# P97 standalone, offline, MIDI-accurate original SoundFont test renderer.
# Only public MIDI/SF2 fixtures are downloaded in CI, not embedded here.
add_executable(awe32_p97_midi_renderer "../../tools/p97_midi_renderer.cpp")
target_include_directories(awe32_p97_midi_renderer PRIVATE "." "include" "../../upstream/AWE32Emu/AWE32Emu/src" "../../upstream/AWE32Emu/AWE32Emu/src/86box/include")
target_link_libraries(awe32_p97_midi_renderer PRIVATE awe32_chip_safety)
set_target_properties(awe32_p97_midi_renderer PROPERTIES CXX_STANDARD 23)
