import os
import sys


def check(name: str, passed: bool) -> bool:
    icon = "OK" if passed else "FAIL"
    print(f"{icon:4} {name}")
    return passed


def main() -> int:
    base = os.path.dirname(__file__)
    checks = []

    checks.append(check("Dockerfile exists", os.path.exists(os.path.join(base, "Dockerfile"))))
    checks.append(check("docker-compose.yml exists", os.path.exists(os.path.join(base, "docker-compose.yml"))))
    checks.append(check(".dockerignore exists", os.path.exists(os.path.join(base, ".dockerignore"))))
    checks.append(check(".env.example exists", os.path.exists(os.path.join(base, ".env.example"))))
    checks.append(check("deploy config exists", os.path.exists(os.path.join(base, "railway.toml")) or os.path.exists(os.path.join(base, "render.yaml"))))

    main_file = os.path.join(base, "app", "main.py")
    if os.path.exists(main_file):
        content = open(main_file, encoding="utf-8").read()
        checks.append(check("health endpoint defined", '"/health"' in content))
        checks.append(check("ready endpoint defined", '"/ready"' in content))
        checks.append(check("SIGTERM handled", "SIGTERM" in content))
        checks.append(check("structured logging present", "log_event(" in content))
    else:
        checks.append(check("main.py exists", False))

    dockerfile = os.path.join(base, "Dockerfile")
    if os.path.exists(dockerfile):
        content = open(dockerfile, encoding="utf-8").read()
        checks.append(check("multi-stage build", "AS builder" in content or "AS runtime" in content))
        checks.append(check("non-root user", "USER agent" in content))
        checks.append(check("healthcheck instruction", "HEALTHCHECK" in content))

    passed = sum(1 for item in checks if item)
    total = len(checks)
    print(f"\nResult: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
