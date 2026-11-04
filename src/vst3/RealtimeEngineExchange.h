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

// P120: one or more concurrent realtime readers per processor instance.
// Publish is serialized by the caller's control mutex; read never takes a
// mutex, allocates or destroys an engine. Retired engines are collected on
// a dedicated NON-audio maintenance thread only when ALL readers have
// completed. The seq_cst acquire-before-pointer-load avoids reclaim races.
// Four retained generations max:
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
            owner_->readers_.fetch_add(1,std::memory_order_seq_cst);
            ptr_=owner_->active_.load(std::memory_order_seq_cst);
        }
        Guard(const Guard&)=delete;
        Guard& operator=(const Guard&)=delete;
        Guard(Guard&&)=delete;
        ~Guard() {
            // Only atomic decrement, no free/lock/notification on audio thread.
            owner_->readers_.fetch_sub(1,std::memory_order_seq_cst);
        }
        T* get() const noexcept {return ptr_;}
        T* operator->() const noexcept {return ptr_;}
        explicit operator bool() const noexcept {return ptr_!=nullptr;}
    private:
        RealtimeEngineExchange* owner_;
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
            retired_.emplace_back(old);
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
    // Protected by mutex_, NOT called from the audio callback.
    void CollectLocked() {
        if(readers_.load(std::memory_order_seq_cst)==0 && !retired_.empty()) {
            retired_.clear();
            changed_.notify_all();
        }
    }
    void CollectLoop() {
        std::unique_lock<std::mutex> lock(mutex_);
        while(!stopping_) {
            changed_.wait_for(lock,std::chrono::milliseconds(10));
            CollectLocked();
        }
    }
    std::atomic<T*> active_{nullptr};
    std::atomic<unsigned> readers_{0};
    mutable std::mutex mutex_;
    std::condition_variable changed_;
    std::vector<std::unique_ptr<T>> retired_;
    std::thread collector_;
    bool stopping_=false;
};
}
