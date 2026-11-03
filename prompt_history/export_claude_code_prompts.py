"""Export the prompts typed into a Claude Code session to Markdown.

Usage:
    python export_claude_code_prompts.py <session.jsonl> <output.md>

Claude Code stores each session as JSON lines under
~/.claude/projects/<project>/<session-id>.jsonl. Only messages typed by
the user are exported: tool results, AI responses and text injected by
the tool itself (<system-reminder> blocks) are left out.
"""

import json
import re
import sys
from pathlib import Path

INJECTED = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL)


def user_prompts(path: Path):
    with path.open(encoding="utf-8") as file:
        for line in file:
            entry = json.loads(line)

            if entry.get("type") != "user" or entry.get("isMeta"):
                continue

            content = entry.get("message", {}).get("content")

            if isinstance(content, str):
                text = content
            elif isinstance(content, list) and all(
                block.get("type") == "text" for block in content
            ):
                text = "\n".join(block["text"] for block in content)
            else:
                continue  # tool results

            text = INJECTED.sub("", text).strip()

            if text:
                yield entry.get("timestamp", ""), text


def main():
    source, target = Path(sys.argv[1]), Path(sys.argv[2])
    prompts = list(user_prompts(source))

    lines = [
        "# Claude Code prompt history",
        "",
        f"Session: `{source.stem}`  ",
        "Tool: Claude Code (CLI agent with file, shell and browser access)  ",
        f"Prompts: {len(prompts)} (timestamps in UTC)",
        "",
        "Exported verbatim with `export_claude_code_prompts.py`. AI responses",
        "are not included. Several prompts paste instructions that were",
        "produced by a separate assistant; see README.md in this folder.",
        "",
    ]

    for number, (timestamp, text) in enumerate(prompts, start=1):
        lines += [
            "---",
            "",
            f"## Prompt {number} · {timestamp}",
            "",
            "````text",
            text,
            "````",
            "",
        ]

    target.write_text("\n".join(lines), encoding="utf-8")
    print(f"Exported {len(prompts)} prompts to {target}")


if __name__ == "__main__":
    main()
