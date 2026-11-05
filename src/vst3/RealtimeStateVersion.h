#pragma once
#include <atomic>
#include <cstdint>
#include <thread>

namespace AWE125 {
// One RT writer or one control/recall writer may mutate the persisted parameter
// tuple at a time. The RT writer makes ONE try-lock CAS: never waits, spins,
// yields or allocates. A simultaneous project recall wins over a conflicting
// RT parameter transaction. The control thread may wait for a short RT write,
// but never holds the gate across ROM loading or host IBStream operations.
class RealtimeStateVersion {
public:
    enum class Domain { Audio, Control };
    struct Stamp { uint64_t generation; uint32_t owner; };
    class Writer {
    public:
        Writer(RealtimeStateVersion& state, Domain domain,
               bool tracked = true) noexcept : state_(state) {
            if (!tracked) return;
            if (domain == Domain::Audio) {
                // A waiting control recall takes priority; the audio callback
                // must not spin while it is preparing a new project state.
                if (state_.controlWaiting_.load(std::memory_order_acquire)) {
                    allowed_ = false;
                    return;
                }
                uint32_t free = 0;
                if (!state_.owner_.compare_exchange_strong(
                        free, 1u, std::memory_order_acq_rel,
                        std::memory_order_relaxed)) {
                    allowed_ = false;
                    return;
                }
            } else {
                state_.controlWaiting_.fetch_add(1, std::memory_order_acq_rel);
                uint32_t free = 0;
                while (!state_.owner_.compare_exchange_weak(
                            free, 2u, std::memory_order_acq_rel,
                            std::memory_order_relaxed)) {
                    free = 0;
                    std::this_thread::yield(); // control thread ONLY
                }
                state_.controlWaiting_.fetch_sub(1, std::memory_order_acq_rel);
            }
            owns_ = true;
            state_.epoch_.fetch_add(1, std::memory_order_seq_cst);
        }
        ~Writer() {
            if (!owns_) return;
            state_.epoch_.fetch_add(1, std::memory_order_seq_cst);
            state_.owner_.store(0, std::memory_order_release);
        }
        Writer(const Writer&) = delete;
        Writer& operator=(const Writer&) = delete;
        explicit operator bool() const noexcept { return allowed_; }
    private:
        RealtimeStateVersion& state_;
        bool owns_ = false;
        bool allowed_ = true;
    };

    Stamp Capture() const noexcept {
        return {epoch_.load(std::memory_order_seq_cst),
                owner_.load(std::memory_order_seq_cst)};
    }
    bool Readable(Stamp stamp) const noexcept {
        return !(stamp.generation & 1u) && stamp.owner == 0;
    }
    bool Unchanged(Stamp before) const noexcept {
        const auto after = Capture();
        return Readable(before) && Readable(after) &&
               after.generation == before.generation;
    }
private:
    std::atomic<uint64_t> epoch_{0};
    std::atomic<uint32_t> owner_{0};
    std::atomic<uint32_t> controlWaiting_{0};
};
} // namespace AWE125
