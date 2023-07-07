# twitter-clone-app

## how to install and use

Run below commands as administrator.

```bash
git clone https://github.com/strangerxxxx/twitter-clone-app.git
cd twitter-clone-app
pip install -r requirements.txt
cd mysite
python mysite/generate_secretkey_setting.py
python manage.py migrate
python manage.py runserver
```

and open http://127.0.0.1:8000/
