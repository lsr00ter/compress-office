# -*- coding: utf-8 -*-
from glob import glob
from os.path import abspath, exists, isfile, join
from shlex import quote
from subprocess import DEVNULL, PIPE, run
from sys import argv

from rich.console import Console

from function import compress, convert_size
from history import history

console = Console(highlighter=None)
exts = ("docx", "pptx", "xlsx")
# Using fd can significantly improve the search speed
use_fd = run("fd --version", shell=True, stdout=DEVNULL, stderr=DEVNULL).returncode == 0

if __name__ == "__main__":
    his = history("process_history.csv")
    his.clean_up()

    file_paths = []
    unchanged_files = 0

    # Collect files
    for arg in argv[1:]:
        if not exists(arg):
            console.print(f"Error: {arg} not found.", style="bold red")
            exit(-1)
        arg = abspath(arg)

        if isfile(arg):
            if arg.split(".")[-1] not in exts:
                console.print(
                    f"Error: {arg} is not a supported file.", style="bold red"
                )
                exit(-1)
            if not his.file_in_history(arg):
                file_paths.append(arg)
            else:
                unchanged_files += 1
        else:
            if use_fd:
                command = f"fd -ip . {quote(arg)}"
                for ext in exts:
                    command += f" -e {ext}"
                res = run(
                    command,
                    shell=True,
                    stdout=PIPE,
                )
                res.check_returncode()
                for file_path in res.stdout.decode().splitlines():
                    if not his.file_in_history(file_path):
                        file_paths.append(file_path)
                    else:
                        unchanged_files += 1
            else:
                for ext in exts:
                    for file_path in glob(join(arg, "**", f"*.{ext}"), recursive=True):
                        if not his.file_in_history(file_path):
                            file_paths.append(file_path)
                        else:
                            unchanged_files += 1

    file_cnt = len(file_paths)
    console.print(
        f"Found {file_cnt} file(s) to compress and {unchanged_files} file(s) skipped.",
        style="bold",
    )

    if file_cnt == 0:
        exit()

    # Compress files
    before_size_sum = 0
    after_size_sum = 0

    try:
        for i, file_path in enumerate(file_paths, start=1):
            print(f"[{i}/{file_cnt}] Processing {file_path}")
            result = compress(file_path)
            his.add_history(file_path)
            before_size_sum += result[0]
            after_size_sum += result[1]
    except Exception as e:
        print(e)
    finally:
        if before_size_sum == 0:
            exit()

        # Print result
        console.print(
            f"Total compressed {convert_size(before_size_sum - after_size_sum)}",
            style="bold green",
        )
        console.print(
            f"Compression rate {round(100 * (before_size_sum - after_size_sum) / before_size_sum, 2)}%",
            style="bold green",
        )
