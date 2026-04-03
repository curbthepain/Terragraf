/**
 * .scaffold/imgui/bridge_client.h
 * C++ TCP client for the Python bridge (bridge.py).
 *
 * Protocol: [4 bytes big-endian length][JSON payload]
 * Connects to localhost:9876, sends/receives JSON messages.
 * Runs a background receive thread; dispatches to registered handlers.
 */

#pragma once

#include <string>
#include <functional>
#include <unordered_map>
#include <vector>
#include <mutex>
#include <thread>
#include <atomic>
#include <cstdint>

/**
 * Lightweight JSON value — enough for bridge messages.
 * Not a full JSON parser; handles the subset bridge.py produces:
 * strings, numbers, bools, arrays, objects (nested).
 */
struct BridgeMsg {
    std::string type;
    std::string raw_json;  // full message as raw JSON string

    // Convenience accessors for common patterns
    std::string get_string(const std::string& key) const;
    double get_number(const std::string& key) const;
    bool get_bool(const std::string& key) const;

    // Access nested "data" object fields
    std::string data_string(const std::string& key) const;
    double data_number(const std::string& key) const;
};

using BridgeHandler = std::function<void(const BridgeMsg&)>;

class BridgeClient {
public:
    BridgeClient(const std::string& host = "127.0.0.1", int port = 9876);
    ~BridgeClient();

    // Connect to bridge.py server. Returns true on success.
    bool connect();

    // Disconnect and stop receive thread.
    void disconnect();

    // Is the connection alive?
    bool is_connected() const { return m_connected.load(); }

    // Register a handler for a message type.
    void on(const std::string& msg_type, BridgeHandler handler);

    // Send a JSON message. data_json is the inner JSON for "data" field.
    // If data_json is empty, sends {"type": "<msg_type>"}.
    void send(const std::string& msg_type, const std::string& data_json = "");

    // Process queued messages on the main thread (call each frame).
    void poll();

private:
    void recv_thread_func();
    bool send_raw(const std::string& json_str);
    std::string recv_msg();

    std::string m_host;
    int m_port;

#ifdef _WIN32
    uintptr_t m_socket = ~(uintptr_t)0;  // INVALID_SOCKET
#else
    int m_socket = -1;
#endif

    std::atomic<bool> m_connected{false};
    std::atomic<bool> m_running{false};
    std::thread m_recv_thread;

    // Handler registry
    std::unordered_map<std::string, BridgeHandler> m_handlers;

    // Thread-safe message queue (recv thread pushes, main thread polls)
    std::mutex m_queue_mutex;
    std::vector<BridgeMsg> m_queue;
};
