/**
 * .scaffold/compute/vulkan/pipeline.cpp
 * Vulkan compute pipeline scaffold.
 *
 * Sets up: shader module → descriptor set layout → pipeline layout → pipeline.
 * This is the core of GPU compute — bind data, dispatch work, read results.
 */

#pragma once

#include <vulkan/vulkan.h>
#include <vector>
#include <fstream>
#include <stdexcept>
#include <string>

namespace scaffold::vulkan {

/**
 * Load a compiled SPIR-V shader from disk.
 * Compile .comp → .spv with: glslangValidator -V shader.comp -o shader.spv
 */
inline std::vector<uint32_t> load_spirv(const std::string& path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file.is_open()) throw std::runtime_error("Failed to open shader: " + path);

    size_t size = file.tellg();
    file.seekg(0);
    std::vector<uint32_t> code(size / sizeof(uint32_t));
    file.read(reinterpret_cast<char*>(code.data()), size);
    return code;
}

/**
 * Create a shader module from SPIR-V bytecode.
 */
inline VkShaderModule create_shader_module(VkDevice device, const std::vector<uint32_t>& code) {
    VkShaderModuleCreateInfo info{};
    info.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
    info.codeSize = code.size() * sizeof(uint32_t);
    info.pCode = code.data();

    VkShaderModule module;
    if (vkCreateShaderModule(device, &info, nullptr, &module) != VK_SUCCESS) {
        throw std::runtime_error("Failed to create shader module");
    }
    return module;
}

/**
 * Create a descriptor set layout for a compute shader.
 * Defines how buffers bind to shader binding points.
 *
 * @param n_buffers Number of storage buffers the shader expects
 */
inline VkDescriptorSetLayout create_descriptor_layout(VkDevice device, uint32_t n_buffers) {
    std::vector<VkDescriptorSetLayoutBinding> bindings(n_buffers);
    for (uint32_t i = 0; i < n_buffers; i++) {
        bindings[i] = {};
        bindings[i].binding = i;
        bindings[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        bindings[i].descriptorCount = 1;
        bindings[i].stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    }

    VkDescriptorSetLayoutCreateInfo info{};
    info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
    info.bindingCount = n_buffers;
    info.pBindings = bindings.data();

    VkDescriptorSetLayout layout;
    if (vkCreateDescriptorSetLayout(device, &info, nullptr, &layout) != VK_SUCCESS) {
        throw std::runtime_error("Failed to create descriptor set layout");
    }
    return layout;
}

/**
 * Create a compute pipeline.
 *
 * @param device      Logical device
 * @param shader_path Path to compiled .spv shader
 * @param desc_layout Descriptor set layout
 * @param entry_point Shader entry function name (usually "main")
 */
inline VkPipeline create_compute_pipeline(
    VkDevice device,
    const std::string& shader_path,
    VkDescriptorSetLayout desc_layout,
    VkPipelineLayout& pipeline_layout,
    const std::string& entry_point = "main"
) {
    // Load shader
    auto code = load_spirv(shader_path);
    VkShaderModule shader = create_shader_module(device, code);

    // Pipeline layout
    VkPipelineLayoutCreateInfo layout_info{};
    layout_info.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
    layout_info.setLayoutCount = 1;
    layout_info.pSetLayouts = &desc_layout;

    if (vkCreatePipelineLayout(device, &layout_info, nullptr, &pipeline_layout) != VK_SUCCESS) {
        throw std::runtime_error("Failed to create pipeline layout");
    }

    // Compute pipeline
    VkComputePipelineCreateInfo pipeline_info{};
    pipeline_info.sType = VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO;
    pipeline_info.stage.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
    pipeline_info.stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
    pipeline_info.stage.module = shader;
    pipeline_info.stage.pName = entry_point.c_str();
    pipeline_info.layout = pipeline_layout;

    VkPipeline pipeline;
    if (vkCreateComputePipelines(device, VK_NULL_HANDLE, 1, &pipeline_info, nullptr, &pipeline) != VK_SUCCESS) {
        throw std::runtime_error("Failed to create compute pipeline");
    }

    vkDestroyShaderModule(device, shader, nullptr);
    return pipeline;
}

} // namespace scaffold::vulkan
