from django.core.management.utils import get_random_secret_key


def main():
    secret_key = get_random_secret_key()
    text = "SECRET_KEY = '{}'".format(secret_key)
    import os
    with open(os.path.join(os.path.dirname(__file__), "local_settings.py"), "w") as f:
        f.write(text + "\n")


if __name__ == '__main__':
    main()
