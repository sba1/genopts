GENOPTS=$(wildcard *genopts)

.PHONY: all
all: test

.PHONY: test
test:
	cat $(GENOPTS) | ./genopts.py >test_cli.c
	gcc test.c -o test
