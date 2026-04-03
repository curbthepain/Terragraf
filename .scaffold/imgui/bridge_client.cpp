/**
 * .scaffold/imgui/bridge_client.cpp
 * TCP bridge client implementation.
 *
 * Connects to bridge.py, sends/receives length-prefixed JSON.
 * Background thread handles recv; main thread polls dispatched messages.
 */

#ifdef _WIN32
  #ifndef WIN32_LEAN_AND_MEAN
    #define WIN32_LEAN_AND_MEAN
  #endif
  #include <winsock2.h>
  #include <ws2tcpip.h>
  #pragma comment(lib, "ws2_32.lib")
  using socket_t = SOCKET;
  static constexpr socket_t INVALID_SOCK = INVALID_SOCKET;
  #define SHUT_RDWR SD_BOTH
#else
  #include <sys/socket.h>
  #include <netinet/in.h>
  #include <arpa/inet.h>
  #include <unistd.h>
  #include <fcntl.h>
  #include <poll.h>
  using socket_t = int;
  static constexpr socket_t INVALID_SOCK = -1;
#endif

#include "bridge_client.h"

#include <cstring>
#include <cstdio>
#include <algorithm>

// ── Minimal JSON helpers (no external dependency) ─────────────────

// Find a top-level key in a JSON object string and return its value as string.
// Handles: "key": "value", "key": number, "key": true/false, "key": {...}, "key": [...]
static std::string json_extract(const std::string& json, const std::string& key) {
    std::string needle = "\"" + key + "\"";
    auto pos = json.find(needle);
    if (pos == std::string::npos) return "";

    // Skip past key and colon
    pos = json.find(':', pos + needle.size());
    if (pos == std::string::npos) return "";
    pos++;

    // Skip whitespace
    while (pos < json.size() && (json[pos] == ' ' || json[pos] == '\t' ||
           json[pos] == '\n' || json[pos] == '\r')) pos++;

    if (pos >= json.size()) return "";

    char c = json[pos];

    // String value
    if (c == '"') {
        auto end = pos + 1;
        while (end < json.size()) {
            if (json[end] == '\\') { end += 2; continue; }
            if (json[end] == '"') break;
            end++;
        }
        return json.substr(pos + 1, end - pos - 1);
    }

    // Object or array — find matching brace/bracket
    if (c == '{' || c == '[') {
        char open = c, close = (c == '{') ? '}' : ']';
        int depth = 1;
        auto end = pos + 1;
        bool in_str = false;
        while (end < json.size() && depth > 0) {
            if (json[end] == '\\' && in_str) { end += 2; continue; }
            if (json[end] == '"') in_str = !in_str;
            if (!in_str) {
                if (json[end] == open) depth++;
                if (json[end] == close) depth--;
            }
            end++;
        }
        return json.substr(pos, end - pos);
    }

    // Number, bool, null
    auto end = json.find_first_of(",}\n\r ", pos);
    if (end == std::string::npos) end = json.size();
    return json.substr(pos, end - pos);
}

// Extract from nested "data" object
static std::string json_data_extract(const std::string& json, const std::string& key) {
    std::string data_obj = json_extract(json, "data");
    if (data_obj.empty()) return "";
    return json_extract(data_obj, key);
}

// ── BridgeMsg ─────────────────────────────────────────────────────

std::string BridgeMsg::get_string(const std::string& key) const {
    return json_extract(raw_json, key);
}

double BridgeMsg::get_number(const std::string& key) const {
    std::string val = json_extract(raw_json, key);
    if (val.empty()) return 0.0;
    try { return std::stod(val); } catch (...) { return 0.0; }
}

bool BridgeMsg::get_bool(const std::string& key) const {
    return json_extract(raw_json, key) == "true";
}

std::string BridgeMsg::data_string(const std::string& key) const {
    return json_data_extract(raw_json, key);
}

double BridgeMsg::data_number(const std::string& key) const {
    std::string val = json_data_extract(raw_json, key);
    if (val.empty()) return 0.0;
    try { return std::stod(val); } catch (...) { return 0.0; }
}

// ── Platform init/cleanup ─────────────────────────────────────────

#ifdef _WIN32
struct WinsockInit {
    WinsockInit() { WSADATA d; WSAStartup(MAKEWORD(2,2), &d); }
    ~WinsockInit() { WSACleanup(); }
};
static WinsockInit _wsa_init;

static void close_socket(socket_t s) { closesocket(s); }
#else
static void close_socket(socket_t s) { close(s); }
#endif

// ── BridgeClient ──────────────────────────────────────────────────

BridgeClient::BridgeClient(const std::string& host, int port)
    : m_host(host), m_port(port) {}

BridgeClient::~BridgeClient() {
    disconnect();
}

