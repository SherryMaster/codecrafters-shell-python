# Python Shell (Mini POSIX-Style REPL)

An educational shell implementation in Python that supports built-in commands, external command execution, history management, tab completion, redirection, and pipelines. The goal of this project is to provide a small, readable shell with practical features and clear behavior.

## Features

### Built-in Commands

- `exit [CODE]` — Exit the shell (default code: `0`).
- `echo [ARGS...]` — Print arguments to stdout.
- `type COMMAND` — Report whether a command is a shell builtin or a PATH-resolved executable.
- `pwd` — Print the current working directory.
- `cd PATH` — Change directory; `~` resolves to the home directory.
- `history` — Manage and display command history (see below).

### External Commands

If a command is not a builtin and exists in `PATH`, it is executed via `subprocess` with arguments parsed using shell-style rules.

### Command History

History is maintained in-memory using `readline` (or `pyreadline3` on Windows) and can optionally be persisted via the `HISTFILE` environment variable.

Supported history operations:

- `history` — list all entries
- `history N` — list the last `N` entries
- `history -r FILE` — read history entries from a file
- `history -a FILE` — append new in-memory entries to a file
- `history -w FILE` — write the full in-memory history to a file

### Tab Completion

Pressing `TAB` completes command names from:

- Built-in commands
- Executables found in `PATH`

If multiple matches exist, the first `TAB` rings the terminal bell and a second `TAB` prints matches.

### Output Redirection

Supports redirecting stdout or stderr:

- `> file` — overwrite
- `>> file` — append
- `2> file` — redirect stderr
- `2>> file` — append stderr

Examples:

- `echo hello > out.txt`
- `ls 2> errors.txt`

### Pipelines

Supports `|` to chain commands. Pipelines work for external commands and builtins. Builtins are executed in forked child processes to allow pipe-based I/O.

Example:

- `echo hello | tr a-z A-Z`

## Project Structure

- [app/main.py](app/main.py) — The shell implementation (REPL, parsing, builtins, history, redirection, pipelines, completion).
- [your_program.sh](your_program.sh) — Entrypoint script used by Codecrafters.
- [requirements.txt](requirements.txt) — Runtime dependencies (e.g., `pyreadline3` on Windows).

## Requirements

- Python 3.10+ (recommended)
- `readline` (Unix/macOS) or `pyreadline3` (Windows)

Install dependencies:

```
pip install -r requirements.txt
```

## Usage

Run the shell using the provided script:

```
./your_program.sh
```

You should see the prompt:

```
$
```

### Example Session

```
$ pwd
/path/to/project
$ echo hello world
hello world
$ type echo
echo is a shell builtin
$ ls | wc -l
12
$ echo hi > output.txt
$ history 5
    10  pwd
    11  echo hello world
    12  type echo
    13  ls | wc -l
    14  echo hi > output.txt
```

## Environment Variables

- `HISTFILE` — If set, history is loaded from this file on startup and saved on exit.

## Design Notes

- **Parsing**: Command lines are parsed with `shlex.split` to respect quoting and spacing rules.
- **Builtins vs External**: Builtins are handled in Python, external commands use `subprocess`.
- **Pipelines**: External commands use `subprocess.Popen`; builtins are executed in forked children to participate in pipelines.
- **Redirection**: Implemented by redirecting stdout/stderr to file objects for both builtins and external commands.

## Known Limitations

- This is a learning-oriented shell; it does not aim for full POSIX compliance.
- Windows support for pipelines involving builtins may be limited due to reliance on `os.fork`.

## Contributing

If you want to extend the shell:

1. Add or modify builtins in [app/main.py](app/main.py).
2. Keep behavior consistent with existing error messages and formatting.
3. Update this README with new features and usage examples.

## License

This project is provided for educational purposes. If you intend to publish it, add a license file appropriate for your use case.
