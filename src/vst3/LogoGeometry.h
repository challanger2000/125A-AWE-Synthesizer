#pragma once
// Geometry-only loader for the authoritative unchanged 125A vector master.
// Original asset: challanger2000/125A-Branding/125A_Logo_Master_FINAL.svg
// SVG uses *only* absolute M/L/Z path commands and even-odd fills.
// Preserve compound counters; never redraw the logo with replacement text.
#include <cmath>
#include <cstddef>
#include <fstream>
#include <iterator>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace AWE125 {
struct LogoCommand {
    char type='Z';
    double x=0,y=0;
};
struct LogoShape {
    bool red=false;
    std::vector<LogoCommand> commands;
};
class MasterLogoGeometry final {
public:
    const std::vector<LogoShape>& Shapes() const noexcept {return shapes_;}
    bool Load(const std::string& path,std::string& error) {
        std::ifstream in(path,std::ios::binary|std::ios::ate);
        if(!in) {error="125A master SVG missing";return false;}
        const auto sz=in.tellg();
        if(sz<100||sz>131072) {error="125A SVG size invalid";return false;}
        std::string svg(static_cast<size_t>(sz),'\0');
        in.seekg(0);
        if(!in.read(svg.data(),sz)) {error="125A SVG unreadable";return false;}
        if(svg.find("<svg")==std::string::npos||
           svg.find("viewBox=\"0 0 1774 887\"")==std::string::npos||
           svg.find("fill-rule=\"evenodd\"")==std::string::npos) {
            error="125A master SVG viewBox/fill rule changed";return false;
        }
        std::vector<LogoShape> candidate;
        size_t pos=0,commands=0;
        while((pos=svg.find("<path ",pos))!=std::string::npos) {
            const auto close=svg.find("/>",pos);
            if(close==std::string::npos||close-pos>32768) {
                error="125A SVG malformed path";return false;
            }
            const auto d=svg.find(" d=\"",pos);
            if(d==std::string::npos||d>=close) {
                error="125A path missing d";return false;
            }
            const auto q=svg.find('"',d+4);
            if(q==std::string::npos||q>=close) {
                error="125A path quote missing";return false;
            }
            const auto fill=svg.find(" fill=\"#",q+1);
            if(fill==std::string::npos||fill>=close) {
                error="125A SVG path has no fill";return false;
            }
            const auto color=svg.substr(fill+7,7);
            if(color!="#D9D9D9"&&color!="#D71920") {
                error="125A SVG color is not master palette";return false;
            }
            LogoShape shape;
            shape.red=color=="#D71920";
            std::istringstream text(svg.substr(d+4,q-(d+4)));
            char command;
            while(text>>command) {
                if(command=='M'||command=='L') {
                    double x,y;
                    if(!(text>>x>>y)||!std::isfinite(x)||!std::isfinite(y)||
                       x<0||x>1774||y<0||y>887) {
                        error="125A SVG point out of bounds";return false;
                    }
                    shape.commands.push_back({command,x,y});
                } else if(command=='Z')shape.commands.push_back({command,0,0});
                else {error="125A SVG contains unsupported path verb";return false;}
                if(++commands>5000) {
                    error="125A SVG path complexity exceeds safety bound";return false;
                }
            }
            if(shape.commands.empty()||shape.commands.front().type!='M') {
                error="125A empty or invalid compound path";return false;
            }
            candidate.push_back(std::move(shape));
            pos=close+2;
        }
        if(candidate.size()!=30||commands<2700||!candidate.back().red) {
            error="125A SVG does not match authoritative 30-path master";return false;
        }
        shapes_=std::move(candidate);
        error.clear();
        return true;
    }
private:
    std::vector<LogoShape> shapes_;
};
} // namespace AWE125
