.PHONY: all
all: test

.PHONY: test
test:
	./genopts.py >test.c
	gcc -c test.c
