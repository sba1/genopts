.PHONY: all
all: test

.PHONY: test
test:
	cat commit.genopts | ./genopts.py >test_cli.c
	gcc test.c -o test
