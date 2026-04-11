/**
 * .scaffold/compute/vulkan/layer.cpp
 * Vulkan layer scaffold — intercept API calls between app and driver.
 *
 * A Vulkan layer sits between the application and the Vulkan driver.
 * It can intercept, validate, profile, debug, or modify any Vulkan call.
 *
 * This is the Terragraf scaffold for building custom Vulkan layers.
 *
 * Layer architecture:
 *   App → [Your Layer] → [Other Layers] → Driver
 *
 * Build as a shared library (.so on Android/Linux, .dll on Windows).
 */

#pragma once

#include <vulkan/vulkan.h>
#include <vulkan/vk_layer.h>
#include <string>
#include <unordered_map>
#include <mutex>

namespace scaffold::vulkan::layer {

// ─── Layer Metadata ─────────────────────────────────────────────────

constexpr const char* LAYER_NAME = "VK_LAYER_KOHALA_scaffold";
constexpr const char* LAYER_DESC = "Terragraf scaffold Vulkan layer";
constexpr uint32_t LAYER_IMPL_VERSION = 1;
constexpr uint32_t LAYER_SPEC_VERSION = VK_API_VERSION_1_3;

// ─── Dispatch Table ─────────────────────────────────────────────────
// Maps VkDevice/VkInstance to their dispatch tables so intercepted
// functions can call down to the next layer.

struct InstanceDispatch {
    PFN_vkGetInstanceProcAddr GetInstanceProcAddr;
    PFN_vkDestroyInstance DestroyInstance;
    PFN_vkEnumeratePhysicalDevices EnumeratePhysicalDevices;
    // Add more intercepted instance functions here
};

struct DeviceDispatch {
    PFN_vkGetDeviceProcAddr GetDeviceProcAddr;
    PFN_vkDestroyDevice DestroyDevice;
    PFN_vkQueueSubmit QueueSubmit;
    PFN_vkCmdDispatch CmdDispatch;
    // Add more intercepted device functions here
};

// Thread-safe dispatch table storage
inline std::mutex g_mutex;
inline std::unordered_map<void*, InstanceDispatch> g_instance_dispatch;
inline std::unordered_map<void*, DeviceDispatch> g_device_dispatch;

// ─── Helper: Get dispatch key ───────────────────────────────────────
// Vulkan dispatchable handles have the loader's dispatch table pointer
// as their first member. This is how layers chain.

inline void* get_dispatch_key(void* handle) {
    return *reinterpret_cast<void**>(handle);
}

// ─── Intercepted Functions ──────────────────────────────────────────
// Override these to add your layer's behavior.
// Call the next layer's function via the dispatch table.

/**
 * Example: intercept vkQueueSubmit to profile GPU work.
 */
/*
VKAPI_ATTR VkResult VKAPI_CALL layer_QueueSubmit(
    VkQueue queue, uint32_t submitCount,
    const VkSubmitInfo* pSubmits, VkFence fence
) {
    // PRE: Before the call reaches the driver
    // ... your profiling/validation/modification code ...

    // CHAIN: Call the next layer
    auto key = get_dispatch_key(queue);
    auto& dispatch = g_device_dispatch[key];
    VkResult result = dispatch.QueueSubmit(queue, submitCount, pSubmits, fence);

    // POST: After the driver returns
    // ... your logging/analysis code ...

    return result;
}
*/

/**
 * Example: intercept vkCmdDispatch to log compute shader dispatches.
 */
/*
VKAPI_ATTR void VKAPI_CALL layer_CmdDispatch(
    VkCommandBuffer commandBuffer,
    uint32_t groupCountX, uint32_t groupCountY, uint32_t groupCountZ
) {
    // Log the dispatch
    // printf("Compute dispatch: %u x %u x %u\n", groupCountX, groupCountY, groupCountZ);

    auto key = get_dispatch_key(commandBuffer);
    auto& dispatch = g_device_dispatch[key];
    dispatch.CmdDispatch(commandBuffer, groupCountX, groupCountY, groupCountZ);
}
*/

// ─── Layer Entry Points ─────────────────────────────────────────────
// These are required for the Vulkan loader to recognize this as a layer.

// vkGetInstanceProcAddr — the loader calls this to get function pointers
// vkGetDeviceProcAddr   — same, for device-level functions
// vkNegotiateLoaderLayerInterfaceVersion — version negotiation

// See the Vulkan Layer documentation for the full boilerplate:
// https://vulkan.lunarg.com/doc/view/latest/windows/loader_and_layer_interface.html

} // namespace scaffold::vulkan::layer
