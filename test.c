/* various definitions are inside a dedicated source file that will be included
 * before this file
 */
int main(int argc, char **argv)
{
	struct cli cli = {0};
	if (!parse_cli(argc, argv, &cli, POF_VALIDATE|POF_USAGE))
	{
		return cli.help?0:-1;
	}
	return 0;
}
