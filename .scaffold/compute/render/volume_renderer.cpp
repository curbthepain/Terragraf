/**
 * .scaffold/compute/render/volume_renderer.cpp
 * GPU ray marching for volumetric data visualization.
 *
 * Renders 3D density fields (CT, ultrasound, dataset volumes) using
 * front-to-back compositing via compute or fragment shaders.
 *
 * Pairs with: compute/shaders/volume.comp for GPU compute path.
 * Pairs with: viz/3d/volume.py for CPU Python path.
 *
 * Build: compile with gl_context.cpp, glad, GLFW.
 */

#pragma once

#include <vector>
#include <array>
#include <cstdint>
#include <cmath>
#include <algorithm>

namespace scaffold::render {

struct VolumeConfig {
    int width = 512;           // render resolution
    int height = 512;
    int max_steps = 256;       // ray march steps
    float step_size = 0.01f;   // world-space step size
    float density_scale = 1.0f;
    float opacity_threshold = 0.95f;
};

/**
 * Transfer function entry: maps density value to RGBA color.
 */
struct TransferPoint {
    float density;      // 0.0 - 1.0
    float r, g, b, a;   // RGBA color at this density
};

/**
 * CPU-based volume ray marcher.
 *
 * Usage:
 *   VolumeRendererCPU renderer;
 *   renderer.set_volume(data, 64, 64, 64);
 *   renderer.set_transfer({
 *       {0.0f, 0, 0, 0, 0},
 *       {0.3f, 0.2f, 0.3f, 0.8f, 0.1f},
 *       {0.7f, 0.8f, 0.6f, 0.2f, 0.4f},
 *       {1.0f, 1, 1, 1, 0.8f}
 *   });
 *   auto image = renderer.render(camera_pos, look_at);
 */
class VolumeRendererCPU {
public:
    VolumeRendererCPU() = default;

    /**
     * Set the 3D volume data.
     * data: flat array of float density values (0-1), ordered [z][y][x].
     */
    void set_volume(const std::vector<float>& data,
                    int size_x, int size_y, int size_z) {
        volume_ = data;
        size_ = {size_x, size_y, size_z};
    }

    /**
     * Set the transfer function (density → color mapping).
     */
    void set_transfer(const std::vector<TransferPoint>& points) {
        transfer_ = points;
    }

    /**
     * Sample volume at a world-space position using trilinear interpolation.
     */
    float sample(float x, float y, float z) const {
        // Normalize to [0, size-1]
        x = std::clamp(x, 0.0f, (float)(size_[0] - 1));
        y = std::clamp(y, 0.0f, (float)(size_[1] - 1));
        z = std::clamp(z, 0.0f, (float)(size_[2] - 1));

        int ix = (int)x, iy = (int)y, iz = (int)z;
        float fx = x - ix, fy = y - iy, fz = z - iz;

        auto idx = [&](int i, int j, int k) -> size_t {
            i = std::clamp(i, 0, size_[0] - 1);
            j = std::clamp(j, 0, size_[1] - 1);
            k = std::clamp(k, 0, size_[2] - 1);
            return k * size_[0] * size_[1] + j * size_[0] + i;
        };

        // Trilinear interpolation
        float c000 = volume_[idx(ix, iy, iz)];
        float c100 = volume_[idx(ix+1, iy, iz)];
        float c010 = volume_[idx(ix, iy+1, iz)];
        float c001 = volume_[idx(ix, iy, iz+1)];
        float c110 = volume_[idx(ix+1, iy+1, iz)];
        float c101 = volume_[idx(ix+1, iy, iz+1)];
        float c011 = volume_[idx(ix, iy+1, iz+1)];
        float c111 = volume_[idx(ix+1, iy+1, iz+1)];

        return c000*(1-fx)*(1-fy)*(1-fz) + c100*fx*(1-fy)*(1-fz) +
               c010*(1-fx)*fy*(1-fz) + c001*(1-fx)*(1-fy)*fz +
               c110*fx*fy*(1-fz) + c101*fx*(1-fy)*fz +
               c011*(1-fx)*fy*fz + c111*fx*fy*fz;
    }

