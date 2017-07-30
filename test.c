#include "test_cli.c"

int main(int argc, char **argv)
{
	struct cli cli = {0};
	if (!parse_cli(argc-1, argv+1, &cli))
	{
		return -1;
	}
	if (!validate_cli(&cli))
	{
		return -1;
	}
	return 0;
}
