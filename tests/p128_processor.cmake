# Optional native SDK harness. The production VST3 remains Windows-only.
# On Windows this uses the SDK already required by 125A_BUILD_VST3.
set(125A_PROCESSOR_SDK_ROOT "" CACHE PATH "SDK root for native P128 Processor regressions")
if(125A_BUILD_VST3)
  set(125A_PROCESSOR_SDK_ROOT "${PROJECT_SOURCE_DIR}/external/vst3sdk")
elseif(125A_PROCESSOR_SDK_ROOT)
  set(SMTG_ENABLE_VSTGUI_SUPPORT OFF CACHE BOOL "" FORCE)
  set(SMTG_ENABLE_VST3_PLUGIN_EXAMPLES OFF CACHE BOOL "" FORCE)
  set(SMTG_ENABLE_VST3_HOSTING_EXAMPLES OFF CACHE BOOL "" FORCE)
  add_subdirectory("${125A_PROCESSOR_SDK_ROOT}" "${PROJECT_BINARY_DIR}/processor-sdk")
endif()
if(125A_PROCESSOR_SDK_ROOT AND 125A_BUILD_ENGINE_PROBES)
  find_package(Python3 COMPONENTS Interpreter REQUIRED)
  set(p128_generated "${PROJECT_BINARY_DIR}/p128-generated")
  file(MAKE_DIRECTORY "${p128_generated}")
  # CI builds below the checkout, whose protected-resource contract scans
  # every directory. Synthetic ROM/SF2 fixtures must still live OUTSIDE it.
  execute_process(COMMAND "${Python3_EXECUTABLE}" -c
    "import pathlib,tempfile; print(pathlib.Path(tempfile.gettempdir()).resolve())"
    OUTPUT_VARIABLE p128_temp_root OUTPUT_STRIP_TRAILING_WHITESPACE
    RESULT_VARIABLE p128_temp_result)
  if(NOT p128_temp_result EQUAL 0 OR NOT p128_temp_root)
    message(FATAL_ERROR "Cannot locate an external temporary directory for P128 assets")
  endif()
  file(TO_CMAKE_PATH "${p128_temp_root}" p128_temp_root)
  string(SHA256 p128_build_key "${PROJECT_BINARY_DIR}")
  string(SUBSTRING "${p128_build_key}" 0 16 p128_build_key)
  set(p128_assets "${p128_temp_root}/125a-p128-${p128_build_key}")
  cmake_path(IS_PREFIX PROJECT_SOURCE_DIR "${p128_assets}" NORMALIZE p128_assets_in_source)
  if(p128_assets_in_source)
    message(FATAL_ERROR "P128 synthetic assets require a temporary directory outside the checkout")
  endif()
  add_custom_command(OUTPUT "${p128_generated}/ProcessorUnderTest.h"
    COMMAND "${Python3_EXECUTABLE}" "${PROJECT_SOURCE_DIR}/tests/p128_extract_processor.py"
      "${PROJECT_SOURCE_DIR}/src/vst3/Factory.cpp" "${p128_generated}/ProcessorUnderTest.h"
    DEPENDS "${PROJECT_SOURCE_DIR}/src/vst3/Factory.cpp" "${PROJECT_SOURCE_DIR}/tests/p128_extract_processor.py")
  # Generate the shared Processor header ONCE before parallel MSBuild compiles.
  # P131 independently reproduced PermissionError without this guard.
  add_custom_target(p128_processor_header DEPENDS "${p128_generated}/ProcessorUnderTest.h")
  add_custom_command(OUTPUT "${p128_assets}/bank.sf2" "${p128_assets}/zero.rom"
    COMMAND "${Python3_EXECUTABLE}" "${PROJECT_SOURCE_DIR}/tests/p128_synthetic_assets.py" "${p128_assets}"
    DEPENDS "${PROJECT_SOURCE_DIR}/tests/p128_synthetic_assets.py")
  add_custom_target(p128_assets DEPENDS "${p128_assets}/bank.sf2" "${p128_assets}/zero.rom")
  add_executable(awe32_p128_processor_order_test
    "${PROJECT_SOURCE_DIR}/tests/p128_processor_order.cpp"
    "${125A_PROCESSOR_SDK_ROOT}/public.sdk/source/common/memorystream.cpp"
    "${125A_PROCESSOR_SDK_ROOT}/public.sdk/source/vst/hosting/parameterchanges.cpp"
    "${125A_PROCESSOR_SDK_ROOT}/public.sdk/source/vst/hosting/eventlist.cpp")
  target_include_directories(awe32_p128_processor_order_test PRIVATE
    "${p128_generated}" "${125A_PROCESSOR_SDK_ROOT}" "${PROJECT_SOURCE_DIR}/src/vst3"
    "${PROJECT_SOURCE_DIR}/src/engine" "${PROJECT_SOURCE_DIR}/src/opl3"
    "${PROJECT_SOURCE_DIR}/upstream/AWE32Emu/AWE32Emu/src")
  target_link_libraries(awe32_p128_processor_order_test PRIVATE sdk awe32_chip_safety)
  add_dependencies(awe32_p128_processor_order_test p128_assets p128_processor_header)
  add_test(NAME 125A_p128_processor_order COMMAND awe32_p128_processor_order_test deterministic "${p128_assets}")
  add_test(NAME 125A_p128_processor_remove_engine COMMAND awe32_p128_processor_order_test nullswap "${p128_assets}")
  # Deterministic regression of accepted master / all GUI parameters during
  # an RT writer refusal, including both project recall ordering directions.
  add_test(NAME 125A_p128_persistent_controls
    COMMAND awe32_p128_processor_order_test persistent-controls "${p128_assets}")
  add_test(NAME 125A_p128_sample_accurate_program_pcm
    COMMAND awe32_p128_processor_order_test midblock-program "${p128_assets}")
  # P166: unlike the browser-only model, execute the exact extracted VST3
  # process() with absent MIDI programs, host automation, real 86Box output
  # and V11 project save/recall. No synthetic ROM copyright contamination.
  add_test(NAME 125A_p166_processor_missing_program
    COMMAND awe32_p128_processor_order_test p166-exact-presets "${p128_assets}")
  set_tests_properties(125A_p128_processor_order 125A_p128_processor_remove_engine
    125A_p128_persistent_controls 125A_p128_sample_accurate_program_pcm
    125A_p166_processor_missing_program PROPERTIES TIMEOUT 90)

  add_test(NAME 125A_p133_fx_processor_modes
    COMMAND awe32_p128_processor_order_test fx-presets "${p128_assets}")
  set_tests_properties(125A_p133_fx_processor_modes PROPERTIES TIMEOUT 120)
  # P134: read actual audio from the ROM-backed VST3 process() after CC120.
  # This test is intentionally red against pre-fix hardware-volume handling.
  add_test(NAME 125A_p134_cc120_physical_stop
    COMMAND awe32_p128_processor_order_test cc120-stop "${p128_assets}")
  set_tests_properties(125A_p134_cc120_physical_stop PROPERTIES TIMEOUT 90)

  # P130 AUDIT-ONLY allocation instrumentation. The harness overrides
  # scalar/array C++ operator new on the PROCESSING THREAD, not malloc.
  add_executable(awe32_p130_rt_alloc_probe
    "${PROJECT_SOURCE_DIR}/tests/p130_rt_cpp_heap_audit.cpp"
    "${125A_PROCESSOR_SDK_ROOT}/public.sdk/source/common/memorystream.cpp"
    "${125A_PROCESSOR_SDK_ROOT}/public.sdk/source/vst/hosting/parameterchanges.cpp"
    "${125A_PROCESSOR_SDK_ROOT}/public.sdk/source/vst/hosting/eventlist.cpp")
  target_include_directories(awe32_p130_rt_alloc_probe PRIVATE
    "${p128_generated}" "${125A_PROCESSOR_SDK_ROOT}" "${PROJECT_SOURCE_DIR}/src/vst3"
    "${PROJECT_SOURCE_DIR}/src/engine" "${PROJECT_SOURCE_DIR}/src/opl3"
    "${PROJECT_SOURCE_DIR}/upstream/AWE32Emu/AWE32Emu/src")
  target_link_libraries(awe32_p130_rt_alloc_probe PRIVATE sdk awe32_chip_safety)
  target_compile_features(awe32_p130_rt_alloc_probe PRIVATE cxx_std_23)
  add_dependencies(awe32_p130_rt_alloc_probe p128_assets p128_processor_header)
  add_test(NAME 125A_p130_no_cpp_new_on_audio_thread
    COMMAND awe32_p130_rt_alloc_probe "${p128_assets}")
  set_tests_properties(125A_p130_no_cpp_new_on_audio_thread PROPERTIES TIMEOUT 120)

