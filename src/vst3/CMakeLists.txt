set(target 125A_AWE_Synthesizer)
smtg_add_vst3plugin(125A_AWE_Synthesizer Factory.cpp)
target_link_libraries(125A_AWE_Synthesizer PRIVATE sdk awe32_chip_safety)
target_include_directories(125A_AWE_Synthesizer PRIVATE
    ../engine ../engine/include
    ../../upstream/AWE32Emu/AWE32Emu/src
    ../../upstream/AWE32Emu/AWE32Emu/src/86box/include
)
target_compile_features(125A_AWE_Synthesizer PRIVATE cxx_std_23)
smtg_target_configure_version_file(125A_AWE_Synthesizer)
