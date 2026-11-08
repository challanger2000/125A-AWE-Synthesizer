# Every mutant is generated outside the checkout and linked ahead of the
# unmodified archive. Production/VST3 targets never use these objects.
option(125A_P170_MUTATION_TESTS "Falsify audio oracles with deliberate regressions" ON)
set(125A_P170_BASELINE_ROOT "" CACHE PATH "Optional pinned pre-fix engine source directory")
if(125A_BUILD_ENGINE_PROBES AND 125A_P170_MUTATION_TESTS)
  find_package(Python3 COMPONENTS Interpreter REQUIRED)
  set(mutant_dir "${PROJECT_BINARY_DIR}/p170-mutants")
  execute_process(COMMAND "${Python3_EXECUTABLE}" "${PROJECT_SOURCE_DIR}/tests/p170_mutations.py"
    "${PROJECT_SOURCE_DIR}" "${mutant_dir}" COMMAND_ERROR_IS_FATAL ANY)
  set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    "${PROJECT_SOURCE_DIR}/src/engine/Synth.cpp" "${PROJECT_SOURCE_DIR}/src/engine/SoundFont.cpp"
    "${PROJECT_SOURCE_DIR}/tests/p170_mutations.py")
  foreach(kind IN ITEMS bank amp filter loop end rom pedal headroom)
    if(kind STREQUAL end)
      set(file SoundFont.cpp)
    else()
      set(file Synth.cpp)
    endif()
    if(kind STREQUAL bank)
      set(probe "${PROJECT_SOURCE_DIR}/tests/p166_exact_sf2_rom.cpp")
    elseif(kind STREQUAL rom)
      set(probe "${PROJECT_SOURCE_DIR}/tests/p171_rom_level.cpp")
    else()
      set(probe "${PROJECT_SOURCE_DIR}/tests/p170_audio_render.cpp")
    endif()
    add_executable(p170_mutant_${kind} "${probe}" "${mutant_dir}/${kind}/${file}")
    target_include_directories(p170_mutant_${kind} PRIVATE
      "${PROJECT_SOURCE_DIR}/src/engine" "${PROJECT_SOURCE_DIR}/src/vst3"
      "${PROJECT_SOURCE_DIR}/src/opl3" "${PROJECT_SOURCE_DIR}/upstream/AWE32Emu/AWE32Emu/src")
    target_link_libraries(p170_mutant_${kind} PRIVATE awe32_chip_safety)
    add_test(NAME 125A_p170_detect_mutant_${kind} COMMAND "${Python3_EXECUTABLE}"
      "${PROJECT_SOURCE_DIR}/tests/p170_expect_mutant.py" "${kind}" "$<TARGET_FILE:p170_mutant_${kind}>"
      "${PROJECT_BINARY_DIR}/p170-negative-${kind}")
    set_tests_properties(125A_p170_detect_mutant_${kind} PROPERTIES TIMEOUT 650
      DEPENDS "125A_p170_pcm_audio_oracles;125A_p166_exact_sf2_rom" RUN_SERIAL TRUE)
  endforeach()
endif()
if(125A_BUILD_ENGINE_PROBES AND 125A_P170_BASELINE_ROOT)
  add_executable(p170_baseline_audio "${PROJECT_SOURCE_DIR}/tests/p170_audio_render.cpp"
    "${125A_P170_BASELINE_ROOT}/Synth.cpp" "${125A_P170_BASELINE_ROOT}/SoundFont.cpp")
  target_include_directories(p170_baseline_audio PRIVATE "${PROJECT_SOURCE_DIR}/src/engine"
    "${PROJECT_SOURCE_DIR}/upstream/AWE32Emu/AWE32Emu/src")
  target_link_libraries(p170_baseline_audio PRIVATE awe32_chip_safety)
  add_test(NAME 125A_p170_pinned_baseline_pcm COMMAND "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/p170_compare_baseline.py" "$<TARGET_FILE:p170_baseline_audio>"
    "$<TARGET_FILE:awe32_p170_audio_render>" "${PROJECT_BINARY_DIR}/p170-paired")
  set_tests_properties(125A_p170_pinned_baseline_pcm PROPERTIES TIMEOUT 1200 RUN_SERIAL TRUE)
endif()
