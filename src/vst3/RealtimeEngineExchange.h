#pragma once
#include <algorithm>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <memory>
#include <mutex>
#include <thread>
#include <utility>
#include <vector>

// P120: one serialized realtime reader per VST3 processor instance.
// Publish is serialized by the caller's control mutex; read never takes a
// mutex, allocates or destroys an engine. Retired engines are collected on
// a dedicated NON-audio maintenance thread after the last reader which
// could have observed each engine finishes. Four retained generations max:
// backpressure affects only Publish/control threads, never audio processing.
namespace AWE125 {
template<class T>
class RealtimeEngineExchange {
public:
    static constexpr std::size_t kRetiredLimit=4;
    class Guard {
    public:
        explicit Guard(RealtimeEngineExchange& owner) noexcept
            : owner_(&owner) {
            // Registration MUST precede load of active_ in the global SC order.
            generation_=owner_->entered_.fetch_add(1,std::memory_order_seq_cst)+1;
            ptr_=owner_->active_.load(std::memory_order_seq_cst);
        }
        Guard(const Guard&)=delete;
        Guard& operator=(const Guard&)=delete;
        Guard(Guard&&)=delete;
        ~Guard() {
            // Single-reader contract: completions are in registration order.
            // The audio callback performs only this atomic store, NO notify.
            owner_->finished_.store(generation_,std::memory_order_seq_cst);
        }
        T* get() const noexcept {return ptr_;}
        T* operator->() const noexcept {return ptr_;}
        explicit operator bool() const noexcept {return ptr_!=nullptr;}
    private:
        RealtimeEngineExchange* owner_;
        std::uint64_t generation_=0;
        T* ptr_=nullptr;
    };
    RealtimeEngineExchange()=default;
    RealtimeEngineExchange(const RealtimeEngineExchange&)=delete;
    RealtimeEngineExchange& operator=(const RealtimeEngineExchange&)=delete;
    ~RealtimeEngineExchange() {
        // Host contract: terminate all process callbacks before destruction.
        {
            std::lock_guard<std::mutex> lock(mutex_);
            stopping_=true;
        }
        changed_.notify_all();
        if(collector_.joinable())collector_.join();
        delete active_.exchange(nullptr,std::memory_order_seq_cst);
        std::lock_guard<std::mutex> lock(mutex_);
        retired_.clear(); // always on a control/teardown thread
    }
    [[nodiscard]] Guard Read() noexcept {return Guard(*this);}

    void Publish(std::unique_ptr<T> next) {
        // Only non-realtime callers may publish (serialized by owning Processor).
        // Advance the active pointer in a single atomic transaction.
        std::unique_lock<std::mutex> lock(mutex_);
        if(!retired_.empty())CollectLocked();
        // Strict memory bound, even when a live audio callback is stalled:
        // wait on this CONTROL thread until the oldest generation is safe.
        while(retired_.size()>=kRetiredLimit) {
            changed_.wait_for(lock,std::chrono::milliseconds(10));
            CollectLocked();
        }
        T* const old=active_.exchange(next.release(),std::memory_order_seq_cst);
        if(old) {
            const auto barrier=entered_.load(std::memory_order_seq_cst);
            retired_.push_back({std::unique_ptr<T>(old),barrier});
            if(!collector_.joinable())
                collector_=std::thread([this]{CollectLoop();});
        }
        CollectLocked();
        lock.unlock();
        changed_.notify_one();
    }
    // Explicit collection remains available to non-realtime test/control code.
    void Collect() {
        std::lock_guard<std::mutex> lock(mutex_);
        CollectLocked();
    }
    std::size_t RetiredCountForTest() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return retired_.size();
    }
private:
    struct Retired {
        std::unique_ptr<T> object;
        std::uint64_t lastPotentialReader=0;
    };
    // Protected by mutex_, NOT called from the audio callback.
    void CollectLocked() {
        const auto complete=finished_.load(std::memory_order_seq_cst);
        const auto oldSize=retired_.size();
        std::erase_if(retired_,[&](const Retired& r) {
            return r.lastPotentialReader<=complete;
        });
        if(oldSize!=retired_.size())changed_.notify_all();
    }
    void CollectLoop() {
        std::unique_lock<std::mutex> lock(mutex_);
        while(!stopping_) {
            changed_.wait_for(lock,std::chrono::milliseconds(10));
            CollectLocked();
        }
    }
    std::atomic<T*> active_{nullptr};
    std::atomic<std::uint64_t> entered_{0},finished_{0};
    mutable std::mutex mutex_;
    std::condition_variable changed_;
    std::vector<Retired> retired_;
    std::thread collector_;
    bool stopping_=false;
};
}
