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
target_include_directories(awe32_sf2_audio_integration_test PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}" "${UPSTREAM_SRC}")
target_link_libraries(awe32_sf2_audio_integration_test PRIVATE awe32_chip_safety)
set_target_properties(awe32_sf2_audio_integration_test PROPERTIES CXX_STANDARD 23)
add_test(NAME 125A_sf2_audio_integration COMMAND awe32_sf2_audio_integration_test)
