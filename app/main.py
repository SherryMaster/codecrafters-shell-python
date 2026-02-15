import sys
import os
import subprocess
import shutil
import shlex
import re
try:
    import readline
except ImportError:  # Windows: use pyreadline3
    import pyreadline3 as readline

def exit_command(code=0):
    """Exit the shell with the given exit code."""
    os._exit(code)

def echo_command(*args):
    """Print the given arguments to standard output."""
    print(" ".join(args))

def type_command(command):
    """Determine if the given command is a built-in or an executable in PATH."""
    if command in commands:
        print(f"{command} is a shell builtin")
    elif shutil.which(command) is not None:
        print(f"{command} is {shutil.which(command)}")
    else:
        print(f"{command}: not found")

def pwd_command():
    """Print the current working directory."""
    print(os.getcwd())

def cd_command(path):
    """Change the current working directory to the given path."""
    if os.path.exists(path) and os.path.isdir(path):
        os.chdir(path)
    elif path == "~":
        os.chdir(os.path.expanduser("~"))
    else:
        print(f"cd: {path}: No such file or directory")

def history_command(*args):
    """List previously executed commands."""
    global _history_append_index
    if len(args) >= 2 and args[0] == "-r":
        history_path = args[1]
        try:
            with open(history_path, "r", encoding="utf-8") as history_file:
                for raw_line in history_file:
                    line = raw_line.rstrip("\n")
                    if line == "":
                        continue
                    readline.add_history(line)
        except OSError as e:
            print(f"history: {history_path}: {e}")
        return

    if len(args) >= 2 and args[0] == "-a":
        history_path = args[1]
        try:
            total = readline.get_current_history_length()
            start = max(1, _history_append_index + 1)
            if start <= total:
                with open(history_path, "a", encoding="utf-8") as history_file:
                    for i in range(start, total + 1):
                        item = readline.get_history_item(i)
                        if item is None:
                            item = ""
                        history_file.write(item + "\n")
            _history_append_index = total
        except OSError as e:
            print(f"history: {history_path}: {e}")
        return

    if len(args) >= 2 and args[0] == "-w":
        history_path = args[1]
        try:
            total = readline.get_current_history_length()
            with open(history_path, "w", encoding="utf-8") as history_file:
                for i in range(1, total + 1):
                    item = readline.get_history_item(i)
                    if item is None:
                        item = ""
                    history_file.write(item + "\n")
        except OSError as e:
            print(f"history: {history_path}: {e}")
        return

    total = readline.get_current_history_length()

    limit = None
    if len(args) >= 1:
        try:
            limit = int(args[0])
        except ValueError:
            limit = None

    if limit is None or limit < 0:
        start = 1
    else:
        start = max(1, total - limit + 1)

    for i in range(start, total + 1):
        print(f"    {i}  {readline.get_history_item(i)}")

def run_executable(command, args, output_file=None, fd="1", append=False):
    """Run the given command as an executable."""
    try:
        if output_file:
            redirect_output(command, args, output_file, fd=fd, append=append)
        else:
            result = subprocess.run([command, *args])
    except Exception as e:
        print(f"{command}: {e}")

def redirect_output(command, args, output_file, fd="1", append=False):
    """Run the command and redirect its output to the specified file."""
    mode = 'a' if append else 'w'
    with open(output_file, mode) as f:
        if fd == "1":
            result = subprocess.run([command, *args], stdout=f)
        elif fd == "2":
            result = subprocess.run([command, *args], stderr=f)

def execute_builtin(command, args, output_file=None, fd="1", append=False):
    """Execute a built-in command with optional output redirection."""
    if output_file:
        # Redirect stdout or stderr to file
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        with open(output_file, 'a' if append else 'w') as f:
            if fd == "1":
                sys.stdout = f
            elif fd == "2":
                sys.stderr = f
            commands[command](*args)
            sys.stdout = original_stdout
            sys.stderr = original_stderr
    else:
        commands[command](*args)

