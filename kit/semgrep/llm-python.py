# Semgrep test fixture for llm-python.yml (semgrep --test). Not executed.
import hashlib
import os
import pickle
import random
import ssl
import subprocess
import tempfile

import requests
import yaml


def swallow(x):
    # ruleid: gates.py.swallowed-broad-exception
    try:
        return int(x)
    except Exception:
        pass


def swallow_bare(x):
    # ruleid: gates.py.swallowed-broad-exception
    try:
        return int(x)
    except:
        return None


def specific(x):
    # ok: gates.py.swallowed-broad-exception
    try:
        return int(x)
    except ValueError:
        return None


def logged(x, log):
    # ok: gates.py.swallowed-broad-exception
    try:
        return int(x)
    except Exception as e:
        log.error("bad %s", e)
        raise


def tls(url):
    # ruleid: gates.py.tls-verify-disabled
    requests.get(url, verify=False)
    # ok: gates.py.tls-verify-disabled
    requests.get(url, timeout=5)
    # ruleid: gates.py.tls-verify-disabled
    return ssl._create_unverified_context()


def shell(name):
    # ruleid: gates.py.subprocess-shell-injection
    subprocess.run(f"ls {name}", shell=True)
    # ok: gates.py.subprocess-shell-injection
    subprocess.run(["ls", name])
    # ok: gates.py.subprocess-shell-injection
    subprocess.run("ls -l", shell=True)
    # ruleid: gates.py.subprocess-shell-injection
    os.system("rm " + name)


def sql(cur, user):
    # ruleid: gates.py.sql-string-formatting
    cur.execute(f"SELECT * FROM users WHERE name = '{user}'")
    # ruleid: gates.py.sql-string-formatting
    cur.execute("SELECT * FROM users WHERE name = '%s'" % user)
    # ok: gates.py.sql-string-formatting
    cur.execute("SELECT * FROM users WHERE name = ?", (user,))


def deser(blob, text):
    # ruleid: gates.py.unsafe-deserialisation
    pickle.loads(blob)
    # ruleid: gates.py.unsafe-deserialisation
    yaml.load(text)
    # ok: gates.py.unsafe-deserialisation
    yaml.load(text, Loader=yaml.SafeLoader)
    # ok: gates.py.unsafe-deserialisation
    return yaml.safe_load(text)


def ev(expr):
    # ruleid: gates.py.eval-exec
    return eval(expr)


def tokens():
    # ruleid: gates.py.weak-random-for-secrets
    reset_token = "".join(random.choice("abc") for _ in range(16))
    # ok: gates.py.weak-random-for-secrets
    jitter = random.random()
    return reset_token, jitter


def hashing(password, data):
    # ruleid: gates.py.weak-hash-for-passwords
    stored = hashlib.md5(password.encode()).hexdigest()
    # ok: gates.py.weak-hash-for-passwords
    etag = hashlib.sha256(data).hexdigest()
    return stored, etag


def run_app(app):
    # ruleid: gates.py.flask-debug-or-bind-all
    app.run(debug=True)


# ruleid: gates.py.placeholder-implementation
def compute_refund(order):
    raise NotImplementedError("TODO")


def check(request):
    # ruleid: gates.py.assert-for-validation
    assert request.user.is_admin, "admin only"
    return True


def tmp():
    # ruleid: gates.py.hardcoded-tmp-path
    p = tempfile.mktemp()
    # ok: gates.py.hardcoded-tmp-path
    fd, q = tempfile.mkstemp()
    return p, fd, q
