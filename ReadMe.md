[![Build Status](https://travis-ci.org/sba1/genopts.svg?branch=master)](https://travis-ci.org/sba1/genopts)

Introduction
============

This is a simple tool for generating command line interface
parser, with the current target language being C.

It is mainly developed for [SimpleGit](https://github.com/sba1/simplegit), a
simple git command replacement based on [libgit2](https://libgit2.github.com/)
with the main target platform being AmigaOS, but it may be useful for other
projects as well.

Usage
-----

Currently, ```genopts.py``` just acts on ```stdin``` and writes the result to
```stdout```. No options are supported.

First, create a file with the command template, for instance:

```
$ cat <<EOF >sync.genopts
sync [--fast] [-n | --dry-run] [<files>...]
EOF
```

Then pipe this file into the standard input of ```genopts.py``` and redirect
the output to a desired file.

```
$ < sync.getopts ./genopts >sync_cli.c
```

You get something like this:

```c
/**
 * Automatically generated file, please don't edit!
 */
#include <stdio.h>
#include <string.h>

struct cli
{
	int dry_run;
	int fast;
	char **files;
	int files_count;
	int help;
	int n;
	int sync;
};

struct cli_aux
{
	int dry_run_cmd;
	int fast_cmd;
	int help_cmd;
	int n_cmd;
	int sync_pos;
	int variadic_argc;
	char **variadic_argv;
};

typedef enum
{
	POF_VALIDATE = (1<<0),
	POF_USAGE = (1<<1)
} parse_cli_options_t;

static int validate_cli(struct cli *cli, struct cli_aux *aux)
{
	if (cli->help)
	{
		return 1;
	}
	if (aux->fast_cmd != 0 && aux->fast_cmd != 2)
	{
		fprintf(stderr, "Option --fast may be given only for the \"sync\" command\n");
		return 0;
	}
	if (aux->n_cmd != 0 && aux->n_cmd != 2)
	{
		fprintf(stderr, "Option -n may be given only for the \"sync\" command\n");
		return 0;
	}
	if (aux->dry_run_cmd != 0 && aux->dry_run_cmd != 2)
	{
		fprintf(stderr, "Option --dry-run may be given only for the \"sync\" command\n");
		return 0;
	}
	if ((!!cli->n + !!cli->dry_run) > (1))
	{
		fprintf(stderr, "Only one of -n or --dry-run may be given\n");
		return 0;
	}
	if (cli->sync)
	{
		cli->files_count = aux->variadic_argc;
		cli->files = aux->variadic_argv;
	}
	else
	{
		fprintf(stderr, "Please specify a proper command. Use --help for usage.\n");
		return 0;
	}
	return 1;
}

/**
 *
 * Print usage for the given cli.
 *
 * @return 1 if usage has been printed, 0 otherwise.
 *
 */
static int usage_cli(char *cmd, struct cli *cli)
{
	if (!cli->help)
	{
		return 0;
	}
	fprintf(stderr, "usage: %s <command> [<options>]\n", cmd);
	fprintf(stderr, "sync [--fast] [-n | --dry-run] [<files>...]\n");
	return 1;
}

static int parse_cli_simple(int argc, char **argv, struct cli *cli, struct cli_aux *aux)
{
	int i;
	int cur_position = 0;
	int cur_command = -1;
	for (i=0; i < argc; i++)
	{
		if (!strcmp(argv[i], "--dry-run"))
		{
			cli->dry_run = 1;
			aux->dry_run_cmd = cur_command;
		}
		else if (!strcmp(argv[i], "--fast"))
		{
			cli->fast = 1;
			aux->fast_cmd = cur_command;
		}
		else if (!strcmp(argv[i], "--help"))
		{
			cli->help = 1;
			aux->help_cmd = cur_command;
		}
		else if (!strcmp(argv[i], "-n"))
		{
			cli->n = 1;
			aux->n_cmd = cur_command;
		}
		else if (!strcmp(argv[i], "sync"))
		{
			cli->sync = 1;
			aux->sync_pos = i;
			cur_command = 2;
		}
		else if (cur_position == 0 && cur_command == 2)
		{
			aux->variadic_argv = &argv[i];
			aux->variadic_argc = (argc) - (i);
			break;
		}
		else
		{
			fprintf(stderr, "Unknown command or option \"%s\"\n", argv[i]);
			return 0;
		}
	}
	return 1;
}

/**
 *
 * Parse the given arguments and fill the struct cli accordingly.
 *
 * @param argc as in main()
 * @param argv as in main()
 * @param cli the filled struct
 * @param opts some options to modify the behaviour of the function.
 * @return 1 if parsing was successful, 0 otherwise.
 *
 */
static int parse_cli(int argc, char **argv, struct cli *cli, parse_cli_options_t opts)
{
	struct cli_aux aux = {0};
	char *cmd = argv[0];
	argc--;
	argv++;
	if (!parse_cli_simple(argc, argv, cli, &aux))
	{
		return 0;
	}
	if (opts & POF_VALIDATE)
	{
		if (!validate_cli(cli, &aux))
		{
			return 0;
		}
	}
	if (opts & POF_USAGE)
	{
		return !usage_cli(cmd, cli);
	}
	return 1;
}

```