def run_pipeline(line):
    """Execute a pipeline of commands connected by pipes."""
    pipeline_parts = line.split('|')
    num_cmds = len(pipeline_parts)
    processes = []

    # If the pipeline has no builtins, delegate to the system shell.
    has_builtin = False
    for part in pipeline_parts:
        cmd_args = shlex.split(part.strip())
        if cmd_args and cmd_args[0] in commands:
            has_builtin = True
            break

    if not has_builtin:
        subprocess.run(line, shell=True)
        return

    for i, part in enumerate(pipeline_parts):
        cmd_args = shlex.split(part.strip())
        if not cmd_args:
            continue

        cmd_name = cmd_args[0]
        is_builtin = cmd_name in commands

        stdin_pipe = processes[-1].stdout if i > 0 else None
        stdout_pipe = subprocess.PIPE if i < num_cmds - 1 else None

        if is_builtin:
            # For built-in commands, we need to fork so we can connect
            # their stdin/stdout to the pipeline pipes.
            read_fd = None
            write_fd = None

            # Set up the stdout pipe for this builtin if it's not the last cmd
            if i < num_cmds - 1:
                r, w = os.pipe()
                read_fd = r
                write_fd = w

            pid = os.fork()
            if pid == 0:
                # Child process
                # Redirect stdin if we have input from a previous command
                if stdin_pipe is not None:
                    os.dup2(stdin_pipe.fileno(), 0)
                    stdin_pipe.close()

                # Redirect stdout if not the last command
                if write_fd is not None:
                    os.close(read_fd)
                    os.dup2(write_fd, 1)
                    os.close(write_fd)

                # Re-bind sys.stdout/sys.stdin to the new fds
                sys.stdin = os.fdopen(0, 'r')
                sys.stdout = os.fdopen(1, 'w')

                commands[cmd_name](*cmd_args[1:])
                sys.stdout.flush()
                os._exit(0)
            else:
                # Parent process
                # Close the stdin pipe from previous process in parent
                if stdin_pipe is not None:
                    stdin_pipe.close()

                if write_fd is not None:
                    os.close(write_fd)
                    # Create a file object from read_fd so it looks like
                    # a Popen.stdout for the next stage
                    read_file = os.fdopen(read_fd, 'r')
                else:
                    read_file = None

                # Create a simple wrapper to mimic Popen interface
                class FakeProc:
                    def __init__(self, pid, stdout):
                        self.pid = pid
                        self.stdout = stdout
                    def wait(self):
                        os.waitpid(self.pid, 0)

                processes.append(FakeProc(pid, read_file))
        else:
            # External command
            proc = subprocess.Popen(
                cmd_args,
                stdin=stdin_pipe,
                stdout=stdout_pipe,
            )
            processes.append(proc)

            # Close the previous process's stdout in the parent so that
            # the pipe can signal EOF when the writer finishes.
            if i > 0 and stdin_pipe is not None:
                stdin_pipe.close()

    # Wait for all processes to finish
    for proc in processes:
        proc.wait()

def complete_command(text, state):
    """Auto-completion function for the shell."""
    # Build matches once per completion cycle (state == 0)
    if state == 0:
        options = [cmd for cmd in commands if cmd.startswith(text)]

        # Include commands found in PATH
        for path in os.environ["PATH"].split(os.pathsep):
            try:
                path_commands = [
                    cmd for cmd in os.listdir(path)
                    if cmd.startswith(text) and os.access(os.path.join(path, cmd), os.X_OK)
                ]
                options.extend(path_commands)
            except FileNotFoundError:
                continue  # Ignore directories that do not exist

        options = sorted(set(options))
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
    "exit": exit_command,
    "echo": echo_command,
    "type": type_command,
    "pwd": pwd_command,
    "cd": cd_command,
    "history": history_command,
}

_history_append_index = 0

def main():
    readline.set_completer(complete_command) # Set the auto-completion function
    readline.parse_and_bind("tab: complete") # Enable tab completion
    readline.parse_and_bind("set editing-mode emacs")
    readline.parse_and_bind("set keymap emacs")
    if hasattr(readline, "set_auto_history"):
        readline.set_auto_history(False)
    
    while True:
        line = input("$ ")
        if not line:
            continue

        readline.add_history(line)

        # Check for pipeline (|) operator
        if '|' in line:
            run_pipeline(line)
            continue

        # Match file descriptor (optional digit) followed by >
        redirect_match = re.search(r'\s*(\d*)(>>|>)\s*(.*)', line)
        
        if redirect_match:
            command_part = line[:redirect_match.start()].strip()
            output_file = redirect_match.group(3).strip()
            command_with_args = shlex.split(command_part)
            
            fd = redirect_match.group(1) if redirect_match.group(1) else '1'
            append = redirect_match.group(2) == ">>"
        else:
            command_with_args = shlex.split(line)
            output_file = None
            fd = "1"
            append = False

        if not command_with_args:
            continue
        
        command = command_with_args[0]
        
        if shutil.which(command) is not None:
            run_executable(command, command_with_args[1:], output_file=output_file, fd=fd, append=append)
        elif command not in commands:
            print(f"{command}: command not found")
        else:
            execute_builtin(command, command_with_args[1:], output_file=output_file, fd=fd, append=append)
if __name__ == "__main__":
    main()
