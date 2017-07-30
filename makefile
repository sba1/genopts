GENOPTS=$(wildcard *genopts)

.PHONY: all
all: check test

.PHONY: check
check:
	./genopts_tests.py

.PHONY: test
test:
	cat $(GENOPTS) | ./genopts.py >test_cli.c
	gcc -ggdb test.c -o test
