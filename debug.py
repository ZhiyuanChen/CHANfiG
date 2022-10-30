from chanfig import Config


class TC(Config):
    def __init__(self):
        super().__init__()
        self.a.b.c = 1


print(TC())
