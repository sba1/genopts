GENOPTS=$(wildcard *genopts)

TEST_GENOPTS_SRCS=$(GENOPTS:%.genopts=test_%_cli.c)
TEST_GENOPTS=$(TEST_GENOPTS_SRCS:%.c=%)

.PHONY: all
all: type-check check test

.PHONY: type-check
type-check:
	mypy --py2 genopts.py

.PHONY: check
check:
	./genopts_tests.py

# Generate a cli source file for a genopts file
$(TEST_GENOPTS_SRCS): test_%_cli.c: %.genopts genopts.py
	cat $< | ./genopts.py >$@

# Generate a single executable for the given cli source file
$(TEST_GENOPTS): test_%_cli: test_%_cli.c
	gcc -ggdb -include $< test.c -o $@

# Generate a main executable that should be paramterized via all included
# genopts
.PHONY: test
test: $(TEST_GENOPTS)
	cat $(GENOPTS) | ./genopts.py >test_cli.c
	gcc -ggdb -include test_cli.c test.c -o test
