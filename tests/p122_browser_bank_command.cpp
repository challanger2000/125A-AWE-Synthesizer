#include "BrowserBankCommand.h"
#include <array>
#include <cstdint>
#include <iostream>
#include <thread>
using AWE125::BrowserBankCommand;
static bool check(bool condition,const char* label) {
    std::cout<<(condition?"PASS: ":"FAIL: ")<<label<<"\n";
    return condition;
}
int main() {
    BrowserBankCommand command;
    uint64_t seen=0;
    uint16_t bank=999;
    bool ok=true;
    ok&=check(!command.Consume(seen,bank),"initially no pending reselect");
    ok&=check(!command.Publish(16384),"invalid 14-bit bank rejected");
    ok&=check(!command.Consume(seen,bank),"invalid bank did not publish");
    ok&=check(command.Publish(128)&&command.Consume(seen,bank)&&bank==128,
              "first browser selection delivered");
    ok&=check(!command.Consume(seen,bank),"consumed exactly once");
    ok&=check(command.Publish(128)&&command.Consume(seen,bank)&&bank==128,
              "same bank selected again is a distinct event");
    ok&=check(command.Publish(0)&&command.Publish(16383)&&
              command.Consume(seen,bank)&&bank==16383,
              "latest queued reselect wins, full bank range accepted");
    std::thread producer([&]{
        for(unsigned i=0;i<6000;++i)command.Publish(i%16384u);
    });
    producer.join();
    ok&=check(command.Publish(321)&&command.Consume(seen,bank)&&bank==321,
              "concurrent production retains last explicit bank");
    ok&=check(!command.Consume(seen,bank),
              "no extra event after concurrent production");
    std::cout<<(ok?"P122_BROWSER_BANK_COMMAND_PASS":"P122_BROWSER_BANK_COMMAND_FAIL")<<"\n";
    return ok?0:1;
}
