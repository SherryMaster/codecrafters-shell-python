import sys
import os
import subprocess
import shutil
import shlex
import re

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

def run_executable(command, args, output_file=None, fd="1"):
    """Run the given command as an executable."""
    try:
        if output_file:
            redirect_output(command, args, output_file, fd=fd)
        else:
            result = subprocess.run([command, *args])
    except Exception as e:
        print(f"{command}: {e}")

def redirect_output(command, args, output_file, fd="1"):
    """Run the command and redirect its output to the specified file."""
    with open(output_file, 'w') as f:
        if fd == "1":
            result = subprocess.run([command, *args], stdout=f)
        elif fd == "2":
            result = subprocess.run([command, *args], stderr=f)

def execute_builtin(command, args, output_file=None, fd="1"):
    """Execute a built-in command with optional output redirection."""
    if output_file:
        # Redirect stdout or stderr to file
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        with open(output_file, 'w') as f:
            if fd == "1":
                sys.stdout = f
            elif fd == "2":
                sys.stderr = f
            commands[command](*args)
            sys.stdout = original_stdout
            sys.stderr = original_stderr
    else:
        commands[command](*args)

commands = {
    "exit": exit_command,
    "echo": echo_command,
    "type": type_command,
    "pwd": pwd_command,
    "cd": cd_command,
}

def main():
    while True:
        sys.stdout.write("$ ")

        line = input()
        if not line:
            continue
        
        # Match file descriptor (optional digit) followed by >
        redirect_match = re.search(r'\s*(\d*)>\s*', line)
        
        if redirect_match:
            command_part = line[:redirect_match.start()].strip()
            output_file = line[redirect_match.end():].strip()
            command_with_args = shlex.split(command_part)
            
            fd = redirect_match.group(1) if redirect_match.group(1) else '1'
        else:
            command_with_args = shlex.split(line)
            output_file = None
            fd = "1" 

        if not command_with_args:
            continue
        
        command = command_with_args[0]
        
        if shutil.which(command) is not None:
            run_executable(command, command_with_args[1:], output_file=output_file, fd=fd)
        elif command not in commands:
            print(f"{command}: command not found")
        else:
            execute_builtin(command, command_with_args[1:], output_file=output_file, fd=fd)

if __name__ == "__main__":
    main()
