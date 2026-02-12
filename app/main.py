import sys
import os
import subprocess

def main():
    builtins = ["echo", "exit", "type", "pwd", "cd", "cat"]
    while True:
        sys.stdout.write("$ ") 
        command = input()
        if command.strip() == "exit":
            break
        elif command.split()[0] == "cd":
            _, *args = command.split()
            if not args:
                sys.stdout.write("cd: missing argument\n")
            else:
                if args[0] == "~":
                    args[0] = os.path.expanduser("~")
                try:
                    os.chdir(args[0])
                except FileNotFoundError:
                    sys.stdout.write(f"cd: {args[0]}: No such file or directory\n")
        elif command.split()[0] == "echo":
            if "\'" in command:
                command = command.replace("echo ", "", 1)
                string_splits = command.split("\'")
                final_string = "".join(string_splits)
                sys.stdout.write(final_string + "\n")
            else:
                _, *args = command.split()
                sys.stdout.write(" ".join(args) + "\n")
        elif command.split()[0] == "type":
            _, *args = command.split()
            for arg in args:
                if arg in builtins:
                    sys.stdout.write(f"{arg} is a shell builtin\n")
                else:
                    found = False
                    for path in os.getenv("PATH", "").split(os.pathsep):
                        if os.path.isfile(os.path.join(path, arg)) and os.access(os.path.join(path, arg), os.X_OK):
                            found = True
                            break
                    if found:
                        sys.stdout.write(f"{arg} is {os.path.join(path, arg)}\n")
                    else:
                        sys.stdout.write(f"{arg}: not found\n")
        elif command.split()[0] == "pwd":
            sys.stdout.write(os.getcwd() + "\n")
        elif command.split()[0] == "cat":
            subprocess.run(command, shell=True)
        else:
            found = False
            filename = command.split()[0]
            for path in os.getenv("PATH", "").split(os.pathsep):
                if os.path.isfile(os.path.join(path, filename)) and os.access(os.path.join(path, filename), os.X_OK):
                    found = True
                    break
            if found:
                subprocess.run(" ".join([filename] + command.split()[1:]), shell=True)
            else:
                sys.stdout.write(f"{command}: command not found\n")

if __name__ == "__main__":
    main()
