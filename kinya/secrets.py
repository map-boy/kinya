import os


def _colab_secret(name):
    try:
        from google.colab import userdata
        return userdata.get(name)
    except Exception:
        return None


def _kaggle_secret(name):
    try:
        from kaggle_secrets import UserSecretsClient
        return UserSecretsClient().get_secret(name)
    except Exception:
        return None


def get_secret(name):
    """Read a secret from environment, then Colab/Kaggle secret vaults."""
    val = os.environ.get(name)
    if val:
        return val
    for reader in (_colab_secret, _kaggle_secret):
        val = reader(name)
        if val:
            os.environ[name] = val
            return val
    return None


def first_secret(names):
    for name in names:
        val = get_secret(name)
        if val:
            return val
    return None
