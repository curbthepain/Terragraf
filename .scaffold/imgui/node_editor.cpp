/**
 * .scaffold/imgui/node_editor.cpp
 * Visual node graph editor — dependency graphs, data flow, neural net architecture.
 *
 * Uses ImNodes for node-based UI.
 * Connects to viz/3d/nodes.py graph structures.
 */

#include "imgui.h"
#include "imnodes.h"

#include <vector>
#include <string>

namespace {

struct NodeInfo {
    int id;
    std::string title;
    float value;
    int group;  // for color coding
};

struct LinkInfo {
    int id;
    int start_attr;
    int end_attr;
};

struct NodeEditorState {
    std::vector<NodeInfo> nodes;
    std::vector<LinkInfo> links;
    int next_node_id = 1;
    int next_link_id = 1;
    int next_attr_id = 1;

    // New node defaults
    char new_node_title[64] = "Node";
    float new_node_value = 0.0f;
};

static NodeEditorState state;

int make_attr_id() { return state.next_attr_id++; }

} // anonymous namespace

/**
 * Render the node graph editor.
 * Call this every frame from main loop.
 */
void render_node_editor() {
    ImGui::Begin("Node Editor");

    // Toolbar
    if (ImGui::Button("Add Node")) {
        state.nodes.push_back({
            state.next_node_id++,
            state.new_node_title,
            state.new_node_value,
            (int)(state.nodes.size() % 4)
        });
    }
    ImGui::SameLine();
    ImGui::InputText("Title", state.new_node_title, 64);
    ImGui::SameLine();
    ImGui::SliderFloat("Value", &state.new_node_value, -10.0f, 10.0f);

    if (ImGui::Button("Clear All")) {
        state.nodes.clear();
        state.links.clear();
    }

    ImGui::Separator();

    // Node editor canvas
    ImNodes::BeginNodeEditor();

    for (auto& node : state.nodes) {
        // Color by group
        const ImU32 colors[] = {
            IM_COL32(80, 120, 200, 255),  // blue
            IM_COL32(200, 80, 80, 255),   // red
            IM_COL32(80, 200, 80, 255),   // green
            IM_COL32(200, 180, 60, 255),  // yellow
        };
        ImNodes::PushColorStyle(ImNodesCol_TitleBar,
            colors[node.group % 4]);

        ImNodes::BeginNode(node.id);

        ImNodes::BeginNodeTitleBar();
        ImGui::Text("%s", node.title.c_str());
        ImNodes::EndNodeTitleBar();

        // Input attribute
        int input_attr = node.id * 100;
        ImNodes::BeginInputAttribute(input_attr);
        ImGui::Text("in");
        ImNodes::EndInputAttribute();

        // Value display
        ImGui::SliderFloat("##val", &node.value, -10.0f, 10.0f);

        // Output attribute
        int output_attr = node.id * 100 + 1;
        ImNodes::BeginOutputAttribute(output_attr);
        ImGui::Text("out");
        ImNodes::EndOutputAttribute();

        ImNodes::EndNode();
        ImNodes::PopColorStyle();
    }

    // Draw existing links
    for (auto& link : state.links) {
        ImNodes::Link(link.id, link.start_attr, link.end_attr);
    }

    ImNodes::EndNodeEditor();

    // Handle new links
    int start_attr, end_attr;
    if (ImNodes::IsLinkCreated(&start_attr, &end_attr)) {
        state.links.push_back({
            state.next_link_id++, start_attr, end_attr
        });
    }

    // Handle link deletion
    int link_id;
    if (ImNodes::IsLinkDestroyed(&link_id)) {
        auto it = std::find_if(state.links.begin(), state.links.end(),
            [link_id](const LinkInfo& l) { return l.id == link_id; });
        if (it != state.links.end())
            state.links.erase(it);
    }

    ImGui::End();
}
