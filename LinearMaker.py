import os
import re
from pathlib import Path
from tkinter import Tk, filedialog, messagebox, Button, Label
from graphviz import Digraph
import threading

def update_status(msg):
    if status_label:
        status_label.config(text=msg)

def process_file_with_ui():
    update_status("Waiting for file selection...")

    # Open file dialog
    file_path = filedialog.askopenfilename(
        title="Select a Choose-Your-Own-Adventure Text File",
        filetypes=[("Text files", "*.txt")]
    )

    if not file_path:
        update_status("No file selected.")
        return

    update_status("Reading story file...")
    with open(file_path, "r", encoding="utf-8") as f:
        story_text = f.read()

    update_status("Parsing sections...")
    section_pattern = re.compile(r"\n\*\*(\d+)\*\*\n")
    section_starts = [(m.start(), m.end(), int(m.group(1))) for m in section_pattern.finditer(story_text)]
    section_starts.append((len(story_text), len(story_text), -1))

    sections = {}
    for i in range(len(section_starts) - 1):
        start_pos = section_starts[i][0]
        end_pos = section_starts[i+1][0]
        section_num = section_starts[i][2]
        section_text = story_text[start_pos:end_pos].strip()
        sections[section_num] = section_text

    update_status("Identifying endings...")
    ending_pattern = re.compile(r"(?<=\n)Ending:\s+(.*?)\n", re.IGNORECASE)
    ending_sections = {}
    for sec_num, text in sections.items():
        match = ending_pattern.search(text)
        if match:
            ending_sections[sec_num] = match.group(1)

    update_status("Building choice graph...")
    choice_pattern = re.compile(r"go to \*\*(\d+)\*\*", re.IGNORECASE)
    story_graph = {}
    for sec_num, text in sections.items():
        choices = choice_pattern.findall(text)
        story_graph[sec_num] = list(map(int, choices)) if choices else []

    update_status("Finding all story paths...")
    def dfs(path, all_paths):
        current = path[-1]
        if current in ending_sections:
            all_paths.append(list(path))
            return
        for next_sec in story_graph.get(current, []):
            if next_sec not in path:
                dfs(path + [next_sec], all_paths)

    all_paths = []
    dfs([1], all_paths)

    update_status("Writing output files...")
    base_dir = os.path.dirname(file_path)
    title_base = Path(file_path).stem.replace(" ", "_")
    output_root = os.path.join(base_dir, "cyoa_paths")
    output_dir = os.path.join(output_root, title_base)
    os.makedirs(output_dir, exist_ok=True)

    title_base = Path(file_path).stem.replace(" ", "_")
    ending_counts = {}  # Track number of paths per ending

    for path in all_paths:
        end_section = path[-1]
        end_name = ending_sections.get(end_section, f"Unknown_{end_section}")
        safe_name = re.sub(r"[^\w\-]", "_", end_name)

        # Count how many times this ending has occurred
        count = ending_counts.get(end_section, 0) + 1
        ending_counts[end_section] = count

        filename = f"{title_base}__{safe_name}__path_{count}.txt"
        output_path = os.path.join(output_dir, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            for sec in path:
                f.write(sections[sec].strip() + "\n\n")

    update_status("Generating story graph image...")

    # Create graph
    graph = Digraph(comment="CYOA Story Graph")
    graph.attr(rankdir='LR', size='8,5', dpi='900')

    # Add nodes
    for sec in story_graph:
        if sec in ending_sections:
            graph.node(str(sec), f"{sec}\n[{ending_sections[sec]}]", shape="doublecircle", color="red")
        else:
            graph.node(str(sec), str(sec))

    # Add edges
    for src, targets in story_graph.items():
        for dst in targets:
            graph.edge(str(src), str(dst))

    # Save in multiple formats
    graph_path = os.path.join(output_dir, f"{title_base}__graph")

    graph.format = 'png'
    graph.render(graph_path, cleanup=True)

    graph.format = 'svg'
    graph.render(graph_path, cleanup=True)

    update_status("Done! Files and graph saved.")
    messagebox.showinfo("Done!", f"Paths saved in folder:\n{output_dir}")

# GUI setup
status_label = None  # Global variable to update status later

def build_ui():
    global status_label

    root = Tk()
    root.title("CYOA Story Path Splitter")
    root.geometry("400x250")

    Label(root, text="Choose Your Own Adventure\nStory Path Linearizer", font=("Arial", 14), pady=10).pack()

    Button(root, text="Select and Process Story File", command=lambda: threading.Thread(target=process_file_with_ui).start(), padx=10, pady=10).pack()

    status_label = Label(root, text="", font=("Arial", 10), fg="blue")
    status_label.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    build_ui()
