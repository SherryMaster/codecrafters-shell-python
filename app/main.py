import sys  # Core Python runtime access (stdout/stderr redirection, exit handling)
import os  # OS-level utilities (cwd, environment, pipes, fork)
import subprocess  # Run external commands and manage processes
import shutil  # Utilities like which() for PATH lookup
import shlex  # Shell-like parsing of command lines
import re  # Regular expressions for redirection parsing
try:
    import readline  # GNU readline (history + completion) when available
except ImportError:  # Windows: use pyreadline3
    import pyreadline3 as readline  # Fallback for Windows to support readline API

# NOTE: This file intentionally implements a minimal shell with built-ins,
# history, completion, redirection, and pipelines. The comments explain why
# each operation exists so future readers can re-orient quickly.

def write_history_file(history_path):
    """
    Write the in-memory readline history to a file on disk.

    This function persists all readline history entries to the specified file path,
    allowing command history to survive shell restarts. Each history entry is written
    on a separate line.

    Args:
        history_path (str): The file path where history should be written.

    Raises:
        Prints an error message to stdout if a filesystem error occurs (e.g., 
        permission denied, invalid path), but does not raise an exception.

    Note:
        - Overwrites the entire history file on each call
        - Readline history indices are 1-based, so iteration starts from 1
        - None values in history are normalized to empty strings to maintain alignment
    """
    try:
        total = readline.get_current_history_length()  # Read total history entries
        with open(history_path, "w", encoding="utf-8") as history_file:  # Overwrite file
            for i in range(1, total + 1):  # Readline history is 1-indexed
                item = readline.get_history_item(i)  # Fetch the i-th history entry
                if item is None:
                    item = ""  # Normalize None to empty line to keep indices aligned
                history_file.write(item + "\n")  # One entry per line
    except OSError as e:
        print(f"history: {history_path}: {e}")  # Surface filesystem errors to user

def exit_command(code=0):
    """
    Exit the shell with the specified exit code.
    
    Before terminating, this function persists the command history to disk if a history
    file path is configured. The history file path is determined by the `_history_path`
    variable or the `HISTFILE` environment variable.
    
    Args:
        code (int, optional): The exit code to return when terminating the process. 
                            Defaults to 0 (success).
    
    Note:
        Uses `os._exit()` instead of `sys.exit()` to avoid raising SystemExit exceptions
        in child processes, ensuring a clean termination of the shell process.
    """
    history_path = _history_path or os.environ.get("HISTFILE")
    if history_path:
        write_history_file(history_path)  # Persist history to disk
    os._exit(code)  # Use os._exit to avoid throwing SystemExit in child processes

def echo_command(*args):
    """
    Prints the given arguments to standard output, separated by spaces.
    
    Mimics the behavior of the shell's echo command by joining all provided
    arguments with spaces and printing them.
    
    Args:
        *args: Variable length argument list of strings to be printed.
    
    Returns:
        None
    """
    print(" ".join(args))  # Mimic shell echo: join arguments with spaces

def type_command(command):
    """
    Determine if the given command is a built-in or an executable in PATH.
    
    Mimics the behavior of the `type` command in common shells by identifying
    where a command resolves to and printing the result.
    
    Args:
        command (str): The command name to look up.
    
    Returns:
        None
        
    Prints:
        - "{command} is a shell builtin" if the command is a built-in
        - "{command} is {path}" if the command is found in PATH
        - "{command}: not found" if the command is neither a built-in nor in PATH
    """
    if command in commands:
        print(f"{command} is a shell builtin")  # Builtins are implemented in Python
    elif shutil.which(command) is not None:
        print(f"{command} is {shutil.which(command)}")  # Print resolved executable path
    else:
        print(f"{command}: not found")  # No builtin and not in PATH

def pwd_command():
    """
    Print the current working directory to standard output.
    
    This function retrieves and displays the absolute path of the current working
    directory by delegating to the operating system's getcwd() function.
    
    Returns:
        None
    """
    print(os.getcwd())  # Delegate to OS for current working directory

