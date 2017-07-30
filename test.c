#include "test_cli.c"

int main(int argc, char **argv)
{
	struct cli cli = {0};
	parse(argc-1, argv+1, &cli);
	if (!validate(&cli))
	{
		return -1;
	}
	return 0;
}
