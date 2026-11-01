set(target 125A_AWE_Synthesizer)
smtg_add_vst3plugin(125A_AWE_Synthesizer Factory.cpp AssetState.h AssetConfig.h)
target_link_libraries(125A_AWE_Synthesizer PRIVATE sdk vstgui_support awe32_chip_safety awe32_opl3_midi)
smtg_target_add_plugin_resources(125A_AWE_Synthesizer
  RESOURCES resource/awe_test_panel.uidesc
)
target_include_directories(125A_AWE_Synthesizer PRIVATE
    ../engine ../engine/include
    ../../upstream/AWE32Emu/AWE32Emu/src
    ../../upstream/AWE32Emu/AWE32Emu/src/86box/include
)
target_compile_features(125A_AWE_Synthesizer PRIVATE cxx_std_23)
smtg_target_configure_version_file(125A_AWE_Synthesizer)
