.PHONY: all
all: test

.PHONY: test
test:
	cat commit.genopts | ./genopts.py >test_cli.c
	gcc -c test_cli.c
