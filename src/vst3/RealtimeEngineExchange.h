#pragma once
#include <atomic>
#include <memory>
#include <utility>
#include <vector>
// P119: one audio reader (VST3 process, serialized per plugin instance) and
// one non-realtime control writer. The read guard never waits, allocates or
// takes a lock. Published engines remain alive until every active read guard
// has exited, and destruction happens ONLY on a control thread.
// Publish/Collect must be externally serialized (Processor::engineMutex_).
namespace AWE125 {
template<class T>
class RealtimeEngineExchange {
public:
    class Guard {
    public:
        explicit Guard(RealtimeEngineExchange& owner) noexcept : owner_(&owner) {
            owner_->readers_.fetch_add(1,std::memory_order_acq_rel);
            ptr_=owner_->active_.load(std::memory_order_acquire);
        }
        Guard(const Guard&)=delete;
        Guard& operator=(const Guard&)=delete;
        Guard(Guard&&)=delete;
        ~Guard() {
            owner_->readers_.fetch_sub(1,std::memory_order_acq_rel);
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
    // Contract: the owning host has stopped callbacks before destruction.
    ~RealtimeEngineExchange() { 
        delete active_.exchange(nullptr,std::memory_order_acq_rel);
    }
    [[nodiscard]] Guard Read() noexcept {return Guard(*this);}
    void Publish(std::unique_ptr<T> next) {
        T* const raw=next.release();
        T* const old=active_.exchange(raw,std::memory_order_acq_rel);
        if(old)retired_.emplace_back(old);
        Collect();
    }
    void Collect() {
        if(readers_.load(std::memory_order_acquire)==0)retired_.clear();
    }
    std::size_t RetiredCountForTest() const noexcept {return retired_.size();}
private:
    std::atomic<T*> active_{nullptr};
    std::atomic<unsigned> readers_{0};
    std::vector<std::unique_ptr<T>> retired_;
};
}
