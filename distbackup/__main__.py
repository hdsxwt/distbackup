"""Allow running as: python -m distbackup [gui|cli ...]"""

import sys


def main():
	if len(sys.argv) > 1 and sys.argv[1] == "cli":
		from distbackup.cli import main as cli_main
		sys.argv.pop(1)
		cli_main()
	else:
		from distbackup.gui import main as gui_main
		gui_main()


if __name__ == "__main__":
	main()
