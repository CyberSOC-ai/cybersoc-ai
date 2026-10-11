"""Check tracked text for merge conflicts and Markdown links to missing files."""

from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit


def main():
    root = Path(__file__).resolve().parents[2]
    tracked = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=root
    ).decode().split("\0")
    errors = []
    checked = 0
    for name in filter(None, tracked):
        path = root / name
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        checked += 1
        for number, line in enumerate(content.splitlines(), 1):
            if re.match(r"^(?:<{7}|={7}|>{7})(?:\s|$)", line):
                errors.append(f"{name}:{number}: unresolved merge conflict")
        if path.suffix.lower() != ".md":
            continue
        # Ignore fenced code examples; validate inline Markdown file links.
        prose = re.sub(r"(?ms)^```[^\n]*\n.*?^```[^\n]*$", "", content)
        for match in re.finditer(r"\[[^\]\n]*\]\(([^\s)]+)\)", prose):
            target = match.group(1).strip("<>")
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            destination = (root if url.path.startswith("/") else path.parent)
            destination = destination / unquote(url.path.lstrip("/"))
            if not destination.exists():
                errors.append(f"{name}: missing link target {target}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Repository integrity passed: {checked} tracked text files checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
