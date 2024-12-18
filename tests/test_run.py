''' Test the `run` command '''

from wke import Configuration, Cluster, run


def test_valid_option():
    config = Configuration('basic', base_path='test-files/configs')
    cluster = Cluster(path='test-files/configs/cluster.toml')

    run(cluster, config, 'setup-rust', options={'channel': 'nightly'}, dry_run=True)


def test_invalid_option():
    config = Configuration('basic', base_path='test-files/configs')
    cluster = Cluster(path='test-files/configs/cluster.toml')

    try:
        run(cluster, config, 'setup-rust', options={'channel': 'cbs'}, dry_run=True)
        assert False
    except ValueError:
        pass
