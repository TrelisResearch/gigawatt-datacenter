import config as original_config

class Config:
    def __init__(self):
        # Import all uppercase variables from the original config
        for key in dir(original_config):
            if key.isupper():
                setattr(self, key, getattr(original_config, key))

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        
        # Recalculate dependent values
        self.NG_PRICE_PER_KWH = self.NG_PRICE_PER_MMBTU / 293.07
        self.EQUITY_RATIO = 1 - self.DEBT_RATIO

config = Config()