def cd_command(path):
    """
    Change the current working directory to the specified path.
    
    Args:
        path (str): The directory path to change to. Can be an absolute path,
                   relative path, or "~" to denote the user's home directory.
    
    Returns:
        None
    
    Raises:
        No exceptions are raised. Instead, an error message is printed to stdout
        if the path does not exist or is not a directory.
    
    Examples:
        >>> cd_command("/home/user/documents")  # Changes to /home/user/documents
        >>> cd_command("~")  # Changes to user's home directory
        >>> cd_command("/nonexistent/path")
        cd: /nonexistent/path: No such file or directory
    """
    if os.path.exists(path) and os.path.isdir(path):
        os.chdir(path)  # Valid directory -> change into it
    elif path == "~":
        os.chdir(os.path.expanduser("~"))  # Tilde -> user's home
    else:
        print(f"cd: {path}: No such file or directory")  # Match shell error style

def history_command(*args):
    """
    Execute history command with various options to manage shell command history.
    This function mirrors the bash `history` command behavior used by Codecrafters.
    It supports reading, appending, writing, and displaying command history using
    the readline module.
    Args:
        *args: Variable length argument list. The first argument can be:
            - "-r": Read history from file. Second argument is the file path.
            - "-a": Append new history entries to file. Second argument is the file path.
            - "-w": Overwrite file with all history entries. Second argument is the file path.
            - A number: Display the last N history entries.
            - Empty or invalid: Display all history entries.
    Returns:
        None
    Raises:
        OSError: Caught and printed as error messages when file operations fail.
    Side Effects:
        - With "-r": Loads history entries from specified file into readline.
        - With "-a": Appends new history entries to specified file and updates _history_append_index.
        - With "-w": Overwrites specified file with all current history entries.
        - Without flags: Prints history entries to stdout in bash format.
        - Modifies global variable _history_append_index when using "-a" option.
    Notes:
        - Empty lines are skipped when reading history with "-r".
        - None entries in history are normalized to empty strings.
        - History item numbering starts at 1 (matches bash behavior).
        - Output format: "    {index}  {command}"
    """
    # This function mirrors the bash `history` command behavior used by Codecrafters.
    global _history_append_index
    if len(args) >= 2 and args[0] == "-r":
        history_path = args[1]  # File to read into history
        try:
            with open(history_path, "r", encoding="utf-8") as history_file:
                for raw_line in history_file:
                    line = raw_line.rstrip("\n")  # Strip newline only
                    if line == "":
                        continue  # Skip empty lines to avoid blank commands
                    readline.add_history(line)  # Load each entry into readline
        except OSError as e:
            print(f"history: {history_path}: {e}")
        return

    if len(args) >= 2 and args[0] == "-a":
        history_path = args[1]  # File to append to
        try:
            total = readline.get_current_history_length()  # Current history count
            start = max(1, _history_append_index + 1)  # Append only new entries
            if start <= total:
                with open(history_path, "a", encoding="utf-8") as history_file:
                    for i in range(start, total + 1):
                        item = readline.get_history_item(i)
                        if item is None:
                            item = ""  # Normalize None entries
                        history_file.write(item + "\n")  # Append entries
            _history_append_index = total  # Update index for next append call
        except OSError as e:
            print(f"history: {history_path}: {e}")
        return

    if len(args) >= 2 and args[0] == "-w":
        history_path = args[1]  # File to overwrite with all history
        try:
            total = readline.get_current_history_length()  # Total entries
            with open(history_path, "w", encoding="utf-8") as history_file:
                for i in range(1, total + 1):
                    item = readline.get_history_item(i)
                    if item is None:
                        item = ""  # Normalize None entries
                    history_file.write(item + "\n")  # Write each entry
        except OSError as e:
            print(f"history: {history_path}: {e}")
        return

    total = readline.get_current_history_length()  # Number of entries to display

    limit = None  # Default: show all entries
    if len(args) >= 1:
        try:
            limit = int(args[0])  # Parse requested count
        except ValueError:
            limit = None  # Invalid number -> fall back to full history

    if limit is None or limit < 0:
        start = 1  # Show from first entry if no valid limit
    else:
        start = max(1, total - limit + 1)  # Show only last N entries

    for i in range(start, total + 1):
        print(f"    {i}  {readline.get_history_item(i)}")  # Format matches bash

def run_executable(command, args, output_file=None, fd="1", append=False):
    """
    Execute a command with optional output redirection.
    
    Args:
        command (str): The name or path of the executable to run.
        args (list): List of arguments to pass to the command.
        output_file (str, optional): Path to file for output redirection. Defaults to None.
        fd (str, optional): File descriptor to redirect ("1" for stdout, "2" for stderr). Defaults to "1".
        append (bool, optional): If True, append to output_file; if False, overwrite. Defaults to False.
    
    Returns:
        None
    
    Raises:
        Prints error message in shell-style format if command execution fails.
    """
    try:
        if output_file:
            redirect_output(command, args, output_file, fd=fd, append=append)
        else:
            result = subprocess.run([command, *args])  # Inherit stdout/stderr
    except Exception as e:
        print(f"{command}: {e}")  # Match shell-style error reporting

