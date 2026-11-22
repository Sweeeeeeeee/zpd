"""Write the 18 restricted-domain scan configurations and their checksum manifest."""
import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOMAINS = ("full", "no_similarity", "circles")


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def freeze(output):
    output.mkdir(parents=True, exist_ok=True)
    configs = ROOT / "pipeline/configs"
    sources, runs = {}, {}
    for domain in DOMAINS:
        for suffix in ("", "_no_ar"):
            name = domain + suffix
            for policy in ("deduction", "heuristics", "combined"):
                if policy == "combined":
                    preset = configs / "domains_transformer" / f"{name}_transformer.json"
                else:
                    preset = configs / "domains" / f"{name}.json"
                cfg = json.loads(preset.read_text())
                cfg.pop("_comment", None)
                cfg["strict_tools"] = True
                if policy == "deduction":
                    cfg["tools"]["heuristics"]["enabled"] = False
                    cfg["proposer_order"] = []
                    cfg["search"]["max_depth"] = 0
                rule_file = cfg["tools"]["ddar"]["options"]["config"]
                if rule_file not in sources:
                    sources[rule_file] = sha256(ROOT / rule_file)
                if policy == "combined":
                    weights = cfg["tools"]["transformer"]["options"]["checkpoint"]
                    if weights not in sources:
                        sources[weights] = sha256(ROOT / weights)
                path = output / f"{name}-{policy}.json"
                path.write_text(json.dumps(cfg, indent=2) + "\n")
                runs[path.name] = sha256(path)
    manifest = {"engine": "python", "newclid": version("newclid"), "sources": sources, "configs": runs}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    freeze(parser.parse_args().output)
