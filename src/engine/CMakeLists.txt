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

# P193: CT4390 reference recordings used the Creative Win95 patch/CC effect
# sends, not the P190 commercial 0%=dry contract. Build a dedicated native
# offline oracle that bypasses the 125A GUI overrides. Never apply it to VST3.
option(AWE125_P193_CT4390_REFERENCE_FX
  "Native-only historical CT4390 comparison: original Creative FX sends" OFF)
if(AWE125_P193_CT4390_REFERENCE_FX)
  if(125A_BUILD_VST3)
    message(FATAL_ERROR
      "P193 historical FX comparison must never be built into the product VST3")
  endif()
  target_compile_definitions(awe32_chip_safety PRIVATE
    AWE125_P193_CT4390_REFERENCE_FX)
endif()
# P198 is never shipping: allow only historical FX reference mode with VST3 OFF.
# Compare possible original Win95 SF2 attenuation scaling without globally
# retuning any productive preset or regression baseline.
set(AWE125_P198_ATTEN_SCALE "" CACHE STRING
  "Research-only alternative to 0.4 SF2 attenuation conversion")
if(NOT "${AWE125_P198_ATTEN_SCALE}" STREQUAL "")
  if(125A_BUILD_VST3 OR NOT AWE125_P193_CT4390_REFERENCE_FX)
    message(FATAL_ERROR "P198 attenuation variant requires native-only P193 CT4390 reference")
  endif()
  if(NOT (AWE125_P198_ATTEN_SCALE STREQUAL "0.50" OR
          AWE125_P198_ATTEN_SCALE STREQUAL "0.53"))
    message(FATAL_ERROR "P198 experiment restricted to predeclared 0.50/0.53 candidates")
  endif()
  target_compile_definitions(awe32_chip_safety PRIVATE
    AWE125_P198_ATTEN_SCALE=${AWE125_P198_ATTEN_SCALE})
endif()
# P201: isolated original-CT4390 envelope experiments; never link candidate
# shaping into any product VST3, commercial DSP or default native renderer.
set(AWE125_P201_MOD_ATTACK_SHAPE "" CACHE STRING
  "Research-only original CT4390 EG1 attack waveform candidate (3 or 70)")
if(NOT "${AWE125_P201_MOD_ATTACK_SHAPE}" STREQUAL "")
  if(125A_BUILD_VST3 OR NOT AWE125_P193_CT4390_REFERENCE_FX)
    message(FATAL_ERROR
      "P201 EG1 candidate is native-only and requires explicit P193 reference mode")
  endif()
  if(NOT (AWE125_P201_MOD_ATTACK_SHAPE STREQUAL "3" OR
          AWE125_P201_MOD_ATTACK_SHAPE STREQUAL "70" OR
          AWE125_P201_MOD_ATTACK_SHAPE STREQUAL "130" OR
          AWE125_P201_MOD_ATTACK_SHAPE STREQUAL "140"))
    message(FATAL_ERROR "P201 invalid research candidate; allowed 3,70,130,140")
  endif()
  target_compile_definitions(awe32_chip_safety PRIVATE
    AWE125_P201_MOD_ATTACK_SHAPE=${AWE125_P201_MOD_ATTACK_SHAPE})
endif()
# P203: test only the slow, *unmeasured* EG1 rate range (0x00..0x0F).
# Preserve every original AWETST25 Block-30 tested rate 0x10..0x3C bitwise.
# Research-only: no commercial VST3 or unrelated driver/DOS/SF1 changes.
option(AWE125_P203_SLOW_MOD_ATTACK
  "Research-only CT4390 slow (<0x10) modulation-envelope shape candidate" OFF)
