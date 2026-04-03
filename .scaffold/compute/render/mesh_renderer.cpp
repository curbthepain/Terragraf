/**
 * .scaffold/compute/render/mesh_renderer.cpp
 * Basic mesh rendering scaffold — vertex arrays, shaders, draw calls.
 *
 * Renders triangle meshes with per-vertex colors or textures.
 * Uses OpenGL 4.5 core profile (via gl_context.cpp).
 *
 * Build: compile alongside gl_context.cpp with glad and GLFW.
 */

#pragma once

#include <vector>
#include <array>
#include <cstdint>
#include <string>

namespace scaffold::render {

struct Vertex {
    std::array<float, 3> position;
    std::array<float, 3> normal;
    std::array<float, 4> color;     // RGBA
    std::array<float, 2> uv;       // texture coords
};

struct Mesh {
    std::vector<Vertex> vertices;
    std::vector<uint32_t> indices;  // triangle indices
    uint32_t vao = 0;              // OpenGL vertex array object
    uint32_t vbo = 0;              // vertex buffer
    uint32_t ebo = 0;              // element buffer
};

/**
 * Basic mesh renderer.
 *
 * Usage:
 *   MeshRenderer renderer;
 *   renderer.init();
 *   Mesh mesh = renderer.create_mesh(vertices, indices);
 *   // in render loop:
 *   renderer.draw(mesh, model_matrix, view_matrix, proj_matrix);
 *   renderer.cleanup(mesh);
 */
class MeshRenderer {
public:
    MeshRenderer() = default;
    ~MeshRenderer() { shutdown(); }

    /**
     * Initialize the renderer — compile shaders, set up state.
     */
    void init() {
        // Compile vertex shader
        // const char* vert_src = R"(
        //     #version 450 core
        //     layout(location = 0) in vec3 aPos;
        //     layout(location = 1) in vec3 aNormal;
        //     layout(location = 2) in vec4 aColor;
        //     layout(location = 3) in vec2 aUV;
        //
        //     uniform mat4 model;
        //     uniform mat4 view;
        //     uniform mat4 projection;
        //
        //     out vec3 FragPos;
        //     out vec3 Normal;
        //     out vec4 Color;
        //     out vec2 TexCoord;
        //
        //     void main() {
        //         FragPos = vec3(model * vec4(aPos, 1.0));
        //         Normal = mat3(transpose(inverse(model))) * aNormal;
        //         Color = aColor;
        //         TexCoord = aUV;
        //         gl_Position = projection * view * model * vec4(aPos, 1.0);
        //     }
        // )";

        // Compile fragment shader
        // const char* frag_src = R"(
        //     #version 450 core
        //     in vec3 FragPos;
        //     in vec3 Normal;
        //     in vec4 Color;
        //     in vec2 TexCoord;
        //
        //     out vec4 FragColor;
        //
        //     uniform vec3 lightPos;
        //     uniform vec3 lightColor;
        //
        //     void main() {
        //         vec3 norm = normalize(Normal);
        //         vec3 lightDir = normalize(lightPos - FragPos);
        //         float diff = max(dot(norm, lightDir), 0.0);
        //         vec3 diffuse = diff * lightColor;
        //         vec3 ambient = 0.15 * lightColor;
        //         FragColor = vec4((ambient + diffuse) * Color.rgb, Color.a);
        //     }
        // )";

        // shader_program_ = compile_and_link(vert_src, frag_src);
        // glEnable(GL_DEPTH_TEST);
    }

    /**
     * Upload mesh data to GPU.
     */
    Mesh create_mesh(const std::vector<Vertex>& vertices,
                     const std::vector<uint32_t>& indices) {
        Mesh mesh;
        mesh.vertices = vertices;
        mesh.indices = indices;

        // glGenVertexArrays(1, &mesh.vao);
        // glGenBuffers(1, &mesh.vbo);
        // glGenBuffers(1, &mesh.ebo);
        //
        // glBindVertexArray(mesh.vao);
        //
        // glBindBuffer(GL_ARRAY_BUFFER, mesh.vbo);
        // glBufferData(GL_ARRAY_BUFFER,
        //              vertices.size() * sizeof(Vertex),
        //              vertices.data(), GL_STATIC_DRAW);
        //
        // glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, mesh.ebo);
        // glBufferData(GL_ELEMENT_ARRAY_BUFFER,
        //              indices.size() * sizeof(uint32_t),
        //              indices.data(), GL_STATIC_DRAW);
        //
        // // Position
        // glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex),
        //                       (void*)offsetof(Vertex, position));
        // glEnableVertexAttribArray(0);
        // // Normal
        // glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex),
        //                       (void*)offsetof(Vertex, normal));
        // glEnableVertexAttribArray(1);
        // // Color
        // glVertexAttribPointer(2, 4, GL_FLOAT, GL_FALSE, sizeof(Vertex),
        //                       (void*)offsetof(Vertex, color));
        // glEnableVertexAttribArray(2);
        // // UV
        // glVertexAttribPointer(3, 2, GL_FLOAT, GL_FALSE, sizeof(Vertex),
        //                       (void*)offsetof(Vertex, uv));
        // glEnableVertexAttribArray(3);
        //
        // glBindVertexArray(0);

        return mesh;
    }

    /**
     * Draw a mesh with given transform matrices.
     * model/view/projection are 4x4 float arrays (column-major).
     */
    void draw(const Mesh& mesh, const float* model,
              const float* view, const float* projection) {
        // glUseProgram(shader_program_);
        // glUniformMatrix4fv(glGetUniformLocation(shader_program_, "model"),
        //                    1, GL_FALSE, model);
        // glUniformMatrix4fv(glGetUniformLocation(shader_program_, "view"),
        //                    1, GL_FALSE, view);
        // glUniformMatrix4fv(glGetUniformLocation(shader_program_, "projection"),
        //                    1, GL_FALSE, projection);
        //
        // glBindVertexArray(mesh.vao);
        // glDrawElements(GL_TRIANGLES, mesh.indices.size(),
        //                GL_UNSIGNED_INT, 0);
        // glBindVertexArray(0);
    }

    void cleanup(Mesh& mesh) {
        // glDeleteVertexArrays(1, &mesh.vao);
        // glDeleteBuffers(1, &mesh.vbo);
        // glDeleteBuffers(1, &mesh.ebo);
        mesh.vao = mesh.vbo = mesh.ebo = 0;
    }

    void shutdown() {
        // glDeleteProgram(shader_program_);
        shader_program_ = 0;
    }

private:
    uint32_t shader_program_ = 0;
};

} // namespace scaffold::render
