# Contributing

Issues and pull requests are welcome. Keep changes focused on the local
relay, its documented protocol, or its skill. Include a unit test for
behavior changes and run this before opening a pull request:

```sh
python3 -m unittest discover -s tests -v
```

The Claude Code peer socket format is an observed internal interface.
When it changes, include the Claude Code and Codex versions used for the
reproduction. Do not include session tokens, private paths containing
secrets, or message contents from other users.
