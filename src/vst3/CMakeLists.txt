# The separate native regression tests still exercise historical OPL3 IBK
# parsing. Fetch their independently verified fixtures at configure time,
# but NEVER ship IBKs or FM engines as AWE VST3 resources.
find_package(Python3 COMPONENTS Interpreter REQUIRED)
execute_process(
  COMMAND "${Python3_EXECUTABLE}" "${PROJECT_SOURCE_DIR}/tools/fetch_ibk_resources.py"
          "${CMAKE_CURRENT_SOURCE_DIR}/resource"
  RESULT_VARIABLE IBK_IMPORT_RESULT
)
if(NOT IBK_IMPORT_RESULT EQUAL 0)
  message(FATAL_ERROR "Historic IBK test fixtures unavailable")
endif()
set(target 125A_AWE_Synthesizer)
smtg_add_vst3plugin(125A_AWE_Synthesizer
  Factory.cpp PresetBrowserView.cpp PresetBrowserView.h PresetBrowserModel.h PresetCatalog.h MasterLogoView.cpp MasterLogoView.h LogoGeometry.h Sf2LoadPolicy.h AssetState.h AssetConfig.h
  # SDK's moduleinit.cpp needs moduleHandle from the real Windows entry.
  "${CMAKE_SOURCE_DIR}/external/vst3sdk/public.sdk/source/main/dllmain.cpp"
)
target_link_libraries(125A_AWE_Synthesizer PRIVATE sdk vstgui_support awe32_chip_safety awe32_opl3_midi)
# P165 requires the user's ORIGINAL faceplate, faithfully reduced to
# 1000x708 (1491x1055 source, proportional LANCZOS). Never silently
# recompose the LCD/chip from legacy P160/P164 parts.
set(P165_FACEPLATE "resource/125A_P165_Original_Faceplate_1000x708.png")
if(NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${P165_FACEPLATE}")
  message(FATAL_ERROR "P165 original faceplate resource missing. No placeholder or old photo is allowed.")
endif()
smtg_target_add_plugin_resources(125A_AWE_Synthesizer
  RESOURCES resource/awe_test_panel.uidesc
                        resource/125A_Logo_Master_FINAL.svg
                        resource/125A_Knob_Standard_33frames_58px.png
                        resource/125A_Knob_Master_33frames_134px.png
                        resource/125A_Button_Atlas_Hardware_Normal_Pressed.png
                        resource/125A_Lcd_Amber_Blank_512x147.png
                        resource/125A_AWE_Gold_Logo_236x147.png
                        resource/125A_PCB_Shared_1000x640.png
                        ${P165_FACEPLATE}
)
target_include_directories(125A_AWE_Synthesizer PRIVATE
    ../engine ../engine/include ../opl3
    ../../upstream/AWE32Emu/AWE32Emu/src
    ../../upstream/AWE32Emu/AWE32Emu/src/86box/include
)
target_compile_features(125A_AWE_Synthesizer PRIVATE cxx_std_23)
smtg_target_configure_version_file(125A_AWE_Synthesizer)

if(WIN32)
  # P150: embed real gold knob filmstrips and exact-size button atlas.
  # Deliberately NO photographic PCB faceplate until geometry is approved.
  configure_file(resource/awe_gold_knobs.rc.in
    "${CMAKE_CURRENT_BINARY_DIR}/awe_gold_knobs.rc" @ONLY)
  # This is the ONLY static faceplate used in the editor.
  file(APPEND "${CMAKE_CURRENT_BINARY_DIR}/awe_gold_knobs.rc"
       "\"125A_P165_Original_Faceplate_1000x708.png\" PNG DISCARDABLE \"${CMAKE_CURRENT_SOURCE_DIR}/${P165_FACEPLATE}\"\n")
  target_sources(125A_AWE_Synthesizer PRIVATE
    "${CMAKE_CURRENT_BINARY_DIR}/awe_gold_knobs.rc")
  target_link_libraries(125A_AWE_Synthesizer PRIVATE comdlg32)
  # P120: query the actual built DLL and VST3 IUnitInfo; do not infer
  # program-change support from source substrings or Validator PASS alone.
  add_executable(awe32_p120_program_host_test
      "${PROJECT_SOURCE_DIR}/tests/p120_vst3_program_host.cpp")
  target_include_directories(awe32_p120_program_host_test PRIVATE
      "${PROJECT_SOURCE_DIR}/external/vst3sdk")
  target_link_libraries(awe32_p120_program_host_test PRIVATE sdk)
  target_compile_features(awe32_p120_program_host_test PRIVATE cxx_std_23)
  add_dependencies(awe32_p120_program_host_test 125A_AWE_Synthesizer)
  add_test(NAME 125A_p120_program_host
      COMMAND awe32_p120_program_host_test
              "$<TARGET_FILE:125A_AWE_Synthesizer>")
endif()

# P122: check the real exported VST3 processor's off-thread bank-reselect
# message, audio-block consumption and persisted bank without a user ROM.
if(WIN32)
  add_executable(awe32_p122_vst3_bank_host_test
      "${PROJECT_SOURCE_DIR}/tests/p122_vst3_bank_host.cpp"
      "${PROJECT_SOURCE_DIR}/external/vst3sdk/public.sdk/source/common/memorystream.cpp")
  target_include_directories(awe32_p122_vst3_bank_host_test PRIVATE
      "${PROJECT_SOURCE_DIR}/external/vst3sdk"
      "${PROJECT_SOURCE_DIR}/src/vst3")
  target_link_libraries(awe32_p122_vst3_bank_host_test PRIVATE sdk sdk_hosting)
  target_compile_features(awe32_p122_vst3_bank_host_test PRIVATE cxx_std_23)
  add_dependencies(awe32_p122_vst3_bank_host_test 125A_AWE_Synthesizer)
  add_test(NAME 125A_p122_vst3_bank_host
      COMMAND awe32_p122_vst3_bank_host_test
              "$<TARGET_FILE:125A_AWE_Synthesizer>")
endif()

# P141: host automation must show named Creative effect modes, not numeric 0..7
# even when the actual GUI is closed. Verify controller exported by real VST3.
if(WIN32)
  add_executable(awe32_p141_vstgui_host_names_test
      "${PROJECT_SOURCE_DIR}/tests/p141_vstgui_host_fx_names.cpp")
  target_include_directories(awe32_p141_vstgui_host_names_test PRIVATE
      "${PROJECT_SOURCE_DIR}/external/vst3sdk")
  target_link_libraries(awe32_p141_vstgui_host_names_test PRIVATE sdk)
  target_compile_features(awe32_p141_vstgui_host_names_test PRIVATE cxx_std_23)
  add_dependencies(awe32_p141_vstgui_host_names_test 125A_AWE_Synthesizer)
  add_test(NAME 125A_p141_vstgui_host_fx_names
      COMMAND awe32_p141_vstgui_host_names_test
              "$<TARGET_FILE:125A_AWE_Synthesizer>")
endif()
