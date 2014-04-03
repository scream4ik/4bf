.PHONY: requirements requirements-upgrade freeze run cloc clean

requirements:
	-@echo "### Installing requirements"
	-@pip install -r requirements.txt

requirements-upgrade:
	-@echo "### Upgrading requirements"
	-@pip freeze | cut -d = -f 1 | xargs pip install -U

freeze:
	-@echo "### Freezing python packages to requirements.txt"
	-@pip freeze > requirements.txt

run:
	@python main.py

cloc:
	-@echo "### Counting lines of code within the project"
	-@echo "# Total:" ; find . -iregex '.*\.py\|.*\.js\|.*\.html\|.*\.css' -type f -exec cat {} + | wc -l
	-@echo "# Python:" ; find . -name '*.py' -type f -exec cat {} + | wc -l
	-@echo "# JavaScript:" ; find . -name '*.js' -type f -exec cat {} + | wc -l
	-@echo "# HTML:" ; find . -name '*.html' -type f -exec cat {} + | wc -l
	-@echo "# CSS:" ; find . -name '*.css' -type f -exec cat {} + | wc -l

clean:
	-@echo "### Cleaning *.pyc files "
	-@find . -name '*.pyc' -exec rm -f {} \;
