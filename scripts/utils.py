import yaml


def read_yaml(config_path):
    configs = yaml.load(
        open(config_path, 'r', encoding='UTF-8'),  Loader=yaml.FullLoader)
    return configs