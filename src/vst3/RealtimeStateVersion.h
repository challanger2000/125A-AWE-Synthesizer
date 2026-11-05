#pragma once
#include <atomic>
#include <cstdint>

namespace AWE125 {
// Nonblocking multi-parameter snapshot epochs. Audio and control writes
// have distinct single-writer counters, so their epochs cannot cancel each
// other if project recall overlaps the render callback. All payload fields
// protected by these epochs are themselves atomics.
class RealtimeStateVersion {
public:
    struct Stamp {uint64_t audio, control;};
    class Writer {
    public:
        explicit Writer(std::atomic<uint64_t>& epoch) noexcept : epoch_(epoch) {
            epoch_.fetch_add(1,std::memory_order_seq_cst);
        }
        ~Writer() {epoch_.fetch_add(1,std::memory_order_seq_cst);}
        Writer(const Writer&)=delete;
        Writer& operator=(const Writer&)=delete;
    private:
        std::atomic<uint64_t>& epoch_;
    };
    std::atomic<uint64_t>& Audio() noexcept {return audio_;}
    std::atomic<uint64_t>& Control() noexcept {return control_;}
    Stamp Capture() const noexcept {
        return {audio_.load(std::memory_order_seq_cst),
                control_.load(std::memory_order_seq_cst)};
    }
    bool Readable(Stamp before) const noexcept {
        return !(before.audio&1u) && !(before.control&1u);
    }
    bool Unchanged(Stamp before) const noexcept {
        const auto after=Capture();
        return Readable(before) &&
            after.audio==before.audio && after.control==before.control;
    }
private:
    std::atomic<uint64_t> audio_{0},control_{0};
};
} // namespace AWE125
