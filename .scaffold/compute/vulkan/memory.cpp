/**
 * .scaffold/compute/vulkan/memory.cpp
 * Vulkan buffer and memory management scaffold.
 *
 * Handles: buffer creation, memory allocation, mapping, data transfer.
 * The plumbing that gets data to and from the GPU.
 */

#pragma once

#include <vulkan/vulkan.h>
#include <vector>
#include <cstring>
#include <stdexcept>

namespace scaffold::vulkan {

/**
 * Find a memory type that matches requirements.
 */
inline uint32_t find_memory_type(VkPhysicalDevice physical_device,
                                  uint32_t type_filter,
                                  VkMemoryPropertyFlags properties) {
    VkPhysicalDeviceMemoryProperties mem_props;
    vkGetPhysicalDeviceMemoryProperties(physical_device, &mem_props);

    for (uint32_t i = 0; i < mem_props.memoryTypeCount; i++) {
        if ((type_filter & (1 << i)) &&
            (mem_props.memoryTypes[i].propertyFlags & properties) == properties) {
            return i;
        }
    }
    throw std::runtime_error("No suitable memory type found");
}

/**
 * Create a buffer + allocate memory for it.
 *
 * @param size       Buffer size in bytes
 * @param usage      VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, etc.
 * @param properties VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | HOST_COHERENT_BIT
 * @return {buffer, memory} pair
 */
inline std::pair<VkBuffer, VkDeviceMemory> create_buffer(
    VkDevice device,
    VkPhysicalDevice physical_device,
    VkDeviceSize size,
    VkBufferUsageFlags usage,
    VkMemoryPropertyFlags properties
) {
    // Create buffer
    VkBufferCreateInfo buffer_info{};
    buffer_info.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
    buffer_info.size = size;
    buffer_info.usage = usage;
    buffer_info.sharingMode = VK_SHARING_MODE_EXCLUSIVE;

    VkBuffer buffer;
    if (vkCreateBuffer(device, &buffer_info, nullptr, &buffer) != VK_SUCCESS) {
        throw std::runtime_error("Failed to create buffer");
    }

    // Allocate memory
    VkMemoryRequirements mem_reqs;
    vkGetBufferMemoryRequirements(device, buffer, &mem_reqs);

    VkMemoryAllocateInfo alloc_info{};
    alloc_info.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    alloc_info.allocationSize = mem_reqs.size;
    alloc_info.memoryTypeIndex = find_memory_type(physical_device,
                                                   mem_reqs.memoryTypeBits,
                                                   properties);

    VkDeviceMemory memory;
    if (vkAllocateMemory(device, &alloc_info, nullptr, &memory) != VK_SUCCESS) {
        throw std::runtime_error("Failed to allocate buffer memory");
    }

    vkBindBufferMemory(device, buffer, memory, 0);
    return {buffer, memory};
}

/**
 * Upload data from CPU to a host-visible GPU buffer.
 */
inline void upload_to_buffer(VkDevice device, VkDeviceMemory memory,
                              const void* data, VkDeviceSize size) {
    void* mapped;
    vkMapMemory(device, memory, 0, size, 0, &mapped);
    std::memcpy(mapped, data, size);
    vkUnmapMemory(device, memory);
}

/**
 * Download data from a host-visible GPU buffer to CPU.
 */
inline void download_from_buffer(VkDevice device, VkDeviceMemory memory,
                                  void* data, VkDeviceSize size) {
    void* mapped;
    vkMapMemory(device, memory, 0, size, 0, &mapped);
    std::memcpy(data, mapped, size);
    vkUnmapMemory(device, memory);
}

/**
 * Create a storage buffer with initial data uploaded.
 * Convenience: create + upload in one call.
 */
template<typename T>
inline std::pair<VkBuffer, VkDeviceMemory> create_storage_buffer(
    VkDevice device,
    VkPhysicalDevice physical_device,
    const std::vector<T>& data
) {
    VkDeviceSize size = sizeof(T) * data.size();
    auto [buffer, memory] = create_buffer(
        device, physical_device, size,
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT,
        VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT
    );
    upload_to_buffer(device, memory, data.data(), size);
    return {buffer, memory};
}

/**
 * Clean up a buffer and its memory.
 */
inline void destroy_buffer(VkDevice device, VkBuffer buffer, VkDeviceMemory memory) {
    vkDestroyBuffer(device, buffer, nullptr);
    vkFreeMemory(device, memory, nullptr);
}

} // namespace scaffold::vulkan
