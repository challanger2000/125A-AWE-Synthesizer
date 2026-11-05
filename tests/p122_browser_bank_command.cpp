#include "BrowserBankCommand.h"
#include "BankOrder.h"
#include "MidiLiveState.h"
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
    // P126: global bank chronology must be shared by ordinary host edits,
    // browser notify and recalls, not inferred from a browser-only command.
    AWE125::BankOrder ordered;
    const uint64_t earlyRecall=ordered.BeginRecall();
    const uint64_t lateAudio=ordered.PublishAudio(5);
    ordered.CommitRecall(earlyRecall,0);
    auto bankChoice=ordered.Latest();
    ok&=check(bankChoice.bank==5&&bankChoice.sequence==lateAudio,
              "earlier slow recall cannot overwrite later host parameter bank 5");
    const uint64_t laterRecall=ordered.BeginRecall();
    ordered.CommitRecall(laterRecall,0);
    bankChoice=ordered.Latest();
    ok&=check(bankChoice.bank==0&&bankChoice.sequence==laterRecall,
              "newer project recall beats older host parameter bank 5");
    ordered.PublishBrowser(7);
    bankChoice=ordered.Latest();
    ok&=check(bankChoice.bank==7,"browser notify supplies latest global bank");
    const uint64_t precedingBrowser=ordered.BeginRecall();
    ordered.PublishBrowser(9);
    ordered.CommitRecall(precedingBrowser,0);
    ok&=check(ordered.Latest().bank==9,
              "later browser bank 9 wins despite slow recall commit");
    // P127 F01: completed newer recall must not be replaced by an older
    // recall whose stream read was delayed before the control epoch snapshot.
    AWE125::BankOrder overlappingRecalls;
    const uint64_t oldProject=overlappingRecalls.BeginRecall();
    const uint64_t newProject=overlappingRecalls.BeginRecall();
    ok&=check(overlappingRecalls.CommitRecall(newProject,5) &&
              overlappingRecalls.LatestRecall().bank==5 &&
              !overlappingRecalls.CommitRecall(oldProject,0) &&
              overlappingRecalls.LatestRecall().sequence==newProject &&
              overlappingRecalls.Latest().bank==5,
              "P127 old delayed recall cannot publish over completed newer recall");
    // P127 F02: rereading the authoritative choice after acquiring the
    // state-writer gate is essential. Reading before the gate is stale.
    AWE125::BankOrder pendingBeforeGate;
    pendingBeforeGate.PublishBrowser(5);
    const auto staleChoice=pendingBeforeGate.Latest();
    const uint64_t laterProject=pendingBeforeGate.BeginRecall();
    ok&=check(pendingBeforeGate.CommitRecall(laterProject,0) &&
              staleChoice.bank==5 &&
              pendingBeforeGate.Latest().bank==0 &&
              pendingBeforeGate.Latest().sequence>staleChoice.sequence,
              "P127 pending bank must be revalidated after a newer recall");
    // MIDI CC0/CC32 is channel-local: neither is allowed to acknowledge or
    // overwrite the latest global browser selection.
    AWE125::MidiLiveState midi;
    struct BankReceiver {
        std::array<int,16> cc0{};
        std::array<int,16> cc32{};
        void ControlChange(uint8_t ch,uint8_t cc,uint8_t val) {
            if(cc==0)cc0[ch]=val;
            if(cc==32)cc32[ch]=val;
        }
    } receiver;
    const uint64_t beforeBrowser=ordered.Next();
    midi.AcceptBank(2,0,5.0/127.0,beforeBrowser);
    const uint64_t browserClock=ordered.Next();
    midi.BrowserBankSelected(browserClock);
    const uint64_t laterChannel=ordered.Next();
    midi.AcceptBank(7,0,11.0/127.0,laterChannel);
    midi.AcceptBank(7,32,3.0/127.0,ordered.Next());
    midi.ReplayNewerBankControls(receiver,browserClock);
    ok&=check(receiver.cc0[2]==0&&receiver.cc0[7]==11&&
              receiver.cc32[7]==3&&receiver.cc0[1]==0,
              "newer channel-8 CC bank survives while old channel-3 CC clears");
    midi.BrowserBankSelected(ordered.Next());
    BankReceiver cleared;
    midi.ReplayNewerBankControls(cleared,ordered.Latest().sequence);
    ok&=check(cleared.cc0[7]==0&&cleared.cc32[7]==0,
              "later global selection invalidates only older MIDI bank touch");
    std::cout<<(ok?"P122_BROWSER_BANK_COMMAND_PASS":"P122_BROWSER_BANK_COMMAND_FAIL")<<"\n";
    return ok?0:1;
}
