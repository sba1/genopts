GENOPTS=$(wildcard *genopts)

TEST_GENOPTS_SRCS=$(GENOPTS:%.genopts=test_%_cli.c)
TEST_GENOPTS=$(TEST_GENOPTS_SRCS:%.c=%)

.PHONY: all
all: type-check check test

.PHONY: type-check
type-check:
	mypy --py2 *.py

.PHONY: check
check:
	./genopts_tests.py

# Generate a cli source file for a genopts file
$(TEST_GENOPTS_SRCS): test_%_cli.c: %.genopts genopts.py
	cat $< | ./genopts.py >$@

# Generate a single executable for the given cli source file
$(TEST_GENOPTS): test_%_cli: test_%_cli.c test.c
	gcc -ggdb -include $< test.c -o $@

# Generate a main executable that should be paramterized via all included
# genopts
test: test.c $(TEST_GENOPTS)
	cat $(GENOPTS) | ./genopts.py >test_cli.c
	gcc -ggdb -include test_cli.c test.c -o test

.PHONY: clean
clean:
	rm -f $(TEST_GENOPTS_SRCS)
	rm -f $(TEST_GENOPTS)
	rm -f test_cli.c
	rm -f test

sync_cli.c: sync.genopts genopts.py
	cat sync.genopts | ./genopts.py >sync_cli.c

ReadMe.md.new: ReadMe.md sync_cli.c update_readme.py
	./update_readme.py

ReadMe.md: ReadMe.md.new
	cp ReadMe.md.new ReadMe.md

# Target whether to check whether ReadMe.md is current
.PHONY: readme-check
readme-check: ReadMe.md.new
	cmp ReadMe.md ReadMe.md.new