def redirect_output(command, args, output_file, fd="1", append=False):
    """
    Executes a command with arguments and redirects its output to a specified file.

    Args:
        command (str): The command to execute.
        args (list): List of arguments for the command.
        output_file (str): Path to the file where output will be redirected.
        fd (str, optional): File descriptor to redirect ('1' for stdout, '2' for stderr). Defaults to "1".
        append (bool, optional): If True, appends to the file; otherwise, overwrites. Defaults to False.

    Returns:
        None
    """
    mode = "a" if append else "w"  # Append vs truncate based on >> or >
    with open(output_file, mode) as f:
        if fd == "1":
            result = subprocess.run([command, *args], stdout=f)  # Redirect stdout
        elif fd == "2":
            result = subprocess.run([command, *args], stderr=f)  # Redirect stderr

def execute_builtin(command, args, output_file=None, fd="1", append=False):
    """
    Executes a built-in shell command, optionally redirecting output to a file.

    Args:
        command (str): The name of the built-in command to execute.
        args (list): Arguments to pass to the command function.
        output_file (str, optional): Path to the file for output redirection. Defaults to None.
        fd (str, optional): File descriptor to redirect ('1' for stdout, '2' for stderr). Defaults to "1".
        append (bool, optional): If True, appends to the output file; otherwise, overwrites. Defaults to False.

    Returns:
        None

    Side Effects:
        Executes the specified built-in command, optionally redirecting stdout or stderr to a file.
    """
    if output_file:
        # Redirect stdout or stderr to file (for builtins, done manually).
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        with open(output_file, "a" if append else "w") as f:
            if fd == "1":
                sys.stdout = f  # Redirect stdout for builtins
            elif fd == "2":
                sys.stderr = f  # Redirect stderr for builtins
            commands[command](*args)  # Execute builtin with redirected streams
            sys.stdout = original_stdout  # Restore stdout
            sys.stderr = original_stderr  # Restore stderr
    else:
        commands[command](*args)  # Execute builtin normally

