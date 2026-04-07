// .scaffold/headers/project.h
// Declares the project's module structure and boundaries.
// AI reads this to understand WHAT exists without scanning every file.

#ifndef PROJECT_H
#define PROJECT_H

// ─── Project Declaration ─────────────────────────────────────────────

#project {
    name: "terragraf",
    lang: "python, c++, glsl, javascript, bash",
    type: "scaffolding-system"
}

// ─── Module Declarations ─────────────────────────────────────────────
// Each module: what it does, where it lives, what it exports, what it needs.

#module math {
    #path "compute/math"
    #exports [mat_mul, mat_inv, determinant, eigenvalues, eigenvectors, svd, lu_decompose, solve, norm, rank, poly_eval, poly_roots, interpolate, curve_fit_poly, lagrange_interpolate, newton_interpolate, descriptive, correlation, covariance, linear_regression, normal_pdf, normal_cdf, t_test, chi_squared, percentile, zscore, dct, idct, hilbert, wavelet_transform, z_transform, laplace_transform_numerical]
    #depends [fft]
    #desc "Linear algebra, statistics, algebra, and signal transforms (NumPy/SciPy)"
}

#module fft {
    #path "compute/fft"
    #exports [fft1d, fft2d, ifft, rfft, magnitude, phase, power_spectrum, freqs, rfreqs, stft, istft, fft_convolve, cross_correlate, spectrogram, spectral_centroid, spectral_rolloff, dominant_frequency, bandpass_filter, mel_filterbank]
    #depends []
    #desc "FFT utilities and spectral analysis (NumPy backend)"
}

#module ml {
    #path "ml"
    #exports [ScaffoldModel, Classifier, CNN, Transformer, TerraLM, ScaffoldDataset, create_dataloader, Trainer, Evaluator, MetricsTracker, TrainConfig, export_onnx, load_onnx, export_safetensors, load_safetensors, export_torchscript, load_torchscript, save_model, load_model, save_checkpoint, load_checkpoint, detect_format, available_backends, ModelIOError, create_logger, create_optimizer, create_scheduler]
    #depends [math]
    #desc "PyTorch ML pipeline — models, datasets, training, evaluation, export, logging"
}

#module viz {
    #path "viz"
    #exports [render_spectrogram, render_mel_spectrogram, render_heatmap, StreamPlotter, export_figure, VolumeRenderer, NodeGraph3D, MeshGenerator, SceneManager]
    #depends [fft, math]
    #desc "2D and 3D visualization — spectrograms, heatmaps, volumes, node graphs"
}

#module vulkan {
    #path "compute/vulkan"
    #exports []
    #depends []
    #desc "Vulkan compute pipeline (instance, pipeline, memory, layers)"
}

#module render {
    #path "compute/render"
    #exports []
    #depends [vulkan]
    #desc "OpenGL rendering — GL context, mesh renderer, volume renderer"
}

#module generators {
    #path "generators"
    #exports [resolve, gen_module, gen_model, gen_shader, scaffold]
    #depends [ml, math, vulkan]
    #desc "Code generators — models, shaders, modules, include resolver"
}

#module instances {
    #path "instances"
    #exports [InstanceManager, ScaffoldInstance]
    #depends []
    #desc "Multi-instancing — parallel AI coordination via filesystem IPC"
}

#module git {
    #path "git"
    #exports [branch, commit, pr]
    #depends []
    #desc "Git workflow scripts — branch, commit, PR, CI/CD templates"
}

#module imgui {
    #path "imgui"
    #exports [render_math_panel, render_spectrogram_panel, render_volume_panel, render_settings_panel, render_debug_panel]
    #depends [viz, tuning, workspace]
    #desc "ImGui viewer panels — math, spectrogram, volume, settings, debug (C++/OpenGL), embeddable via --embedded"
}

#module sharpen {
    #path "sharpen"
    #exports []
    #depends []
    #desc "Self-sharpening feedback loop — post-validation optimization"
}

#module tuning {
    #path "tuning"
    #exports [ThematicEngine, UniverseProfile, Knob, Zone, load_profile, list_profiles]
    #depends [sharpen]
    #desc "Thematic tension calibration — universe profiles, behavioral instructions, zone-aware axes"
}

