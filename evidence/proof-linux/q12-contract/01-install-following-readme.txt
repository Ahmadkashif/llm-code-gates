# Kit added to the sample repo following ONLY kit/README.md (2026-10-15). Paths shortened; tools from project-local dirs on PATH.
# Step 1: vendor the kit as gates/ (rsync of kit/ -> gates/) and run detect-env.sh
== host
os                     Linux 7.0.0-34-generic x86_64
cpus                   16
ram_gb                 31.1
gpu                    no nvidia-smi (Intel Corporation CometLake-S GT2 [UHD Graphics 630] (rev 05))
vram_gb                0
docker                 client 29.8.1
== tools on PATH
python3                Python 3.12.3
git                    git version 2.43.0
task                   3.54.0
semgrep                1.178.0
gitleaks               gitleaks version 8.30.1
osv-scanner            osv-scanner version: 2.7.0
actionlint             1.7.12
zizmor                 zizmor 1.30.1
syft                   syft 1.54.1
grype                  grype 0.120.1
shellcheck             ShellCheck - shell script analysis tool
hadolint               Haskell Dockerfile Linter 2.15.1
python>=3.11           yes
== judge endpoint
endpoint               GATES_JUDGE_BASE_URL not set
api key                not set
== repo (.)
stack                  python
Taskfile contract      check:fast check ci image 
== suggestion
stack profile          python
judge profile          stub
next: python3 gates/render.py --stack python --judge stub

# Step 2: site settings
$ cat .gates/site.env
GATES_LICENCE_OWNER=parcel-quote authors
GATES_HOST_VRAM_GB=0

# Step 3: render
$ python3 gates/render.py --stack python --judge stub
rendered stack=python (verified=True) judge=stub -> .gates/{config.env,judge.json}
$ python3 gates/render.py --check
checked 3 stack + 4 judge profiles, 7 prompts, 2 schemas
render --check: OK

# Step 4: wire the contract (diff in 02-taskfile-wiring.diff) + exclude gates/ from repo-wide tools (README step 4, added after the first run below failed on ruff linting the vendored kit)
diff --git a/pyproject.toml b/pyproject.toml
index 11d7bae..e85ec4b 100644
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -21,6 +21,7 @@ show_missing = true
 [tool.ruff]
 line-length = 120
 target-version = "py311"
+extend-exclude = ["gates"]
 
 [tool.ruff.lint]
 select = ["E", "F", "W", "B", "BLE", "S110", "UP"]

