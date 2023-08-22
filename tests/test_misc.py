import chanfig


class Test:
    def test_interpolate(self):
        config = chanfig.load("tests/interpolate.yaml").interpolate()
        assert config.data.root == "localhost:80"
        assert config.data.imagenet.data_dirs[0] == "localhost:80/X-A"
        assert config.data.imagenet.data_dirs[1] == "localhost:80/X-B"
        assert config.data.imagenet.data_dirs[2] == "localhost:80/X-C"
