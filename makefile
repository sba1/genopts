.PHONY: all
all: test

.PHONY: test
test:
	cat commit.genopts | ./genopts.py >test.c
	gcc -c test.c
