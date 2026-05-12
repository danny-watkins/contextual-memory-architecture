# Email Checker Agent

An agent that watches an inbox, classifies new messages, summarizes long threads, and routes notifications by urgency.

## What it does

1. Polls Gmail for new messages every five minutes (see [[skills/fetch_emails]]).
2. Classifies each message into one of the categories defined in [[docs/classification_taxonomy]].
3. Summarizes long threads using the prompt in [[prompts/summarize_thread]].
4. Routes notifications based on the rules in [[docs/decisions/notification_channels]].

## Architecture

See [[docs/architecture]] for the full design. Short version: stateless polling loop, LLM-backed classifier, channel-routed notifier.

## Files

- `agent.py` — entrypoint and main loop
- `skills/` — composable units the agent calls
- `prompts/` — LLM prompts, versioned
- `docs/` — design notes, decisions, taxonomy
