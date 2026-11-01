#include "LogoGeometry.h"
#include <iostream>
#include <string>
using namespace AWE125;
int main(int argc,char** argv) {
    if(argc!=2)return 2;
    MasterLogoGeometry logo;
    std::string error;
    if(!logo.Load(argv[1],error)) {
        std::cerr<<"FAIL: original logo could not parse: "<<error<<"\n";
        return 1;
    }
    size_t commands=0,red=0,silver=0,holes=0;
    for(const auto& s:logo.Shapes()) {
        commands+=s.commands.size();
        if(s.red)++red;else ++silver;
        size_t moves=0;
        for(const auto& c:s.commands)if(c.type=='M')++moves;
        if(moves>1)++holes;
    }
    bool ok=logo.Shapes().size()==30&&red==1&&silver==29&&
            commands>2750&&holes>=2;
    std::cout<<(ok?"PASS: ":"FAIL: ")
             <<"exact 30-part master, 29 silver + red A, compound paths="
             <<holes<<", commands="<<commands<<"\n";
    std::cout<<"NOT RUN: pixel-perfect GUI appearance, Win32 zoom, Studio One\n";
    return ok?0:1;
}
