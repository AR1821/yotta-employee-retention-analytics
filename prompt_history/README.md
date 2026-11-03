# Prompt history

The challenge rules ask for every prompt submitted to every AI tool used
on this project. This folder holds that record.

| File | Tool | How it was produced |
|---|---|---|
| `claude_code_prompts.md` | Claude Code (Anthropic) | Exported from the local session log with `export_claude_code_prompts.py` |
| `other_assistant/` | Chat assistant used for stage-by-stage planning | Exported from that tool by the author (see below) |

## How the two tools were used

1. **Planning assistant (chat).** Used from the start to plan the stages
   (architecture, schema, generator, validation, scoring, API, frontend)
   and to draft code for each stage, which was then run and adapted
   locally.
2. **Claude Code.** Used once the backend existed (from Stage 7.4 onward)
   to apply the planned changes to the real codebase, debug integration
   problems, test the API and UI end to end, and prepare the repository.
   Several Claude Code prompts paste the planning assistant's
   instructions; Claude Code often changed those instructions after
   reading the existing code (for example, adding backend summary
   endpoints instead of loading 10,000 records in the browser). Those
   deviations are listed in the main README.

## Re-exporting the Claude Code prompts

```powershell
python prompt_history/export_claude_code_prompts.py `
  "$env:USERPROFILE\.claude\projects\<project-folder>\<session-id>.jsonl" `
  prompt_history/claude_code_prompts.md
```

## Known limitations

- The Claude Code export covers prompts up to the time it was generated;
  it is re-run before the final commit.
- Answers given through Claude Code's multiple-choice questions (for
  example, choosing the commit email) are tool interactions rather than
  typed prompts and are not part of the export.
