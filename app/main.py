import sys
import os

def main():
    builtins = ["echo", "exit", "type"]
    while True:
        sys.stdout.write("$ ") 
        command = input()
        if command.strip() == "exit":
            break
        elif command.split()[0] == "echo":
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
        else:
            sys.stdout.write(f"{command}: command not found\n")

if __name__ == "__main__":
    main()