def run_pipeline(line):
    """
    Executes a shell pipeline described by the input line.
    This function parses the pipeline stages separated by '|', determines whether any stage is a shell builtin,
    and executes the pipeline accordingly. If no builtins are present, the pipeline is delegated to the system shell.
    If builtins are present, each stage is executed in a subprocess, with proper piping of stdin and stdout between stages.
    Args:
        line (str): The command line string representing the pipeline (e.g., "cat file.txt | grep foo | wc -l").
    Behavior:
        - Splits the pipeline into stages.
        - Detects if any stage is a shell builtin.
        - If no builtins, delegates execution to the system shell.
        - If builtins are present, forks subprocesses for each stage, sets up pipes for inter-process communication,
          and executes builtins or external commands as appropriate.
        - Waits for all subprocesses to finish before returning.
    Note:
        - Builtin commands are executed in child processes to support pipeline semantics.
        - External commands are executed using subprocess.Popen.
        - Properly manages file descriptors and process cleanup.
    """
    pipeline_parts = line.split("|")  # Split pipeline into stages
    num_cmds = len(pipeline_parts)  # Total number of pipeline commands
    processes = []  # Track child processes so we can wait later

    # If the pipeline has no builtins, delegate to the system shell.
    has_builtin = False  # Use this to decide if we can delegate to system shell
    for part in pipeline_parts:
        cmd_args = shlex.split(part.strip())  # Parse each stage like a shell
        if cmd_args and cmd_args[0] in commands:
            has_builtin = True
            break

    if not has_builtin:
        subprocess.run(line, shell=True)  # Fast-path to system shell
        return

    for i, part in enumerate(pipeline_parts):
        cmd_args = shlex.split(part.strip())  # Parse current stage
        if not cmd_args:
            continue  # Skip empty segments like "||"

        cmd_name = cmd_args[0]  # The program or builtin name
        is_builtin = cmd_name in commands  # Determine if we handle internally

        stdin_pipe = processes[-1].stdout if i > 0 else None  # Pipe from prev stage
        stdout_pipe = subprocess.PIPE if i < num_cmds - 1 else None  # Pipe to next

        if is_builtin:
            # Builtins run in this process, but pipelines require separate fds,
            # so we fork a child process to hook stdin/stdout to pipes.
            read_fd = None
            write_fd = None

            # Set up the stdout pipe for this builtin if it's not the last cmd
            if i < num_cmds - 1:
                r, w = os.pipe()  # Create pipe for this builtin's output
                read_fd = r
                write_fd = w

            pid = os.fork()
            if pid == 0:
                # Child process (executes builtin with pipe-based I/O)
                # Redirect stdin if we have input from a previous command
                if stdin_pipe is not None:
                    os.dup2(stdin_pipe.fileno(), 0)  # Replace stdin with pipe
                    stdin_pipe.close()

                # Redirect stdout if not the last command
                if write_fd is not None:
                    os.close(read_fd)  # Close read end in child
                    os.dup2(write_fd, 1)  # Replace stdout with pipe
                    os.close(write_fd)

                # Re-bind sys.stdout/sys.stdin to the new fds
                sys.stdin = os.fdopen(0, "r")
                sys.stdout = os.fdopen(1, "w")

                commands[cmd_name](*cmd_args[1:])  # Execute builtin
                sys.stdout.flush()  # Ensure pipeline output is flushed
                os._exit(0)  # Exit child without cleanup of parent state
            else:
                # Parent process
                # Close the stdin pipe from previous process in parent
                if stdin_pipe is not None:
                    stdin_pipe.close()

                if write_fd is not None:
                    os.close(write_fd)  # Close write end in parent
                    # Create a file object from read_fd so it looks like
                    # a Popen.stdout for the next stage
                    read_file = os.fdopen(read_fd, "r")
                else:
                    read_file = None

                # Create a simple wrapper to mimic Popen interface
                class FakeProc:
                    def __init__(self, pid, stdout):
                        self.pid = pid
                        self.stdout = stdout
                    def wait(self):
                        os.waitpid(self.pid, 0)  # Wait for child to finish

                processes.append(FakeProc(pid, read_file))  # Track this builtin
        else:
            # External command
            proc = subprocess.Popen(
                cmd_args,
                stdin=stdin_pipe,
                stdout=stdout_pipe,
            )
            processes.append(proc)  # Track external process

            # Close the previous process's stdout in the parent so that
            # the pipe can signal EOF when the writer finishes.
            if i > 0 and stdin_pipe is not None:
                stdin_pipe.close()

    # Wait for all processes to finish so the pipeline completes before prompt
    for proc in processes:
        proc.wait()

def complete_command(text, state):
    """
    Provides command-line completion for shell commands.
    Args:
        text (str): The current input text to complete.
        state (int): The completion state, used by readline to iterate through possible completions.
    Returns:
        str or None: The completed command string, possibly with a trailing space if a single match is found,
        or the longest common prefix if multiple matches exist. Returns None if no matches are found or if
        completion should be suppressed for subsequent states.
    Behavior:
        - On the first completion attempt (state == 0), searches for commands matching the input text among
          built-in commands and executables found in directories listed in the PATH environment variable.
        - If only one match is found, returns the match with a trailing space.
        - If multiple matches are found, returns the longest common prefix (LCP) if it extends the input text.
        - If the LCP equals the input text, rings the terminal bell on the first TAB press, and prints the list
          of possible matches on the second TAB press.
        - For subsequent completion states, suppresses readline insertion by returning None.
    Side Effects:
        - May write to stdout to ring the terminal bell or print possible matches.
        - Stores internal state for handling repeated TAB presses.
    """
    if state == 0:
        options = [cmd for cmd in commands if cmd.startswith(text)]  # Builtins

        # Include commands found in PATH
        for path in os.environ["PATH"].split(os.pathsep):
            try:
                path_commands = [
                    cmd for cmd in os.listdir(path)
                    if cmd.startswith(text) and os.access(os.path.join(path, cmd), os.X_OK)
                ]
                options.extend(path_commands)  # Merge PATH commands with builtins
            except FileNotFoundError:
                continue  # Ignore directories that do not exist

        options = sorted(set(options))  # Unique + sorted for stable completion
        complete_command._last_matches = options
        complete_command._last_text = text

        # No matches -> nothing to do
        if not options:
            return None

        # Single match -> let readline insert it with trailing space
        if len(options) == 1:
            return options[0] + " "

        # Multiple matches: compute the longest common prefix (LCP)
        lcp = os.path.commonprefix(options)

        if len(lcp) > len(text):
            # LCP is longer than what the user typed -> complete to LCP
            # Return the LCP; no trailing space since multiple matches remain
            complete_command._last_tab_text = None
            complete_command._last_tab_bell = False
            return lcp

        # LCP == text: no progress can be made
        # First TAB: ring bell, second TAB: print list
        last_text = getattr(complete_command, "_last_tab_text", None)
        last_bell = getattr(complete_command, "_last_tab_bell", False)

        if last_text == text and last_bell:
            # Second TAB: print matches
            buffer = readline.get_line_buffer()
            sys.stdout.write("\n" + "  ".join(options) + "\n$ " + buffer)
            sys.stdout.flush()
            complete_command._last_tab_bell = False
        else:
            # First TAB: ring bell
            sys.stdout.write("\x07")
            sys.stdout.flush()
            complete_command._last_tab_text = text
            complete_command._last_tab_bell = True

        return None

    # For multiple matches we suppress readline insertion on subsequent states
    return None