if(AWE125_P203_SLOW_MOD_ATTACK)
  if(125A_BUILD_VST3 OR NOT AWE125_P193_CT4390_REFERENCE_FX OR
     NOT "${AWE125_P201_MOD_ATTACK_SHAPE}" STREQUAL "")
    message(FATAL_ERROR
      "P203 slow-mod candidate requires native-only P193 and excludes P201")
  endif()
  target_compile_definitions(awe32_chip_safety PRIVATE AWE125_P203_SLOW_MOD_ATTACK)
endif()
# P215 source-derived EG1 Sustain research: all 70 P210/P212/P214 genuine
# original Win95 register cases can be compared against two independently
# built native 86Box chips. NEVER enable in the commercial VST3.
option(AWE125_P215_SF2_SUSTAIN_LAYERS
  "Native-only original Creative SF2 EG1 layered Sustain research experiment" OFF)
if(AWE125_P215_SF2_SUSTAIN_LAYERS)
  if(125A_BUILD_VST3 OR AWE125_P208_SF2_HOLD_SUSTAIN)
    message(FATAL_ERROR
      "P215 source-derived Sustain candidate is native-only and excludes P208")
  endif()
  # Region is a header-defined type passed between the engine and clients.
  # Propagate the research macro to ALL consumers, preventing a mismatched
  # Region layout between separately compiled P86/Synth translation units.
  target_compile_definitions(awe32_chip_safety PUBLIC
    AWE125_P215_SF2_SUSTAIN_LAYERS)
endif()

# P208 candidate cannot be compiled into VST3. Default remains unchanged.
option(AWE125_P208_SF2_HOLD_SUSTAIN
  "Research-only Win95 SoundFont EG1 hold/sustain converter experiment" OFF)
if(AWE125_P208_SF2_HOLD_SUSTAIN)
  if(125A_BUILD_VST3)
    message(FATAL_ERROR "P208 research-only converter forbidden in product VST3")
  endif()
  target_compile_definitions(awe32_chip_safety PRIVATE
    AWE125_P208_SF2_HOLD_SUSTAIN)
endif()
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

# P118: malformed SF2 negative fixtures exercise the actual production parser.
add_executable(awe32_p118_parser_bounds_test "${PROJECT_SOURCE_DIR}/tests/p118_soundfont_parser_bounds.cpp")
target_include_directories(awe32_p118_parser_bounds_test PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}" "${UPSTREAM_SRC}")
target_link_libraries(awe32_p118_parser_bounds_test PRIVATE awe32_chip_safety)
set_target_properties(awe32_p118_parser_bounds_test PROPERTIES CXX_STANDARD 23)
add_test(NAME 125A_p118_parser_bounds COMMAND awe32_p118_parser_bounds_test)

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

# P166: actual SF2/ROM metadata and 86Box PCM regression, including the
# 77-preset sparse shape (missing 63), explicit ROM banks, MIDI CC0, negative
# mutation control, noncontiguous banks and V11 project identity.
# Creates only synthetic ephemeral fixtures in the OS temp directory.
add_executable(awe32_p166_exact_presets_test
  "${PROJECT_SOURCE_DIR}/tests/p166_exact_sf2_rom.cpp")
target_include_directories(awe32_p166_exact_presets_test PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}" "${PROJECT_SOURCE_DIR}/src/vst3"
  "${PROJECT_SOURCE_DIR}/src/opl3" "${UPSTREAM_SRC}")
target_link_libraries(awe32_p166_exact_presets_test PRIVATE awe32_chip_safety)
target_compile_features(awe32_p166_exact_presets_test PRIVATE cxx_std_23)
add_test(NAME 125A_p166_exact_sf2_rom COMMAND awe32_p166_exact_presets_test)
set_tests_properties(125A_p166_exact_sf2_rom PROPERTIES TIMEOUT 90)

