# AWE-only plugin: no OPL3/CQM bank downloads or resources.
set(target 125A_AWE_Synthesizer)
smtg_add_vst3plugin(125A_AWE_Synthesizer
  Factory.cpp PresetBrowserView.cpp PresetBrowserView.h PresetBrowserModel.h PresetCatalog.h MasterLogoView.cpp MasterLogoView.h LogoGeometry.h Sf2LoadPolicy.h AssetState.h AssetConfig.h
  # SDK's moduleinit.cpp needs moduleHandle from the real Windows entry.
  "${CMAKE_SOURCE_DIR}/external/vst3sdk/public.sdk/source/main/dllmain.cpp"
)
target_link_libraries(125A_AWE_Synthesizer PRIVATE sdk vstgui_support awe32_chip_safety awe32_opl3_midi)
smtg_target_add_plugin_resources(125A_AWE_Synthesizer
  RESOURCES resource/awe_test_panel.uidesc
                        resource/125A_Logo_Master_FINAL.svg
)
target_include_directories(125A_AWE_Synthesizer PRIVATE
    ../engine ../engine/include
    ../../upstream/AWE32Emu/AWE32Emu/src
    ../../upstream/AWE32Emu/AWE32Emu/src/86box/include
)
target_compile_features(125A_AWE_Synthesizer PRIVATE cxx_std_23)
smtg_target_configure_version_file(125A_AWE_Synthesizer)

if(WIN32)
  target_link_libraries(125A_AWE_Synthesizer PRIVATE comdlg32)
endif()
