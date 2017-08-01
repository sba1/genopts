GENOPTS=$(wildcard *genopts)

.PHONY: all
all: check test

.PHONY: type-check
type-check:
	mypy --py2 genopts.py

.PHONY: check
check:
	./genopts_tests.py

.PHONY: test
test:
	cat $(GENOPTS) | ./genopts.py >test_cli.c
	gcc -ggdb test.c -o test
