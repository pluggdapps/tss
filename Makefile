develop :
	rm -rf tss-env
	virtualenv tss-env --no-site-packages
	bash -c "source tss-env/bin/activate ; python ./setup.py develop"

bdist_egg :
	python ./setup.py bdist_egg

sdist :
	cp CHANGELOG docs/CHANGELOG
	cp LICENSE docs/LICENSE
	cp README docs/README
	cp ROADMAP docs/ROADMAP
	python ./setup.py sdist

upload : 
	cp CHANGELOG docs/CHANGELOG
	cp LICENSE docs/LICENSE
	cp README docs/README
	cp ROADMAP docs/ROADMAP
	python ./setup.py sdist register -r http://www.python.org/pypi upload -r http://www.python.org/pypi --show-response 
	
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