#module app_host {
    #path "app"
    #exports [AppHostManager, IDEManifest, IDEHostPage]
    #depends []
    #desc "Modular IDE host — discovers IDEs in apps/ via app.toml manifests, embeds via QWebEngineView or manages as child process"
}

#module workspace {
    #path "app"
    #exports [MainWindow, WorkspaceTabWidget, Session, SessionManager, ScaffoldWatcher, ScaffoldState, SettingsDialog, ExternalTab, ExternalDetector, ImGuiPanel, ImGuiDock, FeedbackLoop, CoherenceManager, WelcomeTab, Sidebar, TopBar, IconButton, CommandDialog, FieldSpec, SkillPicker, RoutesBrowser, HeadersBrowser, KnowledgeBrowser, WorktreeManagerDialog, LookupBrowser, PatternBrowser, HealthPanel, QueuePanel, DepsPanel, MCPServerPanel, SharpenPanel, HotContextEditor, TunePanel, ModePanel, StatusPanel, ViewerPanel, GenerateDialog, TrainDialog, SolveDialog, AnalyzeDialog, RenderDialog, BranchDialog, CommitDialog, GitFlowDialog, KnowledgeAddDialog, ProjectNewDialog, WorktreeCreateDialog, DispatchDialog]
    #depends [instances, app_host]
    #desc "Tabbed workspace — sidebar + hamburger chrome, native/external/welcome tabs, scaffold watcher, state cache, ImGui embedding, feedback loops, coherence detection, command form dialogs, browsers, status panels"
}

#module query {
    #path "query"
    #exports [QueryEngine, IntentParser, QueryResult, Intent, RouteMatch, HeaderMatch]
    #depends [skills, workspace]
    #desc "Structured query engine — intent parsing, route/header/skill resolution, LLM fallback when score < 0.5"
}

#module llm {
    #path "llm"
    #exports [LLMProvider, LLMConfig, LLMContext, AnthropicProvider, OpenAICompatibleProvider, HuggingFaceProvider, LLMWorker, make_provider, load_llm_config, LLM_FALLBACK_THRESHOLD, HarnessInfo, detect, detect_and_persist, read_current, write_current, lookup_capabilities]
    #depends [query, workspace]
    #desc "LLM provider layer — Anthropic + OpenAI-compat + HuggingFace local + universal harness/model detection (Claude Code, Cursor, Windsurf, Continue, terra)"
}

#module hooks {
    #path "hooks"
    #exports [check_threshold, on_commit, on_enter, on_generate, on_instance]
    #depends [skills]
    #desc "Lifecycle hooks — git pre/post commit, generation formatting, instance lifecycle, HOT_CONTEXT threshold guard (universal trigger)"
}

#module skills {
    #path "skills"
    #exports [list_skills, match_skill, run_skill, run_skill_capture, print_skills]
    #depends []
    #desc "Skill system — plugin discovery, intent matching, execution (SKILL.toml manifests)"
}

#module mcp {
    #path "mcp"
    #exports [MCPServer, ResourceRegistry, ResourceDescriptor, Resource, SkillToolAdapter]
    #depends [skills, workspace]
    #desc "MCP resource server — exposes scaffold data as discoverable resources over TCP (port 9878)"
}

#module worktree {
    #path "worktree"
    #exports [WorktreeManager, WorktreeInfo, WorktreeContext]
    #depends [instances, git]
    #desc "Git worktree isolation — parallel agent work in independent working trees"
}

#module projects {
    #path "../projects"
    #exports []
    #depends [skills]
    #desc "User projects directory — scaffolded by skills/scaffold_project"
}

#module deps {
    #path "../src"
    #exports [sync_python, sync_cpp, deps_status, deps_clean]
    #depends []
    #desc "Local dependency sourcing — Python (pip --target) and C++ (git clone) into src/"
}

#module tests {
    #path "tests"
    #exports []
    #depends [math, fft, generators]
    #desc "Pytest test suite — 382 tests covering math, FFT, spectral, tuning, transport, generators"
}

#endif // PROJECT_H
