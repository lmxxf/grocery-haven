"""Build flat WebUI and API workflows from the live 0.44 node schema."""
import json
from pathlib import Path
from h3_generate import graph

ROOT = Path(__file__).resolve().parent
schema = json.loads((ROOT / "object_info.json").read_text())
PORTS = {
    "MODEL", "CLIP", "VAE", "CONDITIONING", "LATENT", "IMAGE", "VIDEO", "AUDIO",
    "NOISE", "GUIDER", "SAMPLER", "SIGMAS",
}
POSITIONS = {
    "1": (0, 0), "2": (0, 240), "3": (0, 420), "4": (0, 590),
    "5": (360, 0), "6": (360, 350), "7": (700, 0), "8": (700, 170),
    "9": (700, 340), "10": (700, 510), "11": (1060, 180),
    "12": (1420, 100), "13": (1420, 270), "14": (1760, 180),
    "15": (2100, 180), "20": (0, 790), "21": (0, 1080),
}


def make_ui(api):
    nodes = {}
    for key, entry in api.items():
        kind = entry["class_type"]
        info = schema[kind]
        params = entry["inputs"]
        inputs = []
        widgets = []
        for name, (datatype, *details) in {
            **info["input"].get("required", {}), **info["input"].get("optional", {})
        }.items():
            options = details[0] if details and isinstance(details[0], dict) else {}
            if datatype == "COMFY_AUTOGROW_V3":
                template = options["template"]
                if "prefix" in template:
                    group = [field for field in params if field.startswith(name + ".")]
                    if group or name == "ref_images":
                        prefix = name + "." + template["prefix"]
                        count = min(template["max"], len(group) + 1)
                        datatype = next(iter(template["input"]["required"].values()))[0]
                        for index in range(count):
                            inputs.append({"name": prefix + str(index), "type": datatype, "link": None, "shape": 7})
            elif isinstance(datatype, str) and datatype in PORTS:
                inputs.append({"name": name, "type": datatype, "link": None})
            elif not options.get("hidden"):
                value = params.get(name, options.get("default"))
                if value is not None:
                    widgets.append(value)
                    if options.get("control_after_generate"):
                        widgets.append("fixed")
        if kind == "SaveVideo":
            widgets = [params["filename_prefix"], "mp4", "auto"]
        if kind == "LoadImage":
            widgets = [params["image"], "image"]
        nodes[key] = {
            "id": int(key), "type": kind, "pos": POSITIONS[key], "size": [320, 200],
            "flags": {}, "order": len(nodes), "mode": 0, "inputs": inputs,
            "outputs": [{"name": name, "type": datatype, "links": []} for name, datatype in zip(info["output_name"], info["output"])],
            "properties": {"Node name for S&R": kind}, "widgets_values": widgets,
        }
    links = []
    for key, node in nodes.items():
        for slot, port in enumerate(node["inputs"]):
            source = api[key]["inputs"].get(port["name"])
            if isinstance(source, list):
                upstream, output = source
                link_id = len(links) + 1
                port["link"] = link_id
                nodes[upstream]["outputs"][output]["links"].append(link_id)
                links.append([link_id, int(upstream), output, int(key), slot, port["type"]])
    return {
        "last_node_id": max(map(int, nodes)), "last_link_id": len(links),
        "nodes": list(nodes.values()), "links": links, "groups": [], "config": {},
        "extra": {"ds": {"scale": 0.53, "offset": [80, 90]}}, "version": 0.4,
    }


for mode, title in [("fl2va", "T2VA"), ("ref2va", "Ref2VA")]:
    prompt = (ROOT / "prompts" / (mode + ".txt")).read_text().strip()
    images = ["h3_character.png", "h3_courtyard.png"] if mode == "ref2va" else []
    turbo = 4 if mode == "ref2va" else 8
    api = graph(mode, prompt, 832, 480, 158, turbo, 20261111, turbo, images, f"H3/{title}")
    for suffix, data in [("", make_ui(api)), ("_api", api)]:
        (ROOT / f"MiniMax_H3_{title}{suffix}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