endif()

if(125A_PROCESSOR_SDK_ROOT AND 125A_BUILD_ENGINE_PROBES)
  # Link the reference C object before the normal engine archive, so only
  # snd_emu8k.c is replaced; Synth/adapter/parser objects remain identical.
  add_library(awe32_p128_uncached_chip OBJECT "${PROJECT_SOURCE_DIR}/src/engine/snd_emu8k.c")
  target_include_directories(awe32_p128_uncached_chip PRIVATE
    "${PROJECT_SOURCE_DIR}/src/engine/include"
    "${PROJECT_SOURCE_DIR}/upstream/AWE32Emu/AWE32Emu/src/86box/include"
    "${PROJECT_SOURCE_DIR}/upstream/AWE32Emu/AWE32Emu/src")
  target_compile_definitions(awe32_p128_uncached_chip PRIVATE AWE125_TEST_DISABLE_FILTER_CACHE)
  set_property(TARGET awe32_p128_uncached_chip PROPERTY C_STANDARD 11)
  if(WIN32)
    target_compile_definitions(awe32_p128_uncached_chip PRIVATE _CRT_SECURE_NO_WARNINGS)
  endif()
  foreach(variant IN ITEMS cached uncached)
    add_executable(awe32_p128_filter_${variant} "${PROJECT_SOURCE_DIR}/tests/p128_filter_cache.cpp")
    target_include_directories(awe32_p128_filter_${variant} PRIVATE
      "${PROJECT_SOURCE_DIR}/src/engine" "${PROJECT_SOURCE_DIR}/upstream/AWE32Emu/AWE32Emu/src")
    target_link_libraries(awe32_p128_filter_${variant} PRIVATE awe32_chip_safety)
    add_dependencies(awe32_p128_filter_${variant} p128_assets)
  endforeach()
  target_sources(awe32_p128_filter_uncached PRIVATE $<TARGET_OBJECTS:awe32_p128_uncached_chip>)
  add_test(NAME 125A_p128_filter_cache_pcm
    COMMAND "${Python3_EXECUTABLE}" "${PROJECT_SOURCE_DIR}/tests/p128_compare_filter.py"
      "$<TARGET_FILE:awe32_p128_filter_cached>" "$<TARGET_FILE:awe32_p128_filter_uncached>"
      "${p128_assets}" "${p128_assets}/filter-pcm")
endif()
