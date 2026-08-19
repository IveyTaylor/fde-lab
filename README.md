# fde-lab

A command-line chat client built directly against the Anthropic Messages API,
without a framework. Conversation history is maintained by hand and token usage
is printed every turn, making the cost of context growth visible.

Built as the first project in a self-directed curriculum on agent development.

## Setup

Requires Python 3.10+ and an Anthropic API key.

```bash
git clone https://github.com/YOUR-USERNAME/fde-lab.git
cd fde-lab
python -m venv .venv
source .venv/Scripts/activate    # Windows (Git Bash)
source .venv/bin/activate        # macOS / Linux
pip install -r requirements.txt
```

Create a file named `.env` in the project root:

ANTHROPIC_API_KEY=sk-ant-your-key-here


The virtual environment must be activated in every new terminal session.

## Running it

```bash
python chat.py
```

Type to chat. Each reply is followed by that turn's input and output token
counts. Type `quit` or `exit` to stop.

## What this demonstrates

The Messages API is stateless — there is no conversation stored server-side.
Memory is a list of role-tagged messages that the client rebuilds and re-sends
in full on every call.

Because the entire history is resent each turn, input tokens grow with
conversation length. In an eight-turn test, input tokens went from 28 to 90
while message length stayed roughly constant. Over a long-running agent session
this growth dominates cost and eventually exhausts the context window.

A bug found during development: omitting the assistant's turns from the history
does not raise an error. The model simply never sees its own replies and
re-answers every prior question. Output looked plausible while the payload was
wrong.