bool BridgeClient::connect() {
    if (m_connected) return true;

    socket_t sock = ::socket(AF_INET, SOCK_STREAM, 0);
    if (sock == INVALID_SOCK) {
        fprintf(stderr, "[bridge] socket() failed\n");
        return false;
    }

    struct sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons((uint16_t)m_port);
    inet_pton(AF_INET, m_host.c_str(), &addr.sin_addr);

    if (::connect(sock, (struct sockaddr*)&addr, sizeof(addr)) != 0) {
        fprintf(stderr, "[bridge] connect to %s:%d failed\n",
                m_host.c_str(), m_port);
        close_socket(sock);
        return false;
    }

#ifdef _WIN32
    m_socket = (uintptr_t)sock;
#else
    m_socket = sock;
#endif

    m_connected = true;
    m_running = true;

    // Start background receive thread
    m_recv_thread = std::thread(&BridgeClient::recv_thread_func, this);

    fprintf(stderr, "[bridge] connected to %s:%d\n", m_host.c_str(), m_port);
    return true;
}

void BridgeClient::disconnect() {
    m_running = false;
    m_connected = false;

#ifdef _WIN32
    if (m_socket != ~(uintptr_t)0) {
        shutdown((SOCKET)m_socket, SHUT_RDWR);
        close_socket((SOCKET)m_socket);
        m_socket = ~(uintptr_t)0;
    }
#else
    if (m_socket >= 0) {
        shutdown(m_socket, SHUT_RDWR);
        close_socket(m_socket);
        m_socket = -1;
    }
#endif

    if (m_recv_thread.joinable()) {
        m_recv_thread.join();
    }
}

void BridgeClient::on(const std::string& msg_type, BridgeHandler handler) {
    m_handlers[msg_type] = handler;
}

void BridgeClient::send(const std::string& msg_type, const std::string& data_json) {
    std::string json;
    if (data_json.empty()) {
        json = "{\"type\": \"" + msg_type + "\"}";
    } else {
        json = "{\"type\": \"" + msg_type + "\", \"data\": " + data_json + "}";
    }
    send_raw(json);
}

void BridgeClient::poll() {
    std::vector<BridgeMsg> batch;
    {
        std::lock_guard<std::mutex> lock(m_queue_mutex);
        batch.swap(m_queue);
    }
    for (auto& msg : batch) {
        auto it = m_handlers.find(msg.type);
        if (it != m_handlers.end()) {
            it->second(msg);
        }
    }
}

// ── Private ───────────────────────────────────────────────────────

bool BridgeClient::send_raw(const std::string& json_str) {
    if (!m_connected) return false;

    uint32_t len = (uint32_t)json_str.size();
    uint8_t header[4];
    header[0] = (len >> 24) & 0xFF;
    header[1] = (len >> 16) & 0xFF;
    header[2] = (len >> 8) & 0xFF;
    header[3] = len & 0xFF;

#ifdef _WIN32
    auto sock = (SOCKET)m_socket;
    if (::send(sock, (const char*)header, 4, 0) != 4) return false;
    if (::send(sock, json_str.c_str(), (int)json_str.size(), 0) != (int)json_str.size()) return false;
#else
    if (::send(m_socket, header, 4, MSG_NOSIGNAL) != 4) return false;
    if (::send(m_socket, json_str.c_str(), json_str.size(), MSG_NOSIGNAL) != (ssize_t)json_str.size()) return false;
#endif
    return true;
}

std::string BridgeClient::recv_msg() {
    // Read 4-byte length header
    uint8_t header[4];
    size_t got = 0;

#ifdef _WIN32
    auto sock = (SOCKET)m_socket;
    while (got < 4) {
        int n = ::recv(sock, (char*)(header + got), (int)(4 - got), 0);
        if (n <= 0) return "";
        got += n;
    }
#else
    while (got < 4) {
        ssize_t n = ::recv(m_socket, header + got, 4 - got, 0);
        if (n <= 0) return "";
        got += n;
    }
#endif

    uint32_t len = ((uint32_t)header[0] << 24) |
                   ((uint32_t)header[1] << 16) |
                   ((uint32_t)header[2] << 8) |
                   (uint32_t)header[3];

    if (len == 0 || len > 16 * 1024 * 1024) return "";  // sanity: 16 MB max

    std::string payload(len, '\0');
    got = 0;
#ifdef _WIN32
    while (got < len) {
        int n = ::recv(sock, &payload[got], (int)(len - got), 0);
        if (n <= 0) return "";
        got += n;
    }
#else
    while (got < len) {
        ssize_t n = ::recv(m_socket, &payload[got], len - got, 0);
        if (n <= 0) return "";
        got += n;
    }
#endif

    return payload;
}

void BridgeClient::recv_thread_func() {
    while (m_running) {
        std::string json = recv_msg();
        if (json.empty()) {
            if (m_running) {
                fprintf(stderr, "[bridge] connection lost\n");
                m_connected = false;
            }
            break;
        }

        BridgeMsg msg;
        msg.raw_json = json;
        msg.type = json_extract(json, "type");

        {
            std::lock_guard<std::mutex> lock(m_queue_mutex);
            m_queue.push_back(std::move(msg));
        }
    }
}
