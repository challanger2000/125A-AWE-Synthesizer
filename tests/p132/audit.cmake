option(125A_P132_AUDIT "Build separate P132 diagnostic DLL/host (no release approval)" OFF)
if(125A_P132_AUDIT)
  if(NOT WIN32 OR NOT 125A_BUILD_VST3)
    message(FATAL_ERROR "P132 actual-DLL audit requires Windows and the full VST3 build")
  endif()
  file(GLOB_RECURSE p132_production_inputs CONFIGURE_DEPENDS "${PROJECT_SOURCE_DIR}/src/engine/*")
  set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    ${p132_production_inputs} "${PROJECT_SOURCE_DIR}/src/vst3/Factory.cpp"
    "${PROJECT_SOURCE_DIR}/tests/p132/generate_probe.py"
    "${PROJECT_SOURCE_DIR}/upstream/AWE32Emu/AWE32Emu/src/Emu8000Box.h")
  set(p132_root "${PROJECT_BINARY_DIR}/p132-source")
  execute_process(COMMAND "${Python3_EXECUTABLE}" "${PROJECT_SOURCE_DIR}/tests/p132/generate_probe.py"
    "${PROJECT_SOURCE_DIR}" "${p132_root}" RESULT_VARIABLE p132_generated)
  if(NOT p132_generated EQUAL 0)
    message(FATAL_ERROR "P132 diagnostic copy failed")
  endif()
  add_library(awe32_p132_chip STATIC
    "${p132_root}/engine/snd_emu8k.c" "${p132_root}/engine/Emu8000Box.cpp"
    "${p132_root}/engine/Emu8000.cpp" "${p132_root}/engine/Synth.cpp"
    "${p132_root}/engine/SoundFont.cpp"
    "${PROJECT_SOURCE_DIR}/upstream/AWE32Emu/AWE32Emu/src/I18n.cpp")
  target_include_directories(awe32_p132_chip PRIVATE "${p132_root}/engine"
    "${p132_root}/engine/include" "${PROJECT_SOURCE_DIR}/tests/p132"
    "${PROJECT_SOURCE_DIR}/upstream/AWE32Emu/AWE32Emu/src"
    "${PROJECT_SOURCE_DIR}/upstream/AWE32Emu/AWE32Emu/src/86box/include")
  target_compile_definitions(awe32_p132_chip PRIVATE AWE32EMU_WITH_86BOX _CRT_SECURE_NO_WARNINGS)
  set_target_properties(awe32_p132_chip PROPERTIES C_STANDARD 11 CXX_STANDARD 23)
  target_compile_options(awe32_p132_chip PRIVATE /Zi)
  smtg_add_vst3plugin(125A_P132_Diagnostic "${p132_root}/Factory.cpp"
    "${PROJECT_SOURCE_DIR}/src/vst3/PresetBrowserView.cpp"
    "${PROJECT_SOURCE_DIR}/src/vst3/MasterLogoView.cpp"
    "${125A_PROCESSOR_SDK_ROOT}/public.sdk/source/main/dllmain.cpp")
  target_include_directories(125A_P132_Diagnostic PRIVATE "${p132_root}/engine"
    "${p132_root}/engine/include" "${PROJECT_SOURCE_DIR}/tests/p132"
    "${PROJECT_SOURCE_DIR}/src/vst3" "${PROJECT_SOURCE_DIR}/src/opl3"
    "${PROJECT_SOURCE_DIR}/upstream/AWE32Emu/AWE32Emu/src")
  target_link_libraries(125A_P132_Diagnostic PRIVATE sdk vstgui_support awe32_p132_chip awe32_opl3_midi comdlg32)
  smtg_target_add_plugin_resources(125A_P132_Diagnostic RESOURCES
    "${PROJECT_SOURCE_DIR}/src/vst3/resource/awe_test_panel.uidesc"
    "${PROJECT_SOURCE_DIR}/src/vst3/resource/125A_Logo_Master_FINAL.svg")
  target_compile_options(125A_P132_Diagnostic PRIVATE /Zi)
  target_link_options(125A_P132_Diagnostic PRIVATE /DEBUG:FULL)
  smtg_target_configure_version_file(125A_P132_Diagnostic)
  add_executable(awe32_p132_dll_host "${PROJECT_SOURCE_DIR}/tests/p132/dll_host.cpp"
    "${125A_PROCESSOR_SDK_ROOT}/public.sdk/source/common/memorystream.cpp"
    "${125A_PROCESSOR_SDK_ROOT}/public.sdk/source/vst/hosting/parameterchanges.cpp"
    "${125A_PROCESSOR_SDK_ROOT}/public.sdk/source/vst/hosting/eventlist.cpp")
  target_include_directories(awe32_p132_dll_host PRIVATE "${125A_PROCESSOR_SDK_ROOT}"
    "${PROJECT_SOURCE_DIR}/src/vst3" "${PROJECT_SOURCE_DIR}/tests/p132")
  target_link_libraries(awe32_p132_dll_host PRIVATE sdk winmm)
  add_dependencies(awe32_p132_dll_host 125A_AWE_Synthesizer 125A_P132_Diagnostic p128_assets)
  add_executable(awe32_p132_etw_reader "${PROJECT_SOURCE_DIR}/tests/p132/etw_reader.cpp")
  target_link_libraries(awe32_p132_etw_reader PRIVATE advapi32 tdh dbghelp)
  add_test(NAME 125A_p132_diagnostic_dll_pcm_census COMMAND awe32_p132_dll_host qualify
    "$<TARGET_FILE:125A_AWE_Synthesizer>" "$<TARGET_FILE:125A_P132_Diagnostic>"
    "${p128_assets}" "${PROJECT_BINARY_DIR}/p132-qualification")
  set_tests_properties(125A_p132_diagnostic_dll_pcm_census PROPERTIES TIMEOUT 180)
  add_test(NAME 125A_p132_measurement_oracle_controls
    COMMAND "${Python3_EXECUTABLE}" "${PROJECT_SOURCE_DIR}/tests/p132/test_analysis.py")
  file(GENERATE OUTPUT "${PROJECT_BINARY_DIR}/p132-paths-$<CONFIG>.txt" CONTENT
    "$<TARGET_FILE:awe32_p132_dll_host>\n$<TARGET_FILE:125A_AWE_Synthesizer>\n$<TARGET_FILE:125A_P132_Diagnostic>\n${p128_assets}\n$<TARGET_FILE:awe32_p132_etw_reader>\n")
endif()