commands = {
    "exit": exit_command,  # Terminate the shell
    "echo": echo_command,  # Print arguments
    "type": type_command,  # Identify builtin vs external command
    "pwd": pwd_command,  # Print current directory
    "cd": cd_command,  # Change directory
    "history": history_command,  # Manage command history
}

_history_append_index = 0  # Track last persisted history index for -a
_history_path = None  # Cache history file path for exit

def main():
    """
    Main entry point for the shell application.
    - Configures readline for command completion, history, and keybindings.
    - Loads command history from a file specified by the HISTFILE environment variable.
    - Enters a REPL loop, prompting the user for input.
    - Adds each non-empty input line to the history.
    - Handles command pipelines (|), file descriptor redirection (> and >>), and command parsing.
    - Executes external commands, built-in commands, or prints an error if the command is not found.
    """
    # Configure readline completion behavior.
    readline.set_completer(complete_command)  # Set the auto-completion function
    readline.parse_and_bind("tab: complete")  # Enable tab completion
    readline.parse_and_bind("set editing-mode emacs")  # Consistent keybindings
    readline.parse_and_bind("set keymap emacs")  # Emacs-style navigation
    if hasattr(readline, "set_auto_history"):
        readline.set_auto_history(False)  # We manually manage history persistence

    history_path = os.environ.get("HISTFILE")  # Read history file location
    if history_path:
        try:
            with open(history_path, "r", encoding="utf-8") as history_file:
                for raw_line in history_file:
                    line = raw_line.rstrip("\n")  # Remove trailing newline
                    if line == "":
                        continue  # Skip empty history entries
                    readline.add_history(line)  # Load entry into readline
        except FileNotFoundError:
            pass  # No history file yet is fine
        except OSError as e:
            print(f"history: {history_path}: {e}")  # Report read errors

        global _history_append_index, _history_path
        _history_append_index = readline.get_current_history_length()  # Save index
        _history_path = history_path  # Cache path for exit handling
    
    while True:
        line = input("$ ")  # Display prompt and read user input
        if not line:
            continue  # Ignore empty lines

        readline.add_history(line)  # Always add non-empty input to history

        # Check for pipeline (|) operator
        if "|" in line:
            run_pipeline(line)  # Delegate to pipeline handler
            continue

        # Match file descriptor (optional digit) followed by > or >>
        redirect_match = re.search(r"\s*(\d*)(>>|>)\s*(.*)", line)
        
        if redirect_match:
            command_part = line[:redirect_match.start()].strip()  # Command before redirection
            output_file = redirect_match.group(3).strip()  # File after redirection
            command_with_args = shlex.split(command_part)  # Parse command args
            
            fd = redirect_match.group(1) if redirect_match.group(1) else "1"  # Default to stdout
            append = redirect_match.group(2) == ">>"  # Append if >>
        else:
            command_with_args = shlex.split(line)  # No redirection -> parse full line
            output_file = None  # No output file
            fd = "1"  # Default to stdout
            append = False  # Overwrite by default

        if not command_with_args:
            continue  # Nothing to execute
        
        command = command_with_args[0]  # Command name
        
        if shutil.which(command) is not None:
            run_executable(command, command_with_args[1:], output_file=output_file, fd=fd, append=append)
        elif command not in commands:
            print(f"{command}: command not found")  # Match shell error message
        else:
            execute_builtin(command, command_with_args[1:], output_file=output_file, fd=fd, append=append)

if __name__ == "__main__":
    main()  # Entry point for running as a script
