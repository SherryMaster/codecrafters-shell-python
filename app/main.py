import sys
import os
import subprocess
import shutil
import shlex

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

def run_executable(command, args):
    """Run the given command as an executable."""
    try:
        result = subprocess.run([command, *args])
    except Exception as e:
        print(f"{command}: {e}")


commands = {
    "exit": exit_command,
    "echo": echo_command,
    "type": type_command,
    "pwd": pwd_command,
    "cd": cd_command,
}

def main():
    while True:
        try:
            user_input = input("$ ")
            if not user_input.strip():
                continue
            parts = shlex.split(user_input)
            command = parts[0]
            args = parts[1:]

            if command in commands:
                commands[command](*args)
            else:
                run_executable(command, args)
        except EOFError:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
