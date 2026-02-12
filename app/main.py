import sys


def main():
    while True:
        sys.stdout.write("$ ") 
        command = input()
        if command.strip() == "exit":
            break
        elif command.split()[0] == "echo":
            _, *args = command.split()
            sys.stdout.write(" ".join(args) + "\n")
        else:
            sys.stdout.write(f"{command}: command not found\n")

if __name__ == "__main__":
    main()
