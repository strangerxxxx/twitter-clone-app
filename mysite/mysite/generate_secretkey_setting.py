from django.core.management.utils import get_random_secret_key
import os


def main():
    secret_key = get_random_secret_key()
    settings_dir = os.path.dirname(__file__)
    repo_root = os.path.dirname(os.path.dirname(settings_dir))

    local_settings_path = os.path.join(settings_dir, 'local_settings.py')
    with open(local_settings_path, 'w') as f:
        f.write(f"SECRET_KEY = '{secret_key}'\n")

    env_example_path = os.path.join(repo_root, '.env.example')
    env_path = os.path.join(repo_root, '.env')
    if os.path.exists(env_example_path) and not os.path.exists(env_path):
        with open(env_example_path, 'r', encoding='utf-8') as example:
            content = example.read()
        content = content.replace(
            'DJANGO_SECRET_KEY=change-me-in-production',
            f'DJANGO_SECRET_KEY={secret_key}',
        )
        with open(env_path, 'w', encoding='utf-8') as env_file:
            env_file.write(content)

    print('Generated local_settings.py')
    if os.path.exists(env_path):
        print('Created .env from .env.example')


if __name__ == '__main__':
    main()
