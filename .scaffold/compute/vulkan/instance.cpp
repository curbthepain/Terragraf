/**
 * .scaffold/compute/vulkan/instance.cpp
 * Vulkan instance creation scaffold.
 *
 * This sets up the Vulkan instance with validation layers (debug)
 * or without (release). Starting point for any Vulkan application.
 *
 * Dependencies: Vulkan SDK (vulkan-headers, vulkan-loader)
 * Build: Link with -lvulkan
 */

#pragma once

#include <vulkan/vulkan.h>
#include <vector>
#include <string>
#include <stdexcept>
#include <cstring>
#include <iostream>

namespace scaffold::vulkan {

/**
 * Check if a validation layer is available.
 */
inline bool check_layer_support(const char* layer_name) {
    uint32_t count;
    vkEnumerateInstanceLayerProperties(&count, nullptr);
    std::vector<VkLayerProperties> layers(count);
    vkEnumerateInstanceLayerProperties(&count, layers.data());

    for (const auto& layer : layers) {
        if (strcmp(layer_name, layer.layerName) == 0) return true;
    }
    return false;
}

/**
 * Create a Vulkan instance.
 *
 * @param app_name    Application name
 * @param api_version Vulkan API version (e.g., VK_API_VERSION_1_3)
 * @param validation  Enable validation layers (debug builds)
 * @return VkInstance handle
 */
inline VkInstance create_instance(
    const std::string& app_name = "ScaffoldApp",
    uint32_t api_version = VK_API_VERSION_1_3,
    bool validation = true
) {
    VkApplicationInfo app_info{};
    app_info.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app_info.pApplicationName = app_name.c_str();
    app_info.applicationVersion = VK_MAKE_VERSION(1, 0, 0);
    app_info.pEngineName = "Scaffold";
    app_info.engineVersion = VK_MAKE_VERSION(1, 0, 0);
    app_info.apiVersion = api_version;

    VkInstanceCreateInfo create_info{};
    create_info.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    create_info.pApplicationInfo = &app_info;

    // Validation layers
    const char* validation_layer = "VK_LAYER_KHRONOS_validation";
    std::vector<const char*> layers;
    if (validation && check_layer_support(validation_layer)) {
        layers.push_back(validation_layer);
        std::cout << "Vulkan validation layers enabled\n";
    }
    create_info.enabledLayerCount = static_cast<uint32_t>(layers.size());
    create_info.ppEnabledLayerNames = layers.data();

    VkInstance instance;
    VkResult result = vkCreateInstance(&create_info, nullptr, &instance);
    if (result != VK_SUCCESS) {
        throw std::runtime_error("Failed to create Vulkan instance: " + std::to_string(result));
    }

    return instance;
}

/**
 * Pick a physical device (GPU) that supports compute.
 */
inline VkPhysicalDevice pick_compute_device(VkInstance instance) {
    uint32_t count;
    vkEnumeratePhysicalDevices(instance, &count, nullptr);
    if (count == 0) throw std::runtime_error("No Vulkan-capable GPU found");

    std::vector<VkPhysicalDevice> devices(count);
    vkEnumeratePhysicalDevices(instance, &count, devices.data());

    // Prefer discrete GPU, fall back to any
    for (const auto& device : devices) {
        VkPhysicalDeviceProperties props;
        vkGetPhysicalDeviceProperties(device, &props);
        if (props.deviceType == VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU) {
            std::cout << "GPU: " << props.deviceName << " (discrete)\n";
            return device;
        }
    }

    VkPhysicalDeviceProperties props;
    vkGetPhysicalDeviceProperties(devices[0], &props);
    std::cout << "GPU: " << props.deviceName << "\n";
    return devices[0];
}

/**
 * Find a queue family that supports compute operations.
 */
inline uint32_t find_compute_queue_family(VkPhysicalDevice device) {
    uint32_t count;
    vkGetPhysicalDeviceQueueFamilyProperties(device, &count, nullptr);
    std::vector<VkQueueFamilyProperties> families(count);
    vkGetPhysicalDeviceQueueFamilyProperties(device, &count, families.data());

    // Prefer a compute-only queue (avoids contention with graphics)
    for (uint32_t i = 0; i < count; i++) {
        if ((families[i].queueFlags & VK_QUEUE_COMPUTE_BIT) &&
            !(families[i].queueFlags & VK_QUEUE_GRAPHICS_BIT)) {
            return i;
        }
    }
    // Fall back to any compute-capable queue
    for (uint32_t i = 0; i < count; i++) {
        if (families[i].queueFlags & VK_QUEUE_COMPUTE_BIT) return i;
    }
    throw std::runtime_error("No compute queue family found");
}

/**
 * Create a logical device with a compute queue.
 */
inline VkDevice create_device(VkPhysicalDevice physical_device,
                               uint32_t queue_family,
                               VkQueue& compute_queue) {
    float priority = 1.0f;
    VkDeviceQueueCreateInfo queue_info{};
    queue_info.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
    queue_info.queueFamilyIndex = queue_family;
    queue_info.queueCount = 1;
    queue_info.pQueuePriorities = &priority;

    VkDeviceCreateInfo device_info{};
    device_info.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
    device_info.queueCreateInfoCount = 1;
    device_info.pQueueCreateInfos = &queue_info;

    VkDevice device;
    if (vkCreateDevice(physical_device, &device_info, nullptr, &device) != VK_SUCCESS) {
        throw std::runtime_error("Failed to create logical device");
    }

    vkGetDeviceQueue(device, queue_family, 0, &compute_queue);
    return device;
}

} // namespace scaffold::vulkan