    /**
     * Apply transfer function to get RGBA from density.
     */
    std::array<float, 4> apply_transfer(float density) const {
        if (transfer_.empty())
            return {density, density, density, density};

        // Find surrounding control points
        for (size_t i = 0; i + 1 < transfer_.size(); ++i) {
            if (density >= transfer_[i].density &&
                density <= transfer_[i+1].density) {
                float t = (density - transfer_[i].density) /
                          (transfer_[i+1].density - transfer_[i].density);
                return {
                    transfer_[i].r + t * (transfer_[i+1].r - transfer_[i].r),
                    transfer_[i].g + t * (transfer_[i+1].g - transfer_[i].g),
                    transfer_[i].b + t * (transfer_[i+1].b - transfer_[i].b),
                    transfer_[i].a + t * (transfer_[i+1].a - transfer_[i].a),
                };
            }
        }
        return {density, density, density, density};
    }

    /**
     * Render the volume. Returns RGBA image as flat float vector.
     * Image size: config.width * config.height * 4.
     */
    std::vector<float> render(
        const std::array<float, 3>& camera_pos,
        const std::array<float, 3>& look_at,
        const VolumeConfig& config = {}
    ) const {
        int w = config.width, h = config.height;
        std::vector<float> image(w * h * 4, 0.0f);

        // Camera basis vectors
        std::array<float, 3> forward, right, up;
        for (int i = 0; i < 3; ++i)
            forward[i] = look_at[i] - camera_pos[i];
        float len = std::sqrt(forward[0]*forward[0] + forward[1]*forward[1] + forward[2]*forward[2]);
        for (int i = 0; i < 3; ++i) forward[i] /= len;

        // Cross with world up (0,1,0)
        right[0] = forward[2]; right[1] = 0; right[2] = -forward[0];
        len = std::sqrt(right[0]*right[0] + right[2]*right[2]);
        if (len > 1e-6) { right[0] /= len; right[2] /= len; }
        else { right[0] = 1; right[2] = 0; }

        up[0] = right[1]*forward[2] - right[2]*forward[1];
        up[1] = right[2]*forward[0] - right[0]*forward[2];
        up[2] = right[0]*forward[1] - right[1]*forward[0];

        float extent = std::max({(float)size_[0], (float)size_[1], (float)size_[2]});

        for (int py = 0; py < h; ++py) {
            for (int px = 0; px < w; ++px) {
                float u = ((float)px / w - 0.5f) * extent;
                float v = ((float)py / h - 0.5f) * extent;

                std::array<float, 3> ray_origin;
                for (int i = 0; i < 3; ++i)
                    ray_origin[i] = camera_pos[i] + right[i] * u + up[i] * v;

                // Front-to-back compositing
                float color[4] = {0, 0, 0, 0};
                for (int step = 0; step < config.max_steps; ++step) {
                    float pos[3];
                    for (int i = 0; i < 3; ++i)
                        pos[i] = ray_origin[i] + forward[i] * step * config.step_size;

                    // Bounds check
                    if (pos[0] < 0 || pos[0] >= size_[0] - 1 ||
                        pos[1] < 0 || pos[1] >= size_[1] - 1 ||
                        pos[2] < 0 || pos[2] >= size_[2] - 1)
                        continue;

                    float density = sample(pos[0], pos[1], pos[2]) * config.density_scale;
                    if (density > 0.01f) {
                        auto rgba = apply_transfer(density);
                        float a = rgba[3] * config.step_size;
                        color[0] += (1 - color[3]) * rgba[0] * a;
                        color[1] += (1 - color[3]) * rgba[1] * a;
                        color[2] += (1 - color[3]) * rgba[2] * a;
                        color[3] += (1 - color[3]) * a;
                        if (color[3] > config.opacity_threshold)
                            break;
                    }
                }

                int idx = (py * w + px) * 4;
                for (int c = 0; c < 4; ++c)
                    image[idx + c] = std::clamp(color[c], 0.0f, 1.0f);
            }
        }

        return image;
    }

private:
    std::vector<float> volume_;
    std::array<int, 3> size_ = {0, 0, 0};
    std::vector<TransferPoint> transfer_;
};

} // namespace scaffold::render
