STAGES, CONNECTORS, FILTERS, PROVIDERS = {}, {}, {}, {}

def _reg(table, name):
    def deco(fn):
        table[name] = fn
        return fn
    return deco

def stage(name): return _reg(STAGES, name)
def connector(name): return _reg(CONNECTORS, name)
def cfilter(name): return _reg(FILTERS, name)
def provider(name): return _reg(PROVIDERS, name)