add_executable(awe32_p170_audio_render "${PROJECT_SOURCE_DIR}/tests/p170_audio_render.cpp")
target_include_directories(awe32_p170_audio_render PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}" "${UPSTREAM_SRC}")
target_link_libraries(awe32_p170_audio_render PRIVATE awe32_chip_safety)
find_package(Python3 COMPONENTS Interpreter REQUIRED)
add_test(NAME 125A_p170_pcm_audio_oracles COMMAND "${Python3_EXECUTABLE}"
  "${PROJECT_SOURCE_DIR}/tests/p170_audio_oracles.py" "$<TARGET_FILE:awe32_p170_audio_render>"
  "${PROJECT_BINARY_DIR}/p170-audio")
set_tests_properties(125A_p170_pcm_audio_oracles PROPERTIES TIMEOUT 600)
add_executable(awe32_p171_rom_level "${PROJECT_SOURCE_DIR}/tests/p171_rom_level.cpp")
target_include_directories(awe32_p171_rom_level PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}"
  "${PROJECT_SOURCE_DIR}/src/vst3" "${PROJECT_SOURCE_DIR}/src/opl3" "${UPSTREAM_SRC}")
target_link_libraries(awe32_p171_rom_level PRIVATE awe32_chip_safety)
add_test(NAME 125A_p171_synthetic_rom_level COMMAND awe32_p171_rom_level)

# P121: real 86Box synthetic ROM / PCM regression for dense pitchbend.
# Exercises the genuine 32,768-write queue and a playing 16-voice bank.
add_executable(awe32_p121_pitchbend_audio_test "${PROJECT_SOURCE_DIR}/tests/p121_pitchbend_audio.cpp")
target_include_directories(awe32_p121_pitchbend_audio_test PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}" "${UPSTREAM_SRC}")
target_link_libraries(awe32_p121_pitchbend_audio_test PRIVATE awe32_chip_safety)
set_target_properties(awe32_p121_pitchbend_audio_test PROPERTIES CXX_STANDARD 23)
add_test(NAME 125A_p121_pitchbend_audio COMMAND awe32_p121_pitchbend_audio_test)

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

# P112: current P110/P111 ROM + user-SF2 all-presets real 86Box audio audit.
add_executable(awe32_p112_all_presets_audio_audit "../../tools/p112_all_presets_audio_audit.cpp")
target_include_directories(awe32_p112_all_presets_audio_audit PRIVATE "." "../../src/vst3" "../../upstream/AWE32Emu/AWE32Emu/src")
target_link_libraries(awe32_p112_all_presets_audio_audit PRIVATE awe32_chip_safety)
set_target_properties(awe32_p112_all_presets_audio_audit PROPERTIES CXX_STANDARD 23)

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
if(AWE125_P193_CT4390_REFERENCE_FX)
  target_compile_definitions(awe32_p97_midi_renderer PRIVATE
    AWE125_P193_CT4390_REFERENCE_FX)
endif()

# P128: audible, allocation-free note transfer at engine publication boundaries.
add_executable(awe32_p128_note_handoff_test "${PROJECT_SOURCE_DIR}/tests/p128_note_handoff.cpp")
target_include_directories(awe32_p128_note_handoff_test PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}" "${UPSTREAM_SRC}")
target_link_libraries(awe32_p128_note_handoff_test PRIVATE awe32_chip_safety)
add_test(NAME 125A_p128_note_handoff COMMAND awe32_p128_note_handoff_test)

# P133 original Creative 8x8 Reverb/Chorus selection through EMU8000
# INIT/HWCF registers, no ROM/SF2 proprietary fixtures required.
add_executable(awe32_p133_fx_modes_test "${PROJECT_SOURCE_DIR}/tests/p133_fx_modes.cpp")
target_include_directories(awe32_p133_fx_modes_test PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}" "${UPSTREAM_SRC}")
target_link_libraries(awe32_p133_fx_modes_test PRIVATE awe32_chip_safety)
set_target_properties(awe32_p133_fx_modes_test PROPERTIES CXX_STANDARD 23)
add_test(NAME 125A_p133_fx_register_modes COMMAND awe32_p133_fx_modes_test)
