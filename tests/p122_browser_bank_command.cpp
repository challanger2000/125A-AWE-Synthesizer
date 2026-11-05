#include "BrowserBankCommand.h"
#include "RealtimeStateVersion.h"
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
    // Old recall must not override an accepted NEWER bank selection.
    const uint64_t oldRecall=command.Snapshot();
    ok&=check(command.Publish(5),"new browser bank 5 is accepted");
    uint64_t stale=oldRecall;
    ok&=check(!command.PublishRecallIfUnchanged(stale,0) &&
              uint16_t(stale&0xFFFFu)==5,
              "old recall cannot overwrite newer accepted bank 5");
    ok&=check(command.Consume(seen,bank)&&bank==5,
              "later accepted bank survives and is consumed exactly once");
    // Conversely, a recall started AFTER an old queued selection must
    // intentionally supersede that old selection.
    ok&=check(command.Publish(7),"queue old bank 7");
    uint64_t freshRecall=command.Snapshot();
    ok&=check(command.PublishRecallIfUnchanged(freshRecall,0) &&
              command.Consume(seen,bank)&&bank==0,
              "new recall replaces only the command visible at its start");
    // A temporarily busy recall writer MUST NOT cause the audio callback
    // to acknowledge-and-drop a waiting GUI bank command.
    AWE125::RealtimeStateVersion version;
    ok&=check(command.Publish(5),"queue bank 5 before recall contention");
    {
        AWE125::RealtimeStateVersion::Writer control(
            version,AWE125::RealtimeStateVersion::Domain::Control);
        AWE125::RealtimeStateVersion::Writer rt(
            version,AWE125::RealtimeStateVersion::Domain::Audio);
        ok&=check(!bool(rt)&&command.HasPending(seen),
                  "busy recall rejects RT writer but retains pending command");
    }
    {
        AWE125::RealtimeStateVersion::Writer rt(
            version,AWE125::RealtimeStateVersion::Domain::Audio);
        ok&=check(bool(rt)&&command.Consume(seen,bank)&&bank==5,
                  "next available audio block applies retained bank 5");
    }
    std::cout<<(ok?"P122_BROWSER_BANK_COMMAND_PASS":"P122_BROWSER_BANK_COMMAND_FAIL")<<"\n";
    return ok?0:1;
}
