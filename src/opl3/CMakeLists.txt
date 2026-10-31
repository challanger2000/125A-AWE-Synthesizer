# Genuine Yamaha YMF262 OPL3 register-emulation core, kept separate from
# EMU8000 and from the product VST3 until independent MIDI integration.
# Upstream: nukeykt/Nuked-OPL3 @ 765ec962e473aeb767e4cba74ffdc8f588ffbfe8
# License: LGPL-2.1-or-later (full text in third_party/Nuked-OPL3/LICENSE).
add_library(awe32_opl3_core STATIC
  "${PROJECT_SOURCE_DIR}/third_party/Nuked-OPL3/opl3.c"
)
target_include_directories(awe32_opl3_core PUBLIC
  "${PROJECT_SOURCE_DIR}/third_party/Nuked-OPL3"
)
set_target_properties(awe32_opl3_core PROPERTIES C_STANDARD 11)
add_executable(awe32_opl3_register_audio_test
  "${PROJECT_SOURCE_DIR}/tests/opl3_register_audio.cpp"
)
target_link_libraries(awe32_opl3_register_audio_test PRIVATE awe32_opl3_core)
target_compile_features(awe32_opl3_register_audio_test PRIVATE cxx_std_23)
add_test(NAME 125A_opl3_register_audio COMMAND awe32_opl3_register_audio_test)

# Separate MIDI-to-YMF262 adapter; no audio-thread heap operations.
# Separate real Creative Quadratic Modulation hardware emulation (CQM 0.9 beta).
# The original C source and LGPL-2.1-or-later license remain verbatim.
add_library(awe32_cqm_core STATIC "${PROJECT_SOURCE_DIR}/third_party/Nuked-CQM/cqm.c")
target_include_directories(awe32_cqm_core PUBLIC
    "${PROJECT_SOURCE_DIR}/third_party/Nuked-CQM")
set_target_properties(awe32_cqm_core PROPERTIES C_STANDARD 11)
add_library(awe32_opl3_midi STATIC Opl3Midi.cpp Opl3Midi.h IbkBank.cpp IbkBank.h)
target_link_libraries(awe32_opl3_midi PUBLIC awe32_opl3_core awe32_cqm_core)
target_include_directories(awe32_opl3_midi PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}")
target_compile_features(awe32_opl3_midi PRIVATE cxx_std_23)
add_executable(awe32_opl3_midi_audio_test "${PROJECT_SOURCE_DIR}/tests/opl3_midi_audio.cpp")
target_link_libraries(awe32_opl3_midi_audio_test PRIVATE awe32_opl3_midi)
target_compile_features(awe32_opl3_midi_audio_test PRIVATE cxx_std_23)
add_test(NAME 125A_opl3_midi_audio COMMAND awe32_opl3_midi_audio_test)

add_executable(awe32_opl3_ibk_bank_test "${PROJECT_SOURCE_DIR}/tests/opl3_ibk_bank.cpp")
target_link_libraries(awe32_opl3_ibk_bank_test PRIVATE awe32_opl3_midi)
target_compile_features(awe32_opl3_ibk_bank_test PRIVATE cxx_std_23)
add_test(NAME 125A_opl3_ibk_bank COMMAND awe32_opl3_ibk_bank_test)

add_executable(awe32_opl3_rhythm_audio_test "${PROJECT_SOURCE_DIR}/tests/opl3_rhythm_audio.cpp")
target_link_libraries(awe32_opl3_rhythm_audio_test PRIVATE awe32_opl3_midi)
target_compile_features(awe32_opl3_rhythm_audio_test PRIVATE cxx_std_23)
add_test(NAME 125A_opl3_rhythm_audio COMMAND awe32_opl3_rhythm_audio_test)

add_executable(awe32_cqm_backend_test "${PROJECT_SOURCE_DIR}/tests/cqm_backend_audio.cpp")
target_link_libraries(awe32_cqm_backend_test PRIVATE awe32_opl3_midi)
target_compile_features(awe32_cqm_backend_test PRIVATE cxx_std_23)
add_test(NAME 125A_cqm_backend_audio COMMAND awe32_cqm_backend_test)
