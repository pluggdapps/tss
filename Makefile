develop :
	rm -rf tss-env
	virtualenv tss-env --no-site-packages
	bash -c "source tss-env/bin/activate ; python ./setup.py develop"

bdist_egg :
	python ./setup.py bdist_egg

sdist :
	python ./setup.py sdist

sphinx-doc :
	cp README.rst sphinxdoc/source/
	cp CHANGELOG.rst sphinxdoc/source/
	rm -rf sphinxdoc/build/html/
	make -C sphinxdoc html
	cd sphinxdoc/build/html; zip -r tss.sphinxdoc.zip ./

upload : 
	python ./setup.py sdist register -r http://www.python.org/pypi upload -r http://www.python.org/pypi --show-response 
	
pushcode: push-googlecode push-bitbucket push-github 

push-googlecode:
	hg push https://prataprc@code.google.com/p/tss/

push-bitbucket:
	hg push https://prataprc@bitbucket.org/prataprc/tss

push-github:
	hg bookmark -f -r default master
	hg push git+ssh://git@github.com:prataprc/tss.git

vimplugin :
	rm -rf ./vim-plugin/vim-tss.tar.gz
	cd ./vim-plugin; tar cvfz ./vim-tss.tar.gz *

cleanall : clean
	rm -rf tss-env

clean :
	rm -rf build;
	rm -rf dist;
	rm -rf tss.egg-info;
	rm -rf tss.egg-info/;
	rm -rf tss/test/samplecss/*.css
	rm -rf tss/test/samplecss/*.tss.py
	rm -rf tss/test/egtss/*.css
	rm -rf tss/test/egtss/*.tss.py
	rm -rf `find ./ -name parsetsstab.py`;
	rm -rf `find ./ -name "*.pyc"`;
	rm -rf `find ./ -name "yacctab.py"`;
	rm -rf `find ./ -name "lextab.py"`;
