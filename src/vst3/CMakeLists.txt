# The two historical IBKs are fetched at BUILD time, verified against the
# owner's uploaded archive and shipped within the VST3 (no user setup).
# Python is used only during development; the finished plugin is standalone.
find_package(Python3 COMPONENTS Interpreter REQUIRED)
execute_process(
  COMMAND "${Python3_EXECUTABLE}" "${PROJECT_SOURCE_DIR}/tools/fetch_ibk_resources.py"
          "${CMAKE_CURRENT_SOURCE_DIR}/resource"
  RESULT_VARIABLE IBK_IMPORT_RESULT
)
if(NOT IBK_IMPORT_RESULT EQUAL 0)
  message(FATAL_ERROR "Historical FM bank packaging failed")
endif()
set(target 125A_AWE_Synthesizer)
smtg_add_vst3plugin(125A_AWE_Synthesizer
  Factory.cpp AssetState.h AssetConfig.h
  # SDK's moduleinit.cpp needs moduleHandle from the real Windows entry.
  "${CMAKE_SOURCE_DIR}/external/vst3sdk/public.sdk/source/main/dllmain.cpp"
)
target_link_libraries(125A_AWE_Synthesizer PRIVATE sdk vstgui_support awe32_chip_safety awe32_opl3_midi)
smtg_target_add_plugin_resources(125A_AWE_Synthesizer
  RESOURCES resource/awe_test_panel.uidesc
            resource/MAUIFM.IBK resource/DRUM.IBK resource/IBK_License.txt
)
target_include_directories(125A_AWE_Synthesizer PRIVATE
    ../engine ../engine/include
    ../../upstream/AWE32Emu/AWE32Emu/src
    ../../upstream/AWE32Emu/AWE32Emu/src/86box/include
)
target_compile_features(125A_AWE_Synthesizer PRIVATE cxx_std_23)
smtg_target_configure_version_file(125A_AWE_Synthesizer)
