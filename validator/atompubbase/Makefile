MODULES = events model

default: doc 

.phony: test 
test:
	python runtests.py

.phony: doc
doc: 
	pydoc -w $(MODULES)
	mv *.html docs


