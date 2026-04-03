// Shader: {{shader_name}}
// Type: {{shader_type}}
// ─────────────────────────────────────────────────────────────────────
#version 450

layout(local_size_x = {{workgroup_x}}, local_size_y = {{workgroup_y}}, local_size_z = 1) in;
