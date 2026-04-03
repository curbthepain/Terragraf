// .scaffold/headers/viz.h
// Visualization contract.
// Declares the viz pipeline: spectrograms, heatmaps, streams, 3D, export.

#ifndef VIZ_H
#define VIZ_H

#include "project.h"
#include "compute.h"

// ─── 2D Visualization ──────────────────────────────────────────────
// Spectrograms, heatmaps, and real-time stream plots

#spectrogram {
    template: "viz/spectrogram.py",
    builds_on: "compute/fft/spectral.py",

    // Operations:
    //   render_spectrogram      — time-frequency plot from signal
    //   render_mel_spectrogram  — mel-scale spectrogram
}

#heatmap {
    template: "viz/heatmap.py",

    // Operations:
    //   heatmap            — 2D array as color-mapped image
    //   annotated_heatmap  — with numeric cell labels
}

#stream {
    template: "viz/stream.py",

    // Operations:
    //   StreamPlotter — animated scrolling line chart
    //   .start(), .update(values), .stop()
}

// ─── Export ─────────────────────────────────────────────────────────

#export {
    template: "viz/export.py",
    formats: ["png", "svg", "pdf", "jpg", "raw"],

    // Operations:
    //   save_figure       — figure to file
    //   figure_to_buffer  — figure to in-memory bytes
}

// ─── 3D Visualization ──────────────────────────────────────────────
// Node graphs, mesh, volumetric rendering

#viz_3d {
    dir: "viz/3d/",

    templates: {
        nodes:  "viz/3d/nodes.py",      // 3D node graph
        mesh:   "viz/3d/mesh.py",       // surface plots, point clouds
        volume: "viz/3d/volume.py",     // volumetric rendering
        scene:  "viz/3d/scene.py",      // camera, lighting
        export: "viz/3d/export.py"      // OBJ, PLY, GLTF
    }
}

#endif // VIZ_H
