import logging

from ruamel.yaml import YAML

from black_hole import BlackHole

if __name__ == '__main__':
    logging.basicConfig(level='INFO')

    yaml = YAML(typ='safe')
    with open('config.yaml', 'r') as fp:
        config = yaml.load(fp)

    bh = BlackHole(config=config)
    bh.run()
