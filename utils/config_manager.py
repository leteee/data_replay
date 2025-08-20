import yaml
from pathlib import Path
from copy import deepcopy

def load_yaml(file_path):
    if not Path(file_path).exists():
        return {}
    with open(file_path, "r") as f:
        return yaml.safe_load(f) or {}

def deep_merge(dict1, dict2):
    result = deepcopy(dict1)
    for k, v in dict2.items():
        if isinstance(v, dict) and k in result:
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result

class ConfigManager:
    def __init__(self, global_cfg="config/global.yaml", case_cfg=None):
        self.config = load_yaml(global_cfg)
        if case_cfg:
            case_conf = load_yaml(case_cfg)
            self.config = deep_merge(self.config, case_conf)

    def get(self, key, default=None):
        return self.config.get(key, default)
