#pragma once
#include <algorithm>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <memory>
#include <mutex>
#include <thread>
#include <utility>
#include <vector>

// P120: control-side publication and engine destruction, realtime-side reads.
// Readers never lock, allocate, wait, or delete an engine. Each published
// envelope keeps its own reader count, so a busy NEW engine cannot delay
// retirement of an unrelated OLD engine. A short global registration window
// protects the interval between loading an envelope pointer and pinning it.
// Both operations use seq_cst for unambiguous publication/reclamation order.
// Publish/Collect are NON-realtime operations and must be serialized by the
// caller's control lock. Retained generations are strictly bounded by 4.
namespace AWE125 {
template<class T>
class RealtimeEngineExchange {
    struct Envelope {
        explicit Envelope(std::unique_ptr<T> value) : object(std::move(value)) {}
        std::unique_ptr<T> object;
        std::atomic<unsigned> readers{0};
    };
public:
    static constexpr std::size_t kRetiredLimit=4;
    class Guard {
    public:
        explicit Guard(RealtimeEngineExchange& owner) noexcept
            : owner_(&owner) {
            // Collector cannot reclaim any retired envelope while a reader
            // is between reading active_ and incrementing its own pin.
            owner_->registering_.fetch_add(1,std::memory_order_seq_cst);
            envelope_=owner_->active_.load(std::memory_order_seq_cst);
            if(envelope_)
                envelope_->readers.fetch_add(1,std::memory_order_seq_cst);
            owner_->registering_.fetch_sub(1,std::memory_order_seq_cst);
        }
        Guard(const Guard&)=delete;
        Guard& operator=(const Guard&)=delete;
        Guard(Guard&&)=delete;
        Guard& operator=(Guard&&)=delete;
        ~Guard() {
            if(envelope_)
                envelope_->readers.fetch_sub(1,std::memory_order_seq_cst);
            // No mutex, destructor, notification, or memory allocation here.
        }
        T* get() const noexcept {
            return envelope_ ? envelope_->object.get() : nullptr;
        }
        T* operator->() const noexcept {return get();}
        explicit operator bool() const noexcept {return get()!=nullptr;}
    private:
        RealtimeEngineExchange* owner_;
        Envelope* envelope_=nullptr;
    };
    RealtimeEngineExchange()=default;
    RealtimeEngineExchange(const RealtimeEngineExchange&)=delete;
    RealtimeEngineExchange& operator=(const RealtimeEngineExchange&)=delete;
    ~RealtimeEngineExchange() {
        // Host must stop all process callbacks before destroying its instance.
        {
            std::lock_guard<std::mutex> lock(mutex_);
            stopping_=true;
        }
        changed_.notify_all();
        if(collector_.joinable())collector_.join();
        delete active_.exchange(nullptr,std::memory_order_seq_cst);
        std::lock_guard<std::mutex> lock(mutex_);
        retired_.clear();
    }
    [[nodiscard]] Guard Read() noexcept {return Guard(*this);}

    void Publish(std::unique_ptr<T> next) {
        // Construct the envelope on the control thread, before publication.
        auto replacement=next ? std::make_unique<Envelope>(std::move(next))
                              : std::unique_ptr<Envelope>{};
        std::unique_lock<std::mutex> lock(mutex_);
        CollectLocked();
        while(retired_.size()>=kRetiredLimit) {
            changed_.wait_for(lock,std::chrono::milliseconds(10));
            CollectLocked();
        }
        Envelope* old=active_.exchange(replacement.release(),
                                       std::memory_order_seq_cst);
        if(old) {
            retired_.emplace_back(old);
            if(!collector_.joinable())
                collector_=std::thread([this]{CollectLoop();});
        }
        CollectLocked();
        lock.unlock();
        changed_.notify_one();
    }
    void Collect() {
        std::lock_guard<std::mutex> lock(mutex_);
        CollectLocked();
    }
    std::size_t RetiredCountForTest() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return retired_.size();
    }
private:
    // Called ONLY while holding mutex_ and never from the audio callback.
    void CollectLocked() {
        // A registering reader may have obtained the old active_ pointer
        // before Publish(), but not yet incremented that envelope's count.
        // Once the registration window is empty, each such reader either
        // has an individual pin or has already left its guard.
        if(registering_.load(std::memory_order_seq_cst)!=0)return;
        const std::size_t before=retired_.size();
        std::erase_if(retired_,[](const std::unique_ptr<Envelope>& item) {
            return item->readers.load(std::memory_order_seq_cst)==0;
        });
        if(retired_.size()!=before)changed_.notify_all();
    }
    void CollectLoop() {
        std::unique_lock<std::mutex> lock(mutex_);
        while(!stopping_) {
            changed_.wait_for(lock,std::chrono::milliseconds(10));
            CollectLocked();
        }
    }
    std::atomic<Envelope*> active_{nullptr};
    std::atomic<unsigned> registering_{0};
    mutable std::mutex mutex_;
    std::condition_variable changed_;
    std::vector<std::unique_ptr<Envelope>> retired_;
    std::thread collector_;
    bool stopping_=false;
};
}
